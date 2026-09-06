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

from services.classroom_service import get_active_courses, get_all_tasks, fetch_courses

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

if __name__ == '__main__':
    unittest.main()
