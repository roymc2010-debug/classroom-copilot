import os
import io
import re
import json
import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader

# Permite relajar el scope en caso de discrepancias menores de Google OAuthlib
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.me.readonly',
    'https://www.googleapis.com/auth/classroom.student-submissions.me.readonly',
    'https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly',
    'https://www.googleapis.com/auth/classroom.announcements.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email'
]

PDF_CACHE_DIR = os.path.join("data", "pdf_cache")

def get_cached_attachment_data(file_id: str) -> dict:
    """Lee del almacenamiento en disco las consignas extraídas y el texto del documento para carga instantánea."""
    if not file_id:
        return {}
    cache_path = os.path.join(PDF_CACHE_DIR, f"{file_id}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cached_attachment_data(file_id: str, data: dict):
    """Guarda en caché persistente en disco el análisis de consignas del archivo."""
    if not file_id or not data:
        return
    try:
        os.makedirs(PDF_CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(PDF_CACHE_DIR, f"{file_id}.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando caché de PDF {file_id}: {e}")

def extract_actionable_consignas(text: str, course_name: str = "", task_title: str = "", max_items: int = 4) -> list[str]:
    """
    Extrae de forma robusta y rigurosa las consignas reales y ejercicios de un texto de PDF universitario.
    Filtra encabezados institucionales, nombres de materia y metadatos docentes para extraer
    exactamente las acciones requeridas por el estudiante (ej. 'Resuelve 5 ejercicios sobre transformada de Laplace...').
    """
    if not text:
        return []

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    IGNORE_PATTERNS = [
        r'universidad', r'departamento', r'divisi[oó]n', r'centro universitario', r'cucei',
        r'profesor', r'docente', r'alumno', r'estudiante', r'c[oó]digo:', r'fecha:',
        r'semestre', r'ciclo escolar', r'licenciatura', r'ingenier[ií]a', r'cr[eé]ditos',
        r'criterios? de evaluaci[oó]n', r'ponderaci[oó]n', r'r[uú]brica', r'bibliograf[ií]a',
        r'p[aá]gina \d+', r'^\d+\s*$'
    ]
    ignore_re = re.compile('|'.join(IGNORE_PATTERNS), re.IGNORECASE)

    ACTION_VERBS = [
        r'resuelve', r'resolver', r'calcula', r'calcular', r'determina', r'determinar',
        r'obten(?:er|ga)?', r'halla(?:r)?', r'grafica(?:r)?', r'demuestra', r'demostrar',
        r'elabora(?:r)?', r'realiza(?:r)?', r'redacta(?:r)?', r'desarrolla(?:r)?',
        r'simula(?:r)?', r'investiga(?:r)?', r'analiza(?:r)?', r'compara(?:r)?',
        r'entrega(?:r)?', r'sube', r'subir', r'contesta(?:r)?', r'responde(?:r)?',
        r'encuentra', r'encontrar', r'aplica(?:r)?', r'ejercicios?', r'problemas?',
        r'transformada de laplace', r'funci[oó]n de transferencia', r'diagrama',
        r'ecuaci[oó]n', r'circuito', r'cuestionario', r'reporte', r'ensayo'
    ]
    action_re = re.compile(r'\b(' + '|'.join(ACTION_VERBS) + r')\b', re.IGNORECASE)

    prefix_clean_re = re.compile(r'^(?:instrucciones?|consigna|objetivo|actividad|tarea|ejercicio\s*\d*|problema\s*\d*)\s*[:.-]\s*', re.IGNORECASE)
    bullet_clean_re = re.compile(r'^(?:[-*•–—]|\d+[\.\)]|[a-zA-Z][\.\)])\s*')

    candidate_sentences = []

    for line in lines:
        if ignore_re.search(line) and not action_re.search(line):
            continue
        
        sentences = re.split(r'(?<=[.!?])\s+', line)
        for s in sentences:
            s_clean = s.strip()
            s_clean = bullet_clean_re.sub('', s_clean).strip()
            s_clean = prefix_clean_re.sub('', s_clean).strip()

            if len(s_clean) < 10:
                continue

            if course_name and s_clean.lower() == course_name.lower():
                continue
            if task_title and s_clean.lower() == task_title.lower():
                continue

            if action_re.search(s_clean):
                s_formatted = s_clean[0].upper() + s_clean[1:]
                if not s_formatted.endswith(('.', '!', '?')):
                    s_formatted += '.'
                if s_formatted not in candidate_sentences:
                    candidate_sentences.append(s_formatted)

    filtered = []
    for c in candidate_sentences:
        if len(c) > 250:
            sub = re.split(r'(?<=[.!?])\s+', c)
            c = sub[0]
        if len(c) >= 15 and c not in filtered:
            filtered.append(c)

    return filtered[:max_items]

def inject_authuser(url: str, user_email: str = None) -> str:
    """
    Inyecta deterministamente ?authuser={user_email} en enlaces externos de Google
    (Classroom, Drive, Docs, etc.) para que el navegador del alumno abra directamente
    su perfil escolar y evite errores de 'cuenta incorrecta / clase no encontrada'.
    """
    if not url or not user_email:
        return url or ""
    if "authuser=" in url:
        return url
    if "google.com" in url or "classroom." in url or "drive." in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}authuser={user_email}"
    return url

def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception:
            creds = None
    return creds

def get_classroom_service(creds=None):
    c = creds if creds else get_credentials()
    return build('classroom', 'v1', credentials=c)

def get_drive_service(creds=None):
    c = creds if creds else get_credentials()
    return build('drive', 'v3', credentials=c)

def get_gmail_service(creds=None):
    try:
        c = creds if creds else get_credentials()
        return build('gmail', 'v1', credentials=c)
    except Exception:
        return None

def extract_pdf_text_from_drive(drive_service, file_id: str) -> str:
    """Extrae texto de un PDF o Documento en Drive bajo demanda (con caché y soporte para Google Docs)."""
    if not file_id or not drive_service:
        return ""
    cached = get_cached_attachment_data(file_id)
    if cached and cached.get("text"):
        return cached["text"]

    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        reader = PdfReader(fh)
        text_content = []
        # Limitar a las primeras 5 páginas para optimizar tiempo y memoria
        for page in reader.pages[:5]:
            t = page.extract_text()
            if t:
                text_content.append(t)
        res = "\n".join(text_content).strip()
        if res:
            return res
    except Exception as e:
        print(f"Aviso: descarga get_media de {file_id} ({e}), probando exportación alternativa...")

    # Intento de respaldo: si es un Google Doc nativo
    try:
        req_export = drive_service.files().export_media(fileId=file_id, mimeType='text/plain')
        fh_exp = io.BytesIO()
        downloader_exp = MediaIoBaseDownload(fh_exp, req_export)
        done = False
        while not done:
            _, done = downloader_exp.next_chunk()
        fh_exp.seek(0)
        return fh_exp.read().decode('utf-8', errors='ignore').strip()
    except Exception as e_exp:
        print(f"Aviso: no se pudo extraer texto del archivo {file_id}: {e_exp}")
        return ""

def get_task_attachment_summary(drive_service, file_id: str, course_name: str = "", task_title: str = "") -> dict:
    """Obtiene el resumen y acciones del adjunto, aprovechando la caché en disco."""
    if not file_id:
        return {"actions": [], "text": ""}
    cached = get_cached_attachment_data(file_id)
    if cached and cached.get("actions"):
        return cached

    text = extract_pdf_text_from_drive(drive_service, file_id)
    actions = extract_actionable_consignas(text, course_name=course_name, task_title=task_title)

    data = {
        "file_id": file_id,
        "actions": actions,
        "text": text[:3000]
    }
    if text or actions:
        save_cached_attachment_data(file_id, data)
    return data

def get_active_courses(service):
    """
    Obtiene todas las materias del usuario de forma ultra-resiliente.
    Evita filtros excesivamente restrictivos que causan listas vacías en cuentas institucionales o escolares.
    """
    courses = []
    page_token = None

    # Intento 1: Consulta amplia sin restricción de studentId ni courseStates
    try:
        while True:
            res = service.courses().list(pageSize=100, pageToken=page_token).execute()
            batch = res.get('courses', [])
            courses.extend(batch)
            page_token = res.get('nextPageToken')
            if not page_token:
                break
    except Exception as e:
        print(f"[Classroom API] Intento 1 (sin filtros) falló: {e}. Probando intento 2...")
        courses = []

    # Intento 2: Si el intento 1 devolvió 0 o falló, probar con studentId='me'
    if not courses:
        try:
            page_token = None
            while True:
                res = service.courses().list(studentId='me', pageSize=100, pageToken=page_token).execute()
                batch = res.get('courses', [])
                courses.extend(batch)
                page_token = res.get('nextPageToken')
                if not page_token:
                    break
        except Exception as e2:
            print(f"[Classroom API] Intento 2 (studentId='me') falló: {e2}")

    # Intento 3: Probar con studentId='me' y courseStates=['ACTIVE'] como último recurso
    if not courses:
        try:
            page_token = None
            while True:
                res = service.courses().list(studentId='me', courseStates=['ACTIVE'], pageSize=100, pageToken=page_token).execute()
                batch = res.get('courses', [])
                courses.extend(batch)
                page_token = res.get('nextPageToken')
                if not page_token:
                    break
        except Exception as e3:
            print(f"[Classroom API] Intento 3 falló: {e3}")

    # Filtrar únicamente si hay materias y descartar solo las archivadas si existen materias activas
    non_archived = [c for c in courses if c.get('courseState') not in ('ARCHIVED', 'DECLINED')]
    final_list = non_archived if non_archived else courses

    print(f"[Classroom API] Cursos recuperados ({len(final_list)}): {[c.get('name') for c in final_list]}")
    return final_list

def get_all_tasks(creds=None, user_email=None):
    service = get_classroom_service(creds=creds)

    # Si no se pasó user_email, intentar extraerlo del perfil
    if not user_email and creds:
        try:
            profile = service.userProfiles().get(userId='me').execute()
            user_email = profile.get('emailAddress', '').lower().strip()
        except Exception:
            pass

    courses = get_active_courses(service)
    tasks = []

    for course in courses:
        course_id = course['id']
        course_name = course.get('name', 'Materia').replace('_', ' ')

        try:
            cw_res = service.courses().courseWork().list(courseId=course_id).execute()
            course_works = cw_res.get('courseWork', [])
        except Exception as e:
            print(f"[Classroom API] Error listando tareas para materia {course_name} ({course_id}): {e}")
            course_works = []

        for cw in course_works:
            cw_id = cw['id']
            title = cw.get('title', 'Sin título')
            desc = cw.get('description', '')
            alt_link = inject_authuser(cw.get('alternateLink', ''), user_email)
            max_points = cw.get('maxPoints')

            due_date = cw.get('dueDate')
            due_time = cw.get('dueTime')
            due_date_iso = None

            if due_date:
                year = due_date.get('year')
                month = due_date.get('month')
                day = due_date.get('day')
                hour = due_time.get('hours', 23) if due_time else 23
                minute = due_time.get('minutes', 59) if due_time else 59
                dt = datetime.datetime(year, month, day, hour, minute, tzinfo=datetime.timezone.utc)
                due_date_iso = dt.isoformat()

            classroom_status = 'PENDIENTE'
            assigned_grade = None

            try:
                sub_res = service.courses().courseWork().studentSubmissions().list(
                    courseId=course_id,
                    courseWorkId=cw_id,
                    userId='me'
                ).execute()
                submissions = sub_res.get('studentSubmissions', [])
                if submissions:
                    sub = submissions[0]
                    state = sub.get('state')
                    assigned_grade = sub.get('assignedGrade')

                    assignment_sub = sub.get('assignmentSubmission', {})
                    attachments = assignment_sub.get('attachments', [])

                    if state == 'RETURNED':
                        if assigned_grade is not None:
                            classroom_status = 'CALIFICADA'
                        else:
                            classroom_status = 'DEVUELTA'
                    elif state == 'TURNED_IN':
                        classroom_status = 'ENTREGADA'
                    elif attachments and state in ('NEW', 'CREATED'):
                        classroom_status = 'SUBIDA_SIN_ENTREGAR'
                    else:
                        classroom_status = 'PENDIENTE'
            except Exception:
                classroom_status = 'PENDIENTE'

            materials = cw.get('materials', [])
            attachment_links = []
            attachment_files = []

            for m in materials:
                drive_file = m.get('driveFile', {}).get('driveFile', {})
                if drive_file:
                    f_id = drive_file.get('id')
                    f_title = drive_file.get('title', 'Documento adjunto')
                    f_link = inject_authuser(drive_file.get('alternateLink', ''), user_email)

                    if f_link:
                        attachment_links.append(f"{f_title} ({f_link})")
                    if f_id:
                        attachment_files.append({'id': f_id, 'title': f_title, 'link': f_link})

            full_desc = desc
            if attachment_links:
                full_desc += "\n\nArchivos adjuntos:\n" + "\n".join(attachment_links)

            cached_actions = []
            for af in attachment_files:
                af_id = af.get('id')
                if af_id:
                    c_data = get_cached_attachment_data(af_id)
                    if c_data and c_data.get('actions'):
                        cached_actions = c_data['actions']
                        break

            tasks.append({
                'id': str(cw_id),
                'course_id': course_id,
                'course_name': course_name,
                'title': title,
                'description': full_desc,
                'link': alt_link,
                'due_date': due_date_iso,
                'classroom_status': classroom_status,
                'assigned_grade': assigned_grade,
                'max_points': max_points,
                'attachment_files': attachment_files,
                'cached_actions': cached_actions
            })

    print(f"[Classroom API] Total de tareas procesadas: {len(tasks)}")
    return tasks

# Exportar con ambos nombres para compatibilidad total
fetch_tasks = get_all_tasks

def fetch_courses(creds=None, user_email=None):
    try:
        service = get_classroom_service(creds=creds)
        if not user_email and creds:
            try:
                profile = service.userProfiles().get(userId='me').execute()
                user_email = profile.get('emailAddress', '').lower().strip()
            except Exception:
                pass

        courses = get_active_courses(service)
        return [{
            'id': c.get('id'),
            'name': c.get('name', 'Materia sin nombre').replace('_', ' '),
            'section': c.get('section', ''),
            'alternateLink': inject_authuser(c.get('alternateLink', ''), user_email)
        } for c in courses]
    except Exception as e:
        print(f"Error en fetch_courses: {e}")
        return []

def get_announcements_and_alerts(creds=None, user_email=None):
    alerts = []
    try:
        service = get_classroom_service(creds=creds)
        if not user_email and creds:
            try:
                profile = service.userProfiles().get(userId='me').execute()
                user_email = profile.get('emailAddress', '').lower().strip()
            except Exception:
                pass

        courses = get_active_courses(service)

        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat() + "Z"

        for course in courses:
            c_id = course['id']
            c_name = course.get('name', 'Materia').replace('_', ' ')

            try:
                ann_res = service.courses().announcements().list(courseId=c_id).execute()
                announcements = ann_res.get('announcements', [])
                for a in announcements:
                    created = a.get('creationTime', '')
                    if created >= cutoff_date:
                        text = a.get('text', '').strip()
                        alerts.append({
                            'source': 'Classroom',
                            'course_name': c_name,
                            'title': f"Aviso en {c_name}",
                            'content': text,
                            'link': inject_authuser(a.get('alternateLink', ''), user_email),
                            'date': created
                        })
            except Exception:
                pass

        gmail_service = get_gmail_service(creds=creds)
        if gmail_service:
            try:
                query = "newer_than:7d (clase OR suspende OR asistencia OR aviso OR cancela OR examen OR práctica)"
                msgs_res = gmail_service.users().messages().list(userId='me', q=query, maxResults=5).execute()
                messages = msgs_res.get('messages', [])

                for m in messages:
                    msg_data = gmail_service.users().messages().get(userId='me', id=m['id'], format='snippet').execute()
                    snippet = msg_data.get('snippet', '')
                    alerts.append({
                        'source': 'Gmail',
                        'course_name': 'Correo Institucional',
                        'title': 'Aviso urgente por Correo',
                        'content': snippet,
                        'link': f"https://mail.google.com/mail/u/0/#inbox/{m['id']}",
                        'date': datetime.datetime.utcnow().isoformat()
                    })
            except Exception:
                pass

    except Exception as e:
        print(f"Error en get_announcements_and_alerts: {e}")

    return alerts
