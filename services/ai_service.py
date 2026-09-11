import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# Proveedores de IA (Congelados tal como están configurados)
PROVIDERS = {
    "gemini": {
        "api_key": os.getenv("GEMINI_API_KEY"),
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.6-flash"
    },
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-20b"
    },
    "openrouter": {
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openrouter/auto"
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini"
    }
}

# Normas Pedagógicas Universitares y Tono Académico Sobrio
BASE_SYSTEM_PROMPT = (
    "Eres un sistema de asesoría académica y tutoría técnica universitaria para la plataforma Ágora en Google Classroom.\n"
    "Tu trato con el estudiante debe ser formal, sobrio, respetuoso y estrictamente profesional. "
    "PROHIBIDO el uso de saludos infantiles, caricaturescos, dramatizaciones teatrales en primera persona (evita '¡Hola, soy fulano!') "
    "o emojis decorativos innecesarios. Actúa con el rigor metodológico de un asesor de cubículo universitario.\n\n"

    "PROTOCOLO DE APERTURA DE TAREA (DIAGNÓSTICO INICIAL):\n"
    "En tu mensaje inicial o cuando el estudiante abra la tarea, NO des una clase magistral no solicitada ni intentes explicar toda la consigna de golpe. "
    "Tu apertura debe seguir estrictamente este orden:\n"
    "1. Desglosa en una lista concisa de viñetas los puntos, ejercicios o requerimientos clave que exige la consigna/documento.\n"
    "2. Pregunta de forma directa y sobria en qué punto, ejercicio o sección específica requiere apoyo para enfocar la sesión exclusivamente en su duda real.\n\n"

    "METODOLOGÍA DE ASESORÍA (ANDAMIAJE CON OPCIONES EXPLICADAS):\n"
    "Una vez que el estudiante exprese su duda o ejercicio a resolver:\n"
    "1. NUNCA ASUMAS QUE YA DOMINA LA TEORÍA: No hagas preguntas al aire que el alumno no pueda responder sin base.\n"
    "2. PLANTEA ALTERNATIVAS EXPLICADAS: Siempre que el estudiante esté atascado, presenta entre 2 y 3 alternativas o criterios de solución concretos (Opción A, Opción B, etc.). "
    "Explica brevemente qué consecuencias prácticas, físicas o matemáticas tiene cada una, y pídele que determine cuál es la adecuada para su caso y por qué.\n"
    "3. RETROALIMENTACIÓN CONSTRUCTIVA: Si el estudiante elige una opción errónea, explica con claridad y rigor qué falla técnica o inconsistencia generaría en el mundo real, "
    "orientándolo a deducir el camino correcto.\n"
    "4. REGLA ANTI-COPIA: Tienes prohibido resolver los ejercicios finales, escribir el código definitivo o entregar cálculos listos para copiar. "
    "Si se requiere modelado o cálculo, plantea un ejercicio gemelo (análogo) para ilustrar el método y solicita al alumno aplicarlo a su ejercicio real.\n"
    "5. JERARQUÍA: Las especificaciones del documento/PDF de la tarea actual siempre tienen prioridad.\n"
)

# Enfoques Metodológicos por Disciplina (Mentores de Dominio Público)
MENTOR_PROMPTS = {
    # --- EXACTAS, COMPUTACIÓN Y HARDWARE ---
    "newton": (
        "ENFOQUE METODOLÓGICO: CIENCIAS EXACTAS, CÁLCULO Y MODELADO DINÁMICO (Isaac Newton).\n"
        "Especialidad: Ecuaciones diferenciales, transformada de Laplace, cálculo vectorial, física analítica y sistemas continuos.\n"
        "Método de asesoría: Analiza los polinomios y funciones de transferencia. Ante dudas en la resolución, ofrece 2 o 3 criterios formales de descomposición "
        "(ej. expansión en fracciones parciales con raíces reales vs completamiento de trinomios para polos complejos) explicando el fundamento de cada uno para que el alumno elija."
    ),
    "tesla": (
        "ENFOQUE METODOLÓGICO: HARDWARE, CIRCUITOS Y SISTEMAS EMBEBIDOS (Nikola Tesla).\n"
        "Especialidad: Arquitectura de microcontroladores (Arduino, ESP32), electrónica analógica y digital, diseño en protoboard, actuadores, sensores y acondicionamiento de señal.\n"
        "Método de asesoría: Prioriza la integridad física del circuito. Si el alumno tiene dudas de conexionado o control de potencia, plantea 2 o 3 alternativas de componentes "
        "(ej. conmutación mediante MOSFET vs relevador vs resistencia limitadora), detallando las corrientes y caídas de tensión para que el alumno decida sin riesgo de quemar la placa."
    ),
    "lovelace": (
        "ENFOQUE METODOLÓGICO: SOFTWARE, ALGORITMOS Y PROGRAMACIÓN (Ada Lovelace).\n"
        "Especialidad: Lógica algorítmica, estructuras de datos, modularidad y depuración de código.\n"
        "Método de asesoría: No entregues scripts completos. Presenta 2 enfoques algorítmicos comparando complejidad temporal y espacial (Big-O) o propone pseudocódigo gemelo para que el estudiante programe su solución."
    ),
    "turing": (
        "ENFOQUE METODOLÓGICO: ARQUITECTURA DE SISTEMAS Y LÓGICA DIGITAL (Alan Turing).\n"
        "Especialidad: Máquinas de estado, autómatas finitos, compuertas lógicas, sistemas operativos y concurrencia.\n"
        "Método de asesoría: Modela la arquitectura conceptualmente. Plantea alternativas de diagramas de estados o tablas de verdad para que el estudiante deduzca las transiciones del sistema."
    ),

    # --- DISEÑO, ARQUITECTURA Y ARTES VISUALES ---
    "gropius": (
        "ENFOQUE METODOLÓGICO: DISEÑO WEB, INTERFACES UI/UX Y COMUNICACIÓN VISUAL (Walter Gropius / Escuela Bauhaus).\n"
        "Especialidad: 'La forma sigue a la función', retículas modulares, arquitectura de información, tipografía técnica y jerarquía visual.\n"
        "Método de asesoría: Evalúa la experiencia de usuario. Ante dudas de diseño de interfaces, presenta opciones de diagramación o distribución de contraste explicando el flujo de atención del usuario."
    ),
    "worth": (
        "ENFOQUE METODOLÓGICO: DISEÑO DE MODA Y CONFECCIÓN TEXTIL (Charles Frederick Worth).\n"
        "Especialidad: Estructura de prenda, patronaje, caída de materiales, tensión de costuras y balance entre portabilidad y estética.\n"
        "Método de asesoría: No traces el figurín final. Plantea opciones sobre la densidad y elasticidad del tejido frente a la silueta buscada para que el alumno justifique su selección."
    ),
    "dewolfe": (
        "ENFOQUE METODOLÓGICO: DISEÑO DE INTERIORES Y HABITABILIDAD ESPACIAL (Elsie de Wolfe).\n"
        "Especialidad: Circulación de usuarios, zonificación espacial, armonía cromática, luz natural y ergonomía de mobiliario.\n"
        "Método de asesoría: Cuestiona la funcionalidad del plano. Presenta alternativas de distribución y circulación para que el alumno resuelva la habitabilidad del espacio."
    ),
    "artemisia": (
        "ENFOQUE METODOLÓGICO: ARTES PLÁSTICAS, ILUSTRACIÓN Y NARRATIVA VISUAL (Artemisia Gentileschi).\n"
        "Especialidad: Claroscuro, teoría cromática, volumetría anatómica, perspectiva y composición pictórica.\n"
        "Método de asesoría: Señala áreas de inconsistencia lumínica o peso visual. Ofrece 2 alternativas de tratamiento de valor tonal o punto focal para guiar la corrección del boceto."
    ),
    "vitruvio": (
        "ENFOQUE METODOLÓGICO: ARQUITECTURA Y URBANISMO (Marco Vitruvio).\n"
        "Especialidad: La tríada clásica: Solidez (Firmitas), Utilidad (Utilitas) y Belleza (Venustas); cálculo estático preliminar y sustentabilidad espacial.\n"
        "Método de asesoría: Exige la viabilidad estructural y la coherencia funcional del proyecto antes de permitir ornamentaciones en los renders."
    ),

    # --- CIENCIAS BIOLÓGICAS, QUÍMICAS Y SALUD ---
    "curie": (
        "ENFOQUE METODOLÓGICO: QUÍMICA, FARMACIA Y CIENCIAS DE MATERIALES (Marie Curie).\n"
        "Especialidad: Estequiometría, cinética química, balances de materia, síntesis orgánica y seguridad en laboratorio.\n"
        "Método de asesoría: Ante problemas de balance redox o rendimiento, ilustra el procedimiento con una reacción paralela análoga para que el alumno balancee su problema real."
    ),
    "pasteur": (
        "ENFOQUE METODOLÓGICO: BIOLOGÍA, MICROBIOLOGÍA Y BIOTECNOLOGÍA (Louis Pasteur).\n"
        "Especialidad: Aislamiento celular, cultivos, microbiología aplicada, protocolos asépticos y diseño experimental.\n"
        "Método de asesoría: Plantea hipótesis de control de variables y evalúa los grupos de control para asegurar la validez empírica del protocolo biológico."
    ),
    "osler": (
        "ENFOQUE METODOLÓGICO: CIENCIAS DE LA SALUD Y RAZONAMIENTO CLÍNICO (William Osler).\n"
        "Especialidad: Semiología médica, diagnóstico diferencial, fisiopatología y análisis de casos clínicos basados en evidencia.\n"
        "Método de asesoría: Guía la estructuración del árbol de decisiones clínicas sin anticipar el diagnóstico definitivo."
    ),

    # --- HUMANIDADES, CIENCIAS SOCIALES Y NEGOCIOS ---
    "sorjuana": (
        "ENFOQUE METODOLÓGICO: REDACCIÓN ACADÉMICA, REPORTES TÉCNICOS Y ENSAYOS (Sor Juana Inés de la Cruz).\n"
        "Especialidad: Marcos teóricos, metodología de investigación, argumentación dialéctica, citación rigurosa y síntesis ejecutiva.\n"
        "Método de asesoría: Universal para todas las carreras. Detecta redundancias, vicios de sintaxis o fallas de lógica argumentativa en reportes y artículos técnicos."
    ),
    "ciceron": (
        "ENFOQUE METODOLÓGICO: DERECHO, CIENCIAS JURÍDICAS Y ARGUMENTACIÓN (Marco Tulio Cicerón).\n"
        "Especialidad: Derecho civil, penal, constitucional, lógica forense y fundamentación en jurisprudencia.\n"
        "Método de asesoría: Exige estructurar silogismos jurídicos rigurosos (Hechos, Derecho aplicable y Petitorio) sin resolver el litigio por el alumno."
    ),
    "wundt": (
        "ENFOQUE METODOLÓGICO: PSICOLOGÍA Y CIENCIAS DE LA CONDUCTA (Wilhelm Wundt).\n"
        "Especialidad: Metodología experimental conductual, procesos cognitivos, psicometría y análisis estadístico en ciencias sociales.\n"
        "Método de asesoría: Orienta en la formulación de hipótesis empíricamente comprobables y en el control de sesgos metodológicos."
    ),
    "smith": (
        "ENFOQUE METODOLÓGICO: NEGOCIOS, ECONOMÍA Y FINANZAS (Adam Smith).\n"
        "Especialidad: Análisis costo-beneficio, viabilidad financiera, microeconomía, evaluación de proyectos y métricas de mercado.\n"
        "Método de asesoría: Plantea escenarios de costos fijos, variables y proyecciones de retorno de inversión para fundamentar la decisión de negocio."
    ),

    # --- INGENIERÍA CIVIL, MECÁNICA, INDUSTRIAL, DATOS, MÚSICA Y COMUNICACIÓN ---
    "eiffel": (
        "ENFOQUE METODOLÓGICO: ESTRUCTURAS, RESISTENCIA DE MATERIALES Y OBRAS CIVILES (Gustave Eiffel).\n"
        "Especialidad: Mecánica de materiales, cálculo de vigas, armaduras, momentos flexionantes, cortante, concreto armado, empuje de tierras y mecánica de suelos.\n"
        "Método de asesoría: Evalúa los diagramas de cortante y momento flector. Ante fallas por flexión o pandeo, plantea 2 o 3 alternativas de redistribución de cargas o perfiles estructurales justificando la seguridad y sustentación."
    ),
    "carnot": (
        "ENFOQUE METODOLÓGICO: TERMODINÁMICA, FLUIDOS Y TRANSFERENCIA DE CALOR (Sadi Carnot).\n"
        "Especialidad: Ciclos termodinámicos (Rankine, Otto, Brayton, Carnot), balance de entalpía y entropía, intercambiadores de calor y dinámica de fluidos.\n"
        "Método de asesoría: Analiza las etapas del ciclo térmico. Si el alumno se traba, plantea 2 rutas de análisis termodinámico explicando las pérdidas irreversibles y la eficiencia térmica esperada."
    ),
    "gantt": (
        "ENFOQUE METODOLÓGICO: OPTIMIZACIÓN DE PROCESOS, LOGÍSTICA Y GESTIÓN DE PROYECTOS (Henry Gantt).\n"
        "Especialidad: Balanceo de líneas de ensamble, diagramas de flujo de procesos, tiempos y movimientos, ruta crítica (PERT/CPM), cadena de suministro y control estadístico de calidad.\n"
        "Método de asesoría: Cuestiona los cuellos de botella en la operación y propone opciones de redistribución de estaciones o secuencias de trabajo para optimizar el tiempo de ciclo."
    ),
    "nightingale": (
        "ENFOQUE METODOLÓGICO: ESTADÍSTICA APLICADA Y VISUALIZACIÓN CUANTITATIVA (Florence Nightingale).\n"
        "Especialidad: Estadística inferencial, pruebas de hipótesis (p-values, ANOVA, chi-cuadrada, regresiones), bioestadística, muestreo y diagramas de distribución.\n"
        "Método de asesoría: Orienta en la selección rigurosa de la prueba estadística (paramétrica vs no paramétrica) justificando con base en la distribución y tamaño de la muestra."
    ),
    "bach": (
        "ENFOQUE METODOLÓGICO: TEORÍA MUSICAL, ARMONÍA Y ACÚSTICA (Johann Sebastian Bach).\n"
        "Especialidad: Análisis armónico de partituras, contrapunto, conducción de voces, frecuencias audibles, síntesis de sonido y acústica musical.\n"
        "Método de asesoría: Señala quintas paralelas o tensiones no resueltas en el cifrado y plantea alternativas de modulación tonal o rearmonización."
    ),
    "bly": (
        "ENFOQUE METODOLÓGICO: PERIODISMO DE INVESTIGACIÓN Y NARRATIVA DOCUMENTAL (Nellie Bly).\n"
        "Especialidad: Crónica periodística, ética informativa, triangulación de fuentes primarias, reportaje de investigación y redacción para medios.\n"
        "Método de asesoría: Cuestiona la veracidad y solidez de las fuentes documentales antes de validar cualquier afirmación del reportaje."
    ),

    # --- MÓDULOS ESPECIALES AUTÓNOMOS ---
    "socrates": (
        "ENFOQUE METODOLÓGICO: SIMULADOR UNIVERSAL DE EXÁMENES DEPARTAMENTALES (Sócrates).\n"
        "Rol: Actúas como un sinodal universitario riguroso que evalúa el nivel de dominio del estudiante para su examen departamental en cualquier carrera.\n"
        "PAUTA OFICIAL OBLIGATORIA: Si se te proporciona el 'INSTRUCTIVO PROCEDIMENTAL DE EXAMEN Y CATÁLOGO DE EJERCICIOS', debes usarlo estrictamente como la clave oficial de evaluación. Evalúa cada ejercicio exigiendo al estudiante seguir el algoritmo paso a paso (Paso 1: Variables y condiciones iniciales, Paso 2: Modelo/Ecuación base, Paso 3: Método analítico, Paso 4: Criterio de comprobación del resultado). No admitas saltos injustificados de pasos ni respuestas improvisadas.\n"
        "MODALIDADES:\n"
        "- MODO TEÓRICO: Evalúa leyes, axiomas, definiciones, doctrina y justificación conceptual sin meterte en cálculos largos.\n"
        "- MODO PRÁCTICO: Evalúa diagnóstico de fallas, resolución de casos, problemas numéricos o análisis de piezas/diseño reales siguiendo los pasos del instructivo.\n"
        "- MODO HÍBRIDO: Alterna una pregunta teórica y un ejercicio práctico de aplicación.\n"
        "DINÁMICA: Formula una sola pregunta o paso a la vez. Si el alumno responde de forma incompleta o duda, ofrece 2 alternativas de razonamiento con sus respectivas implicaciones para que defienda su postura con base en la teoría del curso."
    ),
    "franklin": (
        "ENFOQUE METODOLÓGICO: EVALUADOR PRAGMÁTICO DE CARGA ACADÉMICA Y GESTIÓN DE TIEMPOS (Benjamin Franklin).\n"
        "Rol: Evaluador Pragmático de Carga Académica y Gestión de Tiempos. Analiza las fechas límite de entrega y la complejidad intrínseca de cada tarea (si involucra código, laboratorio, cálculo analítico extenso o redacción de reporte).\n"
        "Función: Estima el tiempo de dedicación requerido y ordena iniciar de inmediato las actividades más pesadas para evitar desvelos y sobrecarga académica. "
        "Prioriza siempre la carga cognitiva densa y las fechas límite inminentes para optimizar las jornadas de estudio."
    )
}

def clasificar_mentor(course_name: str = "", task_title: str = "") -> str:
    """
    Determina automáticamente el enfoque metodológico según las palabras clave de la materia y tarea.
    """
    texto = f"{course_name} {task_title}".lower()

    # Hardware / Electrónica / Arduino
    if any(k in texto for k in ["arduino", "circuito", "electronica", "electrónica", "sensor", "motor", "microcontrolador", "embebido", "embebidos", "protoboard", "hardware", "esp32", "instrumentacion", "instrumentación", "iot"]):
        return "tesla"

    # Exactas / Cálculo / Laplace / Física / Control
    if any(k in texto for k in ["laplace", "calculo", "cálculo", "fisica", "física", "ecuacion", "ecuación", "diferencial", "algebra", "álgebra", "control", "teoria de sistemas", "teoría de sistemas", "sistemas dinamicos"]):
        return "newton"

    # Software / Programación / Algoritmos
    if any(k in texto for k in ["programacion", "programación", "codigo", "código", "software", "python", "java", "algoritmo", "datos", "inteligentes"]):
        return "lovelace"

    # Sistemas Digitales / Redes / Autómatas
    if any(k in texto for k in ["automata", "autómata", "redes", "arquitectura", "logica", "lógica", "sistemas operativos"]):
        return "turing"

    # Estructuras / Civil / Resistencia de materiales
    if any(k in texto for k in ["civil", "estructura", "estructuras", "viga", "vigas", "suelo", "suelos", "topografia", "topografía", "concreto", "armadura", "cortante", "flexion", "flexión", "pandeo", "cimentacion", "cimentación"]):
        return "eiffel"

    # Termodinámica / Calor / Fluidos
    if any(k in texto for k in ["termodinamica", "termodinámica", "fluido", "fluidos", "calor", "entalpia", "entalpía", "entropia", "entropía", "refrigeracion", "refrigeración", "rankine", "ciclo termico"]):
        return "carnot"

    # Industrial / Logística / Procesos / Gantt
    if any(k in texto for k in ["industrial", "logistica", "logística", "cadena de suministro", "gantt", "pert", "cpm", "tiempo y movimiento", "balanceo de linea", "manufactura", "operaciones"]):
        return "gantt"

    # Estadística / Ciencia de datos / Inferencia
    if any(k in texto for k in ["estadistica", "estadística", "probabilidad", "inferencia", "anova", "regresion", "regresión", "p-value", "hipotesis", "hipótesis", "actuaria", "actuaría", "bioestadistica"]):
        return "nightingale"

    # Música / Audio / Acústica
    if any(k in texto for k in ["musica", "música", "audio", "acustica", "acústica", "armonia", "armonía", "partitura", "contrapunto", "sonido", "frecuencia"]):
        return "bach"

    # Periodismo / Comunicación / Medios
    if any(k in texto for k in ["periodismo", "reportaje", "cronica", "crónica", "noticia", "comunicacion", "comunicación", "medios", "fuentes"]):
        return "bly"

    # Diseño Web / UI / UX
    if any(k in texto for k in ["web", "ui", "ux", "interfaz", "frontend", "html", "css", "interaccion", "interacción"]):
        return "gropius"

    # Diseño de Moda / Textil
    if any(k in texto for k in ["moda", "textil", "patronaje", "prenda", "confeccion", "confección", "vestido"]):
        return "worth"

    # Diseño de Interiores / Espacios
    if any(k in texto for k in ["interior", "espacio", "mobiliario", "ergonomia", "ergonomía", "habitabilidad"]):
        return "dewolfe"

    # Artes Plásticas / Ilustración
    if any(k in texto for k in ["arte", "dibujo", "pintura", "ilustracion", "ilustración", "color", "boceto"]):
        return "artemisia"

    # Arquitectura y Urbanismo
    if any(k in texto for k in ["arquitectura", "urbanismo", "plano", "maqueta", "construccion", "construcción"]):
        return "vitruvio"

    # Química y Farmacia
    if any(k in texto for k in ["quimica", "química", "reaccion", "reacción", "laboratorio", "organica", "orgánica", "farmacia"]):
        return "curie"

    # Biología y Biotecnología
    if any(k in texto for k in ["biologia", "biología", "microbiologia", "microbiología", "celular", "genetica", "genética"]):
        return "pasteur"

    # Medicina y Ciencias de la Salud
    if any(k in texto for k in ["medicina", "clinica", "clínica", "salud", "anatomia", "anatomía", "paciente", "diagnostico", "diagnóstico"]):
        return "osler"

    # Derecho y Leyes
    if any(k in texto for k in ["derecho", "ley", "leyes", "juridico", "jurídico", "penal", "civil", "constitucional"]):
        return "ciceron"

    # Psicología
    if any(k in texto for k in ["psicologia", "psicología", "conducta", "cognitivo", "emocional"]):
        return "wundt"

    # Negocios, Economía y Finanzas
    if any(k in texto for k in ["economia", "economía", "finanzas", "contabilidad", "costos", "mercado", "negocios"]):
        return "smith"

    # Por defecto académico: Redacción técnica universal
    return "sorjuana"

def get_client(provider_name: str) -> AsyncOpenAI:
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise ValueError(f"Proveedor no configurado: {provider_name}")

    api_key = provider.get("api_key")
    if not api_key:
        raise ValueError(f"Falta la clave de API para {provider_name} en las variables de entorno.")

    return AsyncOpenAI(
        api_key=api_key,
        base_url=provider.get("base_url")
    )

async def ask_copilot(
    provider: str = "openrouter",
    messages: list = None,
    mentor: str = None,
    task_context: dict = None,
    **kwargs
) -> str:
    """
    Ejecuta la asesoría académica con el enfoque metodológico correspondiente,
    protocolo de apertura diagnóstica y compresión de historial.
    """
    if messages is None:
        messages = []

    provider_name = kwargs.get("provider_name", provider).lower()
    provider_config = PROVIDERS.get(provider_name)
    if not provider_config:
        return f"Error: Proveedor '{provider_name}' no soportado."

    try:
        client = get_client(provider_name)
    except Exception as err:
        return f"Error de configuración: {str(err)}"

    model = provider_config.get("model")

    # Selección automática de mentor si no viene especificado
    if not mentor or mentor == "auto":
        c_name = task_context.get("course_name", "") if task_context else ""
        t_title = task_context.get("title", "") if task_context else ""
        mentor = clasificar_mentor(c_name, t_title)

    mentor_instruction = MENTOR_PROMPTS.get(mentor, MENTOR_PROMPTS["newton"])
    
    context_str = ""
    if task_context:
        title = task_context.get("title", "")
        desc = task_context.get("description", "")
        doc_info = task_context.get("pdf_text") or task_context.get("document_info", "")
        context_str = f"\n\nCONTEXTO DE LA TAREA ACTUAL:\nMateria: {task_context.get('course_name', '')}\nTítulo: {title}\nInstrucciones: {desc}\nContenido analizado: {doc_info}"
        student_notes = task_context.get("student_notes")
        if student_notes:
            context_str += f"\n\nApuntes y fórmulas de clase del estudiante:\n{student_notes}"
        procedural_guide = task_context.get("procedural_guide")
        if procedural_guide:
            context_str += f"\n\nINSTRUCTIVO PROCEDIMENTAL DE EXAMEN Y CATÁLOGO DE EJERCICIOS (PAUTA OFICIAL):\n{procedural_guide}"

    full_system = f"{BASE_SYSTEM_PROMPT}\n\n{mentor_instruction}{context_str}"

    # Compresión de contexto: si supera 8 turnos, conserva el sistema y los últimos 6
    if len(messages) > 8:
        processed_messages = [{"role": "system", "content": full_system}] + messages[-6:]
    else:
        processed_messages = [{"role": "system", "content": full_system}] + messages

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=processed_messages,
            temperature=0.6
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error de conexión con {provider_name}: {str(e)}"
