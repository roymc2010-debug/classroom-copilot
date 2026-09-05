import os
import io
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
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
    'https://www.googleapis.com/auth/gmail.readonly'
]

def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("No se encontro credentials.json en la raiz del proyecto.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def get_classroom_service():
    return build('classroom', 'v1', credentials=get_credentials())

def get_drive_service():
    return build('drive', 'v3', credentials=get_credentials())

def get_gmail_service():
    try:
        return build('gmail', 'v1', credentials=get_credentials())
    except Exception:
        return None

def extract_pdf_text_from_drive(drive_service, file_id: str) -> str:
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
        return ""

def get_all_tasks():
    service = get_classroom_service()
    drive_service = get_drive_service()

    # pageSize=50 para que no se corte Control I
    courses_res = service.courses().list(studentId='me', courseStates=['ACTIVE'], pageSize=50).execute()
    courses = courses_res.get('courses', [])

    tasks = []

    for course in courses:
        course_id = course['id']
        course_name = course['name']

        try:
            cw_res = service.courses().courseWork().list(courseId=course_id).execute()
            course_works = cw_res.get('courseWork', [])
        except Exception:
            course_works = []

        for cw in course_works:
            cw_id = cw['id']
            title = cw.get('title', 'Sin titulo')
            desc = cw.get('description', '')
            alt_link = cw.get('alternateLink', '')
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
                    state = sub.get('state')  # 'NEW', 'CREATED', 'TURNED_IN', 'RETURNED'
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
            extracted_docs = []
            attachment_links = []

            for m in materials:
                drive_file = m.get('driveFile', {}).get('driveFile', {})
                if drive_file:
                    f_id = drive_file.get('id')
                    f_title = drive_file.get('title', 'Documento adjunto')
                    f_link = drive_file.get('alternateLink', '')

                    if f_link:
                        attachment_links.append(f"{f_title} ({f_link})")

                    if f_title.lower().endswith('.pdf') and f_id:
                        pdf_text = extract_pdf_text_from_drive(drive_service, f_id)
                        if pdf_text:
                            extracted_docs.append(f"--- Documento adjunto: {f_title} ---\n{pdf_text}")

            full_desc = desc
            if extracted_docs:
                full_desc += "\n\n" + "\n\n".join(extracted_docs)
            if attachment_links:
                full_desc += "\n\nArchivos/Enlaces adjuntos:\n" + "\n".join(attachment_links)

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
                'max_points': max_points
            })

    return tasks

# Exportar con ambos nombres para compatibilidad total con main.py
fetch_tasks = get_all_tasks

def get_announcements_and_alerts():
    alerts = []
    try:
        service = get_classroom_service()
        courses_res = service.courses().list(studentId='me', courseStates=['ACTIVE'], pageSize=50).execute()
        courses = courses_res.get('courses', [])

        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=3)).isoformat() + "Z"

        for course in courses:
            c_id = course['id']
            c_name = course['name']

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
                            'link': a.get('alternateLink', ''),
                            'date': created
                        })
            except Exception:
                pass

        gmail_service = get_gmail_service()
        if gmail_service:
            try:
                query = "newer_than:3d (clase OR suspende OR asistencia OR aviso OR cancela OR examen OR práctica)"
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

    except Exception:
        pass

    return alerts