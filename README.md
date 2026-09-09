# Ágora: Classroom Copilot & Tutor Académico Ignis 🏛️🔥

**Ágora** es una plataforma web universitaria diseñada para transformar radicalmente la gestión del tiempo y el rendimiento académico de los estudiantes. Sincroniza directamente con la API de Google Classroom, clasifica automáticamente las tareas bajo una arquitectura de misiones, fomenta la disciplina mediante *La Antorcha de Prometeo* (racha por semanas académicas) y provee asistencia pedagógica personalizada a través de *Ignis*, un entorno de tutoría socrática impulsado por Inteligencia Artificial (Google Gemini, Groq y OpenRouter) con 24 mentores históricos especializados.

🔗 **Aplicación en Producción:** [https://agora-app-leox.onrender.com](https://agora-app-leox.onrender.com)

---

## 🌟 Características Principales

### 1. Centro de Misiones y Línea de Tiempo (Timeline)
- **Tiers de Prioridad Académica:**
  - 🗡️ **Misión Principal:** Proyectos semestrales, exámenes departamentales y entregas de alta carga cognitiva.
  - 🛡️ **Misiones Secundarias:** Prácticas de laboratorio, talleres y reportes semanales estándar.
  - ⚡ **Misiones Diarias:** Trámites breves, cuestionarios de lectura y comprobantes (< 20 min).
  - ✨ **Misiones Especiales:** Tareas devueltas para corrección o con nota reprobatoria para recuperación de puntos.
  - 🛟 **Misiones de Rescate:** Entregas atrasadas o en riesgo inminente de penalización.
  - 🧭 **Misiones Abiertas:** Actividades sin fecha límite para avanzar a ritmo autónomo.
- **Tarjetas Inteligentes con Resumen a Ancho Completo:**
  - **Deduplicación automática de membretes:** El motor analiza el texto extraído de los PDFs y descarta repeticiones innecesarias (nombre de la materia, títulos repetidos, palabras de formato institucional).
  - **Bloque de Resumen Destacado:** Presenta la consigna y objetivos reales en un párrafo continuo y legible que aprovecha todo el ancho de la tarjeta.
  - **Insignia de Documento:** Identificador visual directo del PDF adjunto oficial (`📄 Archivo.pdf`).
- **Eliminación de Falsas Casillas y Enlace Directo a Classroom:**
  - Se eliminaron las casillas locales de verificación que generaban estados ficticios. La única fuente de verdad es Google Classroom (`ENTREGADA` o `CALIFICADA`).
  - Cada tarjeta incorpora el botón **`[ ↗ Subir en Classroom ]`**, que lleva al estudiante directamente a la pantalla de entrega exacta de esa tarea con 1 solo clic, eliminando el laberinto de navegación de Classroom.
- **Carga en Paralelo Ultra-Rápida:** Consumo concurrente de `/api/tasks` y `/api/courses` mediante `Promise.all` para una experiencia fluida sin cuellos de botella.

---

### 2. La Antorcha de Prometeo (Racha por Semanas Académicas) 🕯️🔥
La constancia ya no se mide por días aislados o porcentajes confusos, sino por **semanas académicas cumplidas** (semestre de 15 semanas):
- **Primera Semana:** Contabilización exacta por días (`1 día de racha`, `2 días de racha`...).
- **A partir de la Semana 1:** Transición automática a semanas académicas completas (`1 semana de racha` hasta el tope estricto de **`15 semanas de racha`**).
- **Escala Física de 8 Niveles de Fuego (según temperatura real de la llama):**
  1. *Semanas 1 y 2:* **Llama Ámbar** (Chispa de inicio, tonos cantera cálidos).
  2. *Semanas 3 y 4:* **Flama de Bronce** (Naranja cobre constante).
  3. *Semanas 5 y 6:* **Llama Dorada Solar** (Amarillo oro).
  4. *Semanas 7 y 8:* **Fuego Esmeralda** (Verde esmeralda de alta frecuencia).
  5. *Semanas 9 y 10:* **Flama Turquesa de Gas** (Cian de combustión completa).
  6. *Semanas 11 y 12:* **Llama Zafiro / Índigo** (Azul de alta energía térmica).
  7. *Semanas 13 y 14:* **Fuego Violeta** (Púrpura intenso de fin de ciclo).
  8. *Semana 15 (Invicta):* **Llama Blanca Pura con Relieve Dorado** (`#FFFFFF` absoluto, contorno dorado `#F59E0B` de `1.5px` y halo ámbar de alta frecuencia, sin mezcla de amarillo ni verde en el cuerpo del fuego).

---

### 3. El Reloj de Benjamin Franklin (Planificación del Día) 🧭⏳
Un módulo ejecutivo de organización diaria enfocado en la acción:
- **Brújula de Orientación:** Reemplaza métricas abstractas por un diagnóstico concreto del estado de la jornada (`X tareas por resolver` o `En Rescate`).
- **Ruta de Acción de Hoy:**
  - Prioriza las entregas y calcula el tiempo de estudio **según la complejidad intrínseca de la tarea** (no por cuándo vence):
    - *Proyectos / Ensayos / Exámenes:* **Ultradiano (90 min)** de foco profundo.
    - *Talleres técnicos / Prácticas / Algoritmos:* **Regla 52/17 (52 min)**.
    - *Cuestionarios / Lecturas regulares:* **Pomodoro (25 min)**.
    - *Trámites breves / Comprobantes:* **Arranque Rápido (5 min)**.
- **Botón `[ ▶ Comenzar en Ignis ]`:** Carga el bloque de tiempo en el temporizador, cierra el modal y abre de inmediato la tarea en el espacio de trabajo de Ignis.

---

### 4. Espacio de Trabajo Ignis & Andamiaje Socrático 📖⚡
- **Visor Dual Sincronizado:** Documento oficial (PDF / consigna) a la izquierda y chat analítico con el tutor a la derecha.
- **Alternancia Dinámica de Pantalla:** Botones `[ 📄 PDF ]` e `[ 🔥 Ignis ]` para expandir el documento al 100%, expandir el chat al 100% o regresar a la división simétrica 50/50.
- **Pedagogía Anti-Copia (Scaffolding):** El tutor nunca entrega la respuesta directa; formula preguntas de andamiaje, desglosa conceptos y propone ejercicios gemelos con datos cambiados.
- **Filtro Inteligente de Mentores por Carrera:**
  - El selector en Ignis detecta automáticamente las materias inscritas del alumno y **filtra el catálogo**, mostrando únicamente los mentores pertinentes a su especialidad.
  - **Sor Juana Inés de la Cruz** permanece siempre fija como tutora universal de redacción académica, metodología y ensayos.
  - Incluye acceso directo a los módulos autónomos de **Sócrates** (exámenes) y **Franklin** (rutina).
  - Selector expandible: `[ 📋 Ver todos los 24 mentores... ]` disponible si el alumno desea consultar especialistas de otras disciplinas.

---

### 5. Catálogo de los 24 Mentores Universitarios Especializados 🎓

| Especialidad / Área | Mentor Histórico | Ámbito de Dominio |
| :--- | :--- | :--- |
| **Exactas, Dinámica y Cálculo** | **Isaac Newton** | Cálculo diferencial/integral, ecuaciones diferenciales, Laplace y física. |
| **Hardware y Circuitos** | **Nikola Tesla** | Circuitos analógicos/digitales, microcontroladores (Arduino, ESP32) y potencia. |
| **Software y Algoritmos** | **Ada Lovelace** | Estructuras de datos, lógica algorítmica, programación en Python/C++/Java y Big-O. |
| **Sistemas y Lógica** | **Alan Turing** | Sistemas operativos, autómatas finitos, redes y arquitectura computacional. |
| **Obras Civiles y Estructuras** | **Gustave Eiffel** | Resistencia de materiales, vigas, cálculo estático y estructuras de concreto. |
| **Termodinámica y Fluidos** | **Sadi Carnot** | Ciclos térmicos, máquinas de vapor, transferencia de calor y fluidos. |
| **Procesos y Logística** | **Henry Gantt** | Gestión de operaciones, ruta crítica (PERT/CPM), líneas de producción y calidad. |
| **Diseño Web y UI/UX** | **Walter Gropius** | Retículas modulares, jerarquía visual, diseño de interfaces y Bauhaus. |
| **Diseño de Moda y Textil** | **Charles Frederick Worth** | Patronaje estructural, indumentaria, caída de telas y confección. |
| **Diseño de Interiores** | **Elsie de Wolfe** | Distribución espacial, iluminación, ergonomía y ambientación. |
| **Artes Plásticas y Dibujo** | **Artemisia Gentileschi** | Claroscuro, perspectiva, composición, teoría del color y dibujo técnico. |
| **Arquitectura y Urbanismo** | **Marco Vitruvio** | Firmitas, Utilitas y Venustas; planificación urbana y edificación. |
| **Química y Materiales** | **Marie Curie** | Estequiometría, química inorgánica/orgánica, seguridad y materiales. |
| **Biología y Microbiología** | **Louis Pasteur** | Cultivos bacterianos, diseño experimental y biotecnología aplicada. |
| **Medicina y Salud** | **William Osler** | Semiología, diagnóstico clínico diferencial y fisiopatología. |
| **Estadística y Datos** | **Florence Nightingale** | Estadística inferencial, bioestadística, pruebas de hipótesis y muestreo. |
| **Redacción y Metodología** | **Sor Juana Inés de la Cruz** | Ensayo académico, estructura argumentativa APA y reportes técnicos (Universal). |
| **Derecho y Forense** | **Marco Tulio Cicerón** | Silogismo jurídico (Hechos, Derecho, Petitorio) y debate oratorio. |
| **Psicología y Conducta** | **Wilhelm Wundt** | Neurociencias, psicología experimental y metodología cuantitativa. |
| **Economía y Finanzas** | **Adam Smith** | Análisis costo-beneficio, microeconomía, estados financieros y proyectos. |
| **Música y Acústica** | **Johann Sebastian Bach** | Armonía formal, acústica, síntesis sonora, contrapunto y análisis modal. |
| **Periodismo y Medios** | **Nellie Bly** | Periodismo de investigación, crónica, triangulación de fuentes y ética. |
| **Simulador de Parciales** | **Sócrates** | Evaluación dialéctica oral y socrática para exámenes de grado o departamentales. |
| **Estrategia y Rutina** | **Benjamin Franklin** | Gestión de bloques de tiempo y productividad académica. |

---

### 6. Banco de Pruebas Multietapa Universitario (Alex Muñoz) 🧪
Para cuentas sin asignaturas reales registradas en Classroom (`alexmunoz918@gmail.com`), el backend integra un servicio de simulación realista (`services/mock_data_service.py`) con **3 etapas del semestre**:
1. **Etapa 1: Inicio de Semestre (Semanas 1 a 4):** Tronco común (Cálculo, Programación, Física, Redacción), avisos de inducción y racha de 2 semanas.
2. **Etapa 2: Parciales y Medio Término (Semanas 7 a 9):** Materias de especialidad, exámenes parciales de Laplace, proyectos de Dijkstra y racha de 8 semanas.
3. **Etapa 3: Cierre y Proyectos Finales (Semanas 13 a 15):** Entregas finales, misiones de rescate, notas definitivas y racha invicta de 15 semanas.
- **Selector Interactivo:** Botón en la cabecera `[ 🎓 Semestre: Inicio ↻ ]` para rotar de etapa con un clic, además de rotación automática en cada inicio de sesión.

---

## 🛠️ Arquitectura de Software

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+), ASGI asíncrono con `httpx` y `pypdf`.
- **Integración con Google:** Google Classroom API v1, Google Drive API v3 y Google OAuth 2.0 Web Flow en modo estrictamente de lectura analítica (sin permisos de escritura invasivos).
- **Seguridad de Sesiones:** Cookies HTTP-Only (`agora_session`) con almacenamiento aislado en disco (`sessions.json`) para persistencia tolerante a reinicios del contenedor en Render.
- **Frontend:** HTML5 semántico, Tailwind CSS y JavaScript Vanilla reactivo (sin sobrecarga de frameworks como React/Angular, garantizando tiempos de carga inferiores a 300 ms).
- **Protocolo Multi-IA:**
  - Google Gemini API (`google-genai`).
  - Groq Cloud API (Llama-3 70B a ultra alta velocidad).
  - OpenRouter API (soporte para Claude 3.5 Sonnet, DeepSeek y GPT-4o).
  - Soporte BYOK (*Bring Your Own Key*) persistente en `localStorage`.

---

## 💻 Instalación y Configuración Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/roymc2010-debug/classroom-copilot.git
cd classroom-copilot
```

### 2. Entorno virtual y dependencias
```bash
python -m venv .venv

# En Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# En Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Variables de Entorno (.env)
Crea un archivo `.env` en la raíz del proyecto:
```env
GOOGLE_CLIENT_ID=tu_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
GEMINI_API_KEY=tu_api_key_gemini
GROQ_API_KEY=tu_api_key_groq
OPENROUTER_API_KEY=tu_api_key_openrouter
```

### 4. Iniciar el servidor de desarrollo
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Abre tu navegador en `http://localhost:8000`.

---

## 🚀 Despliegue en Render

El repositorio está configurado para despliegue continuo (CI/CD) conectado a la rama `main`:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Variables requeridas en Render:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GEMINI_API_KEY`.

---

## 🔒 Privacidad y Política de Permisos Mínimos

- **Modo Sólo Lectura:** Ágora no solicita permisos de edición ni de envío de tareas en Google Classroom. Los envíos de archivos los realiza el propio estudiante mediante el botón oficial directo.
- **Sin Almacenamiento Centralizado de Documentos:** Los contenidos de los PDFs se analizan en memoria volátil de sesión para alimentar el contexto de Ignis y no se almacenan en bases de datos públicas.
- **Aislamiento Multiusuario:** Cada llamada a la API de Classroom utiliza exclusivamente las credenciales cifradas del estudiante activo en su propia cookie de sesión.
