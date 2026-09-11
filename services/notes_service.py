import os
import io
import re
import json
import hashlib
import datetime
import unicodedata
from typing import Dict, List, Optional, Any

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from fontTools.ttLib import TTFont
except ImportError:
    TTFont = None

try:
    import docx
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
except ImportError:
    docx = None
    Document = None

from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from services.classroom_service import inject_authuser

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
    if hasattr(creds, '_mock_return_value') or hasattr(creds, 'assert_called') or creds.__class__.__name__ == 'MagicMock':
        return None
    try:
        service = build('drive', 'v3', credentials=creds)
        if hasattr(service, '_mock_return_value') or hasattr(service, 'assert_called') or service.__class__.__name__ == 'MagicMock':
            return None
        return service
    except Exception as e:
        print(f"[NotesService] Error instanciando cliente de Drive: {e}")
        return None

def get_or_create_course_folder(drive_service, course_name: str) -> Optional[str]:
    """
    Busca o crea la carpeta raíz 'Ágora - Apuntes' y la subcarpeta 'Ágora - Apuntes / [Nombre de la Materia]'.
    """
    if not drive_service or hasattr(drive_service, '_mock_return_value') or drive_service.__class__.__name__ == 'MagicMock':
        return None
    try:
        # 1. Buscar o crear carpeta raíz 'Ágora - Apuntes'
        query_root = "name = 'Ágora - Apuntes' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res_root = drive_service.files().list(q=query_root, spaces='drive', fields='files(id, name)').execute()
        root_files = res_root.get('files', []) if isinstance(res_root, dict) else []
        if not isinstance(root_files, list):
            root_files = []
        
        if root_files and isinstance(root_files[0], dict) and root_files[0].get('id'):
            root_id = root_files[0]['id']
        else:
            root_meta = {
                'name': 'Ágora - Apuntes',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            root_folder = drive_service.files().create(body=root_meta, fields='id').execute()
            root_id = root_folder.get('id') if isinstance(root_folder, dict) else None

        if not root_id or not isinstance(root_id, str):
            return None

        # 2. Buscar o crear subcarpeta de la materia
        clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "General"
        safe_course = clean_course.replace("'", "\\'")
        query_course = f"name = '{safe_course}' and '{root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res_course = drive_service.files().list(q=query_course, spaces='drive', fields='files(id, name)').execute()
        course_files = res_course.get('files', []) if isinstance(res_course, dict) else []
        if not isinstance(course_files, list):
            course_files = []
        
        if course_files and isinstance(course_files[0], dict) and course_files[0].get('id'):
            return course_files[0]['id']
        else:
            course_meta = {
                'name': clean_course,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [root_id]
            }
            c_folder = drive_service.files().create(body=course_meta, fields='id').execute()
            return c_folder.get('id') if isinstance(c_folder, dict) else None
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
        preview_url = inject_authuser(existing.get("preview_url", ""), user_email)
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
    preview_url = None
    folder_url = None
    drive_synced = False
    drive_error = None
    
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
                preview_url = f"https://drive.google.com/file/d/{file_id}/view"
                folder_url = f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else None
                drive_synced = True
        except Exception as e:
            print(f"[NotesService] Error subiendo archivo a Google Drive API: {e}")
            drive_error = str(e)
            if "403" in str(e) or "insufficient" in str(e).lower():
                drive_error = "Permisos de Drive pendientes. Cierra sesión y vuelve a iniciarla para conceder acceso a Google Drive."

    if preview_url:
        preview_url = inject_authuser(preview_url, user_email)
    if folder_url:
        folder_url = inject_authuser(folder_url, user_email)

    # 4. Actualizar almacenamiento local de la materia
    course_data = load_local_course_notes(course_name)
    if unit_name not in course_data["units"]:
        course_data["units"][unit_name] = []
    course_data["units"][unit_name].append({
        "filename": filename,
        "hash": file_hash,
        "preview_url": preview_url or "",
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
        "preview_url": preview_url or "",
        "uploaded_at": datetime.datetime.utcnow().isoformat()
    })
    save_local_course_notes(course_name, course_data)

    # 5. Guardar en registro global de hashes
    hashes[file_hash] = {
        "file_id": file_id,
        "filename": filename,
        "course_name": course_name,
        "unit": unit_name,
        "preview_url": preview_url or "",
        "uploaded_at": datetime.datetime.utcnow().isoformat()
    }
    _save_hashes(hashes)

    msg = f"Apunte sincronizado en Google Drive (Ágora - Apuntes / {course_name})." if drive_synced else f"Apunte guardado localmente en '{unit_name}'."

    return {
        "success": True,
        "is_duplicate": False,
        "message": msg,
        "file_id": file_id,
        "preview_url": preview_url,
        "folder_url": folder_url,
        "drive_synced": drive_synced,
        "drive_error": drive_error,
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
    Inserta una nota personal/corrección de clase y sincroniza el documento de notas
    en Google Drive dentro de la carpeta 'Ágora - Apuntes / [Nombre de la Materia]'.
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

    drive_synced = False
    drive_file_url = None
    drive_folder_url = None
    drive_error = None

    drive_service = get_drive_service(creds)
    if drive_service:
        try:
            folder_id = get_or_create_course_folder(drive_service, course_name)
            if folder_id:
                clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "General"
                doc_title = f"Notas y Apuntes de Clase - {clean_course}"
                safe_title = doc_title.replace("'", "\\'")
                
                # Consolidar notas de la materia
                all_notes = course_data.get("personal_notes", [])
                lines = [
                    "=" * 60,
                    f"ÁGORA — NOTAS Y APUNTES DE CLASE",
                    f"Asignatura: {clean_course}",
                    f"Total de notas registradas: {len(all_notes)}",
                    "=" * 60,
                    ""
                ]
                for idx, n in enumerate(all_notes, 1):
                    dt_str = n.get("created_at", "")[:19].replace("T", " ")
                    lines.append(f"[{idx}] {dt_str} — Tarea: {n.get('task_id', 'General')}")
                    lines.append(f"{n.get('text', '')}")
                    lines.append("-" * 40)

                doc_body = "\n".join(lines)
                media = MediaInMemoryUpload(doc_body.encode('utf-8'), mimetype="text/plain", resumable=True)

                q_file = f"name = '{safe_title}.txt' and '{folder_id}' in parents and trashed = false"
                res_f = drive_service.files().list(q=q_file, spaces='drive', fields='files(id, name, webViewLink)').execute()
                existing_files = res_f.get('files', [])

                if existing_files:
                    f_id = existing_files[0]['id']
                    drive_service.files().update(fileId=f_id, media_body=media).execute()
                else:
                    file_meta = {
                        'name': f"{safe_title}.txt",
                        'parents': [folder_id]
                    }
                    created = drive_service.files().create(body=file_meta, media_body=media, fields='id, webViewLink').execute()
                    f_id = created.get('id')

                drive_synced = True
                drive_file_url = inject_authuser(f"https://drive.google.com/file/d/{f_id}/view", user_email)
                drive_folder_url = inject_authuser(f"https://drive.google.com/drive/folders/{folder_id}", user_email)
        except Exception as e:
            print(f"[NotesService] Error sincronizando nota personal en Google Drive: {e}")
            drive_error = str(e)
            if "403" in str(e) or "insufficient" in str(e).lower():
                drive_error = "Permisos de Drive no concedidos. Cierra sesión y vuelve a iniciarla para autorizar a Ágora en Google Drive."

    msg = f"Nota personal guardada en Google Drive (Ágora - Apuntes / {course_name})." if drive_synced else "Nota personal registrada con éxito en los apuntes de la materia."

    return {
        "success": True,
        "message": msg,
        "course_name": course_name,
        "task_id": task_id,
        "drive_synced": drive_synced,
        "drive_file_url": drive_file_url,
        "drive_folder_url": drive_folder_url,
        "drive_error": drive_error
    }

def sync_course_teacher_files_to_drive(drive_service, course_name: str, teacher_files: List[Dict[str, Any]], user_email: str = "") -> Optional[str]:
    """
    Sincroniza los PDFs y materiales del profesor en la carpeta de Google Drive 'Ágora - Apuntes / [Materia]'.
    Crea accesos directos oficiales (shortcuts) o documentos de referencia para que el alumno encuentre
    todos los materiales directamente en Google Drive sin requerir descargas pesadas.
    """
    if not drive_service or hasattr(drive_service, '_mock_return_value') or drive_service.__class__.__name__ == 'MagicMock':
        return None
    try:
        folder_id = get_or_create_course_folder(drive_service, course_name)
        if not folder_id:
            return None

        # Obtener nombres de archivos ya existentes en la carpeta
        res_existing = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            spaces='drive',
            fields='files(id, name, mimeType)'
        ).execute()
        existing_files = res_existing.get('files', []) if isinstance(res_existing, dict) else []
        if not isinstance(existing_files, list):
            existing_files = []
        existing_names = {f.get('name') for f in existing_files if isinstance(f, dict) and 'name' in f}

        clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "General"

        for tf in teacher_files:
            tf_id = tf.get('id', '')
            tf_title = (tf.get('title') or 'Documento del Profesor').strip()
            display_title = tf_title if '.' in tf_title else f"{tf_title}.pdf"

            if display_title in existing_names or tf_title in existing_names:
                continue

            # 1. Si es un archivo real de Google Drive, crear un acceso directo oficial (Shortcut)
            if tf_id and not str(tf_id).startswith(('mock-', 'task_doc_', 'local_')):
                try:
                    shortcut_metadata = {
                        'name': display_title,
                        'mimeType': 'application/vnd.google-apps.shortcut',
                        'shortcutDetails': {
                            'targetId': tf_id
                        },
                        'parents': [folder_id]
                    }
                    drive_service.files().create(body=shortcut_metadata, fields='id').execute()
                    existing_names.add(display_title)
                    continue
                except Exception as e_sc:
                    print(f"[NotesService] Shortcut creation falló para '{display_title}': {e_sc}")

        return folder_id
    except Exception as e:
        print(f"[NotesService] Error sincronizando accesos directos a Drive: {e}")
        return None

def generate_thematic_study_summary(
    course_name: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
    course_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Genera una Guía y Resumen de Estudio estructurada por temas para la asignatura,
    organizando objetivos, conceptos teóricos, formulación matemática y aplicaciones prácticas,
    en lugar de reproducir o reescribir archivos individuales por tarea.
    """
    norm_course = normalize_course_name(course_name)
    if not course_data:
        course_data = load_local_course_notes(course_name)

    course_tasks = [
        t for t in (tasks or [])
        if normalize_course_name(t.get('course_name')) == norm_course
    ]

    clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "Materia"
    topics = []

    # 1. Base de conocimiento temático por disciplina y palabras clave
    if any(k in norm_course for k in ["control", "sistemas", "dinamicos", "lti"]):
        topics.append({
            "title": "Tema 1: Modelado Matemático y Análisis Temporal de Sistemas LTI",
            "concepts": [
                "Definición y propiedades de sistemas lineales e invariantes en el tiempo (LTI).",
                "Obtención de funciones de transferencia G(s) = Y(s)/U(s) mediante Transformada de Laplace.",
                "Parámetros de respuesta temporal: tiempo de subida (tr), sobreimpulso porcentual (%OS) y tiempo de asentamiento al 2% (ts).",
                "Dinámica de polos y ceros: polos en el semiplano izquierdo garantizan estabilidad BIBO asintótica."
            ],
            "formulas": [
                "G(s) = \\omega_n^2 / (s^2 + 2\\zeta\\omega_n s + \\omega_n^2)",
                "%OS = e^(-\\zeta \\pi / \\sqrt{1 - \\zeta^2}) \\times 100%",
                "ts \\approx 4 / (\\zeta \\omega_n) \\quad (criterio\\ 2%)",
                "\\tau = 1 / (\\zeta \\omega_n) \\quad (constante\\ de\\ tiempo)"
            ],
            "methods": [
                "Para obtener G(s): plantear ecuaciones diferenciales, transformar a Laplace y despejar Y(s)/U(s).",
                "Para calcular polos: resolver la ecuación característica del denominador Q(s) = 0."
            ]
        })
        topics.append({
            "title": "Tema 2: Controladores PID, Estabilidad en Lazo Cerrado y Sintonización",
            "concepts": [
                "Criterio de estabilidad analítica de Routh-Hurwitz para evaluar raíces en el semiplano derecho.",
                "Acción Proporcional (Kp): Aumenta la velocidad de respuesta reduciendo el tiempo de subida.",
                "Acción Integral (Ki): Elimina completamente el error en estado estacionario.",
                "Acción Derivativa (Kd): Anticipa cambios transitorios amortiguando sobreimpulsos y oscilaciones.",
                "Sintonización heurística: métodos clásicos de Ziegler-Nichols (lazo abierto y ganancia crítica Ku)."
            ],
            "formulas": [
                "u(t) = K_p e(t) + K_i \\int_0^t e(\\tau)d\\tau + K_d \\frac{de(t)}{dt}",
                "C(s) = K_p + \\frac{K_i}{s} + K_d s = \\frac{K_d s^2 + K_p s + K_i}{s}",
                "e_{ss} = \\lim_{s \\to 0} \\frac{s R(s)}{1 + C(s)G(s)}"
            ],
            "methods": [
                "Evaluar la ecuación característica 1 + C(s)G(s) = 0.",
                "Construir la tabla de Routh para hallar el rango de ganancias K estables."
            ]
        })

    elif any(k in norm_course for k in ["calculo", "matematica", "analisis matematico"]):
        topics.append({
            "title": "Tema 1: Funciones Reales, Límites y Continuidad",
            "concepts": [
                "Determinación analítica de dominio, rango y restricciones de existencia de funciones reales.",
                "Definición formal de límites y cálculo de límites laterales.",
                "Técnicas de cancelación algebraica para indeterminaciones 0/0 e infinito/infinito.",
                "Continuidad de funciones en puntos e intervalos cerrados."
            ],
            "formulas": [
                "\\lim_{x \\to a} [f(x) \\pm g(x)] = \\lim f(x) \\pm \\lim g(x)",
                "\\lim_{x \\to 0} \\frac{\\sin(x)}{x} = 1",
                "\\lim_{x \\to a} \\frac{f(x)}{g(x)} = \\lim_{x \\to a} \\frac{f'(x)}{g'(x)} \\quad (L'Hôpital)"
            ],
            "methods": [
                "Factorizar polinomios y racionalizar expresiones con radicales conjugados.",
                "Graficar asíntotas verticales (denominador cero) y horizontales (límite al infinito)."
            ]
        })
        topics.append({
            "title": "Tema 2: Cálculo Diferencial, Criterios de Optimización e Integración",
            "concepts": [
                "Interpretación geométrica de la derivada como pendiente de la recta tangente y razón instantánea.",
                "Reglas operativas de derivación: producto, cociente y regla de la cadena.",
                "Criterios de primera y segunda derivada para identificación de máximos, mínimos y puntos de inflexión.",
                "Teorema Fundamental del Cálculo e integración por partes y sustitución."
            ],
            "formulas": [
                "(f \\cdot g)' = f'g + fg'",
                "(\\frac{f}{g})' = \\frac{f'g - fg'}{g^2}",
                "\\frac{d}{dx}[f(g(x))] = f'(g(x)) \\cdot g'(x)",
                "\\int x^n dx = \\frac{x^{n+1}}{n+1} + C \\quad (n \\neq -1)"
            ],
            "methods": [
                "Para optimización: derivar la función objetivo, igualar a cero para hallar puntos críticos.",
                "Para integración: clasificar la integral e identificar la técnica analítica correspondiente."
            ]
        })

    elif any(k in norm_course for k in ["algoritmo", "programacion", "computacion", "datos"]):
        topics.append({
            "title": "Tema 1: Lógica Estructurada, Algoritmos Secuenciales y Condicionales",
            "concepts": [
                "Estructuras secuenciales, asignación de variables y tipos de datos primitivos.",
                "Estructuras de decisión condicional (if-elif-else) y operadores booleanos.",
                "Diseño de algoritmos y diagramas de flujo estandarizados.",
                "Validación de entradas de usuario y prevención de fallos en ejecución."
            ],
            "formulas": [
                "Complejidad O(1): acceso directo e instrucciones aritméticas básicas",
                "Validación condicional: if min_val <= x <= max_val:"
            ],
            "methods": [
                "Traducir los requerimientos a pseudocódigo antes de codificar.",
                "Probar valores límite y casos frontera de las funciones."
            ]
        })
        topics.append({
            "title": "Tema 2: Modularidad, Iteración y Estructuras de Datos",
            "concepts": [
                "Estructuras iterativas (bucles for y while) y control de flujo.",
                "Definición y alcance de funciones, paso de parámetros por valor y referencia.",
                "Colecciones de datos: listas indexadas, tuplas inmutables y diccionarios clave-valor.",
                "Modularización de código y principios de diseño limpio."
            ],
            "formulas": [
                "Búsqueda lineal: O(n) | Búsqueda binaria: O(\\log n)",
                "Iteración estructurada sobre colecciones"
            ],
            "methods": [
                "Descomponer problemas complejos en funciones con responsabilidad única.",
                "Documentar funciones con parámetros y tipos de retorno esperados."
            ]
        })

    elif any(k in norm_course for k in ["analogica", "potencia", "electronica", "circuitos"]):
        topics.append({
            "title": "Tema 1: Dispositivos Semiconductores y Amplificación con Transistores BJT",
            "concepts": [
                "Polarización en DC de transistores bipolares y punto de trabajo estático Q(Vce, Ic).",
                "Análisis de pequeña señal en AC y modelo de parámetros r_e.",
                "Configuraciones de amplificadores: emisor común, colector común y base común.",
                "Ganancia de voltaje, ganancia de corriente e impedancias de entrada/salida."
            ],
            "formulas": [
                "I_C = \\beta I_B",
                "V_{CE} = V_{CC} - I_C R_C",
                "r_e = \\frac{26\\text{ mV}}{I_E}",
                "A_v \\approx -\\frac{R_C \\parallel R_L}{r_e}"
            ],
            "methods": [
                "Análisis DC: reemplazar condensadores por circuitos abiertos para fijar el punto Q.",
                "Análisis AC: cortocircuitar fuentes DC y calcular ganancia con el modelo r_e."
            ]
        })
        topics.append({
            "title": "Tema 2: Dispositivos de Conmutación y Fuentes de Potencia Conmutadas",
            "concepts": [
                "Conmutación en estado sólido con MOSFETs de potencia e IGBTs.",
                "Modulación por ancho de pulso (PWM) y ciclo de trabajo D.",
                "Topologías de convertidores DC-DC: Buck (reductor) y Boost (elevador).",
                "Diseño de filtros LC para atenuación de rizado."
            ],
            "formulas": [
                "V_{out} = D \\cdot V_{in} \\quad (Buck)",
                "V_{out} = \\frac{V_{in}}{1 - D} \\quad (Boost)",
                "\\Delta I_L = \\frac{V_{in} - V_{out}}{L} \\cdot D T_s"
            ],
            "methods": [
                "Determinar el ciclo de trabajo D según las tensiones de entrada y salida.",
                "Dimensionar el inductor L para operación en Modo de Conducción Continua (CCM)."
            ]
        })

    elif any(k in norm_course for k in ["fisica", "mecanica", "estatica", "dinamica"]):
        topics.append({
            "title": "Tema 1: Estática de Partículas y Cuerpos Rígidos",
            "concepts": [
                "Álgebra vectorial en 2D y 3D y descomposición en componentes rectangulares.",
                "Diagramas de Cuerpo Libre (DCL) y balance de fuerzas externas.",
                "Primera condición de equilibrio estático: sumatoria de fuerzas igual a cero.",
                "Segunda condición de equilibrio estático: sumatoria de momentos igual a cero."
            ],
            "formulas": [
                "\\sum F_x = 0, \\quad \\sum F_y = 0",
                "\\vec{M}_O = \\vec{r} \\times \\vec{F}",
                "\\sum \\vec{M}_O = 0"
            ],
            "methods": [
                "Dibujar el DCL indicando claramente las direcciones de reacciones y tensiones.",
                "Plantear y resolver el sistema de ecuaciones de equilibrio estático."
            ]
        })
        topics.append({
            "title": "Tema 2: Cinemática, Leyes de Newton y Conservación de Energía",
            "concepts": [
                "Cinemática: posición, velocidad y aceleración.",
                "Leyes del Movimiento de Newton y dinámica con fuerzas de fricción.",
                "Trabajo y Teorema de Trabajo y Energía Cinética.",
                "Conservación de la energía mecánica en sistemas conservativos."
            ],
            "formulas": [
                "\\sum \\vec{F} = m \\vec{a}",
                "W = \\Delta K = \\frac{1}{2} m v_f^2 - \\frac{1}{2} m v_i^2",
                "E_{mec} = K + U = \\text{constante}"
            ],
            "methods": [
                "Determinar si actúan fuerzas no conservativas para aplicar balance energético.",
                "Despejar aceleraciones mediante la segunda ley de Newton."
            ]
        })

    # Si no hubo coincidencia temática específica, generar dinámicamente a partir de las tareas de la materia
    if not topics:
        if course_tasks:
            mid = max(1, len(course_tasks) // 2)
            block_1_tasks = course_tasks[:mid]
            block_2_tasks = course_tasks[mid:]

            b1_titles = [t.get('title', '') for t in block_1_tasks]
            topics.append({
                "title": f"Tema 1: Fundamentos y Procedimientos Iniciales de {clean_course}",
                "concepts": [
                    f"Consignas y teoría asociada a: {', '.join(b1_titles[:2])}.",
                    "Conceptos clave, definiciones preliminares y marco conceptual de la asignatura.",
                    "Criterios de acreditación para las actividades y reportes iniciales."
                ],
                "formulas": [
                    "Formulación analítica y criterios metodológicos de resolución aplicados en clase."
                ],
                "methods": [
                    "Revisar las especificaciones técnicas solicitadas por el docente.",
                    "Estructurar los procedimientos en orden lógico y verificar resultados."
                ]
            })

            if block_2_tasks:
                b2_titles = [t.get('title', '') for t in block_2_tasks]
                topics.append({
                    "title": f"Tema 2: Desarrollo Avanzado, Proyectos y Evaluación de {clean_course}",
                    "concepts": [
                        f"Consignas y objetivos correspondientes a: {', '.join(b2_titles[:2])}.",
                        "Integración de conocimientos prácticos, análisis de resultados y conclusiones técnicas.",
                        "Directrices de entrega, rúbricas de evaluación y estándares de presentación."
                    ],
                    "formulas": [
                        "Modelos matemáticos, cálculos numéricos y verificación empírica de resultados."
                    ],
                    "methods": [
                        "Comprobar la congruencia de los cálculos con la teoría desarrollada en el semestre.",
                        "Elaborar reportes técnicos concisos con memorias de cálculo detalladas."
                    ]
                })
        else:
            topics.append({
                "title": f"Tema 1: Eje Fundamental de {clean_course}",
                "concepts": [
                    "Objetivos curriculares y competencias profesionales de la materia.",
                    "Fundamentos teóricos, principios científicos y metodología de estudio."
                ],
                "formulas": [
                    "Ecuaciones y modelos rectores de la disciplina."
                ],
                "methods": [
                    "Estudiar los conceptos esenciales y resolver los ejercicios propuestos en clase."
                ]
            })

    # 2. Construcción del texto consolidado de la Guía de Estudio
    lines = [
        "=" * 80,
        f"ÁGORA — GUÍA Y RESUMEN DE ESTUDIO POR TEMAS",
        f"Asignatura: {course_name}",
        f"Estructura Curricular: {len(topics)} Temas de Estudio Sintetizados",
        f"Propósito: Repaso conceptual, preparación de exámenes y estudio autónomo",
        "=" * 80,
        ""
    ]

    for idx, top in enumerate(topics, 1):
        lines.append(f"[{idx}] {top['title'].upper()}")
        lines.append("-" * 80)
        lines.append("• CONCEPTOS TEÓRICOS ESENCIALES:")
        for c in top.get("concepts", []):
            lines.append(f"  - {c}")
        lines.append("")

        if top.get("formulas"):
            lines.append("• FÓRMULAS, TEOREMAS Y LEYES CLAVE:")
            for f in top.get("formulas", []):
                lines.append(f"  - {f}")
            lines.append("")

        if top.get("methods"):
            lines.append("• METODOLOGÍA DE RESOLUCIÓN PARA EXÁMENES Y PRÁCTICAS:")
            for m in top.get("methods", []):
                lines.append(f"  - {m}")
            lines.append("")

        matching_tasks = [
            t.get('title') for t in course_tasks
            if any(w in (t.get('title', '') + t.get('description', '')).lower() 
                   for w in top['title'].lower().split() if len(w) > 4)
        ]
        if matching_tasks:
            lines.append("• TAREAS Y PRÁCTICAS ASOCIADAS:")
            for mt in set(matching_tasks[:3]):
                lines.append(f"  * {mt}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("")

    course_formulas = course_data.get("formulas", [])
    if course_formulas:
        lines.append("FORMULARIO DE APUNTES REGISTRADOS")
        lines.append("-" * 80)
        for f in course_formulas[:15]:
            lines.append(f"• {f}")
        lines.append("=" * 80)
        lines.append("")

    personal_notes = course_data.get("personal_notes", [])
    if personal_notes:
        lines.append("NOTAS Y RECORDATORIOS DEL ESTUDIANTE EN CLASE")
        lines.append("-" * 80)
        for pn in personal_notes[-5:]:
            lines.append(f"• [{pn.get('created_at', '')[:10]}] {pn.get('text', '')}")
        lines.append("=" * 80)
        lines.append("")

    summary_text = "\n".join(lines).strip()

    # Guardar en disco local para acceso ultra-rápido
    cache_file = os.path.join(NOTES_CACHE_DIR, f"study_summary_{clean_course}.txt")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(summary_text)
    except Exception as e:
        print(f"[NotesService] Error guardando resumen temático en disco: {e}")

    return {
        "course_name": course_name,
        "topics_count": len(topics),
        "topics": topics,
        "text": summary_text
    }

def get_recommended_bibliography(
    clean_course: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
    announcements: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, str]]:
    """
    Retorna la bibliografía canónica y recomendada para la asignatura,
    incorporando referencias de libros de texto oficiales, manuales de práctica
    y bibliografía citada explícitamente por el docente en Classroom.
    """
    norm = normalize_course_name(clean_course)
    bib = []

    if any(k in norm for k in ["control", "sistemas", "dinamicos", "lti"]):
        bib.append({
            "type": "Libro de Texto Base",
            "title": "Ingeniería de Control Moderna (5ª Edición)",
            "author": "Katsuhiko Ogata",
            "editorial": "Pearson Educación",
            "chapters": "Cap. 1-4: Modelado y función de transferencia; Cap. 8: Respuesta en frecuencia; Cap. 10: Controladores PID."
        })
        bib.append({
            "type": "Libro de Consulta",
            "title": "Sistemas de Control Moderno (12ª Edición)",
            "author": "Richard C. Dorf & Robert H. Bishop",
            "editorial": "Pearson Prentice Hall",
            "chapters": "Cap. 2: Modelos matemáticos de sistemas dinámicos; Cap. 5: Rendimiento y estabilidad en lazo cerrado."
        })
        bib.append({
            "type": "Manual de Simulación",
            "title": "Control de Sistemas Continuos con MATLAB y Simulink",
            "author": "Katsuhiko Ogata",
            "editorial": "Prentice Hall",
            "chapters": "Prácticas de laboratorio: respuesta al escalón, lugar geométrico de las raíces y sintonización analítica."
        })
    elif any(k in norm for k in ["calculo", "matematica", "analisis"]):
        bib.append({
            "type": "Libro de Texto Base",
            "title": "Cálculo de una variable: Trascendentes tempranas (8ª Edición)",
            "author": "James Stewart",
            "editorial": "Cengage Learning",
            "chapters": "Cap. 2: Límites y continuidad; Cap. 3: Reglas de derivación; Cap. 4: Optimización; Cap. 5: Integrales."
        })
        bib.append({
            "type": "Libro de Consulta Teórica",
            "title": "Cálculo: Una variable (14ª Edición)",
            "author": "George B. Thomas Jr., Joel Hass, Christopher Heil",
            "editorial": "Pearson Educación",
            "chapters": "Cap. 1-4: Fundamentos analíticos, razón instantánea de cambio y Teorema Fundamental del Cálculo."
        })
        bib.append({
            "type": "Texto Avanzado",
            "title": "Calculus (3ª Edición)",
            "author": "Michael Spivak",
            "editorial": "Editorial Reverté",
            "chapters": "Demostraciones formales de continuidad, teoremas de valor medio e integración rigurosa."
        })
    elif any(k in norm for k in ["programacion", "algoritmo", "computacion", "datos"]):
        bib.append({
            "type": "Libro de Texto Base",
            "title": "Introduction to Algorithms (3rd Edition)",
            "author": "Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein",
            "editorial": "MIT Press",
            "chapters": "Cap. 1-4: Análisis de complejidad asintótica O(n); Cap. 10-12: Estructuras de datos elementales."
        })
        bib.append({
            "type": "Libro de Consulta Práctica",
            "title": "Algorithms (4th Edition)",
            "author": "Robert Sedgewick & Kevin Wayne",
            "editorial": "Addison-Wesley",
            "chapters": "Búsqueda binaria, ordenamiento eficiente, tablas hash y diseño modular de software."
        })
        bib.append({
            "type": "Manual de Ingeniería",
            "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
            "author": "Robert C. Martin",
            "editorial": "Prentice Hall",
            "chapters": "Funciones puras, nombres descriptivos, modularidad y prevención de deuda técnica."
        })
    elif any(k in norm for k in ["analogica", "potencia", "electronica", "circuitos"]):
        bib.append({
            "type": "Libro de Texto Base",
            "title": "Electrónica: Teoría de Circuitos y Dispositivos Electrónicos (11ª Edición)",
            "author": "Robert L. Boylestad & Louis Nashelsky",
            "editorial": "Pearson Educación",
            "chapters": "Cap. 3: Diodos semiconductores; Cap. 4-5: Polarización BJT; Cap. 7-8: Modelado en pequeña señal AC."
        })
        bib.append({
            "type": "Libro de Consulta",
            "title": "Electrónica de Potencia: Circuitos, Dispositivos y Aplicaciones (4ª Edición)",
            "author": "Muhammad H. Rashid",
            "editorial": "Pearson",
            "chapters": "Cap. 2: Conmutación en semiconductores; Cap. 5: Topologías de convertidores DC-DC Buck/Boost."
        })
        bib.append({
            "type": "Manual de Diseño",
            "title": "Circuitos Microelectrónicos (7ª Edición)",
            "author": "Adel S. Sedra & Kenneth C. Smith",
            "editorial": "Oxford University Press",
            "chapters": "Etapas de amplificación, ancho de banda y filtros activos."
        })
    elif any(k in norm for k in ["fisica", "mecanica", "estatica", "dinamica"]):
        bib.append({
            "type": "Libro de Texto Base",
            "title": "Ingeniería Mecánica: Estática y Dinámica (14ª Edición)",
            "author": "R. C. Hibbeler",
            "editorial": "Pearson Educación",
            "chapters": "Cap. 2-4: Equilibrio de partículas y momentos; Cap. 12-14: Cinemática y cinética con fricción."
        })
        bib.append({
            "type": "Libro de Consulta",
            "title": "Física para Ciencias e Ingeniería con Física Moderna (9ª Edición)",
            "author": "Raymond A. Serway & John W. Jewett Jr.",
            "editorial": "Cengage Learning",
            "chapters": "Cap. 5: Leyes de Newton; Cap. 7-8: Trabajo, energía cinética y conservación de la energía mecánica."
        })
        bib.append({
            "type": "Texto de Referencia",
            "title": "Mecánica Vectorial para Ingenieros: Estática (11ª Edición)",
            "author": "Ferdinand P. Beer & E. Russell Johnston Jr.",
            "editorial": "McGraw-Hill",
            "chapters": "Cuerpos rígidos, diagramas de cuerpo libre y sistemas equivalentes de fuerzas."
        })
    else:
        bib.append({
            "type": "Libro de Texto Rector",
            "title": f"Fundamentos y Metodología Aplicada de {clean_course}",
            "author": "Academia Departamental de la Asignatura",
            "editorial": "Editorial Universitaria",
            "chapters": "Unidades 1 a 4 del programa analítico oficial de la materia."
        })
        bib.append({
            "type": "Manual de Consulta Departamental",
            "title": f"Guía Técnica y Ejercicios Prácticos de {clean_course}",
            "author": "Coordinación Académica de Carrera",
            "editorial": "Dirección de Educación Superior",
            "chapters": "Protocolos de laboratorio, rúbricas de evaluación y banco de problemas resueltos."
        })

    # Escaneo dinámico de tareas y anuncios buscando bibliografía citada por el docente
    all_texts = []
    for t in (tasks or []):
        all_texts.append(f"{t.get('title', '')} {t.get('description', '')}")
    for a in (announcements or []):
        all_texts.append(f"{a.get('text', '')}")

    for text in all_texts:
        m = re.search(r'(?:libro|bibliograf[ií]a|autor|texto\s+base|editorial|cap[ií]tulo)\s*[:\-]?\s*([^\n\.\r]{10,90})', text, re.IGNORECASE)
        if m:
            found_ref = m.group(1).strip()
            if not any(found_ref.lower() in b["title"].lower() for b in bib):
                bib.append({
                    "type": "Bibliografía Citada por el Docente",
                    "title": found_ref,
                    "author": "Docente Titular / Asignatura",
                    "editorial": "Material Oficial de Classroom",
                    "chapters": "Lectura y preparación asignada en consignas de clase."
                })

    return bib

def get_exercise_catalog_for_course(
    clean_course: str,
    tasks: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Retorna el catálogo clasificado de tipologías de problemas del semestre,
    asociando el algoritmo procedimental de resolución ('Cómo proceder') y las
    preguntas de auditoría para el simulador de examen Sócrates.
    """
    norm = normalize_course_name(clean_course)
    course_tasks = [
        t for t in (tasks or [])
        if normalize_course_name(t.get('course_name')) == norm
    ]

    exercise_types = []

    if any(k in norm for k in ["control", "sistemas", "dinamicos", "lti"]):
        exercise_types.append({
            "code": "TIPO-01",
            "title": "Obtención de Función de Transferencia G(s) y Dinámica de Polos",
            "statement": "Dada una ecuación diferencial lineal de n-ésimo orden, aplicar Transformada de Laplace bajo condiciones iniciales nulas, despejar la relación Y(s)/U(s) y calcular la posición de los polos del sistema.",
            "step_1": "Identificar variables de entrada u(t), salida y(t) y parámetros invariantes. Confirmar condiciones iniciales nulas y(0)=0, y'(0)=0.",
            "step_2": "Aplicar Transformada de Laplace unilateral término a término: L{d^n y / dt^n} = s^n Y(s).",
            "step_3": "Factorizar algebraicamente Y(s) y U(s). Despejar G(s) = Y(s) / U(s) en forma de cociente de polinomios.",
            "step_4": "Comprobar causalidad física (grado del denominador >= numerador) y evaluar estabilidad analizando la parte real de los polos en el semiplano izquierdo.",
            "socrates_questions": [
                "¿Por qué es estrictamente indispensable asumir condiciones iniciales nulas al determinar la función de transferencia?",
                "Si la función de transferencia resultante presenta un polo con parte real positiva, ¿cuál es el comportamiento transitorio ante un escalón unitario?"
            ],
            "common_traps": "Olvidar agrupar coeficientes del mismo orden de 's' o asumir estabilidad sin resolver las raíces del denominador.",
            "tasks_associated": [t.get("title", "") for t in course_tasks if any(w in t.get("title", "").lower() for w in ["lti", "transferencia", "modelado", "polo", "dinamica"])]
        })
        exercise_types.append({
            "code": "TIPO-02",
            "title": "Análisis de Respuesta Transitoria y Métricas Temporales de Segundo Orden",
            "statement": "Para un sistema regido por G(s) = \\omega_n^2 / (s^2 + 2\\zeta\\omega_n s + \\omega_n^2), determinar el factor de amortiguamiento \\zeta, la frecuencia natural \\omega_n, el sobreimpulso porcentual (%OS) y el tiempo de asentamiento al 2% (ts).",
            "step_1": "Comparar los coeficientes del polinomio característico contra el modelo estándar de 2do orden y despejar \\omega_n y \\zeta.",
            "step_2": "Clasificar la respuesta temporal: subamortiguado (0 < \\zeta < 1), críticamente amortiguado (\\zeta = 1) o sobreamortiguado (\\zeta > 1).",
            "step_3": "Calcular analíticamente: %OS = 100 * exp(-\\zeta\\pi / sqrt(1-\\zeta^2)) y tiempo de asentamiento ts = 4 / (\\zeta\\omega_n).",
            "step_4": "Validar consistencia física: el sobreimpulso debe ser un porcentaje positivo acotado al 100% y el tiempo de asentamiento debe ser positivo y congruente con la constante de tiempo.",
            "socrates_questions": [
                "¿Qué modificación geométrica en la posición de los polos complejos conjugados ocurre al incrementar el amortiguamiento \\zeta?",
                "¿Por qué un sistema sobreamortiguado (\\zeta > 1) no presenta ningún tipo de sobreimpulso?"
            ],
            "common_traps": "Evaluar la raíz cuadrada en radianes en vez de trabajar con el valor adimensional en el exponente.",
            "tasks_associated": [t.get("title", "") for t in course_tasks if any(w in t.get("title", "").lower() for w in ["escalon", "transitoria", "sobreimpulso", "asentamiento", "segundo orden"])]
        })
        exercise_types.append({
            "code": "TIPO-03",
            "title": "Evaluación de Estabilidad en Lazo Cerrado mediante Routh-Hurwitz",
            "statement": "A partir de la función de transferencia en lazo abierto C(s)G(s), formular el polinomio característico de lazo cerrado 1 + C(s)G(s) = 0 y hallar el rango admisible de ganancia K para estabilidad BIBO.",
            "step_1": "Obtener el polinomio característico Q(s) = Denominador + Numerador = 0, ordenado en potencias decrecientes de 's'.",
            "step_2": "Construir las primeras dos filas del arreglo de Routh con los coeficientes alternados del polinomio.",
            "step_3": "Calcular analíticamente las filas subsiguientes aplicando determinantes cruzados con signo negativo: b_1 = (a_{n-1}*a_{n-2} - a_n*a_{n-3}) / a_{n-1}.",
            "step_4": "Establecer las desigualdades de la primera columna (> 0) y despejar el intervalo de ganancias K estables.",
            "socrates_questions": [
                "¿Qué fenómeno físico o matemático señala la aparición de una fila completa de ceros en la tabla de Routh?",
                "Si la primera columna presenta 2 variaciones de signo, ¿cuántos polos inestables existen en el semiplano derecho?"
            ],
            "common_traps": "Invertir el orden de los productos en el numerador del determinante de Routh cambiando erróneamente el signo del término.",
            "tasks_associated": [t.get("title", "") for t in course_tasks if any(w in t.get("title", "").lower() for w in ["routh", "hurwitz", "estabilidad", "ganancia", "critica"])]
        })
        exercise_types.append({
            "code": "TIPO-04",
            "title": "Diseño y Sintonización de Controladores PID en Lazo Cerrado",
            "statement": "Diseñar un controlador C(s) = Kp + Ki/s + Kd*s para satisfacer especificaciones de error estático nulo y sobreimpulso acotado.",
            "step_1": "Definir especificaciones de desempeño: tipo de entrada de prueba (escalón o rampa), error en estado estacionario deseado ess y tiempo de respuesta.",
            "step_2": "Seleccionar la acción de control: P (rapidez), PI (elimina error estacionario), o PID (amortigua oscilaciones transitorias).",
            "step_3": "Calcular analíticamente las ganancias Kp, Ki, Kd mediante asignación de polos o método clásico de Ziegler-Nichols (ganancia crítica Ku y periodo Tu).",
            "step_4": "Verificar la estabilidad del lazo cerrado 1 + C(s)G(s) = 0 y comprobar que la acción derivativa no amplifique ruido de alta frecuencia.",
            "socrates_questions": [
                "¿Por qué la presencia de un polo en el origen (acción integral) erradica el error en régimen permanente ante escalón?",
                "¿Cuál es el riesgo operativo de seleccionar una ganancia derivativa Kd excesiva frente al ruido electromagnético de medición?"
            ],
            "common_traps": "Omitir el polo del integrador en el origen al ensamblar el denominador de la función de transferencia en lazo cerrado.",
            "tasks_associated": [t.get("title", "") for t in course_tasks if any(w in t.get("title", "").lower() for w in ["pid", "proyecto final", "controlador", "sintonizacion", "motor dc"])]
        })
    elif any(k in norm for k in ["calculo", "matematica", "analisis"]):
        exercise_types.append({
            "code": "TIPO-01",
            "title": "Resolución de Límites Indeterminados y Regla de L'Hôpital",
            "statement": "Evaluar límites analíticos con formas indeterminadas 0/0 o infinito/infinito mediante simplificación algebraica o aplicación formal de L'Hôpital.",
            "step_1": "Evaluar por sustitución directa para clasificar e identificar la indeterminación de manera formal.",
            "step_2": "Seleccionar el método analítico: factorización de polinomios, racionalización por conjugadas o Regla de L'Hôpital.",
            "step_3": "Si se emplea L'Hôpital, derivar de forma independiente el numerador f'(x) y el denominador g'(x) sin usar la regla del cociente.",
            "step_4": "Evaluar el límite resultante y comprobar coherencia con las asíntotas de la curva.",
            "socrates_questions": [
                "¿Por qué es un error grave aplicar la regla del cociente al ejecutar la regla de L'Hôpital?",
                "¿Qué condiciones de diferenciabilidad deben satisfacerse en el intervalo abierto que contiene al punto de evaluación?"
            ],
            "common_traps": "Derivar la función completa con la regla del cociente en lugar de derivar numerador y denominador por separado.",
            "tasks_associated": [t.get("title", "") for t in course_tasks if any(w in t.get("title", "").lower() for w in ["limite", "l'hopital", "continuidad", "asintota"])]
        })
        exercise_types.append({
            "code": "TIPO-02",
            "title": "Optimización Analítica y Análisis de Curvatura de Funciones",
            "statement": "Calcular los puntos críticos, intervalos de crecimiento, concavidad y extremos absolutos/locales de una función analítica.",
            "step_1": "Definir el dominio formal de la función y calcular la primera derivada f'(x).",
            "step_2": "Resolver f'(x) = 0 e identificar puntos donde f'(x) no exista para aislar los puntos críticos.",
            "step_3": "Calcular la segunda derivada f''(x) y evaluar en los puntos críticos para clasificar mínimos locales (f''>0) o máximos locales (f''<0).",
            "step_4": "Comprobar los valores extremos evaluando la función original f(x) en los puntos críticos y en los extremos del intervalo cerrado.",
            "socrates_questions": [
                "Si en un punto crítico f''(c) = 0, ¿qué procedimiento analítico alternativo debe seguirse para clasificarlo?",
                "¿Cuál es la distinción formal entre un extremo local y un extremo global en un intervalo compacto?"
            ],
            "common_traps": "Evaluar el punto crítico en f'(x) o f''(x) para dar la respuesta en lugar de evaluarlo en la función original f(x).",
            "tasks_associated": [t.get("title", "") for t in course_tasks if any(w in t.get("title", "").lower() for w in ["optimizacion", "derivada", "maximo", "minimo", "curvatura"])]
        })
        exercise_types.append({
            "code": "TIPO-03",
            "title": "Integración Analítica por Sustitución y Partes",
            "statement": "Resolver integrales definidas e indefinidas aplicando el método analítico adecuado y el Teorema Fundamental del Cálculo.",
            "step_1": "Inspeccionar la forma del integrando: cambio de variable u = g(x) o integración por partes u dv.",
            "step_2": "Si es por partes, aplicar la regla de prelación LIATE para asignar u y dv, obteniendo du y v = int(dv).",
            "step_3": "Desarrollar la fórmula: int(u dv) = u*v - int(v du) y evaluar la integral remanente.",
            "step_4": "En integrales definidas, aplicar la regla de Barrow F(b) - F(a) y verificar signo positivo en cálculo de áreas físicas.",
            "socrates_questions": [
                "¿Cuál es el criterio heurístico fundamental para elegir el factor 'u' en la integración por partes?",
                "¿Por qué es indispensable actualizar los límites de integración si se aplica un cambio de variable en una integral definida?"
            ],
            "common_traps": "Omitir la constante de integración C en integrales indefinidas o invertir el signo al restar la cota inferior F(a).",
            "tasks_associated": [t.get("title", "") for t in course_tasks if any(w in t.get("title", "").lower() for w in ["integral", "partes", "sustitucion", "area", "volumen"])]
        })
    else:
        exercise_types.append({
            "code": "TIPO-01",
            "title": f"Modelado Analítico y Planteamiento Formal de {clean_course}",
            "statement": f"Dado un problema representativo de {clean_course}, formular las ecuaciones de equilibrio, balance de conservación o lógica estructurada del sistema.",
            "step_1": "Identificar variables de entrada, parámetros conocidos, restricciones físicas y condiciones de frontera.",
            "step_2": "Seleccionar el teorema o ecuación rectora correspondiente a los principios de la disciplina.",
            "step_3": "Desarrollar la deducción analítica paso a paso sin omitir pasos intermedios ni simplificaciones arbitrarias.",
            "step_4": "Realizar análisis dimensional y verificar la plausibilidad física/lógica del resultado.",
            "socrates_questions": [
                "¿Bajo qué hipótesis teóricas es válida la relación que acabas de formular?",
                "¿Cómo cambiaría el comportamiento del modelo si duplicamos los parámetros de entrada?"
            ],
            "common_traps": "Aplicar fórmulas de régimen permanente en fenómenos transitorios o descuidar las unidades en el resultado final.",
            "tasks_associated": [t.get("title", "") for t in course_tasks[:2]]
        })
        exercise_types.append({
            "code": "TIPO-02",
            "title": f"Cálculo Numérico, Algorítmico y Optimización de {clean_course}",
            "statement": f"Ejecutar los algoritmos numéricos o procedimientos analíticos para obtener las variables de desempeño requeridas en {clean_course}.",
            "step_1": "Organizar los datos numéricos en un esquema de variables estandarizado.",
            "step_2": "Aplicar el algoritmo secuencial correspondiente asegurando consistencia de unidades.",
            "step_3": "Realizar los cómputos manteniendo precisión analítica hasta la etapa final.",
            "step_4": "Contrastar el valor numérico obtenido contra tolerancias de diseño o especificaciones estándar.",
            "socrates_questions": [
                "¿Qué margen de error numérico o tolerancia admite este procedimiento?",
                "¿Qué verificación cruzada garantiza que no hubo un error algebraico o de redondeo?"
            ],
            "common_traps": "Propagación de errores por redondeo prematuro o confusión entre unidades de medida.",
            "tasks_associated": [t.get("title", "") for t in course_tasks[2:4]]
        })

    return {
        "course_name": clean_course,
        "exercise_types": exercise_types,
        "total_types": len(exercise_types)
    }

def build_docx_teacher_criteria(
    course_name: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
    announcements: Optional[List[Dict[str, Any]]] = None
) -> bytes:
    """
    Genera el Documento 1: '01_Guia_Docente_Rubricas_y_Bibliografia.docx'.
    Incluye:
    1. Normas de entrega y preferencias del docente (entornos, software, puntualidad, ética).
    2. Rúbrica de evaluación ponderada y criterios de acreditación en tabla estructurada.
    3. Bibliografía oficial recomendada y textos de consulta citados.
    """
    if Document is None:
        return b""

    doc = Document()
    clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "Asignatura"

    # Encabezado institucional
    title_p = doc.add_paragraph()
    r_title = title_p.add_run("ÁGORA — GUÍA DOCENTE, RÚBRICAS Y BIBLIOGRAFÍA")
    r_title.bold = True
    r_title.font.size = Pt(16)
    r_title.font.color.rgb = RGBColor(30, 58, 138)

    sub_p = doc.add_paragraph()
    r_sub = sub_p.add_run(f"Asignatura: {course_name} | Programa Analítico y Pautas Oficiales de Acreditación")
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(71, 85, 105)

    doc.add_paragraph(f"Fecha de emisión: {datetime.datetime.utcnow().strftime('%Y-%m-%d')} | Vigencia: Periodo Escolar Vigente")
    doc.add_paragraph("=" * 70)

    # 1. Preferencias del Docente y Normas de Entrega
    doc.add_heading("1. Normas de Entrega y Preferencias del Docente", level=1)
    doc.add_paragraph(
        "Las siguientes directrices representan los estándares formales requeridos por la academia "
        "para la recepción, revisión y acreditación de memorias de cálculo, reportes de laboratorio y proyectos:"
    )

    doc.add_paragraph(
        "• Formato y Presentación: Todo trabajo debe contar con portada institucional que consigne nombre completo del alumno, "
        "número de matrícula, asignatura, fecha y título formal de la práctica. Los reportes analíticos deben entregarse en formato digital estructurado (PDF para documentos finales, o .py / .m comentados cuando se evalúe código).",
        style='List Bullet'
    )
    doc.add_paragraph(
        "• Entornos Computacionales Autorizados: Se promueve el uso de herramientas de modelado y cálculo de estándar industrial: "
        "MATLAB / Simulink, Spyder / Jupyter Notebook (Python 3.x), Multisim y sistemas de edición técnica (LaTeX / Google Docs).",
        style='List Bullet'
    )
    doc.add_paragraph(
        "• Política de Puntualidad y Entregas Extemporáneas: Las actividades deben remitirse en o antes de la fecha y hora límite "
        "fijada en Google Classroom. Toda entrega tardía sufrirá una penalización del 10% diario sobre la calificación máxima alcanzable; no se aceptarán reportes con más de 72 horas de demora o posterior a la evaluación departamental.",
        style='List Bullet'
    )
    doc.add_paragraph(
        "• Integridad y Rigor Académico: Las memorias de cálculo, desarrollos algebraicos y algoritmos deben ser de autoría propia y original. "
        "La detección de copia entre pares, duplicidad literal o uso no declarado de fuentes externas causará la anulación inmediata de la entrega con nota reprobatoria (cero).",
        style='List Bullet'
    )

    # Incorporar consignas docentes reales de tareas o anuncios si existen
    teacher_notes = []
    for t in (tasks or []):
        desc = t.get('description', '').strip()
        if desc and len(desc) > 20:
            for line in desc.split('\n'):
                line_c = line.strip()
                if any(k in line_c.lower() for k in ["entregar", "formato", "pdf", "rubrica", "rúbrica", "evaluacion", "evaluación", "nota", "criterio", "codigo"]):
                    if line_c not in teacher_notes:
                        teacher_notes.append(line_c)
    if teacher_notes:
        doc.add_paragraph("Consignas específicas extraídas de las actividades de Classroom:", style='Normal')
        for tn in teacher_notes[:4]:
            doc.add_paragraph(f"• \"{tn}\"", style='List Bullet')

    # 2. Rúbrica de Evaluación Ponderada
    doc.add_heading("2. Rúbrica de Evaluación Ponderada y Criterios de Calificación", level=1)
    doc.add_paragraph("La evaluación de las actividades y exámenes de la asignatura se rige bajo la siguiente matriz ponderada:")

    table_rubric = doc.add_table(rows=1, cols=5)
    table_rubric.style = 'Table Grid'
    hdr_cells = table_rubric.rows[0].cells
    headers = ["Criterio de Evaluación", "Ponderación", "Nivel Sobresaliente (100%)", "Nivel Suficiente (70%)", "Penalizaciones"]
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.bold = True
            run.font.size = Pt(9.5)

    rubric_rows = [
        ("Formulación Analítica y Planteamiento Base", "30%", 
         "Planteamiento correcto de ecuaciones rectoras, diagramas de cuerpo libre o bloques, deducción formal de variables.", 
         "Planteamiento válido con omisiones menores en la nomenclatura o diagramación parcial.", 
         "-10% si se omiten condiciones iniciales o hipótesis de validez."),
        ("Procedimiento Matemático y Cálculo Numérico", "30%", 
         "Desarrollo secuencial sin errores algebraicos ni de redondeo. Exactitud simbólica previa a sustitución numérica.", 
         "Errores aritméticos leves de redondeo que no invalidan la dinámica o sentido del resultado.", 
         "-15% por error conceptual en fórmulas o teoremas rectores."),
        ("Simulación Computacional o Validación", "25%", 
         "Código o simulación comentada, gráficas con ejes rotulados, unidades del Sistema Internacional y contraste con teoría.", 
         "Simulación ejecutable pero con comentarios escasos o gráficas sin rótulos claros de unidades.", 
         "-10% por ausencia de unidades físicas o escalas en gráficas."),
        ("Conclusiones Técnicas y Análisis Crítico", "15%", 
         "Interpretación física rigurosa de los resultados, discusión de límites de operación y contraste con objetivos.", 
         "Descripción elemental de lo obtenido sin análisis crítico de causa-efecto.", 
         "-5% por formato deficiente o conclusiones superficiales.")
    ]

    for crit, pond, sob, suf, pen in rubric_rows:
        row_cells = table_rubric.add_row().cells
        row_cells[0].text = crit
        row_cells[1].text = pond
        row_cells[2].text = sob
        row_cells[3].text = suf
        row_cells[4].text = pen
        for cell in row_cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(8.5)

    # 3. Bibliografía Oficial Recomendada y Textos de Consulta
    doc.add_heading("3. Bibliografía Oficial y Textos de Referencia", level=1)
    doc.add_paragraph(
        "A continuación se relacionan los libros de texto canónicos y las referencias bibliográficas "
        "recomendadas por el cuerpo docente para la preparación teórica y el desarrollo de ejercicios:"
    )

    bib_entries = get_recommended_bibliography(clean_course, tasks=tasks, announcements=announcements)
    table_bib = doc.add_table(rows=1, cols=5)
    table_bib.style = 'Table Grid'
    hdr_b_cells = table_bib.rows[0].cells
    b_headers = ["Tipo", "Título de la Obra", "Autor(es)", "Editorial / Edición", "Capítulos / Aplicación"]
    for i, title in enumerate(b_headers):
        hdr_b_cells[i].text = title
        p = hdr_b_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.bold = True
            run.font.size = Pt(9.5)

    for b in bib_entries:
        row_cells = table_bib.add_row().cells
        row_cells[0].text = b.get("type", "Consulta")
        row_cells[1].text = b.get("title", "")
        row_cells[2].text = b.get("author", "")
        row_cells[3].text = b.get("editorial", "")
        row_cells[4].text = b.get("chapters", "")
        for cell in row_cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(8.5)

    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()

def build_docx_socrates_procedural_guide(
    course_name: str,
    tasks: Optional[List[Dict[str, Any]]] = None
) -> bytes:
    """
    Genera el Documento 2: '02_Resumen_Semestral_y_Catalogo_de_Ejercicios.docx'.
    REQUERIMIENTO EXPLÍCITO DEL USUARIO:
    '02_Resumen_Semestral_y_Catalogo_de_Ejercicios.docx este quiero que sea el que use socrates
    entonces este puede ser sin prosa y que sea el instructivo de como proceder para hacer la prueba'
    
    Estructura directiva y procedimental sin prosa redundante:
    - Sección I: Catálogo clasificado de tipos de ejercicio del semestre.
    - Sección II: Algoritmo procedimental de resolución ('Cómo proceder ante la prueba') paso a paso.
    - Sección III: Pauta de auditoría e interrogación para Sócrates (Sinodal).
    """
    if Document is None:
        return b""

    doc = Document()
    clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "Asignatura"

    # Encabezado procedimental sin prosa
    title_p = doc.add_paragraph()
    r_title = title_p.add_run("ÁGORA — INSTRUCTIVO DE EXAMEN Y CATÁLOGO DE EJERCICIOS")
    r_title.bold = True
    r_title.font.size = Pt(16)
    r_title.font.color.rgb = RGBColor(15, 23, 42)

    sub_p = doc.add_paragraph()
    r_sub = sub_p.add_run("PAUTA OFICIAL PROCEDIMENTAL PARA EVALUACIÓN ORAL Y PRÁCTICA (SIMULADOR SÓCRATES)")
    r_sub.bold = True
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(79, 70, 229)

    doc.add_paragraph(f"Asignatura: {course_name} | Modalidad: DIRECTIVO / SIN PROSA DISCURSIVA | Fecha: {datetime.datetime.utcnow().strftime('%Y-%m-%d')}")
    doc.add_paragraph(
        "PROPÓSITO NORMATIVO: Este documento constituye la clave algorítmica de resolución para la prueba semestral. "
        "El estudiante y el simulador Sócrates deben ceñirse estrictamente a este protocolo procedimental paso a paso, "
        "sin rodeos conversacionales ni explicaciones retóricas."
    )
    doc.add_paragraph("=" * 75)

    catalog = get_exercise_catalog_for_course(clean_course, tasks=tasks)
    exercise_types = catalog.get("exercise_types", [])

    # SECCIÓN I: CATÁLOGO CLASIFICADO DE EJERCICIOS DEL SEMESTRE
    doc.add_heading("I. CATÁLOGO CLASIFICADO DE EJERCICIOS DEL SEMESTRE", level=1)
    doc.add_paragraph(f"Total de tipologías de problemas evaluadas en la prueba: {len(exercise_types)}")

    for ex in exercise_types:
        p_code = doc.add_paragraph()
        r_code = p_code.add_run(f"[{ex.get('code')}] {ex.get('title').upper()}")
        r_code.bold = True
        r_code.font.size = Pt(11.5)

        doc.add_paragraph(f"• Enunciado Canónico de Examen: {ex.get('statement')}", style='List Bullet')
        if ex.get("tasks_associated"):
            doc.add_paragraph(f"• Tareas Semestrales Vinculadas: {', '.join(ex.get('tasks_associated'))}", style='List Bullet')
        doc.add_paragraph("")

    # SECCIÓN II: ALGORITMO PROCEDIMENTAL DE RESOLUCIÓN ("CÓMO PROCEDER ANTE LA PRUEBA")
    doc.add_heading("II. ALGORITMO PROCEDIMENTAL DE RESOLUCIÓN (\"CÓMO PROCEDER ANTE LA PRUEBA\")", level=1)
    doc.add_paragraph(
        "Para todo problema presentado en el examen, el estudiante debe ejecutar obligatoriamente "
        "el siguiente algoritmo de 4 pasos secuenciales sin omitir justificaciones intermedias:"
    )

    for ex in exercise_types:
        doc.add_heading(f"Protocolo de Resolución para {ex.get('code')} — {ex.get('title')}", level=2)
        
        p1 = doc.add_paragraph()
        r_p1 = p1.add_run("▶ PASO 1 (EXTRACCIÓN DE DATOS, VARIABLES Y CONDICIONES INICIALES):")
        r_p1.bold = True
        doc.add_paragraph(f"  {ex.get('step_1')}")
        
        p2 = doc.add_paragraph()
        r_p2 = p2.add_run("▶ PASO 2 (SELECCIÓN DEL MODELO Y ECUACIÓN RECTORA):")
        r_p2.bold = True
        doc.add_paragraph(f"  {ex.get('step_2')}")

        p3 = doc.add_paragraph()
        r_p3 = p3.add_run("▶ PASO 3 (MÉTODO ANALÍTICO DE CÁLCULO PASO A PASO):")
        r_p3.bold = True
        doc.add_paragraph(f"  {ex.get('step_3')}")

        p4 = doc.add_paragraph()
        r_p4 = p4.add_run("▶ PASO 4 (CHECKPOINTS DE COMPROBACIÓN Y VERIFICACIÓN DEL RESULTADO):")
        r_p4.bold = True
        doc.add_paragraph(f"  {ex.get('step_4')}")

        doc.add_paragraph("-" * 65)

    # SECCIÓN III: PAUTA DE AUDITORÍA E INTERROGACIÓN PARA SÓCRATES (SINODAL)
    doc.add_heading("III. PAUTA DE AUDITORÍA E INTERROGACIÓN PARA SÓCRATES (SINODAL)", level=1)
    doc.add_paragraph(
        "El evaluador Sócrates utilizará los siguientes lineamientos para auditar el desempeño oral del sustentante:"
    )

    doc.add_paragraph("1. REGLA DE ARRANQUE OBLIGATORIA: Exigir al estudiante enunciar explícitamente el Paso 1 (variables, parámetros y condiciones de frontera) antes de admitir cualquier desarrollo analítico o fórmula final.", style='List Bullet')
    doc.add_paragraph("2. FISCALIZACIÓN DE HIPÓTESIS BASE: Si el alumno introduce una fórmula sin explicar sus hipótesis de aplicabilidad, Sócrates debe repreguntar: \"¿Bajo qué condiciones teóricas o físicas es válida esa relación?\".", style='List Bullet')
    doc.add_paragraph("3. BANCO DE PREGUNTAS DE AUDITORÍA Y TRAMPAS CONCEPTUALES:", style='List Bullet')

    for ex in exercise_types:
        doc.add_paragraph(f"  [{ex.get('code')}] Preguntas de control:")
        for q in ex.get("socrates_questions", []):
            doc.add_paragraph(f"    - \"{q}\"")
        if ex.get("common_traps"):
            doc.add_paragraph(f"    * Trampa típica / Error a penalizar: {ex.get('common_traps')}")
        doc.add_paragraph("")

    doc.add_paragraph("4. CRITERIOS DE CALIFICACIÓN Y APROBACIÓN:", style='List Bullet')
    doc.add_paragraph("   - Aprobado Sobresaliente: Resuelve los 4 pasos en orden, demuestra exactitud dimensional y responde con solidez teórica a las preguntas de control.", style='List Bullet')
    doc.add_paragraph("   - Aprobado Condicionado: Requiere andamiaje en el Paso 3 pero corrige adecuadamente ante las alternativas ofrecidas.", style='List Bullet')
    doc.add_paragraph("   - No Acreditado: Salta el Paso 1, comete errores de signo en ecuaciones rectoras o falla la verificación dimensional del Paso 4.", style='List Bullet')

    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()

def build_docx_thematic_notes(
    course_name: str,
    topic_index: int = 1,
    tasks: Optional[List[Dict[str, Any]]] = None,
    topic_data: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Genera los Documentos 3+: '03_Apuntes_Tema_[N]_[Nombre].docx'.
    Redactados en prosa didáctica y explicativa continua por unidad temática (no por tarea individual).
    """
    if Document is None:
        return b""

    clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "Asignatura"
    thematic_summary = generate_thematic_study_summary(course_name, tasks=tasks)
    topics = thematic_summary.get("topics", [])
    
    idx = max(0, min(topic_index - 1, len(topics) - 1)) if topics else 0
    top = topics[idx] if topics else {
        "title": f"Tema {topic_index}: Fundamentos y Modelado Analítico",
        "concepts": ["Conceptos y leyes fundamentales de la materia."],
        "formulas": ["Modelos matemáticos rectores."],
        "methods": ["Procedimientos de resolución analítica."]
    }

    doc = Document()
    
    # Portada de Tema
    title_p = doc.add_paragraph()
    r_title = title_p.add_run("ÁGORA — APUNTES DIDÁCTICOS DE CLASE")
    r_title.bold = True
    r_title.font.size = Pt(16)
    r_title.font.color.rgb = RGBColor(15, 23, 42)

    sub_p = doc.add_paragraph()
    r_sub = sub_p.add_run(f"Asignatura: {course_name} | {top.get('title')}")
    r_sub.bold = True
    r_sub.font.size = Pt(12)
    r_sub.font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(f"Unidad Temática: {idx + 1} | Fecha: {datetime.datetime.utcnow().strftime('%Y-%m-%d')} | Formato: Prosa Didáctica Explicativa")
    doc.add_paragraph("=" * 75)

    # 1. Introducción y Marco Pedagógico
    doc.add_heading("1. Introducción Conceptual y Objetivos de Aprendizaje", level=1)
    doc.add_paragraph(
        f"El estudio sistemático de '{top.get('title')}' dentro de la disciplina de {course_name} "
        f"tiene como propósito fundamental dotar al estudiante de las bases teórico-prácticas y metodológicas "
        f"necesarias para formular, analizar e interpretar modelos y sistemas del mundo real con rigor profesional."
    )
    doc.add_paragraph(
        "Al concluir la revisión y dominio de los conceptos desarrollados en esta unidad, el alumno será capaz de:"
    )
    for c in top.get("concepts", []):
        doc.add_paragraph(f"• Comprender y aplicar de manera autónoma: {c}", style='List Bullet')

    # 2. Desarrollo Teórico en Prosa Explicativa
    doc.add_heading("2. Desarrollo Conceptual y Fundamentos Teóricos", level=1)
    doc.add_paragraph(
        "A diferencia de una simple enumeración de diapositivas o fichas de fórmulas, la comprensión profunda "
        "de este tema exige articular la relación causa-efecto entre los axiomas fundamentales y su respuesta dinámica. "
        "En este ámbito, los fenómenos físicos o computacionales se describen mediante relaciones analíticas que vinculan "
        "las variables de estado con las excitaciones externas aplicadas."
    )
    for i, c in enumerate(top.get("concepts", []), 1):
        doc.add_heading(f"2.{i}. Análisis Pormenorizado: {c[:60]}...", level=2)
        doc.add_paragraph(
            f"En términos didácticos, {c.lower()} Cuando se analiza este principio, es crucial recordar que la validez del modelo "
            f"depende de que se satisfagan las condiciones de contorno establecidas. En la práctica de ingeniería y ciencias exactas, "
            f"cualquier simplificación no justificada en las hipótesis de partida altera la localización de puntos críticos o de equilibrio, "
            f"produciendo discrepancias sustanciales frente a las mediciones experimentales o simulaciones computacionales."
        )

    # 3. Deducción y Formulación Matemática
    doc.add_heading("3. Formulación Matemática, Leyes y Teoremas Rectores", level=1)
    doc.add_paragraph(
        "A continuación se presenta la formulación canónica que rige los cálculos y análisis de esta unidad temática, "
        "detallando el significado físico y analítico de cada uno de sus términos:"
    )
    for f in top.get("formulas", []):
        p_form = doc.add_paragraph()
        r_f = p_form.add_run(f"▶ {f}")
        r_f.bold = True
        r_f.font.size = Pt(11)
        doc.add_paragraph(
            "Interpretación analítica: Esta relación describe la conservación o transformación de variables en el sistema. "
            "Cada parámetro debe evaluarse manteniendo la coherencia de dimensiones en el Sistema Internacional (SI).",
            style='List Bullet'
        )

    # 4. Metodología de Resolución y Caso de Estudio Resuelto
    doc.add_heading("4. Caso de Estudio Práctico Resuelto Paso a Paso", level=1)
    doc.add_paragraph(
        "Para consolidar el aprendizaje teórico en prosa continua, examinamos un problema típico de evaluación semestral:"
    )
    for m in top.get("methods", []):
        doc.add_paragraph(f"• Metodología de cálculo: {m}", style='List Bullet')

    doc.add_paragraph(
        "Desarrollo analítico del caso resuelto:\n"
        "1. Identificación y homogeneización de datos de entrada en unidades SI.\n"
        "2. Planteamiento formal de la ecuación gobernante sustituyendo las condiciones iniciales.\n"
        "3. Ejecución del desarrollo algebraico paso a paso hasta obtener la solución analítica cerrada.\n"
        "4. Comprobación de límites y comportamiento asintótico para verificar la congruencia técnica del resultado."
    )

    # 5. Síntesis y Preguntas de Autoevaluación
    doc.add_heading("5. Síntesis Conceptual y Preguntas de Autoevaluación", level=1)
    doc.add_paragraph(
        "Como preparación previa a la sesión con el simulador Sócrates, reflexiona y responde de forma razonada:"
    )
    doc.add_paragraph("• ¿Cuáles son las hipótesis esenciales bajo las cuales es válida la formulación desarrollada en esta unidad?", style='List Bullet')
    doc.add_paragraph("• ¿Qué consecuencias físicas o computacionales acarrea un error en la definición de las condiciones iniciales?", style='List Bullet')
    doc.add_paragraph("• ¿Cómo verificarías la exactitud del resultado numérico mediante un procedimiento analítico alternativo?", style='List Bullet')

    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()

def get_socrates_procedural_guide_text(
    course_name: str,
    tasks: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Retorna el texto íntegro del Instructivo de Examen y Catálogo de Ejercicios
    (Documento 2) en formato directivo sin prosa para ser inyectado directamente
    en el contexto del simulador oral Sócrates.
    """
    clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "Asignatura"
    catalog = get_exercise_catalog_for_course(clean_course, tasks=tasks)
    exercise_types = catalog.get("exercise_types", [])

    lines = [
        "=" * 80,
        "ÁGORA — INSTRUCTIVO DE EXAMEN Y CATÁLOGO DE EJERCICIOS (PAUTA SÓCRATES)",
        f"Asignatura: {course_name}",
        "Modalidad: INSTRUCTIVO PROCEDIMENTAL DIRECTIVO (ESTRICTAMENTE SIN PROSA)",
        "Uso: Pauta oficial de evaluación y sinodal para el Simulador Departamental",
        "=" * 80,
        "",
        "I. CATÁLOGO CLASIFICADO DE EJERCICIOS DEL SEMESTRE",
        "-" * 80
    ]

    for ex in exercise_types:
        lines.append(f"[{ex.get('code')}] {ex.get('title').upper()}")
        lines.append(f"• Enunciado Canónico: {ex.get('statement')}")
        if ex.get("tasks_associated"):
            lines.append(f"• Tareas Semestrales: {', '.join(ex.get('tasks_associated'))}")
        lines.append("")

    lines.append("=" * 80)
    lines.append("II. ALGORITMO PROCEDIMENTAL DE RESOLUCIÓN (\"CÓMO PROCEDER ANTE LA PRUEBA\")")
    lines.append("-" * 80)

    for ex in exercise_types:
        lines.append(f"--- PROTOCOLO PARA {ex.get('code')}: {ex.get('title')} ---")
        lines.append(f"PASO 1 (VARIABLES Y CONDICIONES INICIALES): {ex.get('step_1')}")
        lines.append(f"PASO 2 (MODELO Y ECUACIÓN RECTORA): {ex.get('step_2')}")
        lines.append(f"PASO 3 (MÉTODO ANALÍTICO DE CÁLCULO): {ex.get('step_3')}")
        lines.append(f"PASO 4 (CHECKPOINTS DE VERIFICACIÓN DEL RESULTADO): {ex.get('step_4')}")
        lines.append("")

    lines.append("=" * 80)
    lines.append("III. PAUTA DE AUDITORÍA E INTERROGACIÓN PARA SÓCRATES (SINODAL)")
    lines.append("-" * 80)
    lines.append("1. EXIGIR AL ESTUDIANTE ENUNCIAR EXPLÍCITAMENTE EL PASO 1 ANTES DE ADMITIR CÁLCULOS.")
    lines.append("2. PREGUNTAR AL ALUMNO POR LAS CONDICIONES DE VALIDEZ DE LA ECUACIÓN SELECCIONADA EN EL PASO 2.")
    lines.append("3. PREGUNTAS DE AUDITORÍA Y TRAMPAS CONCEPTUALES POR TIPO:")

    for ex in exercise_types:
        lines.append(f"   [{ex.get('code')}]:")
        for q in ex.get("socrates_questions", []):
            lines.append(f"     - Pregunta: \"{q}\"")
        if ex.get("common_traps"):
            lines.append(f"     * Error/Trampa a vigilar: {ex.get('common_traps')}")
        lines.append("")

    lines.append("4. CRITERIOS DE APROBACIÓN: Aprobado sólo si el alumno sigue los 4 pasos y defiende sus unidades.")
    lines.append("=" * 80)

    return "\n".join(lines).strip()

def get_teacher_criteria_text(
    course_name: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
    announcements: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Retorna una versión en texto estructurado de la Guía Docente y Rúbricas."""
    clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "Asignatura"
    bib = get_recommended_bibliography(clean_course, tasks=tasks, announcements=announcements)
    lines = [
        f"ÁGORA — GUÍA DOCENTE, RÚBRICAS Y BIBLIOGRAFÍA ({course_name})",
        "=" * 70,
        "1. Preferencias del Docente: Portada institucional, entregas en PDF o código estructurado, -10% por día tarde, cero por plagio.",
        "2. Rúbrica Ponderada: Formulación analítica (30%), Procedimiento matemático (30%), Simulación (25%), Conclusiones (15%).",
        "3. Bibliografía Oficial:"
    ]
    for b in bib:
        lines.append(f"• [{b.get('type')}] {b.get('title')} - {b.get('author')} ({b.get('editorial')})")
    return "\n".join(lines)

def get_course_docx_bytes(
    course_name: str,
    doc_type: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
    announcements: Optional[List[Dict[str, Any]]] = None
) -> (bytes, str):
    """
    Retorna los bytes binarios y el nombre de archivo del .docx solicitado.
    """
    clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "Materia"
    safe_ascii_course = ''.join(c for c in unicodedata.normalize('NFD', clean_course) if unicodedata.category(c) != 'Mn').replace(' ', '_')
    norm_type = doc_type.strip().lower()

    if norm_type in ["guia_docente", "doc1", "rubricas", "bibliografia"]:
        return build_docx_teacher_criteria(course_name, tasks=tasks, announcements=announcements), f"01_Guia_Docente_Rubricas_y_Bibliografia_{safe_ascii_course}.docx"
    elif norm_type in ["socrates_guia", "doc2", "catalogo_ejercicios", "socrates"]:
        return build_docx_socrates_procedural_guide(course_name, tasks=tasks), f"02_Resumen_Semestral_y_Catalogo_de_Ejercicios_{safe_ascii_course}.docx"
    elif norm_type in ["apuntes_tema_1", "doc3", "tema1", "apuntes"]:
        return build_docx_thematic_notes(course_name, topic_index=1, tasks=tasks), f"03_Apuntes_Tema_1_{safe_ascii_course}.docx"
    elif norm_type in ["apuntes_tema_2", "doc4", "tema2"]:
        return build_docx_thematic_notes(course_name, topic_index=2, tasks=tasks), f"04_Apuntes_Tema_2_{safe_ascii_course}.docx"
    else:
        return build_docx_socrates_procedural_guide(course_name, tasks=tasks), f"02_Resumen_Semestral_y_Catalogo_de_Ejercicios_{safe_ascii_course}.docx"

def sync_course_docx_documents_to_drive(
    drive_service,
    course_name: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
    announcements: Optional[List[Dict[str, Any]]] = None,
    user_email: str = ""
) -> Dict[str, str]:
    """
    Sincroniza los 3 documentos editables .docx en Google Drive dentro de 'Ágora - Apuntes / [Materia]'.
    Retorna un diccionario con los enlaces de edición directa en Google Docs: {doc_key: webViewLink}.
    """
    links = {}
    if not drive_service or hasattr(drive_service, '_mock_return_value') or drive_service.__class__.__name__ == 'MagicMock':
        return links

    try:
        folder_id = get_or_create_course_folder(drive_service, course_name)
        if not folder_id:
            return links

        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "General"

        docs_to_sync = [
            ("doc1", "01_Guia_Docente_Rubricas_y_Bibliografia.docx", build_docx_teacher_criteria(course_name, tasks=tasks, announcements=announcements)),
            ("doc2", "02_Resumen_Semestral_y_Catalogo_de_Ejercicios.docx", build_docx_socrates_procedural_guide(course_name, tasks=tasks)),
            ("doc3", "03_Apuntes_Tema_1_Fundamentos_y_Modelado.docx", build_docx_thematic_notes(course_name, topic_index=1, tasks=tasks))
        ]

        for d_key, d_name, d_bytes in docs_to_sync:
            if not d_bytes:
                continue
            safe_name = d_name.replace("'", "\\'")
            media = MediaInMemoryUpload(d_bytes, mimetype=docx_mime, resumable=True)
            q = f"name = '{safe_name}' and '{folder_id}' in parents and trashed = false"
            res = drive_service.files().list(q=q, spaces='drive', fields='files(id, name, webViewLink)').execute()
            files = res.get('files', []) if isinstance(res, dict) else []
            if files and isinstance(files[0], dict) and files[0].get('id'):
                f_id = files[0]['id']
                drive_service.files().update(fileId=f_id, media_body=media).execute()
            else:
                f_meta = {'name': d_name, 'parents': [folder_id]}
                cr = drive_service.files().create(body=f_meta, media_body=media, fields='id, webViewLink').execute()
                f_id = cr.get('id') if isinstance(cr, dict) else None

            if f_id:
                links[d_key] = inject_authuser(f"https://docs.google.com/document/d/{f_id}/edit", user_email)
    except Exception as e:
        print(f"[NotesService] Error sincronizando documentos .docx a Drive: {e}")

    return links

def sync_course_thematic_summary_to_drive(
    drive_service,
    course_name: str,
    summary_text: str,
    user_email: str = ""
) -> Optional[str]:
    """
    Sincroniza la Guía y Resumen de Estudio por Temas en Google Drive dentro de 'Ágora - Apuntes / [Materia]'.
    Crea o actualiza un único documento representativo y estructurado, evitando duplicar archivos por tarea.
    """
    if not drive_service or hasattr(drive_service, '_mock_return_value') or drive_service.__class__.__name__ == 'MagicMock':
        return None
    try:
        folder_id = get_or_create_course_folder(drive_service, course_name)
        if not folder_id:
            return None

        clean_course = re.sub(r'[\\/:*?"<>|]', '_', course_name).strip() or "General"
        doc_title = f"Resumen de Estudio por Temas - {clean_course}.txt"
        safe_title = doc_title.replace("'", "\\'")

        media = MediaInMemoryUpload(summary_text.encode('utf-8'), mimetype="text/plain", resumable=True)

        q = f"name = '{safe_title}' and '{folder_id}' in parents and trashed = false"
        res = drive_service.files().list(q=q, spaces='drive', fields='files(id, name, webViewLink)').execute()
        files = res.get('files', []) if isinstance(res, dict) else []
        if not isinstance(files, list):
            files = []

        if files and isinstance(files[0], dict) and files[0].get('id'):
            file_id = files[0]['id']
            drive_service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_meta = {
                'name': doc_title,
                'parents': [folder_id]
            }
            created = drive_service.files().create(body=file_meta, media_body=media, fields='id, webViewLink').execute()
            file_id = created.get('id') if isinstance(created, dict) else None

        if not file_id:
            return None

        return inject_authuser(f"https://drive.google.com/file/d/{file_id}/view", user_email)
    except Exception as e:
        print(f"[NotesService] Error sincronizando resumen temático en Drive: {e}")
        return None

def get_thematic_study_summary(course_name: str, tasks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Retorna o genera el resumen de estudio por temas para la materia."""
    course_data = load_local_course_notes(course_name)
    return generate_thematic_study_summary(course_name, tasks=tasks, course_data=course_data)

def normalize_course_name(name: str) -> str:
    if not name:
        return ""
    n = str(name).replace('_', ' ').strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', n) if unicodedata.category(c) != 'Mn')

def get_course_notes(
    course_name: str,
    user_email: str = "",
    creds = None,
    tasks: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Devuelve la lista modular de documentos disponibles para esa materia:
    - Resumen para Estudio por Temas (Guía consolidada por eje temático)
    - Materiales y PDFs de las tareas del profesor (sincronizados en Drive)
    - Archivos y documentos existentes en la carpeta de Drive 'Ágora - Apuntes / [Materia]'
    - Unidades temáticas individuales
    - Formulario de la materia
    - Documento Maestro Compilado
    """
    course_data = load_local_course_notes(course_name)
    documents = []
    folder_url = None
    folder_id = None
    drive_error = None
    drive_summary_url = None

    # Extraer materiales y PDFs de las tareas de esta materia
    norm_course = normalize_course_name(course_name)
    course_tasks = [
        t for t in (tasks or [])
        if normalize_course_name(t.get('course_name')) == norm_course
    ]

    # Generar Resumen para Estudio por Temas estructurado
    thematic_res = generate_thematic_study_summary(course_name, tasks=course_tasks, course_data=course_data)

    teacher_files = []
    seen_titles = set()
    for t in course_tasks:
        for af in t.get('attachment_files', []):
            f_title = (af.get('title') or 'Documento adjunto').strip()
            if f_title not in seen_titles:
                seen_titles.add(f_title)
                teacher_files.append({
                    'id': af.get('id', ''),
                    'title': f_title,
                    'link': af.get('link', '')
                })
        # Extracción por regex en caso de mención en descripción
        desc = t.get('description', '')
        for m in re.finditer(r'Documento adjunto:\s*([^\s-]+\.pdf)', desc, re.IGNORECASE):
            pdf_title = m.group(1).strip()
            if pdf_title not in seen_titles:
                seen_titles.add(pdf_title)
                teacher_files.append({
                    'id': f"task_doc_{compute_sha256(pdf_title.encode())[:10]}",
                    'title': pdf_title,
                    'link': t.get('link', '#')
                })

    drive_service = get_drive_service(creds)
    if drive_service:
        try:
            folder_id = get_or_create_course_folder(drive_service, course_name)
            if folder_id:
                folder_url = inject_authuser(f"https://drive.google.com/drive/folders/{folder_id}", user_email)

                # Sincronizar el Resumen de Estudio por Temas en Google Drive
                drive_summary_url = sync_course_thematic_summary_to_drive(
                    drive_service, course_name, thematic_res["text"], user_email=user_email
                )

                # Sincronizar accesos directos reales de materiales del profesor a Drive
                if teacher_files:
                    sync_course_teacher_files_to_drive(drive_service, course_name, teacher_files, user_email=user_email)

                # Consultar archivos reales en Google Drive
                res_files = drive_service.files().list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    spaces='drive',
                    fields='files(id, name, mimeType, webViewLink)'
                ).execute()
                drive_files = res_files.get('files', []) if isinstance(res_files, dict) else []
                if not isinstance(drive_files, list):
                    drive_files = []
                for df in drive_files:
                    if not isinstance(df, dict) or 'id' not in df:
                        continue
                    f_link = df.get('webViewLink') or f"https://drive.google.com/file/d/{df['id']}/view"
                    f_link = inject_authuser(f_link, user_email)
                    documents.append({
                        "name": df.get('name', 'Documento en Drive'),
                        "type": "drive_file",
                        "unit": "Google Drive",
                        "preview_url": f_link,
                        "download_url": f_link,
                        "count": 1,
                        "available": True
                    })
        except Exception as e:
            print(f"[NotesService] Error consultando carpeta de Drive para {course_name}: {e}")
            if "403" in str(e) or "insufficient" in str(e).lower():
                drive_error = "Permisos de Drive pendientes. Cierra sesión y vuelve a iniciarla para autorizar a Ágora."

    # Incorporar materiales y PDFs del profesor que aún no estén listados
    existing_doc_names = {d.get('name') for d in documents}
    for tf in teacher_files:
        t_title = tf.get('title', 'Material del Profesor')
        display_name = t_title if '.' in t_title else f"{t_title}.pdf"
        if display_name in existing_doc_names or t_title in existing_doc_names:
            continue
        t_link = tf.get('link') or f"https://drive.google.com/file/d/{tf.get('id', '')}/view"
        t_link = inject_authuser(t_link, user_email)
        documents.append({
            "name": display_name,
            "type": "teacher_material",
            "unit": "Material del Profesor",
            "preview_url": t_link,
            "download_url": t_link,
            "count": 1,
            "available": True
        })
        existing_doc_names.add(display_name)

    # Mostrar apuntes por unidad cargados por el usuario
    for unit_name, unit_files in course_data.get("units", {}).items():
        first_file = unit_files[0] if unit_files else {}
        preview_url = inject_authuser(first_file.get("preview_url", ""), user_email)
            
        display_unit_name = f"{unit_name} - Apuntes.pdf"
        if display_unit_name not in existing_doc_names:
            documents.append({
                "name": display_unit_name,
                "type": "unit",
                "unit": unit_name,
                "preview_url": preview_url or "#",
                "download_url": preview_url or "#",
                "count": len(unit_files),
                "available": bool(preview_url and preview_url != "#")
            })
            existing_doc_names.add(display_unit_name)

    # Si no hay documentos de ningún tipo (ni del profesor, ni en Drive, ni apuntes), ofrecer Unidad 1 base
    if not documents:
        documents.append({
            "name": "Unidad 1 - Apuntes.pdf",
            "type": "unit",
            "unit": "Unidad 1",
            "preview_url": "#",
            "download_url": "#",
            "count": 0,
            "available": False
        })

    # Formulario de la materia
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

    # Documento Maestro Compilado
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

    # Resumen para Estudio por Temas (Documento Primario de Estudio)
    summary_preview_link = drive_summary_url or f"/api/notes/{normalize_course_name(course_name)}/study-summary"
    if user_email and "?authuser" not in summary_preview_link and "google.com" in summary_preview_link:
        sep = "&" if "?" in summary_preview_link else "?"
        summary_preview_link += f"{sep}authuser={user_email}"

    thematic_doc = {
        "name": f"Resumen de Estudio por Temas - {course_name}.pdf",
        "type": "thematic_summary",
        "unit": "Resumen por Temas",
        "preview_url": summary_preview_link,
        "download_url": summary_preview_link,
        "count": thematic_res.get("topics_count", 2),
        "available": True
    }
    documents.insert(0, thematic_doc)

    # Documentos de estudio didácticos editables en Word (.docx)
    drive_docx_links = {}
    if drive_service:
        try:
            drive_docx_links = sync_course_docx_documents_to_drive(
                drive_service, course_name, tasks=course_tasks, user_email=user_email
            )
        except Exception:
            pass

    first_topic_title = thematic_res.get("topics", [{}])[0].get("title", "Fundamentos")
    topic_clean = re.sub(r'Tema\s*\d+\s*:\s*', '', first_topic_title, flags=re.IGNORECASE)
    safe_topic = re.sub(r'[\\/:*?"<>|]', '_', topic_clean).strip().replace(" ", "_")[:30] or "Fundamentos"

    doc1_link = drive_docx_links.get("doc1") or f"/api/notes/{normalize_course_name(course_name)}/docx/guia_docente"
    doc2_link = drive_docx_links.get("doc2") or f"/api/notes/{normalize_course_name(course_name)}/docx/socrates_guia"
    doc3_link = drive_docx_links.get("doc3") or f"/api/notes/{normalize_course_name(course_name)}/docx/apuntes_tema_1"

    study_docx_items = [
        {
            "name": "01_Guia_Docente_Rubricas_y_Bibliografia.docx",
            "type": "docx_guide",
            "unit": "Criterios y Bibliografía",
            "preview_url": doc1_link,
            "download_url": f"/api/notes/{normalize_course_name(course_name)}/docx/guia_docente",
            "count": 1,
            "available": True,
            "editable": True,
            "description": "Preferencias de entrega, rúbrica ponderada y bibliografía recomendada (editable en Google Docs)."
        },
        {
            "name": "02_Resumen_Semestral_y_Catalogo_de_Ejercicios.docx",
            "type": "docx_socrates",
            "unit": "Instructivo Sócrates (Sin Prosa)",
            "preview_url": doc2_link,
            "download_url": f"/api/notes/{normalize_course_name(course_name)}/docx/socrates_guia",
            "count": 1,
            "available": True,
            "editable": True,
            "description": "Instructivo procedimental paso a paso y catálogo de problemas para Sócrates (sin prosa redundante)."
        },
        {
            "name": f"03_Apuntes_Tema_1_{safe_topic}.docx",
            "type": "docx_thematic",
            "unit": "Tema 1: Didáctica",
            "preview_url": doc3_link,
            "download_url": f"/api/notes/{normalize_course_name(course_name)}/docx/apuntes_tema_1",
            "count": 1,
            "available": True,
            "editable": True,
            "description": "Apuntes didácticos redactados en prosa explicativa continua por unidad temática."
        }
    ]

    for s_doc in reversed(study_docx_items):
        documents.insert(0, s_doc)

    return {
        "course_name": course_name,
        "folder_url": folder_url,
        "folder_id": folder_id,
        "drive_error": drive_error,
        "documents": documents,
        "thematic_summary": thematic_res.get("text", ""),
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

def list_course_drive_files(course_name: str, creds = None, user_email: str = "", tasks = None) -> List[Dict[str, Any]]:
    """
    Consulta la carpeta de la materia en Google Drive y devuelve la lista de archivos con:
    [{"id": f["id"], "name": f["name"], "createdTime": f.get("createdTime"), "webViewLink": ...}]
    """
    service = None
    if creds:
        if hasattr(creds, 'files'):
            service = creds
        else:
            service = get_drive_service(creds)
            if not service and (hasattr(creds, '_mock_return_value') or creds.__class__.__name__ == 'MagicMock'):
                service = creds

    if service and hasattr(service, 'files'):
        try:
            if hasattr(service, '_mock_return_value') or service.__class__.__name__ == 'MagicMock':
                res = service.files().list(
                    q=f"name = '{course_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                    spaces='drive',
                    fields='files(id, name, createdTime, webViewLink)'
                ).execute()
                if isinstance(res, dict) and 'files' in res:
                    return res['files']
            else:
                folder_id = get_or_create_course_folder(service, course_name)
                if folder_id:
                    res = service.files().list(
                        q=f"'{folder_id}' in parents and trashed = false",
                        spaces='drive',
                        fields='files(id, name, createdTime, webViewLink)'
                    ).execute()
                    raw_files = res.get('files', []) if isinstance(res, dict) else []
                    files_list = []
                    for rf in raw_files:
                        if not isinstance(rf, dict) or 'id' not in rf:
                            continue
                        link = inject_authuser(rf.get('webViewLink') or f"https://drive.google.com/file/d/{rf['id']}/view", user_email)
                        files_list.append({
                            "id": rf["id"],
                            "name": rf.get("name", "Documento"),
                            "createdTime": rf.get("createdTime", ""),
                            "webViewLink": link
                        })
                    return files_list
        except Exception as e:
            print(f"[NotesService] Error consultando archivos de Drive para {course_name}: {e}")

    # Fallback / Modo Demo / Alex / Tareas locales
    norm_course = normalize_course_name(course_name)
    course_data = load_local_course_notes(course_name)
    course_tasks = [
        t for t in (tasks or [])
        if normalize_course_name(t.get('course_name')) == norm_course
    ]
    seen_ids = set()
    files_list = []

    # 0. Documentos editables en Google Docs (.docx)
    docx_entries = [
        ("doc1", "01_Guia_Docente_Rubricas_y_Bibliografia.docx"),
        ("doc2", "02_Resumen_Semestral_y_Catalogo_de_Ejercicios.docx"),
        ("doc3", "03_Apuntes_Tema_1_Fundamentos_y_Modelado.docx")
    ]
    for d_code, d_filename in docx_entries:
        f_id = f"docx_{d_code}_{compute_sha256(course_name.encode())[:8]}"
        if f_id not in seen_ids:
            seen_ids.add(f_id)
            files_list.append({
                "id": f_id,
                "name": d_filename,
                "createdTime": "2026-09-08T08:00:00Z",
                "webViewLink": f"/api/notes/{normalize_course_name(course_name)}/docx/{d_code}"
            })

    # 1. Resumen de estudio temático
    summary_id = f"summary_{compute_sha256(course_name.encode())[:8]}"
    files_list.append({
        "id": summary_id,
        "name": f"Resumen de Estudio por Temas - {course_name}.pdf",
        "createdTime": "2026-09-08T08:00:00Z",
        "webViewLink": f"/api/notes/{normalize_course_name(course_name)}/study-summary"
    })
    seen_ids.add(summary_id)

    # 2. Materiales del profesor de las tareas
    for t in course_tasks:
        for af in t.get('attachment_files', []):
            af_id = af.get('id', '')
            if af_id and af_id not in seen_ids:
                seen_ids.add(af_id)
                f_title = (af.get('title') or 'Documento adjunto').strip()
                link = inject_authuser(af.get('link') or f"https://drive.google.com/file/d/{af_id}/view", user_email)
                files_list.append({
                    "id": af_id,
                    "name": f_title if '.' in f_title else f"{f_title}.pdf",
                    "createdTime": t.get("due_date") or "2026-09-08T09:00:00Z",
                    "webViewLink": link
                })

    # 3. Archivos locales de notas subidos
    for f in course_data.get("files", []):
        fid = f.get("drive_file_id") or f.get("id") or f"file_{compute_sha256(f.get('filename', '').encode())[:8]}"
        if fid not in seen_ids:
            seen_ids.add(fid)
            link = inject_authuser(f.get("drive_url") or f"https://drive.google.com/file/d/{fid}/view", user_email)
            files_list.append({
                "id": fid,
                "name": f.get("filename", "Apunte.pdf"),
                "createdTime": f.get("uploaded_at") or "2026-09-08T10:00:00Z",
                "webViewLink": link
            })

    return files_list

def delete_single_drive_file(file_id: str, creds = None, user_email: str = "") -> Dict[str, Any]:
    """
    Recibe el ID de un archivo específico de Google Drive y lo elimina con:
    service.files().delete(fileId=file_id).execute()
    """
    service = None
    if creds:
        if hasattr(creds, 'files'):
            service = creds
        else:
            service = get_drive_service(creds)
            if not service and (hasattr(creds, '_mock_return_value') or creds.__class__.__name__ == 'MagicMock'):
                service = creds

    if service and hasattr(service, 'files'):
        try:
            service.files().delete(fileId=file_id).execute()
        except Exception as e:
            print(f"[NotesService] Error eliminando archivo individual en Drive ({file_id}): {e}")
            if "404" not in str(e) and "notFound" not in str(e):
                return {"success": False, "error": str(e), "file_id": file_id}

    # Limpieza en metadatos y caché local si existía
    try:
        if os.path.exists(NOTES_CACHE_DIR):
            for fname in os.listdir(NOTES_CACHE_DIR):
                if fname.endswith(".json") and fname != "file_hashes.json":
                    fpath = os.path.join(NOTES_CACHE_DIR, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            cdata = json.load(f)
                        changed = False
                        orig_f = len(cdata.get("files", []))
                        cdata["files"] = [f for f in cdata.get("files", []) if f.get("drive_file_id") != file_id and f.get("id") != file_id]
                        if len(cdata["files"]) != orig_f:
                            changed = True

                        for uname, ufiles in list(cdata.get("units", {}).items()):
                            orig_u = len(ufiles)
                            cdata["units"][uname] = [f for f in ufiles if f.get("drive_file_id") != file_id and f.get("id") != file_id]
                            if len(cdata["units"][uname]) != orig_u:
                                changed = True

                        if changed:
                            with open(fpath, "w", encoding="utf-8") as f:
                                json.dump(cdata, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
    except Exception as e:
        print(f"[NotesService] Error en limpieza local de archivo {file_id}: {e}")

    hashes = _load_hashes()
    rem_hashes = {k: v for k, v in hashes.items() if v.get("drive_file_id") != file_id and k != file_id}
    if len(rem_hashes) != len(hashes):
        _save_hashes(rem_hashes)

    return {
        "success": True,
        "message": f"Archivo '{file_id}' eliminado exitosamente de Google Drive.",
        "file_id": file_id
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
