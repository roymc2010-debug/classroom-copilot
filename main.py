import os
import re
import json
import uuid
import urllib.request
import urllib.parse
import traceback
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse, PlainTextResponse
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
        with open(SESSIONS_FILE, "r", encoding="utf-8-sig") as f:
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
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email'
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
            with open('credentials.json', 'r', encoding='utf-8-sig') as f:
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

def restore_and_refresh_credentials(creds_data, session_id: str = None):
    if not creds_data:
        return None
    if isinstance(creds_data, dict) and creds_data.get("is_demo"):
        return None
    try:
        if isinstance(creds_data, dict):
            raw_creds = creds_data.get("creds", creds_data)
        else:
            raw_creds = creds_data
        data = json.loads(raw_creds) if isinstance(raw_creds, str) else raw_creds
        creds = Credentials(
            token=data.get("token") or data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri") or "https://oauth2.googleapis.com/token",
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes") or SCOPES
        )

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest())
                if session_id and session_id in user_sessions:
                    if isinstance(user_sessions[session_id], dict) and "creds" in user_sessions[session_id]:
                        user_sessions[session_id]["creds"] = creds.to_json()
                    else:
                        user_sessions[session_id] = creds.to_json()
                    save_sessions()
            except Exception as e:
                print(f"No se pudo refrescar el token de Google: {e}")

        if creds.token or creds.refresh_token:
            return creds
        return None
    except Exception as e:
        print(f"Error restaurando credenciales: {e}")
        return None

app = FastAPI(title="Agora")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/manifest.json")
def get_manifest():
    return FileResponse("manifest.json", media_type="application/manifest+json")

@app.get("/favicon.ico")
def get_favicon():
    return FileResponse("static/favicon.ico", media_type="image/x-icon")



ALEX_EMAIL = "alexmunoz918@gmail.com"

def get_session_user_email(creds) -> str:
    if not creds:
        return ""
    try:
        from googleapiclient.discovery import build
        service = build('classroom', 'v1', credentials=creds)
        profile = service.userProfiles().get(userId='me').execute()
        return profile.get('emailAddress', '').lower().strip()
    except Exception:
        return ""

def get_session_email(session_id: str, creds=None) -> str:
    if not session_id:
        email = get_session_user_email(creds) if creds else ""
        return email if isinstance(email, str) else ""
    sess = user_sessions.get(session_id)
    if isinstance(sess, dict) and sess.get("email"):
        email = sess["email"]
        return email.lower().strip() if isinstance(email, str) else ""
    if creds:
        email = get_session_user_email(creds)
        if email and isinstance(email, str) and isinstance(sess, dict):
            sess["email"] = email
            save_sessions()
        return email if isinstance(email, str) else ""
    return ""

USER_TASKS_CACHE: Dict[str, List[Dict[str, Any]]] = {}

def get_user_tasks_cached(user_email: str, creds=None) -> List[Dict[str, Any]]:
    if not isinstance(user_email, str):
        user_email = ""
    user_email = user_email.lower().strip()
    if user_email and user_email in USER_TASKS_CACHE:
        return USER_TASKS_CACHE[user_email]

    if user_email == ALEX_EMAIL:
        from services.mock_data_service import get_alex_stage_data, STAGES
        data = get_alex_stage_data()
        active_tasks = data.get("tasks", [])
        all_stage_tasks = []
        seen_ids = set()
        for t in active_tasks:
            seen_ids.add(t["id"])
            all_stage_tasks.append(t)
        for s in STAGES:
            for t in s.get("tasks", []):
                if t["id"] not in seen_ids:
                    seen_ids.add(t["id"])
                    all_stage_tasks.append(t)
        USER_TASKS_CACHE[user_email] = all_stage_tasks
        return all_stage_tasks

    clean_email = re.sub(r'[^a-zA-Z0-9_.-]', '_', user_email.lower()) if user_email else "anonymous"
    cache_file = os.path.join("data", "notes_cache", f"tasks_{clean_email}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                tasks = json.load(f)
                if user_email:
                    USER_TASKS_CACHE[user_email] = tasks
                return tasks
        except Exception:
            pass

    if creds:
        try:
            tasks = fetch_tasks(creds=creds, user_email=user_email)
            if user_email:
                USER_TASKS_CACHE[user_email] = tasks
            os.makedirs(os.path.join("data", "notes_cache"), exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False)
            return tasks
        except Exception as e:
            print(f"[Main] Error obteniendo tareas en get_user_tasks_cached: {e}")

    return []

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    session_id = request.cookies.get("agora_session")
    has_session = False
    user_email = ""
    if session_id and session_id in user_sessions:
        sess = user_sessions[session_id]
        if isinstance(sess, dict) and sess.get("is_demo"):
            has_session = True
            user_email = sess.get("email", ALEX_EMAIL)
        else:
            creds = restore_and_refresh_credentials(sess, session_id=session_id)
            if creds and (creds.token or creds.refresh_token):
                has_session = True
                user_email = get_session_email(session_id, creds=creds)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"has_session": has_session, "user_email": user_email}
    )

@app.get("/auth/demo")
async def auth_demo():
    """Inicia sesión instantánea en Modo de Prueba (Alex Muñoz) con datos completos."""
    demo_session_id = "demo_alex_session"
    user_sessions[demo_session_id] = {
        "email": ALEX_EMAIL,
        "is_demo": True
    }
    save_sessions()
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie(
        key="agora_session",
        value=demo_session_id,
        httponly=True,
        max_age=60 * 60 * 24 * 30,
        samesite="lax"
    )
    return resp

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

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
        f"include_granted_scopes=true&"
        f"prompt=select_account%20consent"
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

        existing_refresh = None
        for s_id, s_data in user_sessions.items():
            try:
                raw_c = s_data.get("creds", s_data) if isinstance(s_data, dict) else s_data
                parsed = json.loads(raw_c) if isinstance(raw_c, str) else raw_c
                if parsed.get("refresh_token"):
                    existing_refresh = parsed.get("refresh_token")
                    break
            except Exception:
                pass

        if not existing_refresh and os.path.exists("token.json"):
            try:
                t_old = json.loads(open("token.json", "r", encoding="utf-8").read())
                existing_refresh = t_old.get("refresh_token")
            except Exception:
                pass

        refresh_token = token_data.get("refresh_token") or existing_refresh

        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )

        # Consultar endpoint oficial userinfo de Google para extraer el email institucional exacto
        user_email = ""
        try:
            uinfo_req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data.get('access_token')}"}
            )
            with urllib.request.urlopen(uinfo_req) as uresp:
                uinfo = json.loads(uresp.read().decode("utf-8"))
                user_email = uinfo.get("email", "").lower().strip()
        except Exception as e:
            print(f"Aviso: userinfo no devolvió email ({e}), intentando perfil de Classroom...")
            try:
                user_email = get_session_user_email(creds)
            except Exception:
                pass

        session_id = str(uuid.uuid4())
        user_sessions[session_id] = {
            "creds": creds.to_json(),
            "email": user_email
        }
        save_sessions()

        try:
            with open("token.json", "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception:
            pass

        print(f"Autenticacion completada con exito para {user_email or 'usuario'} (sesion: {session_id})")

        try:
            from services.mock_data_service import cycle_alex_stage
            if user_email == ALEX_EMAIL:
                cycle_alex_stage()
        except Exception:
            pass

        is_https = "https" in redirect_uri
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="agora_session",
            value=session_id,
            max_age=30 * 24 * 3600,
            path="/",
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
    sess = user_sessions.get(session_id)
    if isinstance(sess, dict) and sess.get("is_demo"):
        from services.mock_data_service import get_alex_stage_data
        alex_data = get_alex_stage_data()
        return {"courses": alex_data["courses"]}

    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)

    if not creds:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    user_email = get_session_email(session_id, creds=creds)
    if user_email == ALEX_EMAIL:
        from services.mock_data_service import get_alex_stage_data
        alex_data = get_alex_stage_data()
        return {"courses": alex_data["courses"]}

    try:
        courses = fetch_courses(creds=creds, user_email=user_email)
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
    sess = user_sessions.get(session_id)
    if isinstance(sess, dict) and sess.get("is_demo"):
        from services.mock_data_service import get_alex_stage_data
        alex_data = get_alex_stage_data()
        tasks = alex_data["tasks"]
        tasks_with_dates = [t for t in tasks if t.get('due_date')]
        tasks_without_dates = [t for t in tasks if not t.get('due_date')]
        return {
            "user_email": ALEX_EMAIL,
            "enrolled_courses": alex_data.get("courses", []),
            "mock_stage_id": alex_data["id"],
            "mock_stage_name": alex_data["name"],
            "mock_streak_weeks": alex_data["streak_weeks"],
            "mock_streak_days": alex_data["streak_days"],
            "tasks_with_dates": tasks_with_dates,
            "tasks_without_dates": tasks_without_dates
        }

    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)

    if not creds:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    user_email = get_session_email(session_id, creds=creds)

    # Si es Alex, servir paquete de datos falsos de la etapa activa
    if user_email == ALEX_EMAIL:
        from services.mock_data_service import get_alex_stage_data
        alex_data = get_alex_stage_data()
        tasks = alex_data["tasks"]
        USER_TASKS_CACHE[user_email] = tasks
        tasks_with_dates = [t for t in tasks if t.get('due_date')]
        tasks_without_dates = [t for t in tasks if not t.get('due_date')]
        return {
            "user_email": user_email,
            "enrolled_courses": alex_data.get("courses", []),
            "mock_stage_id": alex_data["id"],
            "mock_stage_name": alex_data["name"],
            "mock_streak_weeks": alex_data["streak_weeks"],
            "mock_streak_days": alex_data["streak_days"],
            "tasks_with_dates": tasks_with_dates,
            "tasks_without_dates": tasks_without_dates
        }

    try:
        courses = fetch_courses(creds=creds, user_email=user_email)
        tasks = fetch_tasks(creds=creds, user_email=user_email)
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

        if user_email:
            USER_TASKS_CACHE[user_email] = tasks
            clean_email = re.sub(r'[^a-zA-Z0-9_.-]', '_', user_email.lower())
            cache_file = os.path.join("data", "notes_cache", f"tasks_{clean_email}.json")
            try:
                os.makedirs(os.path.join("data", "notes_cache"), exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(tasks, f, ensure_ascii=False)
            except Exception:
                pass

        tasks_with_dates = [t for t in tasks if t.get('due_date')]
        tasks_without_dates = [t for t in tasks if not t.get('due_date')]
        return {
            "user_email": user_email,
            "enrolled_courses": courses,
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

@app.post("/api/notes/upload")
async def upload_course_note(
    request: Request,
    file: UploadFile = File(...),
    course_name: str = Form(...)
):
    """
    Sube un archivo de apuntes (PDF/imagen): calcula SHA-256 para deduplicación,
    extrae texto/fórmulas y organiza en la carpeta de Drive de la asignatura.
    """
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)
    user_email = get_session_email(session_id, creds=creds)

    try:
        import services.notes_service as notes_service
        file_bytes = await file.read()
        res = notes_service.process_and_upload_note(
            file_bytes=file_bytes,
            filename=file.filename or "apunte.pdf",
            course_name=course_name,
            user_email=user_email,
            creds=creds
        )
        return res
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/notes/personal")
async def add_personal_note_endpoint(request: Request):
    """
    Inserta una nota personal/corrección de clase al final de la unidad correspondiente.
    """
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)
    user_email = get_session_email(session_id, creds=creds)

    try:
        data = await request.json()
        course_name = data.get("course_name", "")
        task_id = data.get("task_id", "")
        note_text = data.get("note_text", "")

        import services.notes_service as notes_service
        res = notes_service.add_personal_note(
            course_name=course_name,
            task_id=task_id,
            note_text=note_text,
            user_email=user_email,
            creds=creds
        )
        return res
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/notes/{course_name}")
async def get_course_notes_endpoint(course_name: str, request: Request):
    """
    Devuelve la lista modular de documentos disponibles para esa materia
    (unidades temáticas, formulario y documento maestro compilado).
    """
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)
    user_email = get_session_email(session_id, creds=creds)

    try:
        import services.notes_service as notes_service
        tasks = get_user_tasks_cached(user_email=user_email, creds=creds)
        res = notes_service.get_course_notes(
            course_name=course_name,
            user_email=user_email,
            creds=creds,
            tasks=tasks
        )
        return res
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/notes/{course_name}/study-summary")
async def get_course_study_summary_endpoint(course_name: str, request: Request):
    """
    Devuelve la Guía y Resumen de Estudio estructurada por temas para esa materia.
    """
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)
    user_email = get_session_email(session_id, creds=creds)

    try:
        import services.notes_service as notes_service
        tasks = get_user_tasks_cached(user_email=user_email, creds=creds)
        summary_info = notes_service.get_thematic_study_summary(course_name, tasks=tasks)
        return PlainTextResponse(summary_info.get("text", "Sin resumen disponible."), media_type="text/plain; charset=utf-8")
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/api/notes/{course_name}")
async def delete_course_notes_endpoint(course_name: str, request: Request):
    """
    Elimina los archivos de apuntes de esa materia en Google Drive y limpia el almacenamiento local.
    """
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)
    user_email = get_session_email(session_id, creds=creds)

    try:
        import services.notes_service as notes_service
        res = notes_service.delete_course_notes(
            course_name=course_name,
            user_email=user_email,
            creds=creds
        )
        return res
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/announcements")
async def api_announcements(request: Request):
    """
    Devuelve avisos de Classroom y Gmail del usuario autenticado.
    """
    session_id = request.cookies.get("agora_session")
    sess = user_sessions.get(session_id)
    if isinstance(sess, dict) and sess.get("is_demo"):
        from services.mock_data_service import get_alex_stage_data
        alex_data = get_alex_stage_data()
        return {"announcements": alex_data["announcements"]}

    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)

    if not creds:
        return {"announcements": []}

    user_email = get_session_email(session_id, creds=creds)
    if user_email == ALEX_EMAIL:
        from services.mock_data_service import get_alex_stage_data
        alex_data = get_alex_stage_data()
        return {"announcements": alex_data["announcements"]}

    try:
        alerts = get_announcements_and_alerts(creds=creds, user_email=user_email)
        return {"announcements": alerts}
    except Exception as e:
        print(f"Error obteniendo avisos: {e}")
        return {"announcements": []}

@app.post("/api/alex/stage/cycle")
async def cycle_alex_semester_stage(request: Request):
    """
    Permite rotar o cambiar la etapa del semestre de prueba para Alex.
    """
    from services.mock_data_service import cycle_alex_stage
    new_stage = cycle_alex_stage()
    return {"ok": True, "stage": new_stage}

@app.get("/api/tasks/{task_id}/attachment_summary")
async def get_attachment_summary(
    task_id: str,
    request: Request,
    file_id: str = None,
    course_name: str = "",
    title: str = ""
):
    """
    Extrae y devuelve de forma asíncrona las consignas y ejercicios reales del documento adjunto de la tarea.
    Utiliza caché en disco para respuesta inmediata (<1ms) en cargas posteriores.
    """
    session_id = request.cookies.get("agora_session")
    creds_json = user_sessions.get(session_id)
    creds = restore_and_refresh_credentials(creds_json, session_id=session_id)

    if not creds:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    user_email = get_session_email(session_id, creds=creds)

    # Para Alex (mock), devolver acciones realistas según título
    if user_email == ALEX_EMAIL:
        t_low = (title or "").lower()
        if "laplace" in t_low or "sistemas" in t_low:
            return {"actions": [
                "Resuelve 5 ejercicios sobre transformada de Laplace aplicando linealidad y traslación.",
                "Determina la función de transferencia del sistema dinámico dado.",
                "Grafica la respuesta al escalón unitario para comprobar la estabilidad.",
                "Entrega el reporte de ejercicios manuscritos en PDF."
            ]}
        elif "funci" in t_low or "calculo" in t_low:
            return {"actions": [
                "Determina analíticamente el dominio y rango de las funciones racionales.",
                "Grafica las asíntotas verticales y horizontales de los ejercicios 1 al 8.",
                "Justifica la continuidad en cada intervalo."
            ]}
        elif "algoritmo" in t_low or "python" in t_low:
            return {"actions": [
                "Desarrolla en Python un script que calcule el índice de masa corporal.",
                "Implementa estructuras condicionales y validación de entradas numéricas.",
                "Adjunta diagrama de flujo en formato Mermaid."
            ]}
        return {"actions": [
            f"Revisar los ejercicios y requerimientos del documento adjunto para {title or 'la tarea'}.",
            "Completar el procedimiento de cálculo y estructurar la entrega en PDF."
        ]}

    if not file_id:
        return {"actions": []}

    try:
        from services.classroom_service import get_drive_service, get_task_attachment_summary
        drive_service = get_drive_service(creds=creds)
        res = get_task_attachment_summary(drive_service, file_id, course_name=course_name, task_title=title)
        return {"actions": res.get("actions", [])}
    except Exception as e:
        print(f"Error obteniendo resumen de adjunto {file_id}: {e}")
        return {"actions": []}

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

    # Enriquecer el contexto de Ignis con el contenido real del documento si está en caché
    file_id = data.get("file_id") or task_context.get("file_id")
    if file_id:
        try:
            from services.classroom_service import get_cached_attachment_data
            cached_doc = get_cached_attachment_data(file_id)
            if cached_doc and cached_doc.get("text"):
                doc_text = cached_doc["text"][:2500]
                curr_desc = task_context.get("description", "")
                if "Contenido del documento adjunto:" not in curr_desc:
                    task_context["description"] = f"{curr_desc}\n\n[Contenido del documento adjunto:\n{doc_text}]".strip()
        except Exception:
            pass

    # Enriquecer con apuntes de clase de la materia si están disponibles
    c_name = task_context.get("course_name")
    if c_name and "student_notes" not in task_context:
        try:
            import services.notes_service as notes_service
            notes_text = notes_service.get_course_notes_text(c_name)
            if notes_text:
                task_context["student_notes"] = notes_text
        except Exception:
            pass

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
    Simulador de Parciales Universitarios (Sócrates).
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

    if course_name and "student_notes" not in task_context:
        try:
            import services.notes_service as notes_service
            notes_text = notes_service.get_course_notes_text(course_name)
            if notes_text:
                task_context["student_notes"] = notes_text
        except Exception:
            pass

    response_text = await ask_copilot(
        provider=provider,
        mentor="socrates",
        task_context=task_context,
        messages=messages
    )
    return {"response": response_text}
