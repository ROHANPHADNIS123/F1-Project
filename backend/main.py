from fastapi import FastAPI, Response, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
import sys
import threading
import uuid
import time

# Ensure backend directory is in sys.path so imports work regardless of execution directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from agent import ask_f1_agent
from dotenv import load_dotenv
import subprocess
import requests
import base64

# Import database methods
from database import (
    init_db,
    create_user,
    verify_user_credentials,
    create_session,
    verify_session,
    delete_session,
    create_chat,
    get_user_chats,
    delete_chat,
    update_chat_label,
    add_message,
    get_chat_messages,
    # Admin helpers
    ensure_admin_exists,
    get_all_users,
    get_user_by_id,
    admin_update_username,
    admin_update_password,
    admin_delete_user,
    admin_toggle_admin,
)

# Load environment variables (like GEMINI_API_KEY, GROQ_API_KEY) from .env file
load_dotenv()

# ── Admin credentials (change these!) ────────────────────────────────────────
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "F1Admin@2024!")

app = FastAPI(title="F1 AI Assistant API")

# Initialize database on startup and seed admin account
@app.on_event("startup")
async def startup_event():
    init_db()
    ensure_admin_exists(ADMIN_USERNAME, ADMIN_PASSWORD)

# Allow CORS so our frontend can communicate with the FastAPI backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth Dependencies ─────────────────────────────────────────────────────────

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
    token = authorization.split(" ")[1]
    user = verify_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return user

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str

class ChatCreateRequest(BaseModel):
    id: str
    label: str

class ChatQueryRequest(BaseModel):
    chat_id: str
    query: str

class UpdateUsernameRequest(BaseModel):
    new_username: str

class UpdatePasswordRequest(BaseModel):
    new_password: str

class ToggleAdminRequest(BaseModel):
    is_admin: bool

# ── Auth Routes ───────────────────────────────────────────────────────────────

@app.post("/api/auth/register")
async def register(req: AuthRequest):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if len(req.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
    success = create_user(req.username, req.password)
    if not success:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"message": "Registration successful"}

@app.post("/api/auth/login")
async def login(req: AuthRequest):
    user = verify_user_credentials(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(user['id'])
    return {"token": token, "username": user['username'], "is_admin": bool(user['is_admin'])}

@app.post("/api/auth/logout")
async def logout(authorization: str = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        delete_session(token)
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Returns the currently authenticated user's profile — used by the frontend to recover username."""
    return {"username": current_user["username"], "is_admin": current_user["is_admin"]}

# ── Chat Session Routes ───────────────────────────────────────────────────────

@app.get("/api/chats")
async def list_chats(current_user: dict = Depends(get_current_user)):
    return get_user_chats(current_user['id'])

@app.post("/api/chats")
async def create_chat_session(req: ChatCreateRequest, current_user: dict = Depends(get_current_user)):
    success = create_chat(current_user['id'], req.id, req.label)
    if not success:
        raise HTTPException(status_code=400, detail="Chat ID already exists")
    return {"id": req.id, "label": req.label}

@app.delete("/api/chats/{chat_id}")
async def remove_chat_session(chat_id: str, current_user: dict = Depends(get_current_user)):
    delete_chat(current_user['id'], chat_id)
    return {"message": "Chat deleted"}

@app.get("/api/chats/{chat_id}/messages")
async def list_chat_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    user_chats = get_user_chats(current_user['id'])
    chat_ids = [c['id'] for c in user_chats]
    if chat_id not in chat_ids:
        raise HTTPException(status_code=404, detail="Chat not found")
    return get_chat_messages(chat_id)

@app.post("/api/chat")
async def chat(req: ChatQueryRequest, current_user: dict = Depends(get_current_user)):
    user_chats = get_user_chats(current_user['id'])
    chat_ids = [c['id'] for c in user_chats]
    
    if req.chat_id not in chat_ids:
        create_chat(current_user['id'], req.chat_id, "New Chat")
        
    history_list = get_chat_messages(req.chat_id)
    answer = ask_f1_agent(req.query, history_list)
    
    # Detect Groq rate-limit / token exhaustion sentinel
    if answer == "__GROQ_RATE_LIMIT__":
        raise HTTPException(status_code=429, detail="groq_rate_limit")
        
    add_message(req.chat_id, "user", req.query)
    add_message(req.chat_id, "assistant", answer)
    
    user_msgs_count = sum(1 for m in history_list if m['role'] == 'user')
    if user_msgs_count == 0:
        label = req.query[:25] + "..." if len(req.query) > 25 else req.query
        update_chat_label(current_user['id'], req.chat_id, label)
        
    return {"response": answer}

# ── Admin Routes ──────────────────────────────────────────────────────────────

@app.get("/api/admin/users")
async def admin_list_users(admin: dict = Depends(get_admin_user)):
    return get_all_users()

@app.patch("/api/admin/users/{user_id}/username")
async def admin_change_username(
    user_id: int,
    req: UpdateUsernameRequest,
    admin: dict = Depends(get_admin_user)
):
    if len(req.new_username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    success = admin_update_username(user_id, req.new_username)
    if not success:
        raise HTTPException(status_code=400, detail="Username already taken or user not found")
    return {"message": "Username updated"}

@app.patch("/api/admin/users/{user_id}/password")
async def admin_change_password(
    user_id: int,
    req: UpdatePasswordRequest,
    admin: dict = Depends(get_admin_user)
):
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    success = admin_update_password(user_id, req.new_password)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Password updated"}

@app.patch("/api/admin/users/{user_id}/role")
async def admin_change_role(
    user_id: int,
    req: ToggleAdminRequest,
    admin: dict = Depends(get_admin_user)
):
    # Prevent removing your own admin
    if user_id == admin['id'] and not req.is_admin:
        raise HTTPException(status_code=400, detail="Cannot remove your own admin privileges")
    success = admin_toggle_admin(user_id, req.is_admin)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Role updated"}

@app.delete("/api/admin/users/{user_id}")
async def admin_remove_user(user_id: int, admin: dict = Depends(get_admin_user)):
    if user_id == admin['id']:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    success = admin_delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# ── Static Files & Frontend ───────────────────────────────────────────────────

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if not os.path.exists(frontend_dir):
    os.makedirs(frontend_dir)

# 1x1 transparent PNG bytes for placeholder response
TRANSPARENT_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")

@app.get("/static/graphs/{filename}")
async def get_graph(filename: str):
    """Route to serve graph files or a transparent placeholder if the file does not exist."""
    filepath = os.path.join(frontend_dir, "graphs", filename)
    if os.path.exists(filepath):
        return FileResponse(filepath)
    else:
        if filename.endswith(".svg"):
            empty_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"></svg>'
            return Response(content=empty_svg, media_type="image/svg+xml")
        else:
            return Response(content=TRANSPARENT_PNG, media_type="image/png")

app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/admin")
async def admin_panel():
    admin_path = os.path.join(frontend_dir, "admin.html")
    response = FileResponse(admin_path)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

@app.get("/")
async def root():
    response = FileResponse(os.path.join(frontend_dir, "index.html"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
