"""
Re-exportación unificada del servicio de Google Classroom desde services/classroom_service.py
Evita discrepancias y código duplicado entre la raíz y la carpeta services.
"""
from services.classroom_service import (
    SCOPES,
    get_credentials,
    get_classroom_service,
    get_drive_service,
    get_gmail_service,
    extract_pdf_text_from_drive,
    get_all_tasks,
    fetch_tasks,
    fetch_courses,
    get_announcements_and_alerts,
)

__all__ = [
    "SCOPES",
    "get_credentials",
    "get_classroom_service",
    "get_drive_service",
    "get_gmail_service",
    "extract_pdf_text_from_drive",
    "get_all_tasks",
    "fetch_tasks",
    "fetch_courses",
    "get_announcements_and_alerts",
]
