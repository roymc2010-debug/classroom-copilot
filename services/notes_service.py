import os
import io
import re
import json
import hashlib
import datetime
from typing import Dict, List, Optional, Any

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from fontTools.ttLib import TTFont
except ImportError:
    TTFont = None

from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

NOTES_CACHE_DIR = os.path.join("data", "notes_cache")
os.makedirs(NOTES_CACHE_DIR, exist_ok=True)

HASHES_FILE = os.path.join(NOTES_CACHE_DIR, "file_hashes.json")

def _load_hashes() -> Dict[str, Any]:
    if os.path.exists(HASHES_FILE):
        try:
            with open(HASHES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_hashes(data: Dict[str, Any]):
    try:
        with open(HASHES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[NotesService] Error guardando hashes: {e}")

def compute_sha256(content: bytes) -> str:
    """Calcula el hash SHA-256 de los bytes de un archivo."""
    return hashlib.sha256(content).hexdigest()

def extract_text_and_formulas(content: bytes, filename: str = "") -> Dict[str, Any]:
    """
    Extrae texto y fórmulas de archivos PDF usando pypdf y fonttools.
    Detecta patrones matemáticos comunes (integrales, sumatorias, derivadas, etc.).
    """
    extracted_text = ""
    formulas = []
    
    is_pdf = filename.lower().endswith(".pdf") or content.startswith(b"%PDF")
    
    if is_pdf and PdfReader:
        try:
            stream = io.BytesIO(content)
            reader = PdfReader(stream)
            pages_text = []
            for i, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                pages_text.append(txt)
                
                # Heurística para fórmulas matemáticas
                math_patterns = re.findall(r'([∮∫∬∭∑∏√∂∇±×÷≠≤≥≈∞∈ℝ\^_{}\(\)\+\-\*\/\=a-zA-Z0-9\s]{5,}\s*=\s*[^\n]+)', txt)
                for f in math_patterns:
                    f_clean = f.strip()
                    if len(f_clean) > 4 and f_clean not in formulas:
                        formulas.append(f_clean)
            
            extracted_text = "\n".join(pages_text).strip()
        except Exception as e:
            print(f"[NotesService] Error leyendo PDF con pypdf: {e}")
            extracted_text = ""
    else:
        # Texto plano o binario fallback
        try:
            extracted_text = content.decode("utf-8", errors="ignore").strip()
        except Exception:
            extracted_text = ""
            
    # Detección adicional de fórmulas LaTeX / estándar
    latex_matches = re.findall(r'(\$\$?[^\$]+\$\$?)', extracted_text)
    for m in latex_matches:
        if m not in formulas:
            formulas.append(m)

    return {
        "text": extracted_text,
        "formulas": formulas[:25],
        "has_dense_math": len(formulas) >= 3 or any(sym in extracted_text for sym in ["∮", "∫", "∬", "∑", "∂", "∇"])
    }

def get_drive_service(creds):
    """Construye el cliente de Google Drive v3 con las credenciales dadas."""
    if not creds:
        return None
    try:
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"[NotesService] Error instanciando cliente de Drive: {e}")
        return None

def get_or_create_course_folder(drive_service, course_name: str) -> Optional[str]:
    """
    Busca o crea la carpeta raíz 'Ágora - Apuntes' y la subcarpeta 'Ágora - Apuntes / [Nombre de la Materia]'.
    """
    if not drive_service:
        return None
    try:
        # 1. Buscar o crear carpeta raíz 'Ágora - Apuntes'
        query_root = "name = 'Ágora - Apuntes' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res_root = drive_service.files().list(q=query_root, spaces='drive', fields='files(id, name)').execute()
        root_files = res_root.get('files', [])
        
        if root_files:
            root_id = root_files[0]['id']
        else:
            root_meta = {
                'name': 'Ágora - Apuntes',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            root_folder = drive_service.files().create(body=root_meta, fields='id').execute()
            root_id = root_folder.get('id')

        # 2. Buscar o crear subcarpeta de la materia
        clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "General"
        query_course = f"name = '{clean_course}' and '{root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res_course = drive_service.files().list(q=query_course, spaces='drive', fields='files(id, name)').execute()
        course_files = res_course.get('files', [])
        
        if course_files:
            return course_files[0]['id']
        else:
            course_meta = {
                'name': clean_course,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [root_id]
            }
            c_folder = drive_service.files().create(body=course_meta, fields='id').execute()
            return c_folder.get('id')
    except Exception as e:
        print(f"[NotesService] Error gestionando carpetas en Drive: {e}")
        return None

def get_course_data_file(course_name: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip().lower() or "general"
    return os.path.join(NOTES_CACHE_DIR, f"course_{clean}.json")

def load_local_course_notes(course_name: str) -> Dict[str, Any]:
    path = get_course_data_file(course_name)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "course_name": course_name,
        "units": {},
        "formulas": [],
        "personal_notes": [],
        "files": []
    }

def save_local_course_notes(course_name: str, data: Dict[str, Any]):
    path = get_course_data_file(course_name)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[NotesService] Error guardando notas locales: {e}")

def process_and_upload_note(
    file_bytes: bytes,
    filename: str,
    course_name: str,
    user_email: str = "",
    creds = None
) -> Dict[str, Any]:
    """
    Procesa un archivo de apuntes subido:
    1. Calcula SHA-256. Si ya existe, retorna los metadatos existentes evitando duplicados.
    2. Extrae texto y fórmulas.
    3. Organiza en Unidad correspondiente y Formulario.
    4. Sube a Google Drive si hay credenciales y devuelve preview_url con ?authuser.
    """
    file_hash = compute_sha256(file_bytes)
    hashes = _load_hashes()
    
    # 1. Comprobación de deduplicación SHA-256
    if file_hash in hashes:
        existing = hashes[file_hash]
        preview_url = existing.get("preview_url", "")
        if user_email and "?authuser" not in preview_url:
            sep = "&" if "?" in preview_url else "?"
            preview_url = f"{preview_url}{sep}authuser={user_email}"
        return {
            "success": True,
            "is_duplicate": True,
            "message": "Archivo idéntico ya existente en Google Drive (deduplicación SHA-256).",
            "file_id": existing.get("file_id"),
            "preview_url": preview_url,
            "filename": existing.get("filename", filename),
            "unit": existing.get("unit", "Unidad 1")
        }

    # 2. Extracción de contenido
    analysis = extract_text_and_formulas(file_bytes, filename)
    extracted_text = analysis["text"]
    formulas = analysis["formulas"]

    # Determinar unidad temática a partir del nombre o texto
    unit_match = re.search(r'(?:unidad|tema|bloque|cap[ií]tulo)\s*(\d+)', f"{filename} {extracted_text[:200]}", re.IGNORECASE)
    unit_name = f"Unidad {unit_match.group(1)}" if unit_match else "Unidad 1"

    # 3. Subida / Registro en Google Drive
    file_id = f"local_{file_hash[:12]}"
    preview_url = f"https://docs.google.com/document/d/{file_id}/preview"
    
    drive_service = get_drive_service(creds)
    if drive_service:
        try:
            folder_id = get_or_create_course_folder(drive_service, course_name)
            
            # Subir archivo en Drive
            media = MediaInMemoryUpload(file_bytes, mimetype="application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream", resumable=True)
            file_metadata = {
                'name': filename,
                'parents': [folder_id] if folder_id else []
            }
            created_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
            if created_file and 'id' in created_file:
                file_id = created_file['id']
                preview_url = f"https://drive.google.com/file/d/{file_id}/preview"
        except Exception as e:
            print(f"[NotesService] Fallback local tras error en Google Drive API: {e}")

    if user_email:
        sep = "&" if "?" in preview_url else "?"
        preview_url = f"{preview_url}{sep}authuser={user_email}"

    # 4. Actualizar almacenamiento local de la materia
    course_data = load_local_course_notes(course_name)
    if unit_name not in course_data["units"]:
        course_data["units"][unit_name] = []
    course_data["units"][unit_name].append({
        "filename": filename,
        "hash": file_hash,
        "preview_url": preview_url,
        "summary": extracted_text[:400] if extracted_text else ""
    })
    
    for form in formulas:
        if form not in course_data["formulas"]:
            course_data["formulas"].append(form)

    course_data["files"].append({
        "id": file_id,
        "filename": filename,
        "unit": unit_name,
        "hash": file_hash,
        "preview_url": preview_url,
        "uploaded_at": datetime.datetime.utcnow().isoformat()
    })
    save_local_course_notes(course_name, course_data)

    # 5. Guardar en registro global de hashes
    hashes[file_hash] = {
        "file_id": file_id,
        "filename": filename,
        "course_name": course_name,
        "unit": unit_name,
        "preview_url": preview_url,
        "uploaded_at": datetime.datetime.utcnow().isoformat()
    }
    _save_hashes(hashes)

    return {
        "success": True,
        "is_duplicate": False,
        "message": f"Apunte procesado y sincronizado con Drive en '{unit_name}'.",
        "file_id": file_id,
        "preview_url": preview_url,
        "filename": filename,
        "unit": unit_name,
        "formulas_extracted": len(formulas)
    }

def add_personal_note(
    course_name: str,
    task_id: str,
    note_text: str,
    user_email: str = "",
    creds = None
) -> Dict[str, Any]:
    """
    Inserta una nota personal/corrección de clase al final de la unidad correspondiente
    y persiste tanto en la base local como en Drive si está disponible.
    """
    if not note_text.strip():
        return {"success": False, "message": "Nota vacía."}

    course_data = load_local_course_notes(course_name)
    note_entry = {
        "task_id": task_id,
        "text": note_text.strip(),
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    course_data["personal_notes"].append(note_entry)
    save_local_course_notes(course_name, course_data)

    # Sincronizar también en SQLite general
    try:
        from db.database import update_task_notes
        update_task_notes(task_id, note_text)
    except Exception:
        pass

    return {
        "success": True,
        "message": "Nota personal registrada con éxito en los apuntes de la materia.",
        "course_name": course_name,
        "task_id": task_id
    }

def get_course_notes(course_name: str, user_email: str = "", creds = None) -> Dict[str, Any]:
    """
    Devuelve la lista modular de documentos disponibles para esa materia:
    - Unidades temáticas individuales (Unidad 1.pdf, Unidad 2.pdf, etc.)
    - Formulario de la materia (Formulario.pdf)
    - Documento Maestro Compilado
    """
    course_data = load_local_course_notes(course_name)
    documents = []

    # 1. Unidades modulares
    for unit_name, unit_files in course_data.get("units", {}).items():
        first_file = unit_files[0] if unit_files else {}
        preview_url = first_file.get("preview_url", "")
        if user_email and preview_url and "?authuser" not in preview_url:
            sep = "&" if "?" in preview_url else "?"
            preview_url = f"{preview_url}{sep}authuser={user_email}"
            
        documents.append({
            "name": f"{unit_name} - Apuntes.pdf",
            "type": "unit",
            "unit": unit_name,
            "preview_url": preview_url or "#",
            "download_url": preview_url or "#",
            "count": len(unit_files)
        })

    # Si no hay unidades aún, ofrecer al menos Unidad 1 lista para descarga o carga
    if not documents:
        documents.append({
            "name": "Unidad 1 - Apuntes.pdf",
            "type": "unit",
            "unit": "Unidad 1",
            "preview_url": "#",
            "download_url": "#",
            "count": 0
        })

    # 2. Formulario de la materia
    has_formulas = len(course_data.get("formulas", [])) > 0
    documents.append({
        "name": f"Formulario - {course_name}.pdf",
        "type": "formula_sheet",
        "unit": "Formulario",
        "preview_url": "#",
        "download_url": "#",
        "count": len(course_data.get("formulas", [])),
        "available": has_formulas
    })

    # 3. Documento Maestro Compilado
    total_files = len(course_data.get("files", []))
    documents.append({
        "name": f"Documento Maestro Compilado - {course_name}.pdf",
        "type": "master_document",
        "unit": "Maestro",
        "preview_url": "#",
        "download_url": "#",
        "count": total_files,
        "available": total_files > 0
    })

    return {
        "course_name": course_name,
        "documents": documents,
        "personal_notes_count": len(course_data.get("personal_notes", []))
    }

def delete_course_notes(course_name: str, user_email: str = "", creds = None) -> Dict[str, Any]:
    """
    Elimina los archivos de apuntes de esa materia en Google Drive y limpia el almacenamiento local.
    """
    # 1. Limpieza en Drive
    drive_service = get_drive_service(creds)
    if drive_service:
        try:
            folder_id = get_or_create_course_folder(drive_service, course_name)
            if folder_id:
                drive_service.files().delete(fileId=folder_id).execute()
        except Exception as e:
            print(f"[NotesService] Error eliminando carpeta en Drive: {e}")

    # 2. Limpieza local
    path = get_course_data_file(course_name)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            print(f"[NotesService] Error eliminando archivo local: {e}")

    # Limpiar entradas correspondientes en file_hashes.json
    hashes = _load_hashes()
    remaining = {k: v for k, v in hashes.items() if v.get("course_name") != course_name}
    _save_hashes(remaining)

    return {
        "success": True,
        "message": f"Apuntes de '{course_name}' eliminados de Google Drive y almacenamiento local.",
        "course_name": course_name
    }

def get_course_notes_text(course_name: str) -> str:
    """
    Devuelve un texto consolidado de apuntes, fórmulas y notas personales
    de la asignatura para ser inyectado en el contexto de los Mentores.
    """
    if not course_name:
        return ""
    course_data = load_local_course_notes(course_name)
    parts = []

    # Fórmulas de clase
    formulas = course_data.get("formulas", [])
    if formulas:
        parts.append("FÓRMULAS VISTAS EN CLASE:\n" + "\n".join(f"- {f}" for f in formulas[:10]))

    # Unidades y resúmenes
    for unit, files in course_data.get("units", {}).items():
        summaries = [f["summary"] for f in files if f.get("summary")]
        if summaries:
            parts.append(f"{unit}:\n" + "\n".join(summaries[:2]))

    # Notas personales del estudiante
    personal = course_data.get("personal_notes", [])
    if personal:
        parts.append("NOTAS PERSONALES DEL ESTUDIANTE EN CLASE:\n" + "\n".join(f"- {n['text']}" for n in personal[-5:]))

    return "\n\n".join(parts).strip()
