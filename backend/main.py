from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent import ask_f1_agent
from dotenv import load_dotenv
import os
import subprocess
import requests

# Load environment variables (like GEMINI_API_KEY) from .env file
load_dotenv()

def check_and_start_ollama():
    ollama_url = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=1)
        if resp.status_code == 200:
            print("Ollama server is already running.")
            return
    except Exception:
        pass
        
    # Ollama is not running. Let's see if we can start it.
    ollama_exe = "E:\\Ollama\\ollama.exe"
    if os.path.exists(ollama_exe):
        print(f"Ollama is not running. Attempting to start it from {ollama_exe}...")
        env = os.environ.copy()
        env["OLLAMA_MODELS"] = "E:\\Ollama\\models"
        try:
            # Start as a detached background process on Windows
            subprocess.Popen(
                [ollama_exe, "serve"],
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("Ollama server start command issued.")
        except Exception as e:
            print(f"Failed to auto-start Ollama: {e}")
    else:
        print(f"Ollama executable not found at {ollama_exe}. Skip auto-start.")

app = FastAPI(title="F1 AI Assistant API")

@app.on_event("startup")
async def startup_event():
    check_and_start_ollama()

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
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_dir, "index.html"))
