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

def send_web_push(subscription_info, title, body, url="/", silent=False, tag="agora-notice"):
    """
    Despacha una notificación Push encriptada al Push Service (FCM/Apple) usando RFC 8291.
    Si silent=True, no genera sonido ni vibración física en el teléfono móvil.
    """
    get_or_create_vapid_keys()

    payload = {
        "title": title,
        "body": body,
        "icon": "/static/agora_logo_192.png?v=4",
        "badge": "/static/agora_logo_light_32.png?v=4",
        "url": url,
        "silent": bool(silent),
        "vibrate": [] if silent else [300, 150, 300, 150, 400],
        "tag": tag,
        "timestamp": int(time.time() * 1000),
        "data": {
            "url": url,
            "silent": bool(silent)
        }
    }

    try:
        response = webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PEM_PATH,
            vapid_claims={"sub": "mailto:agora.copilot@gmail.com"},
            ttl=86400
        )
        return True, "sent"
    except WebPushException as ex:
        status_code = getattr(ex.response, "status_code", None) if hasattr(ex, "response") else None
        if status_code in (404, 410):
            return False, "expired"
        return False, f"error: {ex}"
    except Exception as e:
        return False, f"exception: {e}"
