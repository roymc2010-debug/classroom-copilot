import os
import json
import time
import asyncio
import datetime
from google.oauth2.credentials import Credentials
import db.database as db
from services.classroom_service import fetch_courses, get_all_tasks, get_announcements_and_alerts
from services.push_service import send_web_push

SESSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sessions.json")
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "token.json")

def is_night_time():
    """
    Verifica si la hora actual local está dentro del periodo nocturno (23:00 a 06:59).
    En este horario las alertas se envían en modo silencioso (silent: true).
    """
    cur_hour = datetime.datetime.now().hour
    return cur_hour >= 23 or cur_hour < 7

def get_active_user_credentials():
    """
    Recupera las credenciales válidas guardadas en sessions.json o token.json.
    Retorna una lista de tuplas: (email, credentials)
    """
    results = []
    seen_emails = set()

    # 1. De sessions.json
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                sessions = json.load(f)
                for sid, sdata in sessions.items():
                    creds_json = sdata.get("creds")
                    email = (sdata.get("email") or "").lower().strip()
                    if creds_json and email and email not in seen_emails:
                        try:
                            creds_dict = json.loads(creds_json) if isinstance(creds_json, str) else creds_json
                            creds = Credentials.from_authorized_user_info(creds_dict)
                            results.append((email, creds))
                            seen_emails.add(email)
                        except Exception:
                            pass
        except Exception as e:
            print(f"[Background Sync] Error leyendo sessions.json: {e}")

    # 2. De token.json (fallback de sesión individual)
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                token_data = json.load(f)
                if token_data and "token" in token_data:
                    email = token_data.get("user_email", "").lower().strip()
                    if email and email not in seen_emails:
                        try:
                            creds = Credentials.from_authorized_user_info(token_data)
                            results.append((email, creds))
                            seen_emails.add(email)
                        except Exception:
                            pass
        except Exception:
            pass

    return results

def sync_once():
    """
    Ejecuta un ciclo de sincronización contra Google Classroom.
    Detecta nuevas tareas y avisos y despacha Web Push.
    Retorna el número de nuevos ítems notificados.
    """
    users = get_active_user_credentials()
    if not users:
        return 0

    seen_ids = db.get_seen_item_ids()
    is_initial_run = (len(seen_ids) == 0)
    total_notified = 0

    for email, creds in users:
        try:
            tasks = get_all_tasks(creds, user_email=email)
            announcements = get_announcements_and_alerts(creds, user_email=email)
        except Exception as e:
            print(f"[Background Sync] Error obteniendo datos de Classroom para {email}: {e}")
            continue

        new_items_to_save = []
        new_items_to_notify = []

        # 1. Tareas de Classroom
        for t in (tasks or []):
            t_id = str(t.get("id"))
            if not t_id:
                continue

            course_name = (t.get("course_name") or "Asignatura").replace("_", " ")
            title = t.get("title") or "Nueva Tarea"
            due_str = t.get("due_date") or "Sin fecha límite"

            if t_id not in seen_ids:
                item_data = {
                    "item_id": t_id,
                    "item_type": "task",
                    "course_name": course_name,
                    "title": title,
                    "due_date": due_str
                }
                new_items_to_save.append(item_data)
                seen_ids.add(t_id)

                if not is_initial_run:
                    new_items_to_notify.append(item_data)

        # 2. Avisos de Profesores (incluye cancelaciones de clases)
        for a in (announcements or []):
            a_id = str(a.get("id") or a.get("content", ""))
            if not a_id:
                continue

            course_name = (a.get("course_name") or "Aviso").replace("_", " ")
            content = a.get("content") or "Aviso publicado por el profesor."
            short_content = (content[:120] + '...') if len(content) > 120 else content

            if a_id not in seen_ids:
                item_data = {
                    "item_id": a_id,
                    "item_type": "announcement",
                    "course_name": course_name,
                    "title": short_content,
                    "due_date": ""
                }
                new_items_to_save.append(item_data)
                seen_ids.add(a_id)

                if not is_initial_run:
                    new_items_to_notify.append(item_data)

        # Guardar en base de datos los ítems recién detectados
        if new_items_to_save:
            db.mark_items_seen_bulk(new_items_to_save)

        # Si es la primera ejecución, no spamear al usuario con tareas previas
        if is_initial_run:
            print(f"[Background Sync] Inicialización: {len(new_items_to_save)} ítems marcados como existentes para {email}.")
            continue

        # Despachar notificaciones para cada ítem nuevo
        if new_items_to_notify:
            subscriptions = db.get_push_subscriptions_for_user(email)
            if not subscriptions:
                # Si no hay suscripciones registradas específicamente para el email, enviar a todas
                subscriptions = db.get_all_push_subscriptions()

            silent_mode = is_night_time()

            for item in new_items_to_notify:
                if item["item_type"] == "announcement":
                    notif_title = f"📢 Aviso: {item['course_name']}"
                    notif_body = f"{item['title']}"
                else:
                    notif_title = f"📝 Nueva Tarea: {item['course_name']}"
                    notif_body = f"{item['title']}\nEntrega: {item['due_date']}"

                if silent_mode:
                    notif_body += " (Aviso silencioso nocturno)"

                for sub in subscriptions:
                    ok, res = send_web_push(
                        subscription_info=sub,
                        title=notif_title,
                        body=notif_body,
                        url="/",
                        silent=silent_mode,
                        tag=f"{item['item_type']}-{item['item_id']}"
                    )
                    if res == "expired":
                        db.delete_push_subscription(sub.get("endpoint"))

                total_notified += 1

    return total_notified

async def run_background_sync_loop(interval_seconds=180):
    """
    Bucle asíncrono infinito que corre en el servidor cada 3 minutos (180s) 24/7.
    """
    print(f"[Background Sync] Vigilante 24/7 iniciado (Intervalo: {interval_seconds}s).")
    # Esperar 15 segundos tras el arranque de FastAPI antes del primer ciclo
    await asyncio.sleep(15)
    while True:
        try:
            # Ejecutar en thread pool para no bloquear el bucle de eventos de FastAPI
            notified = await asyncio.to_thread(sync_once)
            if notified > 0:
                print(f"[Background Sync] {notified} notificaciones enviadas exitosamente.")
        except Exception as e:
            print(f"[Background Sync] Error en ciclo de sincronización: {e}")

        await asyncio.sleep(interval_seconds)

def check_and_dispatch_due_timer_alarms():
    """
    Revisa si existen alarmas de foco programadas cuya hora 'ends_at' haya vencido
    y despacha de inmediato un Web Push con prioridad ALTA, vibración vigorosa
    y requireInteraction para despertar el celular aunque esté bloqueado.
    """
    now_ms = time.time() * 1000
    due_alarms = db.get_due_timer_alarms(now_ms)
    count = 0
    for alarm in due_alarms:
        alarm_id = alarm["id"]
        user_email = (alarm.get("user_email") or "").lower().strip()
        phase = alarm.get("phase", "focus")
        label = alarm.get("preset_label", "Foco")

        if phase == "focus":
            title = "⏰ ¡Foco Completado!"
            body = f"¡Tu bloque de {label} ha terminado! Entra a Ágora para iniciar tu descanso."
        else:
            title = "🔔 ¡Descanso Concluido!"
            body = "Tu tiempo de descanso terminó. ¿Listo para otro bloque de foco?"

        subscriptions = db.get_push_subscriptions_for_user(user_email) if user_email else []
        if not subscriptions:
            subscriptions = db.get_all_push_subscriptions()

        for sub in subscriptions:
            send_web_push(
                subscription_info=sub,
                title=title,
                body=body,
                url="/?openTimer=1",
                silent=False,
                tag="agora-timer-alarm",
                is_alarm=True
            )
        db.mark_timer_alarm_notified(alarm_id)
        count += 1
    return count

async def run_timer_alarm_watcher_loop():
    """
    Vigilante de alta frecuencia (cada 1s) para alarmas de foco/descanso en segundo plano.
    """
    while True:
        try:
            await asyncio.to_thread(check_and_dispatch_due_timer_alarms)
        except Exception as e:
            pass
        await asyncio.sleep(1)
