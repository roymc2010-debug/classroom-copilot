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

from services.classroom_service import fetch_tasks, fetch_courses, get_announcements_and_alerts
from services.ai_service import ask_copilot

# Persistencia de sesiones en disco para mantener logins entre reinicios de Render
SESSIONS_FILE = "sessions.json"
user_sessions = {}

if os.path.exists(SESSIONS_FILE):
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            user_sessions = json.load(f)
    except Exception as e:
        print(f"Error cargando sessions.json: {e}")
        user_sessions = {}

def save_sessions():
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_sessions, f)
    except Exception as e:
        print(f"No se pudo persistir sessions.json: {e}")

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
    # 1. Prioridad: Variables de entorno (ideal para despliegue seguro en Render)
    env_client_id = os.getenv("GOOGLE_CLIENT_ID")
    env_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if env_client_id and env_client_secret:
        return env_client_id.strip(), env_client_secret.strip()

    # 2. Respaldo: Archivo físico credentials.json (para desarrollo local)
    if os.path.exists('credentials.json'):
        try:
            with open('credentials.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                cfg = data.get('web') or data.get('installed') or {}
                return cfg.get('client_id'), cfg.get('client_secret')
        except Exception as e:
            print(f"Error leyendo credentials.json: {e}")

    return None, None

def get_redirect_uri(request: Request):
    # Permite especificar una URL de callback fija mediante variable de entorno
    env_redirect = os.getenv("GOOGLE_REDIRECT_URI")
    if env_redirect:
        return env_redirect.strip()

    base = str(request.base_url).rstrip('/')
    if "onrender.com" in base:
        return "https://agora-app-leox.onrender.com/auth/callback"
    return f"{base}/auth/callback"

def restore_and_refresh_credentials(creds_json: str, session_id: str = None):
    if not creds_json:
        return None
    try:
        data = json.loads(creds_json)
        creds = Credentials.from_authorized_user_info(data, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest())
                if session_id and session_id in user_sessions:
                    user_sessions[session_id] = creds.to_json()
                    save_sessions()
            except Exception as e:
                print(f"No se pudo refrescar el token de Google: {e}")
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
@app.get("/login")
async def auth_login(request: Request):
    client_id, _ = load_client_secrets()
    if not client_id:
        return HTMLResponse(
            "<h2>Error de Configuración</h2><p>No se encontró GOOGLE_CLIENT_ID ni archivo credentials.json.</p>",
            status_code=500
        )

    redirect_uri = get_redirect_uri(request)
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
        print(f"Error o cancelación de Google OAuth: {error}")
        return RedirectResponse(url="/")

    client_id, client_secret = load_client_secrets()
    if not client_id or not client_secret:
        return RedirectResponse(url="/?error=oauth_config_missing")

    redirect_uri = get_redirect_uri(request)

    try:
        token_url = "https://oauth2.googleapis.com/token"
        payload = urllib.parse.urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }).encode("utf-8")

        req = urllib.request.Request(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
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
        save_sessions()

        print(f"Autenticacion completada con exito para sesion: {session_id}")

        is_https = "https" in redirect_uri
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="agora_session",
            value=session_id,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax",
            secure=is_https
        )
        return response
    except Exception as e:
        print(f"Error en canje de token: {e}")
        traceback.print_exc()
        return RedirectResponse(url="/?error=token_exchange_failed", status_code=303)

@app.get("/auth/logout")
@app.get("/logout")
async def auth_logout(request: Request):
    """
    Cierre de sesión total para el usuario activo: borra la cookie e invalida la sesión.
    """
    session_id = request.cookies.get("agora_session")
    if session_id and session_id in user_sessions:
        del user_sessions[session_id]
        save_sessions()

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("agora_session", path="/")
    return response

@app.get("/api/courses")
async def get_courses(request: Request):
    """
    Devuelve las materias inscritas del usuario autenticado para la barra lateral.
    """
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)

    if not creds:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    try:
        courses = fetch_courses(creds=creds)
        return {"courses": courses}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/tasks")
async def get_tasks(request: Request):
    """
    Devuelve las tareas y misiones exclusivas del usuario autenticado.
    """
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)

    if not creds:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    try:
        tasks = fetch_tasks(creds=creds)
        try:
            from db.database import get_all_task_states
            states = get_all_task_states()
            for t in tasks:
                t_id = str(t.get('id'))
                if t_id in states:
                    t['status'] = states[t_id].get('status', 'pending')
                    t['notes'] = states[t_id].get('notes', '')
        except Exception:
            pass

        tasks_with_dates = [t for t in tasks if t.get('due_date')]
        tasks_without_dates = [t for t in tasks if not t.get('due_date')]
        return {
            "tasks_with_dates": tasks_with_dates,
            "tasks_without_dates": tasks_without_dates
        }
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/tasks/{task_id}/toggle")
async def toggle_task_status(task_id: str, request: Request):
    data = await request.json()
    status = data.get("status", "pending")
    try:
        from db.database import update_task_status
        update_task_status(task_id, status)
        return {"ok": True, "status": status}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/tasks/{task_id}/notes")
async def save_task_notes(task_id: str, request: Request):
    data = await request.json()
    notes = data.get("notes", "")
    try:
        from db.database import update_task_notes
        update_task_notes(task_id, notes)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/announcements")
async def api_announcements(request: Request):
    """
    Devuelve avisos de Classroom y Gmail del usuario autenticado.
    """
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)

    if not creds:
        return {"announcements": []}

    try:
        alerts = get_announcements_and_alerts(creds=creds)
        return {"announcements": alerts}
    except Exception as e:
        print(f"Error obteniendo avisos: {e}")
        return {"announcements": []}

@app.post("/api/copilot/ask")
async def ask_ai(request: Request):
    """
    Copiloto Ignis: Asesoría académica sobria con andamiaje y selección de mentor.
    """
    data = await request.json()
    provider = data.get("provider", "openrouter")
    mentor = data.get("mentor", "auto")
    task_context = data.get("task_context", {})
    messages = data.get("messages", [])

    response_text = await ask_copilot(
        provider=provider,
        mentor=mentor,
        task_context=task_context,
        messages=messages
    )
    return {"response": response_text}

@app.post("/api/socrates/exam")
async def socrates_exam(request: Request):
    """
    Simulador Socrático de Exámenes Departamentales Universales.
    Soporta modalidades: 'teorico', 'practico' e 'hibrido'.
    """
    data = await request.json()
    provider = data.get("provider", "openrouter")
    course_name = data.get("course_name", "Materia Universitaria")
    mode = data.get("mode", "hibrido")
    messages = data.get("messages", [])

    task_context = {
        "course_name": course_name,
        "title": f"Examen Departamental ({mode.upper()})",
        "description": f"Simulación de evaluación oral bajo modalidad {mode}. Evalúa al estudiante con rigor sobre los temas de {course_name}."
    }

    response_text = await ask_copilot(
        provider=provider,
        mentor="socrates",
        task_context=task_context,
        messages=messages
    )
    return {"response": response_text}
