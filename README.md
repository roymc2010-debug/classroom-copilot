# Ágora: Classroom Copilot & Tutor Académico Ignis 🏛️🔥

**Ágora** es una plataforma web integral diseñada para transformar la experiencia de estudio universitario. Conecta directamente con la API de Google Classroom para sincronizar asignaturas, organizar tareas bajo un sistema de misiones y ofrecer asistencia pedagógica personalizada mediante modelos de Inteligencia Artificial de vanguardia (Google Gemini, Groq y OpenRouter) estructurados con roles históricos y andamiaje cognitivo.

Desplegado en producción: [https://agora-app-leox.onrender.com](https://agora-app-leox.onrender.com)

---

## 🚀 Características Principales

### 1. Centro de Misiones y Línea de Tiempo (Timeline)
- **Clasificación Automática por Tiers de Prioridad:**
  - 🗡️ **Misión Principal:** Proyectos de alto impacto, exámenes parciales y entregas complejas (bloques de 4+ horas).
  - 🛡️ **Misiones Secundarias:** Tareas semanales, prácticas y reportes de laboratorio regulares.
  - ⚡ **Misiones Diarias:** Trámites ágiles, comprobantes y lecturas breves (< 20 min).
  - ✨ **Misiones Especiales:** Tareas devueltas por el profesor o con calificación baja para rescate de puntos.
  - 🛟 **Misiones de Rescate:** Entregas tardías o atrasadas priorizadas para evitar penalizaciones.
  - 🧭 **Misiones Abiertas:** Actividades sin fecha límite para avanzar a ritmo propio.
- **Sincronización Total de Materias:** Detecta e incluye en los filtros todas las asignaturas activas en las que el alumno está inscrito, incluso durante las primeras semanas del ciclo lectivo cuando aún no tienen tareas asignadas.
- **Limpieza Tipográfica Automática:** Los identificadores técnicos con guiones bajos (ej. TUTORIAS_2026B) se formatean automáticamente a nombres limpios y legibles (TUTORIAS 2026B).
- **Diseño Centrado y Balanceado:** Espaciado simétrico con barra lateral ergonómica y vista de entregas centrada y adaptable.

---

### 2. Espacio de Trabajo Ignis (Tutor de Estudio con Andamiaje)
- **Visor Dual Sincronizado:** Permite consultar los documentos adjuntos (PDFs, consignas y archivos de Google Drive) en un panel y debatir con la IA en el otro.
- **Alternancia de Vista:** Botones directos [ 📄 PDF ] y [ 🔥 Ignis ] para expandir el documento o el chat al 100% de la pantalla, o volver a la vista dividida 50/50.
- **Andamiaje Pedagógico (Scaffolding):** La IA no regala la tarea resuelta; explica con ejemplos gemelos con datos numéricos cambiados y guía al estudiante paso a paso.
- **Carrusel Multidocumento:** Navegación entre todos los archivos adjuntos de la entrega con enlace de respaldo a Drive.

---

### 3. Simulador Socrático de Exámenes 🏛️
- **Evaluación Oral Dialéctica:** Módulo dedicado para simular defensas orales y exámenes departamentales bajo presión.
- **3 Modalidades de Examen:**
  - 📘 **Teórico:** Énfasis en definiciones formales, deducciones y conceptos clave.
  - 🛠️ **Práctico:** Planteamiento de casos de estudio, resolución de problemas y escenarios reales.
  - ⚖️ **Híbrido:** Balance riguroso entre fundamentos conceptuales y aplicación técnica.
- **Mayéutica Interactiva:** Sócrates evalúa cada respuesta del alumno, señala imprecisiones y formula repreguntas profundas para asegurar el dominio real del tema.

---

### 4. Panel de Profesores y Mentores Académicos
Ignis clasifica automáticamente tu materia o te permite elegir a tu mentor preferido:
1. **Isaac Newton:** Exactas, cálculo diferencial/integral y física.
2. **Ada Lovelace:** Software, algoritmos, arquitectura de datos y depuración lógica.
3. **Alan Turing:** Sistemas, máquinas de estado, autómatas y lógica proposicional.
4. **Sor Juana Inés de la Cruz:** Ensayos, marco teórico, redacción académica y reportes.
5. **William Osler:** Medicina, razonamiento clínico y árboles diagnósticos.
6. **Marco Tulio Cicerón:** Argumentación jurídica, debate y silogismos legales.
7. **Adam Smith:** Finanzas, viabilidad económica y estrategia de negocios.
8. **Sócrates:** Simulador de exámenes y mayéutica rigurosa.
9. **Benjamin Franklin:** Estrategia de productividad, agenda y fraccionamiento de bloques de estudio.

---

### 5. Productividad, Ritmo y Estado
- **Reloj Digital en Vivo:** Visualización en tiempo real de hora y fecha académica.
- **Temporizador Multitécnica Integrado:**
  - *Pomodoro Clásico:* 25 min de foco / 5 min de descanso.
  - *Regla 52 / 17:* 52 min de flujo profundo / 17 min de desconexión.
  - *Ciclo Ultradiano:* 90 min de trabajo biológico / 20 min de pausa.
  - *Regla de los 5 Minutos:* Activador contra la procrastinación.
- **Calendario Académico Interactivo:** Matriz mensual con 4 puntos semánticos (Pendiente, Entregada, Examen y Aviso).
- **Avisos de Profesores:** Campana con contador de avisos no leídos persistente en localStorage, formato de fecha limpio y modal de lectura completa.
- **Temas Visuales Helios y Selene:** Paleta Cantera cálida para el día y Noche profunda (Dark mode) para sesiones nocturnas.

---

## 🛠️ Arquitectura Técnica

- **Backend:** FastAPI (Python 3.10+), ASGI de alto rendimiento.
- **Autenticación:** Google OAuth 2.0 Web Flow con aislamiento estricto de sesiones mediante cookies HTTP-Only (gora_session) y persistencia en disco (sessions.json) resistente a reinicios en la nube.
- **Frontend:** HTML5 semántico, Tailwind CSS y JavaScript Vanilla reactivo integrado (cero dependencias externas pesadas).
- **Modelos de Lenguaje:** Protocolo Multi-IA unificado (Google Gemini, Groq Llama-3, OpenRouter) con soporte para configuración local de llaves de API (BYOK - *Bring Your Own Key*).
- **Almacenamiento Local:** Notas privadas y estado de tareas complementadas con SQLite y localStorage.

---

## 📦 Instalación y Configuración Local

### 1. Clonar el repositorio
`ash
git clone https://github.com/roymc2010-debug/classroom-copilot.git
cd classroom-copilot
`

### 2. Entorno virtual y dependencias
`ash
python -m venv .venv
# En Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# En Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
`

### 3. Configuración de Credenciales de Google
1. Entra a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto y habilita:
   - **Google Classroom API**
   - **Google Drive API**
3. En **OAuth consent screen**, define el tipo como *External* y añade los correos de prueba necesarios.
4. En **Credentials**, crea un *OAuth client ID* de tipo **Web application**.
5. Añade como URI de redireccionamiento autorizada:
   - Local: http://localhost:8000/auth/callback
   - Producción (Render): https://agora-app-leox.onrender.com/auth/callback
6. Descarga el JSON y guárdalo como credentials.json en la raíz del proyecto, o configura las variables de entorno.

### 4. Variables de Entorno (Opcional pero recomendado)
Crea un archivo .env en la raíz:
`env
GOOGLE_CLIENT_ID=tu_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
GEMINI_API_KEY=tu_gemini_key
GROQ_API_KEY=tu_groq_key
OPENROUTER_API_KEY=tu_openrouter_key
`

### 5. Iniciar el servidor
`ash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
`
Abre tu navegador en http://localhost:8000.

---

## 🌐 Despliegue en Render

1. Conecta tu repositorio de GitHub en [Render](https://render.com/).
2. Crea un **Web Service**:
   - **Runtime:** Python
   - **Build Command:** pip install -r requirements.txt
   - **Start Command:** uvicorn main:app --host 0.0.0.0 --port 
3. Configura las variables de entorno en el panel de Render:
   - GOOGLE_CLIENT_ID
   - GOOGLE_CLIENT_SECRET
   - GOOGLE_REDIRECT_URI = https://agora-app-leox.onrender.com/auth/callback
   - GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY

---

## 🔒 Privacidad y Seguridad

- **Tokens Aislados:** Cada usuario cuenta con un identificador de sesión único (session_id) transmitido mediante cookies seguras HTTP-Only.
- **Sin Fugas de Datos:** Las tareas, calificaciones y archivos de cada alumno solo se solicitan mediante el token de su propia sesión de Google.
- **BYOK (Bring Your Own Key):** Las claves personales de IA para Groq u OpenRouter se almacenan exclusivamente en el localStorage del navegador del usuario.
