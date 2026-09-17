"""
Servicio de Datos Universitarios para Modo Demo (estudiante.demo@agora.edu.mx).
Provee datos realistas de 6 materias universitarias de ingenieria, tareas tecnicas
con consignas detalladas, diversos estados (PENDIENTE, ENTREGADA, DEVUELTA, CALIFICADA),
distintas fechas limites (urgente, diaria, semanal, sin fecha) y avisos academicos autenticos.
"""

from datetime import datetime, timedelta

DEMO_STUDENT_EMAIL = "estudiante.demo@agora.edu.mx"
DEMO_STUDENT_NAME = "Estudiante Demo - Ágora"

demo_current_stage_idx = 0

COURSES_BASE = [
    {"id": "mock-c1", "name": "Cálculo Diferencial e Integral", "section": "Tronco Común", "room": "Edificio A-101"},
    {"id": "mock-c2", "name": "Estructuras de Datos y Algoritmos", "section": "Ingeniería de Software", "room": "Laboratorio 3"},
    {"id": "mock-c3", "name": "Física y Mecánica Clásica", "section": "Ciencias Básicas", "room": "Edificio B-204"},
    {"id": "mock-c4", "name": "Teoría de Sistemas y Señales", "section": "Computación y Control", "room": "Edificio C-302"},
    {"id": "mock-c5", "name": "Probabilidad y Estadística Aplicada", "section": "Ciencias Básicas", "room": "Aula 12"},
    {"id": "mock-c6", "name": "Taller de Redacción y Comunicación Académica", "section": "Tronco Común", "room": "Aula Magna"}
]

STAGES = [
    {
        "id": "inicio",
        "name": "Etapa 1: Inicio de Semestre (Semanas 1 a 4)",
        "streak_weeks": 2,
        "streak_days": 6,
        "courses": COURSES_BASE,
        "announcements": [
            {
                "id": "ann-1",
                "course_name": "Cálculo Diferencial e Integral",
                "creation_time": (datetime.now() - timedelta(days=2)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Bienvenidos al curso universitario. Se anexa el temario oficial del semestre y los criterios de acreditación (70% tareas y talleres, 30% examen departamental). Las asesorías de cubículo serán los miércoles de 11:00 a 13:00 hrs.",
                "type": "classroom"
            },
            {
                "id": "ann-2",
                "course_name": "Estructuras de Datos y Algoritmos",
                "creation_time": (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Aviso importante de laboratorio: Para la sesión del viernes, verificar la instalación de GCC/Clang o Python 3.11 con entorno virtual configurado en sus equipos personales.",
                "type": "classroom"
            },
            {
                "id": "ann-3",
                "course_name": "Física y Mecánica Clásica",
                "creation_time": (datetime.now() - timedelta(days=3)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Protocolo de Laboratorio: Es obligatorio el uso de bata blanca de algodón y calzado cerrado para ingresar a la práctica de colisiones mecánicas del lunes.",
                "type": "classroom"
            },
            {
                "id": "ann-4",
                "course_name": "Teoría de Sistemas y Señales",
                "creation_time": (datetime.now() - timedelta(days=4)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Fechas de tutorías: Están abiertas las inscripciones para las asesorías sabatinas de Transformada de Laplace y Modelado Dinámico en el aula C-104.",
                "type": "classroom"
            }
        ],
        "tasks": [
            {
                "id": "mock-t101",
                "course_id": "mock-c1",
                "course_name": "Cálculo Diferencial e Integral",
                "title": "Taller 1: Dominio, Rango y Asíntotas de Funciones Reales",
                "description": "--- Documento adjunto: Taller_1_Funciones_Reales.pdf ---\nObjetivo: Determinar analíticamente el dominio, rango y límites unilaterales de funciones racionales y seccionadas. Graficar con precisión las asíntotas verticales y horizontales de los ejercicios 1 al 12 en hoja milimétrica.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(hours=6)).isoformat(),
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
                "course_name": "Estructuras de Datos y Algoritmos",
                "title": "Práctica 1: Listas Enlazadas Dobles y Pilas en Memoria Dinámica",
                "description": "--- Documento adjunto: Practica_1_EDD_Pilas.pdf ---\nConsigna: Implementar en C++/Python una estructura de lista doblemente enlazada con operaciones de inserción ordenada O(n) y reversión in-place O(1) de memoria auxiliar. Anexar pruebas unitarias y captura de ejecución en Valgrind.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=1, hours=3)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "daily",
                "attachment_files": [
                    {"id": "mock-pdf-edd-1", "title": "Practica_1_EDD_Pilas.pdf", "link": "https://drive.google.com/file/d/mock-pdf-edd-1/view"}
                ]
            },
            {
                "id": "mock-t103",
                "course_id": "mock-c3",
                "course_name": "Física y Mecánica Clásica",
                "title": "Laboratorio 1: Conservación de la Cantidad de Movimiento y Colisiones 1D",
                "description": "--- Documento adjunto: Protocolo_Lab1_Colisiones.pdf ---\nAnálisis experimental de choque elástico e inelástico empleando sensores ópticos de fotopuerta. Calcular incertidumbre combinada propagada en LaTeX y comparar el coeficiente de restitución teórico vs experimental.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "daily",
                "attachment_files": [
                    {"id": "mock-pdf-fis-1", "title": "Protocolo_Lab1_Colisiones.pdf", "link": "https://drive.google.com/file/d/mock-pdf-fis-1/view"}
                ]
            },
            {
                "id": "mock-t104",
                "course_id": "mock-c4",
                "course_name": "Teoría de Sistemas y Señales",
                "title": "Tarea 1: Modelado Matemático de Sistemas Físicos Masa-Resorte-Amortiguador",
                "description": "--- Documento adjunto: Guia_Sistemas_Dinamicos_1.pdf ---\nPlantear las ecuaciones diferenciales de segundo orden para un sistema mecánico traslacional de dos masas acopladas. Obtener las funciones de transferencia en el dominio de Laplace Y(s)/U(s).",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=4)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "weekly",
                "attachment_files": [
                    {"id": "mock-pdf-sis-1", "title": "Guia_Sistemas_Dinamicos_1.pdf", "link": "https://drive.google.com/file/d/mock-pdf-sis-1/view"}
                ]
            },
            {
                "id": "mock-t105",
                "course_id": "mock-c5",
                "course_name": "Probabilidad y Estadística Aplicada",
                "title": "Taller Estadístico: Distribuciones Continuas y Teorema del Límite Central",
                "description": "--- Documento adjunto: Taller_Distribuciones_Continuas.pdf ---\nResolver los problemas aplicados sobre distribución Normal tipificada, Exponencial y Gamma en fiabilidad de componentes de red. Simular en R o Python el TLC para 10,000 iteraciones.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=5)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "weekly",
                "attachment_files": [
                    {"id": "mock-pdf-prob-1", "title": "Taller_Distribuciones_Continuas.pdf", "link": "https://drive.google.com/file/d/mock-pdf-prob-1/view"}
                ]
            },
            {
                "id": "mock-t106",
                "course_id": "mock-c6",
                "course_name": "Taller de Redacción y Comunicación Académica",
                "title": "Ensayo Crítico: Ética y Responsabilidad en Inteligencia Artificial y Datos",
                "description": "--- Documento adjunto: Rubrica_Ensayo_Academico_APA7.pdf ---\nRedactar un ensayo argumentativo de 4 cuartillas en formato APA 7ma edición analizando el sesgo algorítmico y la privacidad diferencial en modelos de lenguaje masivos. Mínimo 8 citas de artículos peer-reviewed.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=6)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "weekly",
                "attachment_files": [
                    {"id": "mock-pdf-red-1", "title": "Rubrica_Ensayo_Academico_APA7.pdf", "link": "https://drive.google.com/file/d/mock-pdf-red-1/view"}
                ]
            },
            {
                "id": "mock-t107",
                "course_id": "mock-c2",
                "course_name": "Estructuras de Datos y Algoritmos",
                "title": "Repositorio GitHub del Semestre y Configuración de CI/CD",
                "description": "--- Documento adjunto: Setup_Git_Workflows.pdf ---\nCrear el repositorio personal en GitHub para las prácticas de la materia, configurar el archivo .gitignore y un GitHub Action que ejecute los linters y pruebas automatizadas en cada push.",
                "link": "#",
                "due_date": None,
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 50,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-git-1", "title": "Setup_Git_Workflows.pdf", "link": "https://drive.google.com/file/d/mock-pdf-git-1/view"}
                ]
            },
            {
                "id": "mock-t108",
                "course_id": "mock-c1",
                "course_name": "Cálculo Diferencial e Integral",
                "title": "Lectura Formativa: Demostración Formal de Límites con Épsilon-Delta (Cauchy)",
                "description": "--- Documento adjunto: Notas_Rigor_Epsilon_Delta.pdf ---\nLectura complementaria opcional para comprender el rigor matemático de Cauchy y Weierstrass en el cálculo infinitesimal moderno. Resolver los dos retos al final del documento.",
                "link": "#",
                "due_date": None,
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 30,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-calc-eps", "title": "Notas_Rigor_Epsilon_Delta.pdf", "link": "https://drive.google.com/file/d/mock-pdf-calc-eps/view"}
                ]
            },
            {
                "id": "mock-t109",
                "course_id": "mock-c1",
                "course_name": "Cálculo Diferencial e Integral",
                "title": "Cuestionario 0: Diagnóstico de Álgebra y Trigonometría Fundamental",
                "description": "--- Documento adjunto: Examen_Diagnostico_Algebra.pdf ---\nEvaluación de conocimientos previos: factorización de polinomios, identidades trigonométricas fundamentales y resolución de inecuaciones no lineales.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=2)).isoformat(),
                "classroom_status": "ENTREGADA",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-diag-1", "title": "Examen_Diagnostico_Algebra.pdf", "link": "https://drive.google.com/file/d/mock-pdf-diag-1/view"}
                ]
            },
            {
                "id": "mock-t110",
                "course_id": "mock-c3",
                "course_name": "Física y Mecánica Clásica",
                "title": "Práctica 0: Teoría de Errores, Cifras Significativas y Calibración de Instrumentos",
                "description": "--- Documento adjunto: Manual_Metrologia_Basica.pdf ---\nMediciones repetidas con vernier y micrómetro. Elaboración del histograma de dispersión y cálculo de desviación estándar e incertidumbre tipo A y tipo B.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=3)).isoformat(),
                "classroom_status": "ENTREGADA",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-fis-0", "title": "Manual_Metrologia_Basica.pdf", "link": "https://drive.google.com/file/d/mock-pdf-fis-0/view"}
                ]
            },
            {
                "id": "mock-t111",
                "course_id": "mock-c6",
                "course_name": "Taller de Redacción y Comunicación Académica",
                "title": "Ficha Bibliográfica: Formato de Citas y Paráfrasis en Formato APA",
                "description": "--- Documento adjunto: Ejercicio_Citas_APA7.pdf ---\nEjercicios prácticos de citación directa (corta y en bloque) y paráfrasis con dos y más autores.\n\nComentario del Profesor: 'Excelente estructura en la paráfrasis, pero en el ejercicio 4 faltó incluir el número de página en la cita directa. Revisa la corrección adjunta para la nota final.'",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=4)).isoformat(),
                "classroom_status": "DEVUELTA",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-apa-rev", "title": "Ejercicio_Citas_APA7.pdf", "link": "https://drive.google.com/file/d/mock-pdf-apa-rev/view"}
                ]
            },
            {
                "id": "mock-t112",
                "course_id": "mock-c2",
                "course_name": "Estructuras de Datos y Algoritmos",
                "title": "Evaluación Diagnóstica: Complejidad Temporal Notación Big-O",
                "description": "--- Documento adjunto: Evaluacion_BigO.pdf ---\nAnálisis asintótico de bucles anidados, recurrencias simples y teorema maestro para algoritmos de división y conquista.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=7)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 100,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-bigo", "title": "Evaluacion_BigO.pdf", "link": "https://drive.google.com/file/d/mock-pdf-bigo/view"}
                ]
            },
            {
                "id": "mock-t113",
                "course_id": "mock-c4",
                "course_name": "Teoría de Sistemas y Señales",
                "title": "Práctica Introductoria: Clasificación de Señales Continuas y Discretas",
                "description": "--- Documento adjunto: Clasificacion_Senales.pdf ---\nDeterminación de propiedades de señales: periodicidad, simetría (par/impar), causalidad y estabilidad en sentido BIBO. Gráficas en Python con NumPy y Matplotlib.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=8)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 95,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-sen-1", "title": "Clasificacion_Senales.pdf", "link": "https://drive.google.com/file/d/mock-pdf-sen-1/view"}
                ]
            },
            {
                "id": "mock-t114",
                "course_id": "mock-c5",
                "course_name": "Probabilidad y Estadística Aplicada",
                "title": "Taller 1: Análisis Exploratorio de Datos Multivariados y Regresión Lineal",
                "description": "--- Documento adjunto: Taller1_AED_Regresion.pdf ---\nCálculo de estadísticos de tendencia central, variabilidad, diagramas de dispersión, covarianza y recta de mínimos cuadrados ordinarios para un dataset meteorológico.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=10)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 90,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-aed-1", "title": "Taller1_AED_Regresion.pdf", "link": "https://drive.google.com/file/d/mock-pdf-aed-1/view"}
                ]
            }
        ]
    },
    {
        "id": "parciales",
        "name": "Etapa 2: Periodo de Exámenes Parciales y Entregas Críticas (Semanas 7 a 9)",
        "streak_weeks": 6,
        "streak_days": 18,
        "courses": COURSES_BASE,
        "announcements": [
            {
                "id": "ann-201",
                "course_name": "Cálculo Diferencial e Integral",
                "creation_time": (datetime.now() - timedelta(days=2)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Examen Parcial Departamental confirmado para el próximo martes. Traer formulario oficial impreso sin anotaciones y calculadora no programable.",
                "type": "classroom"
            },
            {
                "id": "ann-202",
                "course_name": "Estructuras de Datos y Algoritmos",
                "creation_time": (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Entrega de Avance de Proyecto: La demostración en vivo de Árboles AVL y Grafos será durante la sesión práctica de este jueves.",
                "type": "classroom"
            }
        ],
        "tasks": [
            {
                "id": "mock-t201",
                "course_id": "mock-c1",
                "course_name": "Cálculo Diferencial e Integral",
                "title": "Preparación Examen Parcial: Métodos Avanzados de Integración",
                "description": "--- Documento adjunto: Problemario_Parcial_Integrales.pdf ---\nResolución paso a paso de integrales por sustitución trigonométrica, fracciones parciales y partes. Seleccionar 15 problemas de los 30 propuestos.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "daily",
                "attachment_files": [
                    {"id": "mock-pdf-calc-2", "title": "Problemario_Parcial_Integrales.pdf", "link": "https://drive.google.com/file/d/mock-pdf-calc-2/view"}
                ]
            },
            {
                "id": "mock-t202",
                "course_id": "mock-c2",
                "course_name": "Estructuras de Datos y Algoritmos",
                "title": "Proyecto Parcial: Árboles Balanceados AVL y Grafos con Dijkstra",
                "description": "--- Documento adjunto: Especificacion_Proyecto_AVL_Dijkstra.pdf ---\nDesarrollo completo en C++/Python de un motor de búsqueda de rutas óptimas sobre grafos con rebalanceo automático AVL para índices de nodos.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "weekly",
                "attachment_files": [
                    {"id": "mock-pdf-avl", "title": "Especificacion_Proyecto_AVL_Dijkstra.pdf", "link": "https://drive.google.com/file/d/mock-pdf-avl/view"}
                ]
            },
            {
                "id": "mock-t203",
                "course_id": "mock-c4",
                "course_name": "Teoría de Sistemas y Señales",
                "title": "Práctica de Laboratorio: Diagramas de Bode y Márgenes de Fase/Ganancia",
                "description": "--- Documento adjunto: Guia_Bode_Nyquist.pdf ---\nAnálisis de respuesta en frecuencia en lazo cerrado para sistemas de tercer orden empleando MATLAB/Python Control Systems Toolbox.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=4)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "weekly",
                "attachment_files": [
                    {"id": "mock-pdf-bode", "title": "Guia_Bode_Nyquist.pdf", "link": "https://drive.google.com/file/d/mock-pdf-bode/view"}
                ]
            },
            {
                "id": "mock-t204",
                "course_id": "mock-c3",
                "course_name": "Física y Mecánica Clásica",
                "title": "Reporte Experimental: Oscilador Armónico Amortiguado y Forzado",
                "description": "--- Documento adjunto: Reporte_Oscilaciones_Mecanicas.pdf ---\nDeterminación experimental del factor de amortiguamiento gamma y el factor de calidad Q a partir de la envolvente exponencial.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=2)).isoformat(),
                "classroom_status": "ENTREGADA",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-osc", "title": "Reporte_Oscilaciones_Mecanicas.pdf", "link": "https://drive.google.com/file/d/mock-pdf-osc/view"}
                ]
            },
            {
                "id": "mock-t205",
                "course_id": "mock-c5",
                "course_name": "Probabilidad y Estadística Aplicada",
                "title": "Prueba de Hipótesis para Medias y Proporciones Poblacionales",
                "description": "--- Documento adjunto: Examen_Parcial_Probabilidad.pdf ---\nCálculo de p-valores, estadísticos Z y t-Student con intervalos de confianza del 95% y 99% en control de calidad industrial.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 96,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-hip", "title": "Examen_Parcial_Probabilidad.pdf", "link": "https://drive.google.com/file/d/mock-pdf-hip/view"}
                ]
            }
        ]
    },
    {
        "id": "finales",
        "name": "Etapa 3: Cierre de Semestre y Proyectos Integradores (Semanas 14 a 16)",
        "streak_weeks": 12,
        "streak_days": 45,
        "courses": COURSES_BASE,
        "announcements": [
            {
                "id": "ann-301",
                "course_name": "Estructuras de Datos y Algoritmos",
                "creation_time": (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Entrega final de proyectos: El repositorio debe contener README detallado, suite completa de pruebas unitarias y documentación de arquitectura.",
                "type": "classroom"
            },
            {
                "id": "ann-302",
                "course_name": "Teoría de Sistemas y Señales",
                "creation_time": (datetime.now() - timedelta(days=2)).strftime("%d/%m/%Y, %H:%M"),
                "text": "Publicación de calificaciones ordinarias preliminares este viernes. Dudas y aclaraciones en horario de clase.",
                "type": "classroom"
            }
        ],
        "tasks": [
            {
                "id": "mock-t301",
                "course_id": "mock-c2",
                "course_name": "Estructuras de Datos y Algoritmos",
                "title": "Entrega Final: Sistema de Archivos Virtual Indexado B+ Tree",
                "description": "--- Documento adjunto: Proyecto_Final_BPlusTree.pdf ---\nImplementación completa en disco de un índice multinivel B+ Tree con soporte a transacciones ACID simplificadas y caching LRU.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "daily",
                "attachment_files": [
                    {"id": "mock-pdf-btree", "title": "Proyecto_Final_BPlusTree.pdf", "link": "https://drive.google.com/file/d/mock-pdf-btree/view"}
                ]
            },
            {
                "id": "mock-t302",
                "course_id": "mock-c4",
                "course_name": "Teoría de Sistemas y Señales",
                "title": "Proyecto Integrador: Filtro Digital IIR/FIR con Procesamiento en Tiempo Real",
                "description": "--- Documento adjunto: Guia_Proyecto_DSP.pdf ---\nDiseño de filtro Chebyshev Tipo I para supresión de armónicos de 60 Hz en señal biomédica ECG. Simulación y verificación en Python.",
                "link": "#",
                "due_date": (datetime.now() + timedelta(days=4)).isoformat(),
                "classroom_status": "PENDIENTE",
                "assigned_grade": None,
                "max_points": 100,
                "mission_type": "weekly",
                "attachment_files": [
                    {"id": "mock-pdf-dsp", "title": "Guia_Proyecto_DSP.pdf", "link": "https://drive.google.com/file/d/mock-pdf-dsp/view"}
                ]
            },
            {
                "id": "mock-t303",
                "course_id": "mock-c6",
                "course_name": "Taller de Redacción y Comunicación Académica",
                "title": "Artículo de Divulgación Científica Final en Formato IEEE",
                "description": "--- Documento adjunto: Template_Articulo_IEEE.pdf ---\nArtículo final de 6 páginas en formato IEEE a dos columnas con abstract en inglés y español, conclusiones y bibliografía indexada.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=3)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 98,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-ieee", "title": "Template_Articulo_IEEE.pdf", "link": "https://drive.google.com/file/d/mock-pdf-ieee/view"}
                ]
            },
            {
                "id": "mock-t304",
                "course_id": "mock-c1",
                "course_name": "Cálculo Diferencial e Integral",
                "title": "Examen Colegiado Ordinario Departamental de Cálculo",
                "description": "--- Documento adjunto: Hoja_Respuestas_Examen_Ordinario.pdf ---\nEvaluación integradora de Cálculo diferencial e integral de funciones de una variable real.",
                "link": "#",
                "due_date": (datetime.now() - timedelta(days=5)).isoformat(),
                "classroom_status": "CALIFICADA",
                "assigned_grade": 94,
                "max_points": 100,
                "mission_type": "secondary",
                "attachment_files": [
                    {"id": "mock-pdf-ord", "title": "Hoja_Respuestas_Examen_Ordinario.pdf", "link": "https://drive.google.com/file/d/mock-pdf-ord/view"}
                ]
            }
        ]
    }
]

def get_demo_stage_data(stage_id: str = None) -> dict:
    """Devuelve el paquete de datos de la etapa solicitada o de la activa actual."""
    global demo_current_stage_idx
    if stage_id:
        for idx, s in enumerate(STAGES):
            if s["id"] == stage_id:
                demo_current_stage_idx = idx
                return s
    return STAGES[demo_current_stage_idx % len(STAGES)]

def cycle_demo_stage() -> dict:
    """Avanza a la siguiente etapa del semestre (rotación al entrar)."""
    global demo_current_stage_idx
    demo_current_stage_idx = (demo_current_stage_idx + 1) % len(STAGES)
    return STAGES[demo_current_stage_idx]

# Aliases de compatibilidad con codigo existente
get_alex_stage_data = get_demo_stage_data
cycle_alex_stage = cycle_demo_stage
