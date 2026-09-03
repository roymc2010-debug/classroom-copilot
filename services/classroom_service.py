import os
import os.path
import io
from pypdf import PdfReader

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# Avoid Scope aliases errors
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

def get_google_credentials():
    """Retrieves Google Credentials, handling token generation and renewal."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        # Check if scopes changed (if existing token doesn't have the new drive scope)
        if creds and not set(SCOPES).issubset(set(creds.scopes)):
            print("Scopes changed, requiring new authorization...")
            os.remove("token.json")
            creds = None

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                # If credentials.json is missing, return None to handle it gracefully in main app
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            # Run local server to allow user login flow
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def get_services():
    """Returns Classroom and Drive services."""
    creds = get_google_credentials()
    if not creds:
        return None, None
    try:
        classroom_service = build("classroom", "v1", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)
        return classroom_service, drive_service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None, None

def extract_pdf_text_from_drive(drive_service, file_id):
    """Downloads a PDF from Drive and extracts text using pypdf."""
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        file_io.seek(0)
        reader = PdfReader(file_io)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Failed to extract text from PDF {file_id}: {e}")
        return "(No se pudo extraer el texto del archivo adjunto)"

def fetch_tasks():
    """
    Fetches active courses and extracts pending assignments.
    Returns a list of dictionaries with: id, course_name, title, description, due_date, link, materials, materials_text.
    """
    classroom_service, drive_service = get_services()
    if not classroom_service:
        return None

    tasks = []
    try:
        # Get active courses
        results = classroom_service.courses().list(courseStates=['ACTIVE']).execute()
        courses = results.get("courses", [])

        if not courses:
            return []

        for course in courses:
            course_id = course.get("id")
            course_name = course.get("name")

            # Get coursework for each course
            # We fetch courseWork, then optionally submissions to filter "pending", but for simplicity and read-only
            # we fetch courseWork and handle completion in our local SQLite.
            coursework_results = classroom_service.courses().courseWork().list(courseId=course_id).execute()
            courseworks = coursework_results.get("courseWork", [])

            for cw in courseworks:
                cw_id = cw.get("id")
                title = cw.get("title")
                description = cw.get("description", "")
                link = cw.get("alternateLink")

                materials = cw.get("materials", [])
                parsed_materials = []
                materials_text_parts = []

                for material in materials:
                    if "driveFile" in material:
                        drive_file = material["driveFile"]["driveFile"]
                        file_title = drive_file.get("title", "Documento")
                        file_url = drive_file.get("alternateLink", "")
                        file_id = drive_file.get("id")

                        parsed_materials.append({"title": file_title, "url": file_url, "type": "driveFile"})

                        # Process PDF files
                        if file_title.lower().endswith(".pdf") and file_id:
                            extracted_text = extract_pdf_text_from_drive(drive_service, file_id)
                            materials_text_parts.append(f"--- Archivo: {file_title} ---\n{extracted_text}")

                    elif "link" in material:
                        link_material = material["link"]
                        parsed_materials.append({"title": link_material.get("title", "Enlace"), "url": link_material.get("url", ""), "type": "link"})

                materials_text = "\n\n".join(materials_text_parts)

                # Format due_date if available
                due_date_obj = cw.get("dueDate")
                due_time_obj = cw.get("dueTime")

                due_date_str = None
                if due_date_obj:
                    year = due_date_obj.get('year')
                    month = due_date_obj.get('month')
                    day = due_date_obj.get('day')
                    if year and month and day:
                        due_date_str = f"{year}-{month:02d}-{day:02d}"

                        if due_time_obj:
                            hours = due_time_obj.get('hours', 0)
                            minutes = due_time_obj.get('minutes', 0)
                            due_date_str += f"T{hours:02d}:{minutes:02d}:00"

                tasks.append({
                    "id": cw_id,
                    "course_name": course_name,
                    "title": title,
                    "description": description,
                    "due_date": due_date_str, # Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or None
                    "link": link,
                    "materials": parsed_materials,
                    "materials_text": materials_text
                })

    except HttpError as error:
        print(f"An error occurred: {error}")

    return tasks
