# Classroom Task Manager con Multi-IA Copilot

Una aplicación web full-stack para gestionar tareas pendientes de Google Classroom, visualizarlas en una línea de tiempo (Timeline) y contar con la ayuda de un asistente "Copilot" potenciado por múltiples modelos de IA (Gemini, Groq, OpenRouter).

## Requisitos previos

1. Python 3.9 o superior.
2. Claves de API de IA:
   - Gemini (Google AI Studio)
   - Groq (https://console.groq.com)
   - OpenRouter (https://openrouter.ai)
3. Archivo `credentials.json` de Google Cloud Console.

## Configuración de Google Classroom (`credentials.json`)

Para conectar la app con tu cuenta de Google Classroom:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un nuevo proyecto.
3. En el menú lateral, ve a **APIs & Services > Library** y busca "Google Classroom API". Habilítala.
4. Ve a **APIs & Services > OAuth consent screen**. Configúralo como "External" (o "Internal" si tienes Workspace) y añade tu correo como usuario de prueba. Añade los scopes: `.../auth/classroom.courses.readonly` y `.../auth/classroom.coursework.me.readonly`.
5. Ve a **APIs & Services > Credentials**. Haz clic en "Create Credentials" y selecciona "OAuth client ID".
6. Tipo de aplicación: "Desktop app".
7. Descarga el archivo JSON generado, renómbralo a `credentials.json` y colócalo en la raíz de este proyecto.

## Instalación y Configuración

1. Instala las dependencias:
   pip install -r requirements.txt
2. Renombra `.env.example` a `.env` y añade tus claves API:
   cp .env.example .env

## Cómo ejecutar

Para iniciar el servidor y hacerlo accesible desde tu red local (por ejemplo, desde tu celular):

uvicorn main:app --reload --host 0.0.0.0 --port 8000

1. La primera vez que lo ejecutes y entres a la web, tendrás que autorizar el acceso en la consola del servidor (se abrirá una ventana del navegador o te dará un enlace). Esto creará un archivo `token.json` local.
2. Entra a `http://localhost:8000` o a la IP de tu computadora (ej: `http://192.168.1.XX:8000`) desde cualquier dispositivo en tu red Wi-Fi para usar la app.

## Arquitectura

- **Backend:** FastAPI (Python), SQLite.
- **Frontend:** HTML5, Tailwind CSS, JavaScript Vanilla.
- **Servicios Integrados:** Google Classroom API, OpenAI SDK (unificado para múltiples proveedores).
