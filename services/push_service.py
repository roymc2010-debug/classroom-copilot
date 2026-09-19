import os
import json
import time
import base64
from py_vapid import Vapid
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pywebpush import webpush, WebPushException

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
VAPID_PEM_PATH = os.path.join(DATA_DIR, "vapid_private.pem")
VAPID_META_PATH = os.path.join(DATA_DIR, "vapid_meta.json")

_cached_vapid = None
_cached_public_key_b64 = None

def get_or_create_vapid_keys():
    """
    Inicializa o recupera el par de claves criptográficas VAPID (RFC 8292).
    Genera el formato Base64URL sin relleno del punto público no comprimido para navegadores.
    """
    global _cached_vapid, _cached_public_key_b64
    if _cached_vapid and _cached_public_key_b64:
        return _cached_vapid, _cached_public_key_b64

    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(VAPID_PEM_PATH) and os.path.exists(VAPID_META_PATH):
        try:
            vapid = Vapid.from_file(VAPID_PEM_PATH)
            with open(VAPID_META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
                pub_b64 = meta.get("public_key_b64")
                if pub_b64:
                    _cached_vapid = vapid
                    _cached_public_key_b64 = pub_b64
                    return vapid, pub_b64
        except Exception as e:
            print(f"Aviso: Error cargando VAPID existente ({e}), regenerando...")

    # Generar nuevo par VAPID
    vapid = Vapid()
    vapid.generate_keys()
    vapid.save_key(VAPID_PEM_PATH)

    raw_bytes = vapid.public_key.public_bytes(
        encoding=Encoding.X962,
        format=PublicFormat.UncompressedPoint
    )
    pub_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8").rstrip("=")

    with open(VAPID_META_PATH, "w", encoding="utf-8") as f:
        json.dump({"public_key_b64": pub_b64, "created_at": time.time()}, f)

    _cached_vapid = vapid
    _cached_public_key_b64 = pub_b64
    return vapid, pub_b64

def get_public_key():
    """Retorna la clave pública VAPID en Base64URL lista para el navegador."""
    _, pub_key = get_or_create_vapid_keys()
    return pub_key

def send_web_push(subscription_info, title, body, url="/", silent=False, tag="agora-notice", is_alarm=False, vibrate=None, break_minutes=5):
    """
    Despacha una notificación Push encriptada al Push Service (FCM/Apple) usando RFC 8291.
    Si is_alarm=True, utiliza vibración continua de alarma, requireInteraction y máxima urgencia.
    """
    get_or_create_vapid_keys()

    alarm_vibrate = [600, 250, 600, 250, 600, 250, 1000]
    std_vibrate = [300, 150, 300, 150, 400]
    if vibrate is not None:
        chosen_vibrate = vibrate
    elif silent and not is_alarm:
        chosen_vibrate = []
    elif is_alarm:
        chosen_vibrate = alarm_vibrate
    else:
        chosen_vibrate = std_vibrate

    actions = []
    if is_alarm:
        actions = [
            {"action": "stop_alarm", "title": "⏹ Detener Alarma"},
            {"action": "start_break", "title": f"☕ Iniciar Descanso ({int(break_minutes)} min)"}
        ]

    payload = {
        "title": title,
        "body": body,
        "icon": "/static/agora_logo_192.png?v=4",
        "badge": "/static/img/badge.png",
        "url": url,
        "silent": bool(silent),
        "vibrate": chosen_vibrate,
        "alarm": bool(is_alarm),
        "isAlarm": bool(is_alarm),
        "requireInteraction": bool(is_alarm),
        "actions": actions,
        "breakMinutes": int(break_minutes),
        "timestamp": int(time.time() * 1000),
        "data": {
            "url": url,
            "silent": bool(silent),
            "alarm": bool(is_alarm),
            "isAlarm": bool(is_alarm),
            "breakMinutes": int(break_minutes),
            "actions": actions
        }
    }

    headers = {}
    if is_alarm:
        headers["Urgency"] = "high"

    try:
        response = webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PEM_PATH,
            vapid_claims={"sub": "mailto:agora.copilot@gmail.com"},
            ttl=300 if is_alarm else 86400,
            headers=headers if headers else None
        )
        try:
            endpoint_display = (subscription_info.get("endpoint") or "")[:55]
            title_safe = str(title).encode("ascii", errors="replace").decode("ascii")
            print(f"[WebPush] [OK] Notificacion Push enviada con exito (titulo: '{title_safe}') a {endpoint_display}...")
        except Exception:
            pass
        return True, "sent"
    except WebPushException as ex:
        status_code = getattr(ex.response, "status_code", None) if hasattr(ex, "response") and ex.response is not None else None
        resp_text = getattr(ex.response, "text", "") if hasattr(ex, "response") and ex.response is not None else ""
        try:
            endpoint_display = (subscription_info.get("endpoint") or "")[:55]
            err_safe = str(ex).encode("ascii", errors="replace").decode("ascii")
            print(f"[WebPush] [ERROR] WebPushException (status={status_code}): {err_safe} | Endpoint: {endpoint_display}...")
        except Exception:
            pass
        if status_code in (404, 410):
            return False, "expired"
        return False, f"error: {ex} (status={status_code})"
    except Exception as e:
        try:
            endpoint_display = (subscription_info.get("endpoint") or "")[:55]
            err_safe = str(e).encode("ascii", errors="replace").decode("ascii")
            print(f"[WebPush] [ERROR] Excepcion inesperada al enviar Web Push: {err_safe} | Endpoint: {endpoint_display}...")
        except Exception:
            pass
        return False, f"exception: {e}"
