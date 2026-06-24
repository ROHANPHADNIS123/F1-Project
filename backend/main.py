from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent import ask_f1_agent
from dotenv import load_dotenv
import os

# Load environment variables (like GEMINI_API_KEY) from .env file
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

class QueryRequest(BaseModel):
    query: str

@app.post("/api/chat")
async def chat(request: QueryRequest):
    """Endpoint to interact with the F1 AI Agent."""
    answer = ask_f1_agent(request.query)
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
