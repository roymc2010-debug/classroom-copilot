import os
import json
import uuid
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from services.classroom_service import fetch_tasks, get_announcements_and_alerts
from services.ai_service import ask_copilot

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

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

def get_oauth_flow(redirect_uri: str):
    try:
        return Flow.from_client_secrets_file(
            'credentials.json',
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            autogenerate_code_verifier=False
        )
    except TypeError:
        return Flow.from_client_secrets_file(
            'credentials.json',
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

app = FastAPI(title="Ágora")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# -------------------------------------------------------------
# RUTAS DE AUTENTICACIÓN GOOGLE CON PKCE CONTROLADO
# -------------------------------------------------------------
@app.get("/auth/login")
async def auth_login(request: Request):
    base = str(request.base_url).rstrip('/')
    if "onrender.com" in base:
        redirect_uri = "https://agora-app-leox.onrender.com/auth/callback"
    else:
        redirect_uri = f"{base}/auth/callback"
    
    flow = get_oauth_flow(redirect_uri)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    verifier = getattr(flow, 'code_verifier', None)
    response = RedirectResponse(authorization_url)
    if verifier:
        response.set_cookie(key="agora_oauth_verifier", value=verifier, max_age=600, httponly=True, samesite="lax")
    return response

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, error: str = None):
    if error:
        print(f"Error devuelto por Google: {error}")
        return RedirectResponse(url="/")

    base = str(request.base_url).rstrip('/')
    if "onrender.com" in base:
        redirect_uri = "https://agora-app-leox.onrender.com/auth/callback"
    else:
        redirect_uri = f"{base}/auth/callback"
    
    verifier = request.cookies.get("agora_oauth_verifier")
    flow = get_oauth_flow(redirect_uri)
    if verifier:
        flow.code_verifier = verifier

    try:
        if verifier:
            flow.fetch_token(code=code, code_verifier=verifier)
        else:
            flow.fetch_token(code=code)

        creds = flow.credentials
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = creds.to_json()
        print(f"Sesion iniciada con exito en Render: {session_id}")
        
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="agora_session",
            value=session_id,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        response.delete_cookie("agora_oauth_verifier")
        return response
    except Exception as e:
        print(f"Error en OAuth callback: {e}")
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

# -------------------------------------------------------------
# API DE TAREAS Y CALIFICACIONES POR USUARIO
# -------------------------------------------------------------
@app.get("/api/tasks")
async def get_tasks(request: Request):
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = None
    
    if creds_json:
        try:
            creds = Credentials.from_authorized_user_info(json.loads(creds_json), SCOPES)
        except Exception as e:
            print(f"Error reconstruyendo credenciales: {e}")
            creds = None

    if not creds:
        if os.path.exists('token.json') and "localhost" in str(request.base_url):
            creds = None
        else:
            return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    try:
        tasks = fetch_tasks(creds=creds)
        tasks_with_dates = [t for t in tasks if t.get('due_date')]
        tasks_without_dates = [t for t in tasks if not t.get('due_date')]
        return {
            "tasks_with_dates": tasks_with_dates,
            "tasks_without_dates": tasks_without_dates
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/announcements")
async def api_announcements(request: Request):
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = None
    if creds_json:
        try:
            creds = Credentials.from_authorized_user_info(json.loads(creds_json), SCOPES)
        except Exception:
            pass
    try:
        alerts = get_announcements_and_alerts(creds=creds)
        return {"announcements": alerts}
    except Exception:
        return {"announcements": []}

# -------------------------------------------------------------
# TUTOR SOCRÁTICO IGNIS
# -------------------------------------------------------------
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
