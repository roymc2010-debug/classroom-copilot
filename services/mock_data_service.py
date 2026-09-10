"""
Servicio de Datos Falsos Universitarios por Etapas del Semestre para Alex Muñoz (alexmunoz918@gmail.com).
Provee datos realistas de materias, tareas con consignas detalladas, avisos y progreso de racha.
"""

from datetime import datetime, timedelta

alex_current_stage_idx = 0

STAGES = [
    {
        "id": "inicio",
        "name": "Etapa 1: Inicio de Semestre (Semanas 1 a 4)",
        "streak_weeks": 2,
        "streak_days": 6,
        "courses": [
            {"id": "mock-c1", "name": "Cálculo Diferencial e Integral", "section": "Tronco Común", "room": "Edificio A-101"},
            {"id": "mock-c2", "name": "Algoritmos y Programación Básica", "section": "Tronco Común", "room": "Laboratorio 3"},
            {"id": "mock-c3", "name": "Física y Mecánica Clásica", "section": "Tronco Común", "room": "Edificio B-204"},
            {"id": "mock-c4", "name": "Taller de Redacción y Comunicación Académica", "section": "Tronco Común", "room": "Aula Magna"}
        ],
        "announcements": [
            {
                "id": "ann-1",
                "course_name": "Cálculo Diferencial e Integral",
                "creation_time": (datetime.now() - timedelta(days=2)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Bienvenidos al curso universitario. Se anexa el temario oficial del semestre y los criterios de acreditación (70% tareas y talleres, 30% examen departamental). Las asesorías de cubículo serán los miércoles.",
                "type": "classroom"
            },
            {
                "id": "ann-2",
                "course_name": "Algoritmos y Programación Básica",
                "creation_time": (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Aviso general: Para la práctica del viernes, favor de verificar que tengan instalada la versión 3.10 o superior de Python y VS Code en sus portátiles.",
                "type": "classroom"
            }
        ],
        "tasks": [
            {
                "id": "mock-t101",
                "course_id": "mock-c1",
                "course_name": "Cálculo Diferencial e Integral",
                "title": "Taller 1: Dominio, Rango y Composición de Funciones",
                "description": "--- Documento adjunto: Taller_1_Funciones_Reales.pdf ---\nObjetivo: Determinar analíticamente el dominio y rango de funciones racionales y con radicales. Graficar las asíntotas verticales y horizontales de los ejercicios 1 al 8. Justificar la continuidad en cada intervalo.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=1, hours=4)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "daily",
                "attachment_files": [
                    {"id": "mock-pdf-calc-1", "title": "Taller_1_Funciones_Reales.pdf", "link": "https://drive.google.com/file/d/mock-pdf-calc-1/view"}
                ]
            },
            {
                "id": "mock-t102",
                "course_id": "mock-c2",
                "course_name": "Algoritmos y Programación Básica",
                "title": "Práctica 1: Algoritmos Secuenciales y Estructuras Condicionales",
                "description": "--- Documento adjunto: Practica_1_Python_Basico.pdf ---\nConsigna: Desarrollar en Python un script que calcule el índice de masa corporal y aplique descuentos según volumen de compra. Implementar validación de entradas y diagramas de flujo en formato mermaid.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-algo-1", "title": "Practica_1_Python_Basico.pdf", "link": "https://drive.google.com/file/d/mock-pdf-algo-1/view"}
                ]
            },
            {
                "id": "mock-t103",
                "course_id": "mock-c3",
                "course_name": "Física y Mecánica Clásica",
                "title": "Cuestionario Diagnóstico: Vectores y Estática de la Partícula",
                "description": "Resolver los problemas de equilibrio estático en dos dimensiones aplicando descomposición en componentes rectangulares. Se debe subir el procedimiento manuscrito legible.",
                "link": "#",
                "due_date": None,
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "open",
                "attachment_files": [
                    {"id": "mock-pdf-fis-1", "title": "Guia_Vectores_Estatica.pdf", "link": "https://drive.google.com/file/d/mock-pdf-fis-1/view"}
                ]
            },
            {
                "id": "mock-t104",
                "course_id": "mock-c4",
                "course_name": "Taller de Redacción y Comunicación Académica",
                "title": "Ensayo Inicial: La Importancia del Pensamiento Crítico en la Ciencia",
                "description": "Redactar un ensayo argumentativo de 2 cuartillas con formato APA 7ma edición. Introducción, postura personal fundamentada en 2 fuentes académicas y conclusiones.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=2)).isoformat(),
                "classroom_status": "ENTREGADA",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-red-1", "title": "Rubrica_Ensayo_Critico.pdf", "link": "https://drive.google.com/file/d/mock-pdf-red-1/view"}
                ]
            }
        ]
    },
    {
        "id": "parciales",
        "name": "Etapa 2: Mitad de Semestre y Exámenes Parciales (Semanas 7 a 9)",
        "streak_weeks": 8,
        "streak_days": 32,
        "courses": [
            {"id": "mock-c21", "name": "Ecuaciones Diferenciales y Laplace", "section": "Ingeniería", "room": "Edificio C-302"},
            {"id": "mock-c22", "name": "Estructuras de Datos y Algoritmos", "section": "Ingeniería", "room": "Laboratorio 5"},
            {"id": "mock-c23", "name": "Circuitos Eléctricos y Electrónica", "section": "Ingeniería", "room": "Laboratorio Electrónica"},
            {"id": "mock-c24", "name": "Métodos Numéricos", "section": "Ingeniería", "room": "Edificio B-102"},
            {"id": "mock-c25", "name": "Legislación y Ética Profesional", "section": "Humanidades", "room": "Aula 10"}
        ],
        "announcements": [
            {
                "id": "ann-21",
                "course_name": "Circuitos Eléctricos y Electrónica",
                "creation_time": (datetime.now() - timedelta(hours=6)).strftime("%d/%m/%Y, %H:%M"),
                "text": "AVISO DE PARCIAL: El examen departamental de medio término se aplicará este jueves a las 9:00 hrs. Temario: Leyes de Kirchhoff, método de nodos, mallas y teoremas de Thevenin/Norton. Traer calculadora científica no programable.",
                "type": "classroom"
            },
            {
                "id": "ann-22",
                "course_name": "Estructuras de Datos y Algoritmos",
                "creation_time": (datetime.now() - timedelta(days=2)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Se han publicado las calificaciones correspondientes al avance del árbol binario y grafos. Revisar notas en el portal.",
                "type": "classroom"
            }
        ],
        "tasks": [
            {
                "id": "mock-t201",
                "course_id": "mock-c21",
                "course_name": "Ecuaciones Diferenciales y Laplace",
                "title": "Misión Principal: Examen Parcial de Transformada de Laplace y Sistemas Dinámicos",
                "description": "--- Documento adjunto: Parcial_Laplace_Sistemas.pdf ---\nInstrucciones del examen: Resolver analíticamente los 4 problemas de valor inicial mediante la transformada de Laplace. Obtener la función de transferencia y determinar la estabilidad del sistema mediante el criterio de Routh-Hurwitz.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(hours=14)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "main",
                "attachment_files": [
                    {"id": "mock-pdf-ed-1", "title": "Parcial_Laplace_Sistemas.pdf", "link": "https://drive.google.com/file/d/mock-pdf-ed-1/view"}
                ]
            },
            {
                "id": "mock-t202",
                "course_id": "mock-c22",
                "course_name": "Estructuras de Datos y Algoritmos",
                "title": "Proyecto Intermedio: Implementación de Algoritmo de Dijkstra para Rutas Óptimas",
                "description": "--- Documento adjunto: Proyecto_Grafos_Dijkstra.pdf ---\nRequerimientos: Programar en C++ o Python una estructura de grafo ponderado dirigido con lista de adyacencia. Medir la complejidad temporal Big-O y generar casos de prueba con al menos 20 nodos.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-eda-1", "title": "Proyecto_Grafos_Dijkstra.pdf", "link": "https://drive.google.com/file/d/mock-pdf-eda-1/view"}
                ]
            },
            {
                "id": "mock-t203",
                "course_id": "mock-c23",
                "course_name": "Circuitos Eléctricos y Electrónica",
                "title": "Reporte de Laboratorio 3: Teorema de Thevenin y Máxima Transferencia de Potencia",
                "description": "Contrastar las mediciones experimentales con los cálculos teóricos y la simulación en LTSpice. Calcular el error relativo porcentual.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=3)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 96,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-circ-1", "title": "Guia_Lab3_Thevenin_Potencia.pdf", "link": "https://drive.google.com/file/d/mock-pdf-circ-1/view"}
                ]
            },
            {
                "id": "mock-t204",
                "course_id": "mock-c24",
                "course_name": "Métodos Numéricos",
                "title": "Taller 4: Solución de Ecuaciones No Lineales (Newton-Raphson y Bisección)",
                "description": "Tabular iteraciones y criterios de convergencia con tolerancia de 0.0001.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 92,
                "max_points": 100,
                "mission_type": "daily",
                "attachment_files": [
                    {"id": "mock-pdf-num-1", "title": "Taller4_Newton_Raphson.pdf", "link": "https://drive.google.com/file/d/mock-pdf-num-1/view"}
                ]
            },
            {
                "id": "mock-t205",
                "course_id": "mock-c25",
                "course_name": "Legislación y Ética Profesional",
                "title": "Análisis de Caso: Responsabilidad Civil en Fallos de Software Crítico",
                "description": "Redactar silogismo jurídico y análisis de jurisprudencia sobre el caso Therac-25.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=1)).isoformat(),
                "classroom_status": "ENTREGADA",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-eti-1", "title": "Caso_Estudio_Responsabilidad_Etica.pdf", "link": "https://drive.google.com/file/d/mock-pdf-eti-1/view"}
                ]
            }
        ]
    },
    {
        "id": "finales",
        "name": "Etapa 3: Cierre de Semestre, Proyectos Finales y Rescate (Semanas 13 a 15)",
        "streak_weeks": 15,
        "streak_days": 60,
        "courses": [
            {"id": "mock-c31", "name": "Teoría de Sistemas y Control Automático", "section": "Especialidad", "room": "Edificio D-401"},
            {"id": "mock-c32", "name": "Arquitectura de Computadoras y Microcontroladores", "section": "Especialidad", "room": "Laboratorio Embebidos"},
            {"id": "mock-c33", "name": "Redes de Datos y Telecomunicaciones", "section": "Especialidad", "room": "Laboratorio Redes"},
            {"id": "mock-c34", "name": "Formulación y Evaluación de Proyectos de Inversión", "section": "Económico-Administrativa", "room": "Aula 22"},
            {"id": "mock-c35", "name": "Seminario de Titulación e Investigación", "section": "Investigación", "room": "Sala de Seminarios"}
        ],
        "announcements": [
            {
                "id": "ann-31",
                "course_name": "Teoría de Sistemas y Control Automático",
                "creation_time": (datetime.now() - timedelta(hours=3)).strftime("%d/%m/%Y, %H:%M"),
                "text": "ENTREGA FINAL: El prototipo del controlador PID sintonizado en hardware debe presentarse funcionando en el laboratorio el próximo lunes. Fecha improrrogable.",
                "type": "classroom"
            },
            {
                "id": "ann-32",
                "course_name": "Redes de Datos y Telecomunicaciones",
                "creation_time": (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Se adjunta la rúbrica oficial para la defensa oral del proyecto de subredes VLAN y enrutamiento OSPF.",
                "type": "classroom"
            }
        ],
        "tasks": [
            {
                "id": "mock-t301",
                "course_id": "mock-c31",
                "course_name": "Teoría de Sistemas y Control Automático",
                "title": "Misión Principal: Proyecto Final de Control PID en Lazo Cerrado con ESP32",
                "description": "--- Documento adjunto: Proyecto_Final_Control_PID.pdf ---\nConsigna Final: Presentar el modelado matemático de la planta térmica, la simulación en Simulink y la implementación en microcontrolador con acondicionamiento de señal analógica. Incluir gráfica de respuesta al escalón y análisis de sobrepaso porcentual.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "main",
                "attachment_files": [
                    {"id": "mock-pdf-ctrl-1", "title": "Proyecto_Final_Control_PID.pdf", "link": "https://drive.google.com/file/d/mock-pdf-ctrl-1/view"}
                ]
            },
            {
                "id": "mock-t302",
                "course_id": "mock-c32",
                "course_name": "Arquitectura de Computadoras y Microcontroladores",
                "title": "Misión Especial: Corrección y Rescate de Diseño de Procesador MIPS en FPGA",
                "description": "--- Documento adjunto: Correcciones_MIPS_Pipeline.pdf ---\nTu profesor devolvió el avance de la Unidad Aritmética Lógica (ALU) para corregir los riesgos de datos (data hazards). Resuelve las dependencias con adelantamiento de operandos para recuperar la máxima puntuación.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(hours=18)).isoformat(),
                "classroom_status": "DEVUELTA",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "special",
                "attachment_files": [
                    {"id": "mock-pdf-arq-1", "title": "Correcciones_MIPS_Pipeline.pdf", "link": "https://drive.google.com/file/d/mock-pdf-arq-1/view"}
                ]
            },
            {
                "id": "mock-t303",
                "course_id": "mock-c33",
                "course_name": "Redes de Datos y Telecomunicaciones",
                "title": "Misión de Rescate: Diseño de Esquema de Direccionamiento IPv4 y Subnetting VLSM",
                "description": "--- Documento adjunto: Guia_Subnetting_VLSM.pdf ---\nEntrega rezagada de la práctica de laboratorio de cálculo de máscaras de subred de longitud variable. Entregar antes de las 18:00 hrs para evitar reprobación.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(hours=5)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "rescue",
                "attachment_files": [
                    {"id": "mock-pdf-redes-1", "title": "Guia_Subnetting_VLSM.pdf", "link": "https://drive.google.com/file/d/mock-pdf-redes-1/view"}
                ]
            },
            {
                "id": "mock-t304",
                "course_id": "mock-c34",
                "course_name": "Formulación y Evaluación de Proyectos de Inversión",
                "title": "Entrega Final: Estudio Financiero, VAN, TIR y Período de Recuperación",
                "description": "--- Documento adjunto: Plantilla_Evaluacion_Financiera.pdf ---\nBalance proforma, flujo de caja neto proyectado a 5 años y análisis de sensibilidad ante variaciones de tasa de descuento.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=3)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 98,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-proy-1", "title": "Plantilla_Evaluacion_Financiera.pdf", "link": "https://drive.google.com/file/d/mock-pdf-proy-1/view"}
                ]
            },
            {
                "id": "mock-t305",
                "course_id": "mock-c35",
                "course_name": "Seminario de Titulación e Investigación",
                "title": "Reporte Final: Marco Teórico y Estado del Arte de la Tesis",
                "description": "--- Documento adjunto: Guia_Marco_Teorico_Tesis.pdf ---\nRevisión sistemática de literatura con al menos 25 referencias indexadas en Scopus o IEEE Xplore.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=6)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 100,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-tesis-1", "title": "Guia_Marco_Teorico_Tesis.pdf", "link": "https://drive.google.com/file/d/mock-pdf-tesis-1/view"}
                ]
            }
        ]
    }
]

def get_alex_stage_data(stage_id: str = None) -> dict:
    """Devuelve el paquete de datos de la etapa solicitada o de la activa actual."""
    global alex_current_stage_idx
    if stage_id:
        for idx, s in enumerate(STAGES):
            if s["id"] == stage_id:
                alex_current_stage_idx = idx
                return s
    return STAGES[alex_current_stage_idx % len(STAGES)]

def cycle_alex_stage() -> dict:
    """Avanza a la siguiente etapa del semestre (rotación al entrar)."""
    global alex_current_stage_idx
    alex_current_stage_idx = (alex_current_stage_idx + 1) % len(STAGES)
    return STAGES[alex_current_stage_idx]