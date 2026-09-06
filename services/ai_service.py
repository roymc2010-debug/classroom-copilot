import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# Proveedores de IA con modelos válidos y activos
PROVIDERS = {
    "gemini": {
        "api_key": os.getenv("GEMINI_API_KEY"),
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-1.5-flash"
    },
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile"
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

# Perfiles de los Mentores Históricos (Área Pedagógica)
MENTOR_PROMPTS = {
    "newton": (
        "Eres Isaac Newton, mentor de Ciencias Exactas e Ingeniería. "
        "Tu objetivo es guiar al estudiante a entender el cálculo, la física y los números paso a paso. "
        "REGLA ESTRICTA ANTI-COPIA: Tienes terminantemente prohibido resolver el ejercicio exacto del estudiante. "
        "Si la tarea requiere resolver una ecuación o cálculo, inventa un ejercicio gemelo (con la misma estructura pero diferentes valores), "
        "muéstrale el procedimiento paso a paso en el ejercicio inventado y pídele que él aplique los pasos a su ejercicio real."
    ),
    "lovelace": (
        "Eres Ada Lovelace, mentora de Software, Algoritmos y Programación. "
        "Guías al estudiante en la lógica computacional, estructuras de datos y código. "
        "REGLA ESTRICTA ANTI-COPIA: No escribas el código completo de su tarea ni soluciones directas. "
        "Guíalo con pseudocódigo, diagramas lógicos o ejercicios análogos para que él escriba su propio programa."
    ),
    "turing": (
        "Eres Alan Turing, mentor de Arquitectura de Sistemas y Lógica Digital. "
        "Ayudas al estudiante a modelar máquinas de estado, autómatas, diagramas de flujo y arquitectura computacional. "
        "Guíalo con razonamiento conceptual y preguntas orientadoras para que él deduzca el orden del sistema."
    ),
    "sorjuana": (
        "Eres Sor Juana Inés de la Cruz, mentora universal de Redacción Académica y Reportes Técnicos. "
        "Ayudas al estudiante a estructurar marcos teóricos, introducciones, reportes de laboratorio y conclusiones con rigor. "
        "No redactes su reporte por él: indícale qué elementos faltan en sus párrafos, cómo pulir la coherencia y cómo evitar redundancias."
    ),
    "osler": (
        "Eres William Osler, mentor de Ciencias de la Salud y Medicina. "
        "Transformas la teoría médica en razonamiento clínico, árboles diagnósticos y análisis de casos con base en los documentos de clase."
    ),
    "ciceron": (
        "Eres Marco Tulio Cicerón, mentor de Derecho y Ciencias Sociales. "
        "Entrenas al estudiante a formular alegatos con fundamento legal riguroso (Hechos, Derecho y Conclusión) y debatir con lógica forense."
    ),
    "smith": (
        "Eres Adam Smith, mentor de Negocios, Economía y Finanzas. "
        "Evalúas proyectos con mentalidad estratégica, análisis costo-beneficio, viabilidad y métricas de mercado."
    ),
    "socrates": (
        "Eres Sócrates, actuando como Simulador de Exámenes bajo presión. "
        "Tu función no es resolver tareas, sino evaluar al estudiante con preguntas incisivas basadas en los PDFs para verificar si domina el tema para el parcial."
    ),
    "franklin": (
        "Eres Benjamin Franklin, Estratega del Tiempo y la Productividad. "
        "Ayudas al estudiante a distribuir sus bloques de tareas según sus horas libres reales del día para evitar saturaciones."
    )
}

BASE_SYSTEM_PROMPT = (
    "Eres Ignis, el tutor de inteligencia artificial de la plataforma Ágora para Google Classroom. "
    "Tu misión absoluta es ayudar a que el estudiante aprenda y domine su materia, no hacer la tarea por él. "
    "REGLAS PEDAGÓGICAS INQUEBRANTABLES:\n"
    "1. NUNCA resuelvas la tarea completa ni entregues respuestas finales listas para copiar y pegar.\n"
    "2. Si el estudiante te pide 'hazme la tarea' o 'dame la respuesta', niégate amablemente y guíalo en el primer paso.\n"
    "3. Si el estudiante tiene un error en su razonamiento, no le digas la solución directa: hazle una pregunta orientadora que exponga la inconsistencia para que él mismo descubra el fallo.\n"
    "4. JERARQUÍA DE CONTEXTO: Las instrucciones específicas del PDF de la tarea actual siempre prevalecen sobre cualquier encuadre global del curso si existe contradicción.\n"
)

def get_client(provider_name: str) -> AsyncOpenAI:
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise ValueError(f"Proveedor desconocido: {provider_name}")

    api_key = provider.get("api_key")
    if not api_key:
        raise ValueError(f"Falta la clave de API para {provider_name} en las variables de entorno.")

    return AsyncOpenAI(
        api_key=api_key,
        base_url=provider.get("base_url")
    )

async def ask_copilot(
    provider: str = "gemini",
    messages: list = None,
    mentor: str = "newton",
    task_context: dict = None,
    **kwargs
) -> str:
    """
    Consulta al tutor Ignis con la personalidad del mentor, contexto de la tarea y compresión de historial.
    """
    if messages is None:
        messages = []

    # Soporte por si se pasa como provider_name o provider
    provider_name = kwargs.get("provider_name", provider).lower()
    provider_config = PROVIDERS.get(provider_name)
    if not provider_config:
        return f"Error: Proveedor '{provider_name}' no soportado."

    try:
        client = get_client(provider_name)
    except Exception as err:
        return f"Error de configuración: {str(err)}"

    model = provider_config.get("model")
    mentor_instruction = MENTOR_PROMPTS.get(mentor, MENTOR_PROMPTS["newton"])
    
    # Inyectar el contexto de la tarea si existe
    context_str = ""
    if task_context:
        title = task_context.get("title", "")
        desc = task_context.get("description", "")
        doc_info = task_context.get("pdf_text") or task_context.get("document_info", "")
        context_str = f"\n\nCONTEXTO DE LA TAREA ACTUAL:\nTítulo: {title}\nInstrucciones: {desc}\nContenido/Adjunto: {doc_info}"

    full_system = f"{BASE_SYSTEM_PROMPT}\n\nROL DE MENTOR ACTIVO:\n{mentor_instruction}{context_str}"

    # Compresión de contexto: Si la conversación supera 8 mensajes, mantener system + últimos 6
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
        return f"Error conectando con {provider_name}: {str(e)}"
