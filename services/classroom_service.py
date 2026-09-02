import os
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/classroom.courses.readonly", "https://www.googleapis.com/auth/classroom.coursework.me.readonly"]

def get_classroom_service():
    """Shows basic usage of the Classroom API.
    Prints the names of the first 10 courses the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
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

    try:
        service = build("classroom", "v1", credentials=creds)
        return service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def fetch_tasks():
    """
    Fetches active courses and extracts pending assignments.
    Returns a list of dictionaries with: id, course_name, title, description, due_date, link.
    """
    service = get_classroom_service()
    if not service:
        return None

    tasks = []
    try:
        # Get active courses
        results = service.courses().list(courseStates=['ACTIVE']).execute()
        courses = results.get("courses", [])

        if not courses:
            return []

        for course in courses:
            course_id = course.get("id")
            course_name = course.get("name")

            # Get coursework for each course
            # We fetch courseWork, then optionally submissions to filter "pending", but for simplicity and read-only
            # we fetch courseWork and handle completion in our local SQLite.
            coursework_results = service.courses().courseWork().list(courseId=course_id).execute()
            courseworks = coursework_results.get("courseWork", [])

            for cw in courseworks:
                cw_id = cw.get("id")
                title = cw.get("title")
                description = cw.get("description", "")
                link = cw.get("alternateLink")

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
                    "link": link
                })

    except HttpError as error:
        print(f"An error occurred: {error}")

    return tasks
