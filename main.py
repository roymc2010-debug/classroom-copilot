import os
import json
import uuid
import urllib.request
import urllib.parse
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

try:
    from services.classroom_service import fetch_tasks, get_announcements_and_alerts
except ImportError:
    from classroom_service import fetch_tasks, get_announcements_and_alerts

from services.ai_service import ask_copilot

user_sessions = {}

SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.me.readonly',
    'https://www.googleapis.com/auth/classroom.student-submissions.me.readonly',
    'https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly',
    'https://www.googleapis.com/auth/classroom.announcements.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def load_client_secrets():
    with open('credentials.json', 'r') as f:
        data = json.load(f)
        cfg = data.get('web') or data.get('installed') or {}
        return cfg.get('client_id'), cfg.get('client_secret')

def restore_and_refresh_credentials(creds_json: str):
    if not creds_json:
        return None
    try:
        data = json.loads(creds_json)
        creds = Credentials.from_authorized_user_info(data, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest())
            except Exception as e:
                print(f"No se pudo refrescar el token: {e}")
        return creds
    except Exception as e:
        print(f"Error restaurando credenciales: {e}")
        return None

app = FastAPI(title="Agora")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/auth/login")
async def auth_login(request: Request):
    client_id, _ = load_client_secrets()
    base = str(request.base_url).rstrip('/')
    redirect_uri = "https://agora-app-leox.onrender.com/auth/callback" if "onrender.com" in base else f"{base}/auth/callback"
    
    scopes_str = "%20".join(SCOPES)
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"response_type=code&"
        f"scope={scopes_str}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, error: str = None):
    if error or not code:
        print(f"Error de Google OAuth: {error}")
        return RedirectResponse(url="/")

    client_id, client_secret = load_client_secrets()
    base = str(request.base_url).rstrip('/')
    redirect_uri = "https://agora-app-leox.onrender.com/auth/callback" if "onrender.com" in base else f"{base}/auth/callback"

    try:
        token_url = "https://oauth2.googleapis.com/token"
        payload = urllib.parse.urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }).encode("utf-8")

        req = urllib.request.Request(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))

        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )

        session_id = str(uuid.uuid4())
        user_sessions[session_id] = creds.to_json()

        try:
            with open("token.json", "w") as f:
                f.write(creds.to_json())
        except Exception:
            pass

        print(f"Autenticacion completada con exito en Render: {session_id}")

        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="agora_session",
            value=session_id,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        return response
    except Exception as e:
        print(f"Error en canje directo de token: {e}")
        traceback.print_exc()
        return RedirectResponse(url="/", status_code=303)

@app.get("/auth/logout")
async def auth_logout(request: Request):
    session_id = request.cookies.get("agora_session")
    if session_id in user_sessions:
        del user_sessions[session_id]
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("agora_session")
    return response

@app.get("/api/tasks")
async def get_tasks(request: Request):
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json)

    if not creds:
        if os.path.exists('token.json'):
            try:
                creds = restore_and_refresh_credentials(open('token.json').read())
            except Exception:
                creds = None

    if not creds:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    try:
        try:
            tasks = fetch_tasks(creds=creds)
        except TypeError:
            tasks = fetch_tasks()

        tasks_with_dates = [t for t in tasks if t.get('due_date')]
        tasks_without_dates = [t for t in tasks if not t.get('due_date')]
        return {
            "tasks_with_dates": tasks_with_dates,
            "tasks_without_dates": tasks_without_dates
        }
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/announcements")
async def api_announcements(request: Request):
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json)

    try:
        try:
            alerts = get_announcements_and_alerts(creds=creds)
        except TypeError:
            alerts = get_announcements_and_alerts()
        return {"announcements": alerts}
    except Exception:
        return {"announcements": []}

@app.post("/api/copilot/ask")
async def ask_ai(request: Request):
    data = await request.json()
    provider = data.get("provider", "gemini")
    mentor = data.get("mentor", "newton")
    task_context = data.get("task_context", {})
    messages = data.get("messages", [])

    response_text = ask_copilot(
        provider=provider,
        mentor=mentor,
        task_context=task_context,
        messages=messages
    )
    return {"response": response_text}
