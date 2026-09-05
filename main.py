from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict
import datetime

from services.classroom_service import fetch_tasks, get_announcements_and_alerts
from services.ai_service import ask_copilot
from db.database import get_all_task_states, update_task_status, update_task_notes

app = FastAPI(title="Classroom Task Manager")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class TaskToggleRequest(BaseModel):
    status: str

class ChatMessage(BaseModel):
    role: str
    content: str

class TaskNotesRequest(BaseModel):
    notes: str

class CopilotRequest(BaseModel):
    provider: str
    task_context: Dict[str, Optional[str]]
    messages: List[ChatMessage]

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

@app.get("/api/tasks")
async def api_get_tasks():
    classroom_tasks = fetch_tasks()
    if classroom_tasks is None:
        # User needs to authenticate
        raise HTTPException(status_code=401, detail="Authentication required")

    local_states = get_all_task_states()

    tasks_with_dates = []
    tasks_without_dates = []

    for task in classroom_tasks:
        task_id = task["id"]
        local_state = local_states.get(task_id, {"status": "pending", "notes": ""})
        task["status"] = local_state["status"]
        task["notes"] = local_state["notes"]

        if task["due_date"]:
            tasks_with_dates.append(task)
        else:
            tasks_without_dates.append(task)

    # Sort tasks with dates chronologically
    tasks_with_dates.sort(key=lambda x: x["due_date"])

    return {
        "tasks_with_dates": tasks_with_dates,
        "tasks_without_dates": tasks_without_dates
    }

@app.get("/api/announcements")
async def api_announcements():
    try:
        alerts = get_announcements_and_alerts()
        return {"announcements": alerts}
    except Exception:
        return {"announcements": []}
    
@app.post("/api/tasks/{task_id}/toggle")
async def toggle_task(task_id: str, request: TaskToggleRequest):
    if request.status not in ["pending", "done"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    update_task_status(task_id, request.status)
    return {"status": "success"}

@app.post("/api/tasks/{task_id}/notes")
async def update_notes(task_id: str, request: TaskNotesRequest):
    update_task_notes(task_id, request.notes)
    return {"status": "success"}

@app.post("/api/copilot/ask")
async def api_copilot_ask(request: CopilotRequest):
    try:
        # System prompt with task context
        system_prompt = f"""
You are a helpful and experienced teaching assistant and tutor.
You are helping a student with the following assignment:
Course: {request.task_context.get('course_name', 'Unknown')}
Title: {request.task_context.get('title', 'Unknown')}
Description: {request.task_context.get('description', 'No description')}
Due Date: {request.task_context.get('due_date', 'No due date')}

Please provide helpful guidance, explain concepts clearly, and assist the student with understanding the assignment. Do not just give out direct answers, but help them learn.
        """

        messages = [{"role": "system", "content": system_prompt}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        response_text = await ask_copilot(request.provider, messages)
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
