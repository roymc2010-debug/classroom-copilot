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

if __name__ == '__main__':
    unittest.main()
