import os
import io
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
    """Extrae texto de un PDF en Drive bajo demanda (para usar en Ignis, no en el listado general)."""
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
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_content.append(t)
        return "\n".join(text_content).strip()
    except Exception as e:
        print(f"Aviso: no se pudo extraer texto del PDF {file_id}: {e}")
        return ""

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
                dt = datetime.datetime(year, month, day, hour, minute)
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
                'attachment_files': attachment_files
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
