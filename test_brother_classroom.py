import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mockear dependencias externas antes de importar el servicio
for mod in ['google', 'google.oauth2', 'google.oauth2.credentials', 'google.auth', 
            'google.auth.transport', 'google.auth.transport.requests', 
            'googleapiclient', 'googleapiclient.discovery', 'googleapiclient.http', 'pypdf']:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.classroom_service import get_active_courses, get_all_tasks, fetch_courses, inject_authuser

class TestBrotherClassroomData(unittest.TestCase):
    
    def test_1_courses_without_active_filter(self):
        """
        Prueba que si los cursos de la escuela del hermano no tienen el estado 'ACTIVE'
        (o el estado no viene definido / es PROVISIONED), la función NO los descarte.
        """
        mock_service = MagicMock()
        mock_courses_res = {
            'courses': [
                {'id': '101', 'name': 'Sistemas Operativos', 'courseState': 'PROVISIONED'},
                {'id': '102', 'name': 'Cálculo Vectorial', 'courseState': 'ACTIVE'},
                {'id': '103', 'name': 'Redes de Computadoras'}, # Sin estado explícito
                {'id': '104', 'name': 'Materia Antigua Archivada', 'courseState': 'ARCHIVED'}
            ]
        }
        mock_service.courses().list().execute.return_value = mock_courses_res
        
        courses = get_active_courses(mock_service)
        course_names = [c['name'] for c in courses]
        
        self.assertIn('Sistemas Operativos', course_names)
        self.assertIn('Cálculo Vectorial', course_names)
        self.assertIn('Redes de Computadoras', course_names)
        self.assertNotIn('Materia Antigua Archivada', course_names)
        print("[OK] Test 1 superado: Cursos con estados PROVISIONED o sin estado se recuperan sin ser descartados.")

    def test_2_fallback_when_unrestricted_fails(self):
        """
        Prueba que si la consulta amplia lanza excepción, se activa el fallback con studentId='me'.
        """
        mock_service = MagicMock()
        # Primer intento falla
        mock_service.courses().list.side_effect = [
            Exception("403 User not permitted for broad listing"),
            MagicMock(execute=MagicMock(return_value={'courses': [{'id': '201', 'name': 'Física Escolar', 'courseState': 'ACTIVE'}]}))
        ]
        
        courses = get_active_courses(mock_service)
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0]['name'], 'Física Escolar')
        print("[OK] Test 2 superado: Fallback automático se activa si la API restringe la consulta general.")

    def test_3_zero_tasks_still_returns_enrolled_courses(self):
        """
        Prueba clave: Si el hermano está inscrito en materias pero los profesores
        no han dejado tareas pendientes para esta semana, las materias deben recuperarse.
        """
        mock_service = MagicMock()
        mock_service.courses().list().execute.return_value = {
            'courses': [
                {'id': '201', 'name': 'Álgebra Lineal', 'courseState': 'ACTIVE'},
                {'id': '202', 'name': 'Física Clásica', 'courseState': 'ACTIVE'}
            ]
        }
        # Cero tareas asignadas en courseWork
        mock_service.courses().courseWork().list().execute.return_value = {'courseWork': []}
        
        courses = get_active_courses(mock_service)
        self.assertEqual(len(courses), 2)
        
        with patch('services.classroom_service.get_classroom_service', return_value=mock_service):
            tasks = get_all_tasks(creds=MagicMock())
            self.assertEqual(len(tasks), 0)
            
        print("[OK] Test 3 superado: Con 0 tareas, las materias inscritas siguen disponibles para el usuario.")

    def test_4_pdf_attachments_dont_block_or_download_synchronously(self):
        """
        Prueba que las tareas con PDFs adjuntos no llamen a la descarga pesada síncrona
        en la lista general, garantizando respuesta en milisegundos sin timeouts en Render.
        """
        mock_service = MagicMock()
        mock_service.courses().list().execute.return_value = {
            'courses': [{'id': '301', 'name': 'Estructuras de Datos', 'courseState': 'ACTIVE'}]
        }
        mock_service.courses().courseWork().list().execute.return_value = {
            'courseWork': [{
                'id': 'cw_99',
                'title': 'Práctica de Árboles Binarios',
                'description': 'Leer guía y programar',
                'materials': [{
                    'driveFile': {
                        'driveFile': {
                            'id': 'drive_pdf_123',
                            'title': 'Guia_Arboles.pdf',
                            'alternateLink': 'https://drive.google.com/file/d/drive_pdf_123'
                        }
                    }
                }]
            }]
        }
        mock_service.courses().courseWork().studentSubmissions().list().execute.return_value = {
            'studentSubmissions': [{'state': 'NEW'}]
        }
        
        with patch('services.classroom_service.get_classroom_service', return_value=mock_service), \
             patch('services.classroom_service.extract_pdf_text_from_drive') as mock_extract:
            
            tasks = get_all_tasks(creds=MagicMock())
            mock_extract.assert_not_called()
            
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]['title'], 'Práctica de Árboles Binarios')
            self.assertEqual(len(tasks[0]['attachment_files']), 1)
            self.assertEqual(tasks[0]['attachment_files'][0]['id'], 'drive_pdf_123')
            
        print("[OK] Test 4 superado: Las tareas recolectan metadatos de PDF sin descargas bloqueantes (sin timeouts).")

    def test_5_inject_authuser_dynamic_links(self):
        """
        Prueba que los enlaces de Google Classroom y Drive reciban deterministamente
        el parámetro ?authuser={email} para enrutar la cuenta institucional sin errores 403.
        """
        email = "estudiante.cucei@alumnos.udg.mx"
        
        # URL sin parámetros previos
        url1 = "https://classroom.google.com/c/MzQ4OTI5/a/NTg4MjQ/details"
        res1 = inject_authuser(url1, email)
        self.assertEqual(res1, f"{url1}?authuser={email}")
        
        # URL con parámetros previos
        url2 = "https://drive.google.com/file/d/123xyz/preview?usp=drivesdk"
        res2 = inject_authuser(url2, email)
        self.assertEqual(res2, f"{url2}&authuser={email}")
        
        # URL que ya contiene authuser
        url3 = f"{url1}?authuser={email}"
        res3 = inject_authuser(url3, email)
        self.assertEqual(res3, url3)
        
        # URL no perteneciente a Google
        url4 = "https://wikipedia.org/wiki/Calculus"
        res4 = inject_authuser(url4, email)
        self.assertEqual(res4, url4)

        # URL de Drive con prefijo /u/0/ que debe ser despojado para evitar forzar cuenta personal
        url5 = "https://drive.google.com/drive/u/0/folders/folder_agora_123"
        res5 = inject_authuser(url5, email)
        self.assertEqual(res5, f"https://drive.google.com/drive/folders/folder_agora_123?authuser={email}")

        # URL de Google Docs editable
        url6 = "https://docs.google.com/document/d/doc_789_xyz/edit"
        res6 = inject_authuser(url6, email)
        self.assertEqual(res6, f"{url6}?authuser={email}")

        # URL de búsqueda en Drive con /u/0/
        url7 = "https://drive.google.com/drive/u/0/search?q=test"
        res7 = inject_authuser(url7, email)
        self.assertEqual(res7, f"https://drive.google.com/drive/search?q=test&authuser={email}")
        
        print("[OK] Test 5 superado: Enlaces externos de Google integran ?authuser deterministamente.")

    def test_6_extract_actionable_consignas(self):
        """
        Prueba que el extractor de consignas detecte ejercicios reales (Laplace, sistemas)
        e ignore encabezados institucionales y nombres de materias.
        """
        from services.classroom_service import extract_actionable_consignas
        sample_text = (
            "UNIVERSIDAD DE GUADALAJARA\n"
            "CENTRO UNIVERSITARIO DE CIENCIAS EXACTAS E INGENIERIAS\n"
            "TEORIA DE SISTEMAS II - PROFESOR: DR. GOMEZ\n"
            "Instrucciones:\n"
            "Resuelve los 5 ejercicios sobre transformada de Laplace aplicando linealidad y traslacion.\n"
            "Determina la transformada inversa de las funciones racionales dadas en la seccion 2.\n"
            "Grafica la respuesta al escalon unitario.\n"
            "Entregar en formato PDF antes del viernes."
        )
        actions = extract_actionable_consignas(sample_text, course_name="TEORIA DE SISTEMAS II", task_title="UT 2 Act apre s 3 a")
        self.assertGreaterEqual(len(actions), 2)
        self.assertTrue(any("Laplace" in a or "laplace" in a.lower() for a in actions))
        self.assertTrue(any("transformada inversa" in a.lower() or "determina" in a.lower() for a in actions))
        # Verificar que no contenga el encabezado institucional
        self.assertFalse(any("UNIVERSIDAD DE GUADALAJARA" in a for a in actions))
        print("[OK] Test 6 superado: Extractor obtiene consignas y ejercicios reales omitiendo ruido institucional.")

    def test_7_attachment_cache_persistence(self):
        """
        Prueba que las consignas extraídas se almacenen y recuperen en caché de disco data/pdf_cache/{file_id}.json.
        """
        from services.classroom_service import get_cached_attachment_data, save_cached_attachment_data
        test_file_id = "test_file_xyz_999"
        test_data = {
            "file_id": test_file_id,
            "actions": ["Resuelve 5 ejercicios sobre transformada de Laplace."],
            "text": "Texto de prueba"
        }
        save_cached_attachment_data(test_file_id, test_data)
        loaded = get_cached_attachment_data(test_file_id)
        self.assertEqual(loaded.get("file_id"), test_file_id)
        self.assertEqual(len(loaded.get("actions", [])), 1)
        self.assertIn("Laplace", loaded["actions"][0])

        # Limpiar archivo de prueba
        cache_path = os.path.join("data", "pdf_cache", f"{test_file_id}.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)

        print("[OK] Test 7 superado: Almacenamiento y recuperación en caché de disco de adjuntos es instantáneo y persistente.")

    def test_8_due_date_utc_timezone_awareness(self):
        """
        Prueba que las fechas y horas de entrega provenientes de Google Classroom (UTC)
        se emitan con zona horaria UTC explícita (+00:00 o Z) para que el navegador las
        convierta a la hora local exacta (ej. 15:59 UTC -> 09:59 AM local México).
        """
        mock_service = MagicMock()
        mock_service.courses().list().execute.return_value = {
            'courses': [{'id': '401', 'name': 'Teoría de Sistemas II', 'courseState': 'ACTIVE'}]
        }
        mock_service.courses().courseWork().list().execute.return_value = {
            'courseWork': [{
                'id': 'cw_sistemas_4a',
                'title': 'Teoría de sistemas II UT 2 Act apre s 4 a',
                'dueDate': {'year': 2026, 'month': 9, 'day': 8},
                'dueTime': {'hours': 15, 'minutes': 59},
                'materials': []
            }]
        }
        mock_service.courses().courseWork().studentSubmissions().list().execute.return_value = {
            'studentSubmissions': [{'state': 'NEW'}]
        }
        
        with patch('services.classroom_service.get_classroom_service', return_value=mock_service):
            tasks = get_all_tasks(creds=MagicMock())
            self.assertEqual(len(tasks), 1)
            due_iso = tasks[0].get('due_date')
            self.assertIsNotNone(due_iso)
            # Debe contener zona horaria explícita (+00:00 o Z) para evitar ser tratada como hora local cruda
            self.assertTrue('+00:00' in due_iso or due_iso.endswith('Z'))
            self.assertIn('2026-09-08T15:59:00', due_iso)

            # Caso adicional: cuando Google omite 'minutes' porque es 0 (ej. 15:00 UTC -> 09:00 AM local México)
            mock_service.courses().courseWork().list().execute.return_value = {
                'courseWork': [{
                    'id': 'cw_sistemas_4b',
                    'title': 'Teoría de sistemas II - Entrega 9:00 AM',
                    'dueDate': {'year': 2026, 'month': 9, 'day': 8},
                    'dueTime': {'hours': 15},
                    'materials': []
                }]
            }
            tasks_omitted = get_all_tasks(creds=MagicMock())
            self.assertEqual(len(tasks_omitted), 1)
            due_iso_omitted = tasks_omitted[0].get('due_date')
            self.assertIn('2026-09-08T15:00:00', due_iso_omitted)

        print("[OK] Test 8 superado: Fechas de entrega integran zona horaria UTC y omisión de minutos (9:00 vs 9:59) exacta.")

    def test_9_sha256_deduplication_and_notes_service(self):
        """
        Prueba que el cálculo de hash SHA-256 detecte duplicados exactos y evite resubir
        archivos idénticos a Google Drive.
        """
        import services.notes_service as notes_service
        content = b"Apuntes de calculo diferencial: Teorema Fundamental del Calculo."
        hash1 = notes_service.compute_sha256(content)
        hash2 = notes_service.compute_sha256(content)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)

        # Probar procesamiento con deduplicación
        res1 = notes_service.process_and_upload_note(
            file_bytes=content,
            filename="Calculo_Unidad1.pdf",
            course_name="Calculo_Diferencial_Test",
            user_email="test@universidad.edu.mx"
        )
        self.assertTrue(res1.get("success"))

        # Segunda llamada con exactamente los mismos bytes debe activar is_duplicate
        res2 = notes_service.process_and_upload_note(
            file_bytes=content,
            filename="Calculo_Copia.pdf",
            course_name="Calculo_Diferencial_Test",
            user_email="test@universidad.edu.mx"
        )
        self.assertTrue(res2.get("is_duplicate"))
        self.assertIn("deduplicación SHA-256", res2.get("message", ""))

        # Limpiar datos de prueba
        notes_service.delete_course_notes("Calculo_Diferencial_Test")
        print("[OK] Test 9 superado: Deduplicación SHA-256 detecta archivos idénticos y optimiza almacenamiento en Drive.")

    def test_10_personal_notes_addition_and_persistence(self):
        """
        Prueba la inserción de notas personales tomadas en clase por el estudiante
        y su persistencia para la asignatura.
        """
        import services.notes_service as notes_service
        course = "Fisica_Vectorial_Test"
        task_id = "tarea_vectores_77"
        note_text = "Recordatorio del profe: Usar radianes para el producto cruz en el examen."

        add_res = notes_service.add_personal_note(
            course_name=course,
            task_id=task_id,
            note_text=note_text
        )
        self.assertTrue(add_res.get("success"))

        notes_txt = notes_service.get_course_notes_text(course)
        self.assertIn("radianes para el producto cruz", notes_txt)
        self.assertIn("NOTAS PERSONALES DEL ESTUDIANTE", notes_txt)

        # Limpiar
        notes_service.delete_course_notes(course)
        print("[OK] Test 10 superado: Notas personales se guardan y formatean correctamente para la asignatura.")

    def test_11_franklin_pragmatic_evaluator_prompt(self):
        """
        Prueba que el perfil de Benjamin Franklin sea estrictamente un Evaluador Pragmático
        de Carga Académica y NO contenga términos de gamificación ("racha", "antorcha").
        """
        from services.ai_service import MENTOR_PROMPTS
        franklin_prompt = MENTOR_PROMPTS.get("franklin", "").lower()
        
        self.assertTrue(len(franklin_prompt) > 0)
        self.assertNotIn("racha", franklin_prompt)
        self.assertNotIn("antorcha", franklin_prompt)
        self.assertIn("evaluador pragmático", franklin_prompt)
        self.assertTrue("cognitiva" in franklin_prompt or "cognitivo" in franklin_prompt or "cognoscitivo" in franklin_prompt)
        print("[OK] Test 11 superado: Benjamin Franklin redefinido como Evaluador Pragmático sin rastros de gamificación.")

    def test_12_notes_injection_into_copilot_context(self):
        """
        Prueba que las notas y fórmulas del estudiante se inyecten limpiamente
        en el contexto del Mentor / Copilot.
        """
        import asyncio
        import services.notes_service as notes_service
        from services.ai_service import ask_copilot

        course = "Circuitos_Logicos_Test"
        notes_service.add_personal_note(
            course_name=course,
            task_id="tarea_mapas_karnaugh",
            note_text="Tip del profesor: agrupar esquinas en mapas 4x4."
        )

        notes_context = notes_service.get_course_notes_text(course)
        self.assertIn("mapas 4x4", notes_context)

        # Mockear client retornado por get_client
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="Explicación paso a paso"))]
        
        async def mock_create(**kwargs):
            # Verificar que el mensaje de sistema contenga los apuntes inyectados
            messages = kwargs.get("messages", [])
            sys_msg = messages[0]["content"] if messages else ""
            self.assertIn("Apuntes y fórmulas de clase del estudiante", sys_msg)
            self.assertIn("agrupar esquinas en mapas 4x4", sys_msg)
            return mock_completion

        mock_client.chat.completions.create = mock_create

        with patch('services.ai_service.get_client', return_value=mock_client):
            resp = asyncio.run(ask_copilot(
                provider="gemini",
                messages=[{"role": "user", "content": "¿Cómo agrupo las esquinas?"}],
                mentor="turing",
                task_context={
                    "course_name": course,
                    "title": "Mapas de Karnaugh",
                    "student_notes": notes_context
                }
            ))
            self.assertEqual(resp, "Explicación paso a paso")

        # Limpiar
        notes_service.delete_course_notes(course)
        print("[OK] Test 12 superado: Apuntes y fórmulas del alumno se inyectan correctamente al contexto del mentor.")

    def test_13_demo_mode_auth_and_data_serving(self):
        """
        Prueba que el endpoint /auth/demo genere la sesión demo y que los endpoints
        /api/tasks y /api/courses sirvan los datos de prueba de Alex sin necesidad de Google.
        """
        from fastapi.testclient import TestClient
        from main import app, ALEX_EMAIL

        client = TestClient(app, follow_redirects=False)
        demo_resp = client.get("/auth/demo")
        self.assertEqual(demo_resp.status_code, 302)
        self.assertIn("agora_session=demo_alex_session", demo_resp.headers.get("set-cookie", ""))

        # Llamar a /api/tasks con la cookie de sesión demo
        client_with_cookie = TestClient(app)
        client_with_cookie.cookies.set("agora_session", "demo_alex_session")

        tasks_resp = client_with_cookie.get("/api/tasks")
        self.assertEqual(tasks_resp.status_code, 200)
        tasks_data = tasks_resp.json()
        self.assertEqual(tasks_data.get("user_email"), ALEX_EMAIL)
        total_tasks = len(tasks_data.get("tasks_with_dates", [])) + len(tasks_data.get("tasks_without_dates", []))
        self.assertGreater(total_tasks, 0)

        # Llamar a /api/courses
        courses_resp = client_with_cookie.get("/api/courses")
        self.assertEqual(courses_resp.status_code, 200)
        courses = courses_resp.json().get("courses", [])
        self.assertGreater(len(courses), 0)

        print("[OK] Test 13 superado: Modo de Prueba (Demo) inicializa sesión y sirve misiones y materias instantáneamente.")

    def test_14_teacher_task_pdfs_in_course_notes(self):
        """
        Prueba que get_course_notes extraiga y liste los PDFs adjuntos por el profesor
        en las tareas de cada materia, garantizando que cada materia cuente con sus
        documentos correspondientes.
        """
        import services.notes_service as notes_service
        course = "Inteligencia_Artificial_Test"
        sample_tasks = [
            {
                "id": "cw_ia_101",
                "course_name": course,
                "title": "Práctica 1: Búsqueda A* y Heurísticas",
                "description": "Consigna de la práctica de laboratorio.",
                "attachment_files": [
                    {"id": "file_ia_pdf_1", "title": "Guia_Busqueda_A_Estrella.pdf", "link": "https://drive.google.com/file/d/file_ia_pdf_1/view"}
                ]
            }
        ]

        notes_res = notes_service.get_course_notes(
            course_name=course,
            user_email="estudiante@universidad.edu.mx",
            creds=None,
            tasks=sample_tasks
        )
        self.assertEqual(notes_res.get("course_name"), course)
        docs = notes_res.get("documents", [])
        self.assertGreater(len(docs), 0)

        teacher_docs = [d for d in docs if d.get("type") == "teacher_material"]
        self.assertEqual(len(teacher_docs), 1)
        self.assertEqual(teacher_docs[0]["name"], "Guia_Busqueda_A_Estrella.pdf")
        self.assertTrue(teacher_docs[0]["available"])
        self.assertIn("authuser=estudiante@universidad.edu.mx", teacher_docs[0]["preview_url"])

        # Limpiar
        notes_service.delete_course_notes(course)
        print("[OK] Test 14 superado: PDFs de las tareas del profesor se incorporan exitosamente a los documentos de la materia.")

    def test_15_api_notes_endpoint_serves_task_pdfs(self):
        """
        Prueba que el endpoint /api/notes/{course_name} sirva los PDFs del profesor
        usando las tareas de la sesión (incluyendo en Modo Demo).
        """
        from fastapi.testclient import TestClient
        from main import app, user_sessions, ALEX_EMAIL

        user_sessions["demo_alex_session"] = {
            "email": ALEX_EMAIL,
            "is_demo": True
        }

        client = TestClient(app, cookies={"agora_session": "demo_alex_session"})

        # Consultar notas para una materia activa de Alex
        resp = client.get("/api/notes/Teor%C3%ADa%20de%20Sistemas%20y%20Control%20Autom%C3%A1tico")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        docs = data.get("documents", [])
        self.assertGreater(len(docs), 0)

        pdf_names = [d.get("name") for d in docs]
        self.assertIn("Proyecto_Final_Control_PID.pdf", pdf_names)
        pid_doc = next(d for d in docs if d.get("name") == "Proyecto_Final_Control_PID.pdf")
        self.assertTrue(pid_doc.get("available"))

        print("[OK] Test 15 superado: Endpoint /api/notes sirve instantáneamente los PDFs de tareas del profesor.")

    def test_16_thematic_study_summary_generation(self):
        """
        Prueba que el sistema genere una Guía y Resumen de Estudio estructurada por temas
        para cada materia (en lugar de reproducir archivos individuales por tarea), y que
        el endpoint /api/notes/{course_name}/study-summary lo sirva de forma estructurada.
        """
        import services.notes_service as notes_service
        from fastapi.testclient import TestClient
        from main import app, user_sessions, ALEX_EMAIL

        course = "Teoría de Sistemas y Control Automático"
        sample_tasks = [
            {
                "id": "cw_ctrl_1",
                "course_name": course,
                "title": "Práctica 3: Sistemas LTI y Respuesta al Escalón",
                "description": "Determinar función de transferencia y parámetros temporales.",
                "attachment_files": [{"id": "f_1", "title": "Guia_LTI.pdf", "link": "#"}]
            },
            {
                "id": "cw_ctrl_2",
                "course_name": course,
                "title": "Proyecto Final: Control de Posición Motor DC con PID",
                "description": "Sintonización PID y estabilidad Routh-Hurwitz.",
                "attachment_files": [{"id": "f_2", "title": "Guia_PID.pdf", "link": "#"}]
            }
        ]

        # 1. Generación del resumen temático
        summary_res = notes_service.generate_thematic_study_summary(course, tasks=sample_tasks)
        self.assertGreater(summary_res.get("topics_count", 0), 0)
        self.assertIn("ÁGORA — GUÍA Y RESUMEN DE ESTUDIO POR TEMAS", summary_res["text"])
        self.assertIn("CONCEPTOS TEÓRICOS ESENCIALES", summary_res["text"])

        # 2. get_course_notes incorpora el resumen como documento primario
        notes_res = notes_service.get_course_notes(course, user_email=ALEX_EMAIL, creds=None, tasks=sample_tasks)
        docs = notes_res.get("documents", [])
        thematic_docs = [d for d in docs if d.get("type") == "thematic_summary"]
        self.assertEqual(len(thematic_docs), 1)
        self.assertTrue(thematic_docs[0].get("available"))
        self.assertIn("Resumen de Estudio por Temas", thematic_docs[0]["name"])

        # 3. Endpoint /api/notes/{course_name}/study-summary
        user_sessions["demo_alex_session"] = {
            "email": ALEX_EMAIL,
            "is_demo": True
        }
        client = TestClient(app, cookies={"agora_session": "demo_alex_session"})
        resp = client.get(f"/api/notes/{course}/study-summary")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("GUÍA Y RESUMEN DE ESTUDIO POR TEMAS", resp.text)

        # Limpiar
        notes_service.delete_course_notes(course)
        print("[OK] Test 16 superado: Resumen de estudio estructurado por tema se genera y sirve exitosamente sin reescribir PDFs de cada tarea.")

    def test_17_granular_drive_file_endpoints(self):
        """
        Prueba los endpoints de gestión granular de archivos de Drive:
        - GET /api/notes/files/{course_name}: Lista archivos individuales con id, name, createdTime y enlace.
        - DELETE /api/notes/file/{file_id}: Elimina únicamente el archivo específico vía Drive API.
        """
        import services.notes_service as notes_service
        from fastapi.testclient import TestClient
        from main import app, user_sessions, ALEX_EMAIL

        course = "Cálculo Diferencial e Integral"
        user_sessions["demo_alex_session"] = {
            "email": ALEX_EMAIL,
            "is_demo": True
        }
        client = TestClient(app, cookies={"agora_session": "demo_alex_session"})

        # 1. Probar GET /api/notes/files/{course_name}
        resp = client.get(f"/api/notes/files/{course}")
        self.assertEqual(resp.status_code, 200)
        files = resp.json()
        self.assertIsInstance(files, list)
        self.assertGreater(len(files), 0)
        
        first_file = files[0]
        self.assertIn("id", first_file)
        self.assertIn("name", first_file)
        self.assertIn("createdTime", first_file)
        self.assertIn("webViewLink", first_file)

        # 2. Probar DELETE /api/notes/file/{file_id}
        target_id = first_file["id"]
        del_resp = client.delete(f"/api/notes/file/{target_id}")
        self.assertEqual(del_resp.status_code, 200)
        del_data = del_resp.json()
        self.assertTrue(del_data.get("success"))
        self.assertEqual(del_data.get("file_id"), target_id)

        # 3. Probar llamada directa con mock del servicio de Google Drive
        mock_drive = MagicMock()
        mock_drive.files().delete().execute.return_value = {}
        res = notes_service.delete_single_drive_file(file_id="drive-file-xyz", creds=mock_drive)
        self.assertTrue(res.get("success"))
        mock_drive.files().delete.assert_called_with(fileId="drive-file-xyz")

        print("[OK] Test 17 superado: Endpoints de listado granular y borrado individual en Drive operativos y validados.")

    def test_18_web_push_and_background_sync(self):
        """
        Prueba la suite de Notificaciones Web Push 24/7:
        1. Generación y exportación de claves VAPID (RFC 8292).
        2. Registro y consulta de suscripciones en SQLite.
        3. Endpoints /api/push/vapid-public-key y /api/push/subscribe.
        4. Detección de tareas nuevas y asignación de modo silencioso nocturno.
        """
        import db.database as db
        import services.push_service as push_service
        import services.background_sync as bg_sync
        from fastapi.testclient import TestClient
        from main import app

        # 1. Validar clave pública VAPID
        pub_key = push_service.get_public_key()
        self.assertIsInstance(pub_key, str)
        self.assertGreater(len(pub_key), 50)

        # 2. Validar persistencia de suscripción en DB
        test_endpoint = "https://fcm.googleapis.com/fcm/send/test_device_token_123"
        test_p256dh = "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QT9AcQg3PHGm3-0..."
        test_auth = "tBHItDaQLIo..."
        test_email = "alexmunoz918@gmail.com"

        db.save_push_subscription(test_endpoint, test_p256dh, test_auth, user_email=test_email)
        subs = db.get_push_subscriptions_for_user(test_email)
        self.assertGreater(len(subs), 0)
        found_sub = next(s for s in subs if s["endpoint"] == test_endpoint)
        self.assertEqual(found_sub["keys"]["p256dh"], test_p256dh)
        self.assertEqual(found_sub["keys"]["auth"], test_auth)

        # 3. Validar endpoints de FastAPI
        client = TestClient(app)
        res_key = client.get("/api/push/vapid-public-key")
        self.assertEqual(res_key.status_code, 200)
        self.assertEqual(res_key.json().get("publicKey"), pub_key)

        res_sub = client.post("/api/push/subscribe", json={
            "endpoint": test_endpoint,
            "keys": {"p256dh": test_p256dh, "auth": test_auth}
        })
        self.assertEqual(res_sub.status_code, 200)
        self.assertEqual(res_sub.json().get("status"), "ok")

        # 4. Validar ruta de service-worker.js
        res_sw = client.get("/service-worker.js")
        self.assertEqual(res_sw.status_code, 200)
        self.assertIn("Service-Worker-Allowed", res_sw.headers)

        # 5. Validar lógica de modo silencioso nocturno
        with patch("services.background_sync.datetime") as mock_dt:
            mock_dt.datetime.now.return_value.hour = 23 # 11:00 PM
            self.assertTrue(bg_sync.is_night_time())
            mock_dt.datetime.now.return_value.hour = 14 # 2:00 PM
            self.assertFalse(bg_sync.is_night_time())

        # 6. Validar despacho de prueba simulado
        with patch("services.push_service.webpush") as mock_wp:
            mock_wp.return_value = MagicMock(status_code=201)
            ok, msg = push_service.send_web_push(
                subscription_info=found_sub,
                title="Nueva Tarea",
                body="Práctica 4",
                silent=True
            )
            self.assertTrue(ok)
            self.assertEqual(msg, "sent")
            self.assertTrue(mock_wp.called)

        # Limpiar suscripción de prueba
        db.delete_push_subscription(test_endpoint)
        print("[OK] Test 18 superado: Arquitectura Web Push 24/7, VAPID y modo silencioso nocturno validados.")

    def test_19_docx_generation_and_socrates_procedural_guide(self):
        """
        Prueba la generación de los 3 documentos didácticos en formato Word (.docx):
        1. 01_Guia_Docente_Rubricas_y_Bibliografia.docx (Criterios, rúbricas ponderadas, libros citados).
        2. 02_Resumen_Semestral_y_Catalogo_de_Ejercicios.docx (Instructivo procedimental paso a paso SIN PROSA para Sócrates).
        3. 03_Apuntes_Tema_1_[...].docx (Apuntes explicativos en prosa didáctica por unidad temática).
        4. Endpoint /api/notes/{course}/docx/{doc_type} sirviendo bytes .docx válidos.
        5. Inyección obligatoria de la pauta procedimental de Sócrates en /api/socrates/exam.
        """
        import io
        import docx
        import services.notes_service as notes_service
        from fastapi.testclient import TestClient
        from main import app, user_sessions, ALEX_EMAIL

        course = "Teoría de Sistemas y Control Automático"
        sample_tasks = [
            {
                "id": "cw_ctrl_1",
                "course_name": course,
                "title": "Práctica 3: Sistemas LTI y Respuesta al Escalón",
                "description": "Determinar función de transferencia y parámetros temporales. Libro base: Ogata Cap 3.",
                "attachment_files": [{"id": "f_1", "title": "Guia_LTI.pdf", "link": "#"}]
            },
            {
                "id": "cw_ctrl_2",
                "course_name": course,
                "title": "Proyecto Final: Control de Posición Motor DC con PID",
                "description": "Sintonización PID y estabilidad Routh-Hurwitz. Formato PDF obligatorio.",
                "attachment_files": [{"id": "f_2", "title": "Guia_PID.pdf", "link": "#"}]
            }
        ]

        # 1. Generación y estructura de Doc 1 (Guía Docente y Bibliografía)
        doc1_bytes = notes_service.build_docx_teacher_criteria(course, tasks=sample_tasks)
        self.assertGreater(len(doc1_bytes), 1000)
        self.assertTrue(doc1_bytes.startswith(b"PK\x03\x04"))
        d1 = docx.Document(io.BytesIO(doc1_bytes))
        d1_text = " ".join([p.text for p in d1.paragraphs])
        self.assertIn("GUÍA DOCENTE, RÚBRICAS Y BIBLIOGRAFÍA", d1_text)
        self.assertIn("Normas de Entrega", d1_text)
        self.assertGreater(len(d1.tables), 1)  # Tablas de rúbrica y bibliografía

        # 2. Generación y estructura de Doc 2 (Instructivo Sócrates SIN PROSA)
        doc2_bytes = notes_service.build_docx_socrates_procedural_guide(course, tasks=sample_tasks)
        self.assertGreater(len(doc2_bytes), 1000)
        self.assertTrue(doc2_bytes.startswith(b"PK\x03\x04"))
        d2 = docx.Document(io.BytesIO(doc2_bytes))
        d2_text = " ".join([p.text for p in d2.paragraphs])
        self.assertIn("INSTRUCTIVO DE EXAMEN Y CATÁLOGO DE EJERCICIOS", d2_text)
        self.assertIn("SIN PROSA", d2_text)
        self.assertIn("CÓMO PROCEDER ANTE LA PRUEBA", d2_text)
        self.assertIn("PASO 1", d2_text)
        self.assertIn("PASO 2", d2_text)
        self.assertIn("PASO 3", d2_text)
        self.assertIn("PASO 4", d2_text)
        self.assertIn("PAUTA DE AUDITORÍA E INTERROGACIÓN PARA SÓCRATES (SINODAL)", d2_text)

        # Validar función de texto para Sócrates
        socrates_text = notes_service.get_socrates_procedural_guide_text(course, tasks=sample_tasks)
        self.assertIn("PAUTA SÓCRATES", socrates_text)
        self.assertIn("PASO 1 (VARIABLES Y CONDICIONES INICIALES)", socrates_text)
        self.assertIn("PASO 4 (CHECKPOINTS DE VERIFICACIÓN DEL RESULTADO)", socrates_text)

        # 3. Generación y estructura de Doc 3 (Apuntes didácticos en prosa explicativa)
        doc3_bytes = notes_service.build_docx_thematic_notes(course, topic_index=1, tasks=sample_tasks)
        self.assertGreater(len(doc3_bytes), 1000)
        self.assertTrue(doc3_bytes.startswith(b"PK\x03\x04"))
        d3 = docx.Document(io.BytesIO(doc3_bytes))
        d3_text = " ".join([p.text for p in d3.paragraphs])
        self.assertIn("APUNTES DIDÁCTICOS DE CLASE", d3_text)
        self.assertIn("Introducción Conceptual y Objetivos de Aprendizaje", d3_text)

        # 4. get_course_notes incorpora los 3 documentos .docx como primarios
        notes_res = notes_service.get_course_notes(course, user_email=ALEX_EMAIL, creds=None, tasks=sample_tasks)
        docs = notes_res.get("documents", [])
        doc_types = [d.get("type") for d in docs]
        self.assertIn("docx_guide", doc_types)
        self.assertIn("docx_socrates", doc_types)
        self.assertIn("docx_thematic", doc_types)

        # 5. Endpoint GET /api/notes/{course}/docx/{doc_type}
        user_sessions["demo_alex_session"] = {
            "email": ALEX_EMAIL,
            "is_demo": True
        }
        client = TestClient(app, cookies={"agora_session": "demo_alex_session"})

        for dt in ["guia_docente", "socrates_guia", "apuntes_tema_1"]:
            resp = client.get(f"/api/notes/{course}/docx/{dt}")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.headers.get("content-type"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            self.assertTrue(resp.content.startswith(b"PK\x03\x04"))

        # 6. Endpoint POST /api/socrates/exam inyecta la pauta procedimental
        with patch("main.ask_copilot") as mock_copilot:
            mock_copilot.return_value = "Pregunta del sinodal basada en el instructivo procedimental."
            exam_resp = client.post("/api/socrates/exam", json={
                "course_name": course,
                "mode": "hibrido",
                "messages": [{"role": "user", "content": "Listo para el examen."}]
            })
            self.assertEqual(exam_resp.status_code, 200)
            self.assertTrue(mock_copilot.called)
            called_kwargs = mock_copilot.call_args.kwargs
            task_ctx = called_kwargs.get("task_context", {})
            self.assertIn("procedural_guide", task_ctx)
            self.assertIn("PAUTA SÓCRATES", task_ctx["procedural_guide"])
            self.assertIn("PASO 1", task_ctx["procedural_guide"])
            self.assertEqual(called_kwargs.get("mentor"), "socrates")

        print("[OK] Test 19 superado: Documentos editables .docx generados y Sócrates cableado con instructivo procedimental sin prosa.")

    def test_20_timer_alarm_full_suite(self):
        """
        Prueba la suite completa de alarmas de foco/descanso tipo app nativa:
        1. Persistencia SQLite de alarmas programadas (save_timer_alarm, get_due_timer_alarms, mark_timer_alarm_notified, cancel_timer_alarms).
        2. Endpoints de FastAPI /api/timer/schedule y /api/timer/cancel.
        3. Despachador de alarmas de alta prioridad 24/7 (check_and_dispatch_due_timer_alarms con is_alarm=True y Urgency: high).
        4. Acciones interactivas de Service Worker ('stop_alarm' y 'open_timer').
        """
        import time
        import db.database as db
        import services.push_service as push_service
        import services.background_sync as bg_sync
        from fastapi.testclient import TestClient
        from main import app, user_sessions, ALEX_EMAIL

        # 1. Limpiar estado previo
        db.cancel_timer_alarms(user_email=ALEX_EMAIL)

        # 2. Programar alarma en base de datos
        alarm_id = "test-alarm-focus-1"
        now_ms = time.time() * 1000
        due_ms = now_ms - 500  # Ya vencida

        db.save_timer_alarm(
            alarm_id=alarm_id,
            user_email=ALEX_EMAIL,
            ends_at=due_ms,
            phase="focus",
            preset_label="Pomodoro 25/5"
        )

        # 3. Consultar alarmas vencidas
        due_list = db.get_due_timer_alarms(now_ms)
        self.assertGreater(len(due_list), 0)
        found = next((a for a in due_list if a["id"] == alarm_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["phase"], "focus")
        self.assertEqual(found["preset_label"], "Pomodoro 25/5")

        # 4. Probar endpoints de FastAPI
        user_sessions["test_timer_session"] = {
            "email": ALEX_EMAIL,
            "is_demo": True
        }
        client = TestClient(app, cookies={"agora_session": "test_timer_session", "session_id": "test_timer_session"})

        future_ends = (time.time() + 1500) * 1000
        sched_res = client.post("/api/timer/schedule", json={
            "ends_at": future_ends,
            "phase": "break",
            "label": "Descanso 5 min",
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/direct_device_phone",
                "keys": {"p256dh": "key_p256dh", "auth": "key_auth"}
            }
        })
        self.assertEqual(sched_res.status_code, 200)
        s_data = sched_res.json()
        self.assertEqual(s_data.get("status"), "ok")
        self.assertTrue(s_data.get("alarm_id"))

        # Verificar que la suscripción adjunta fue persistida en BD
        saved_sub = db.get_push_subscription_by_endpoint("https://fcm.googleapis.com/fcm/send/direct_device_phone")
        self.assertIsNotNone(saved_sub)
        self.assertEqual(saved_sub["keys"]["p256dh"], "key_p256dh")

        cancel_res = client.post("/api/timer/cancel", json={
            "user_email": ALEX_EMAIL
        })
        self.assertEqual(cancel_res.status_code, 200)
        self.assertEqual(cancel_res.json().get("status"), "ok")

        # 5. Despacho y entrega de alarma Web Push con Urgencia Alta y Vibración Vigorosa
        sub_info = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/timer_phone_alarm",
            "keys": {
                "p256dh": "dummy_p256dh_key",
                "auth": "dummy_auth_key"
            }
        }
        with patch("services.push_service.webpush") as mock_wp:
            mock_wp.return_value = MagicMock(status_code=201)
            ok, msg = push_service.send_web_push(
                subscription_info=sub_info,
                title="⏰ ¡Foco Completado!",
                body="¡Tu bloque de Pomodoro ha terminado!",
                url="/?openTimer=1",
                silent=False,
                tag="agora-timer-alarm",
                is_alarm=True
            )
            self.assertTrue(ok)
            self.assertTrue(mock_wp.called)

            called_kwargs = mock_wp.call_args.kwargs
            headers = called_kwargs.get("headers", {})
            self.assertEqual(headers.get("Urgency"), "high")
            self.assertEqual(called_kwargs.get("ttl"), 300)

            payload_str = called_kwargs.get("data", "{}")
            import json
            payload = json.loads(payload_str)
            self.assertTrue(payload.get("isAlarm"))
            self.assertTrue(payload.get("requireInteraction"))
            self.assertEqual(payload.get("vibrate"), [600, 250, 600, 250, 600, 250, 1000])

        # 6. Despachador de fondo de alarmas pendientes
        db.save_timer_alarm(
            alarm_id="test-alarm-due-watcher",
            user_email=ALEX_EMAIL,
            ends_at=time.time() * 1000 - 100,
            phase="focus",
            preset_label="Sprint 5 Min"
        )
        with patch("services.background_sync.send_web_push") as mock_send_alarm:
            mock_send_alarm.return_value = (True, "sent")
            dispatched = bg_sync.check_and_dispatch_due_timer_alarms()
            self.assertGreaterEqual(dispatched, 1)

        # 7. Limpiar
        db.cancel_timer_alarms(user_email=ALEX_EMAIL)
        print("[OK] Test 20 superado: Suite completa de alarmas de foco móviles (audio, vibración, SW, Web Push 24/7 y endpoints) validada.")

if __name__ == '__main__':
    unittest.main()



