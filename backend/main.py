from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys

# Ensure backend directory is in sys.path so imports work regardless of execution directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from agent import ask_f1_agent
from dotenv import load_dotenv
import subprocess
import requests
import base64

# Load environment variables (like GEMINI_API_KEY, GROQ_API_KEY) from .env file
load_dotenv()

app = FastAPI(title="F1 AI Assistant API")

# Allow CORS so our frontend can communicate with the FastAPI backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    query: str
    history: list[Message] = []

@app.post("/api/chat")
async def chat(request: QueryRequest):
    """Endpoint to interact with the F1 AI Agent."""
    history_dicts = [{"role": m.role, "content": m.content} for m in request.history]
    answer = ask_f1_agent(request.query, history_dicts)
    return {"response": answer}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# Serve static files from the frontend directory
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if not os.path.exists(frontend_dir):
    os.makedirs(frontend_dir)

# 1x1 transparent PNG bytes for placeholder response
TRANSPARENT_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")

@app.get("/static/graphs/{filename}")
async def get_graph(filename: str):
    """Route to serve graph files or a transparent placeholder if the file does not exist, preventing terminal 404 errors."""
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

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_dir, "index.html"))
