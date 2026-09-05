import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from services.classroom_service import fetch_tasks, get_announcements_and_alerts
from services.ai_service import ask_copilot

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

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
    return Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

app = FastAPI(title="Ágora")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "agora-secret-key-production-udg-cucei-2026")
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# -------------------------------------------------------------
# RUTAS DE AUTENTICACIÓN GOOGLE (MULTI-USUARIO WEB)
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
    request.session['oauth_state'] = state
    return RedirectResponse(authorization_url)

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = None):
    base = str(request.base_url).rstrip('/')
    if "onrender.com" in base:
        redirect_uri = "https://agora-app-leox.onrender.com/auth/callback"
    else:
        redirect_uri = f"{base}/auth/callback"
    
    flow = get_oauth_flow(redirect_uri)
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        request.session['credentials'] = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
    except Exception as e:
        print(f"Error en OAuth callback: {e}")
        
    return RedirectResponse(url="/")

@app.get("/auth/logout")
async def auth_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

# -------------------------------------------------------------
# API DE TAREAS Y CALIFICACIONES POR USUARIO
# -------------------------------------------------------------
@app.get("/api/tasks")
async def get_tasks(request: Request):
    creds_data = request.session.get('credentials')
    creds = None
    
    if creds_data:
        try:
            creds = Credentials(**creds_data)
        except Exception:
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
    creds_data = request.session.get('credentials')
    creds = None
    if creds_data:
        try:
            creds = Credentials(**creds_data)
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
