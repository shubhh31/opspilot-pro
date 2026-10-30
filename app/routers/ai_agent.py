from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task
from app.services.ai_service import get_copilot_response, generate_workflow_summary
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter(prefix="/api/copilot", tags=["AI Copilot"])

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] # list of {"role": "user"|"assistant", "text": "..."}

@router.post("/chat")
def chat_with_copilot(req: ChatRequest, db: Session = Depends(get_db)):
    """
    RAG-enabled AI Chat endpoint. Takes current conversation history, retrieves 
    live SAP tasks from database, and queries Gemini (or fallback model) for answers.
    """
    # Retrieve all live tasks to provide context to the AI model
    tasks = db.query(Task).all()
    
    reply = get_copilot_response(req.history, req.message, tasks)
    
    return {"reply": reply}

@router.get("/summary")
def get_management_summary(db: Session = Depends(get_db)):
    """
    Generate an AI executive workflow bottleneck report based on live system tasks.
    """
    tasks = db.query(Task).all()
    
    summary = generate_workflow_summary(tasks)
    
    return {"summary": summary}
