# Ágora: Classroom Copilot & Tutor Académico Ignis 🏛️🔥

**Ágora** es una plataforma web universitaria diseñada para transformar radicalmente la gestión del tiempo y el rendimiento académico de los estudiantes. Sincroniza directamente con la API de Google Classroom, clasifica automáticamente las tareas bajo una arquitectura de misiones, fomenta la constancia mediante *La Antorcha de Prometeo* (racha por semanas académicas) y provee asistencia pedagógica personalizada a través de *Ignis*, un entorno de tutoría socrática impulsado por Inteligencia Artificial (Google Gemini, Groq y OpenRouter) con 24 mentores históricos especializados.

🔗 **Aplicación en Producción:** [https://agora-app-leox.onrender.com](https://agora-app-leox.onrender.com)

---

## 🌟 Características Principales

### 1. Centro de Misiones y Línea de Tiempo (Timeline)
- **Tiers de Prioridad Académica:**
  - 🗡️ **Misión Principal:** Proyectos semestrales, exámenes departamentales y entregas de alta carga cognitiva.
  - 🛡️ **Misiones Secundarias:** Prácticas de laboratorio, talleres y reportes semanales estándar.
  - ⚡ **Misiones Diarias:** Trámites breves, cuestionarios de lectura y comprobantes (< 20 min).
  - ✨ **Misiones Especiales:** Tareas devueltas para corrección o con nota reprobatoria para recuperación de puntos.
  - 🛟 **Misiones de Rescate (Tardías):** Entregas vencidas o en riesgo inminente de penalización. Al activar el filtro, se despliegan directamente en la línea de tiempo principal al frente y al centro, ocultando secciones colapsadas redundantes.
  - 🧭 **Misiones Abiertas:** Actividades sin fecha límite para avanzar a ritmo autónomo.
- **Tarjetas Inteligentes con Resumen a Ancho Completo:**
  - **Deduplicación automática de membretes:** El motor analiza el texto extraído de los PDFs y descarta repeticiones innecesarias (nombre de la materia, títulos repetidos, palabras de formato institucional).
  - **Bloque de Resumen Destacado:** Presenta la consigna y objetivos reales en un párrafo continuo y legible que aprovecha todo el ancho de la tarjeta.
  - **Insignia de Documento:** Identificador visual directo del PDF adjunto oficial (`📄 Archivo.pdf`).
- **Eliminación de Falsas Casillas y Enlace Directo a Classroom:**
  - Se eliminaron las casillas locales de verificación que generaban estados ficticios. La única fuente de verdad es Google Classroom (`ENTREGADA` o `CALIFICADA`).
  - Cada tarjeta incorpora el botón **`[ ↗ Subir en Classroom ]`**, que lleva al estudiante directamente a la pantalla de entrega exacta de esa tarea con 1 solo clic.
- **Precisión Horaria UTC:** Ajuste exacto de zonas horarias para evitar inconsistencias (resuelve entregas a las 9:00 en punto sin omisión de minutos).
- **Carga en Paralelo Ultra-Rápida:** Consumo concurrente de `/api/tasks` y `/api/courses` mediante `Promise.all` para una experiencia fluida sin cuellos de botella.

---

### 2. Guía y Resumen de Estudio por Temas (Google Drive & Visor de Apuntes) 📚🧠
En lugar de saturar el almacenamiento reescribiendo o duplicando archivos individuales por cada tarea, Ágora sintetiza el conocimiento de la materia en una **Guía y Resumen de Estudio por Temas**:
- **Estructura Curricular por Ejes Temáticos:**
  - **Conceptos Teóricos Esenciales:** Resumen conceptual riguroso para preparación de exámenes y parciales.
  - **Fórmulas, Leyes y Teoremas Clave:** Formulario matemático organizado con ecuaciones rectoras.
  - **Metodología de Solución:** Procedimientos analíticos paso a paso para ejercicios típicos de examen.
  - **Tareas y Prácticas Asociadas:** Vinculación directa con las consignas y prácticas del curso.
- **Sincronización Automática en Google Drive:**
  - Crea o actualiza en la carpeta `Ágora - Apuntes / [Materia]` el documento oficial: `Resumen de Estudio por Temas - [Materia].txt`.
  - Mantiene los accesos directos oficiales (Drive Shortcuts) a los materiales originales del docente sin descargas pesadas.
- **Visor Modular en Ágora:**
  - En el panel de notas, el documento aparece al inicio con icono de graduación (`fa-graduation-cap`) y botón directo de *"Guía de Estudio"*.
  - Endpoint dedicado: `GET /api/notes/{course_name}/study-summary`.
- **Gestión Granular de Archivos en Google Drive:**
  - En el modal de Configuración (*Gestión de Apuntes*), al seleccionar una asignatura se consulta dinámicamente el contenido de su carpeta en Drive (`GET /api/notes/files/{course_name}`).
  - Cada archivo individual cuenta con enlace directo y botón de eliminación individual `[ 🗑️ ]` (`DELETE /api/notes/file/{file_id}`), permitiendo depurar archivos específicos sin borrar la carpeta ni los demás apuntes.

---

### 3. La Antorcha de Prometeo (Racha por Semanas Académicas) 🕯️🔥
La constancia se mide por **semanas académicas cumplidas** (semestre de 15 semanas):
- **Primera Semana:** Contabilización exacta por días (`1 día de racha`, `2 días de racha`...).
- **A partir de la Semana 1:** Transición automática a semanas académicas completas (`1 semana de racha` hasta el tope de **`15 semanas de racha`**).
- **Escala Física de 8 Niveles de Fuego (según temperatura real de la llama):**
  1. *Semanas 1 y 2:* **Llama Ámbar** (Chispa de inicio, tonos cantera cálidos).
  2. *Semanas 3 y 4:* **Flama de Bronce** (Naranja cobre constante).
  3. *Semanas 5 y 6:* **Llama Dorada Solar** (Amarillo oro).
  4. *Semanas 7 y 8:* **Fuego Esmeralda** (Verde esmeralda de alta frecuencia).
  5. *Semanas 9 y 10:* **Flama Turquesa de Gas** (Cian de combustión completa).
  6. *Semanas 11 y 12:* **Llama Zafiro / Índigo** (Azul de alta energía térmica).
  7. *Semanas 13 y 14:* **Fuego Violeta** (Púrpura intenso de fin de ciclo).
  8. *Semana 15 (Invicta):* **Llama Blanca Pura con Relieve Dorado** (`#FFFFFF` absoluto, contorno dorado `#F59E0B` y halo ámbar).
- **Diseño Móvil Optimizado:** La llama y el contador de pendientes se presentan en un solo renglón sin quiebres de línea visuales.

---

### 4. El Reloj de Benjamin Franklin (Planificación y Carga Académica) 🧭⏳
Un evaluador pragmático y ejecutivo de organización diaria:
- **Brújula de Orientación:** Reemplaza métricas abstractas por un diagnóstico concreto del estado de la jornada (`X tareas por resolver` o `En Rescate`).
- **Ruta de Acción de Hoy:**
  - Prioriza las entregas y calcula el tiempo de estudio según la complejidad intrínseca de la tarea:
    - *Proyectos / Ensayos / Exámenes:* **Ultradiano (90 min)** de foco profundo.
    - *Talleres técnicos / Prácticas / Algoritmos:* **Regla 52/17 (52 min)**.
    - *Cuestionarios / Lecturas regulares:* **Pomodoro (25 min)**.
    - *Trámites breves / Comprobantes:* **Arranque Rápido (5 min)**.
- **Botón `[ ▶ Comenzar en Ignis ]`:** Carga el bloque de tiempo en el temporizador, cierra el modal y abre de inmediato la tarea en el espacio de trabajo de Ignis.
- **Temporizador de Foco por Marca de Tiempo (Anti-Congelamiento Móvil):**
  - Calcula `tiempoFin = Date.now() + duracionMs` en lugar de decrementar síncronamente segundos en reposo. Al bloquear o suspender la pantalla del teléfono, el reloj realiza un salto determinista al tiempo transcurrido sin retrasos ni desfasajes.
  - **Alertas Hápticas, Acústicas y de Sistema al Llegar a Cero:**
    - Solicita permiso de notificaciones push del sistema con `Notification.requestPermission()` al pulsar "Iniciar".
    - Dispara vibración física en móviles: `navigator.vibrate([300, 150, 300, 150, 500])`.
    - Reproduce campana armónica sintetizada nativamente con la Web Audio API (cero dependencias de archivos externos).
    - Lanza notificación del sistema operativo: `new Notification("¡Foco completado!", ...)`.

---

### 5. Espacio de Trabajo Ignis & Andamiaje Socrático 📖⚡
- **Visor Dual Sincronizado:** Documento oficial (PDF / consigna) a la izquierda y chat analítico con el tutor a la derecha.
- **Alternancia Dinámica de Pantalla (Web y Móvil):**
  - Botones `[ 📄 PDF ]` e `[ 🔥 Ignis ]` para expandir el documento al 100%, el chat al 100% o la división simétrica 50/50.
  - En móviles: navegación por deslizamiento táctil horizontal tipo carrusel con indicador de puntos discretos estilo Instagram (`N documentos + 1 Ignis Chat`).
- **Pedagogía Anti-Copia (Scaffolding):** El tutor nunca entrega la respuesta directa; formula preguntas de andamiaje, desglosa conceptos y propone ejercicios gemelos con datos cambiados.
- **Filtro Inteligente de Mentores por Carrera:**
  - El selector en Ignis detecta automáticamente las materias inscritas del alumno y **filtra el catálogo**, mostrando únicamente los mentores pertinentes a su especialidad.
  - **Sor Juana Inés de la Cruz** permanece siempre fija como tutora universal de redacción académica, metodología y ensayos.

---

### 6. Catálogo de los 24 Mentores Universitarios Especializados 🎓

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

### 7. Experiencia Móvil & Menú Ágora Depurado 📱
- **Logo de Ágora Multifunción:** El logo oficial en la cabecera actúa como disparador interactivo del Menú Lateral / Drawer tanto en escritorio como en móvil.
- **Drawer Móvil Depurado:** Contiene estrictamente:
  1. Alternador de tema **Selene (Noche) / Helios (Día)**.
  2. Filtro interactivo de **Materias**.
  3. Filtro por **Tiers de Misiones** con conteos en tiempo real.
- **Modo de Prueba (Demo sin cuenta Google):** Botón directo en la pantalla de bienvenida para explorar Ágora instantáneamente con un semestre universitario completo (Alex Muñoz) sin requerir inicio de sesión de Google.

---

## 🛠️ Arquitectura de Software

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+), servidor ASGI asíncrono con `httpx`, `pypdf` y `google-api-python-client`.
- **Integración con Google:** Google Classroom API v1, Google Drive API v3 y Google OAuth 2.0 Web Flow con credenciales seguras.
- **Seguridad y Candados:** Exclusión estricta en `.gitignore` de `.env`, `credentials.json`, `token.json` y `sessions.json`. Cookies HTTP-Only (`agora_session`).
- **Frontend:** HTML5 semántico, Tailwind CSS y JavaScript Vanilla reactivo (cargas menores a 300 ms sin sobrecarga de frameworks).
- **Protocolo Multi-IA:**
  - Google Gemini API (`google-genai`).
  - Groq Cloud API (Llama-3 a ultra alta velocidad).
  - OpenRouter API (Claude 3.5 Sonnet, DeepSeek, GPT-4o).
  - Soporte BYOK (*Bring Your Own Key*) persistente en `localStorage`.

---

## 🧪 Pruebas Unitarias Automatizadas

El proyecto cuenta con una suite completa de **17 pruebas unitarias** en [`test_brother_classroom.py`](test_brother_classroom.py):

```bash
python -m unittest test_brother_classroom.py
```

| Prueba | Descripción |
| :--- | :--- |
| **Test 1** | Recuperación de cursos con estados `PROVISIONED` o sin estado explícito. |
| **Test 2** | Activación de fallback automático `studentId='me'` ante restricciones de la API. |
| **Test 3** | Conservación de asignaturas inscritas activas incluso con 0 tareas pendientes. |
| **Test 4** | Recolección de metadatos de PDF sin descargas bloqueantes (prevención de timeouts). |
| **Test 5** | Integración determinista de `?authuser` en enlaces de Google Drive y Classroom. |
| **Test 6** | Extractor inteligente de consignas reales omitiendo membretes institucionales. |
| **Test 7** | Caché de disco y memoria para materiales adjuntos con respuesta instantánea. |
| **Test 8** | Tratamiento exacto de zonas horarias UTC y minutos implícitos (9:00 vs 9:59). |
| **Test 9** | Deduplicación SHA-256 para optimización de almacenamiento en Drive. |
| **Test 10** | Almacenamiento y formateo de notas personales por asignatura. |
| **Test 11** | Redefinición de Benjamin Franklin como Evaluador Pragmático de carga académica. |
| **Test 12** | Inyección de apuntes y fórmulas del estudiante al contexto pedagógico del tutor. |
| **Test 13** | Inicialización y servicio instantáneo de tareas en Modo de Prueba (Demo). |
| **Test 14** | Incorporación de PDFs de tareas del docente al catálogo de documentos de la materia. |
| **Test 15** | Endpoint `/api/notes/{course}` sirviendo materiales y tareas del profesor. |
| **Test 16** | Generación de la Guía y Resumen de Estudio por Temas y endpoint `/study-summary`. |
| **Test 17** | Endpoints de listado granular (`/api/notes/files/{course}`) y borrado individual en Drive (`DELETE /api/notes/file/{id}`). |

---

## 💻 Instalación y Configuración Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/roymc2010-debug/classroom-copilot.git
cd classroom-copilot
```

### 2. Entorno virtual e instalación de dependencias
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

### 4. Iniciar el servidor
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Abre tu navegador en `http://localhost:8000`.

---

## 🌐 Opciones Recomendadas para Tener el Servidor Gratis 24/7

Si deseas que Ágora esté encendido las 24 horas del día, los 7 días de la semana, sin pagar nada, aquí tienes las mejores opciones evaluadas:

### Opción 1: Render (Free Tier) + Uptime Robot / Cron-Job (⭐ Más Rápida y Fácil)
Render ofrece 750 horas de cómputo gratuitas al mes (suficiente para 1 servicio web 24/7 continuo). Sin embargo, en el plan gratuito el contenedor entra en reposo (*sleep*) tras 15 minutos sin tráfico web, tardando unos 30-50 segundos en despertar (*cold start*).
- **Cómo mantenerlo activo 24/7 gratis:**
  1. Crea una cuenta gratuita en [UptimeRobot](https://uptimerobot.com/) o [cron-job.org](https://cron-job.org/).
  2. Agrega un monitor HTTP tipo `GET` hacia la URL de tu app en Render (por ejemplo: `https://tu-app.onrender.com/favicon.ico` o `https://tu-app.onrender.com/manifest.json`).
  3. Configura el intervalo de ping cada **10 minutos**.
  4. Al recibir solicitudes constantes, Render **nunca dormirá el contenedor**, manteniéndolo despierto 24/7 sin coste alguno.

### Opción 2: Oracle Cloud Always Free (⭐ La Mejor Solución Técnica Definitiva)
Oracle Cloud ofrece el nivel gratuito más generoso y potente de toda la industria en su programa *Always Free*:
- **Recursos Gratuitos para Siempre:**
  - 2 instancias de cómputo AMD x86 con IP pública fija, o hasta 4 núcleos ARM Ampere con **24 GB de RAM** y 200 GB de disco.
  - Servidor Linux VPS real (Ubuntu) que **nunca se apaga, nunca hiberna y no tiene cold starts**.
  - Soporte para Docker, `systemd`, SQLite persistente y reinicios automáticos.
- **Configuración rápida en Oracle Cloud:**
  1. Crea una instancia gratuita con Ubuntu 22.04 LTS.
  2. Clona el repositorio e instala Python / Uvicorn / Nginx.
  3. Configura Uvicorn como servicio de `systemd` para que corra 24/7 automáticamente.

### Opción 3: Koyeb / Fly.io / Hugging Face Spaces
- **Koyeb:** Instancia gratuita de 512 MB de RAM en Frankfurt o Washington DC con despliegue nativo desde GitHub y soporte de dominios propios.
- **Hugging Face Spaces (Docker / FastAPI):** 2 vCPU y 16 GB de RAM gratuitos en infraestructura de alta velocidad para prototipos y backends de IA.

---

## 🔒 Privacidad y Política de Permisos Mínimos

- **Modo Sólo Lectura:** Ágora no solicita permisos de edición ni de envío destructivo en Google Classroom.
- **Sin Almacenamiento Centralizado de Tareas:** Los contenidos de los PDFs se analizan en memoria de sesión para alimentar el andamiaje pedagógico de Ignis sin exponer información privada.
- **Aislamiento Multiusuario:** Cada usuario interactúa exclusivamente con sus credenciales y sesiones cifradas.

