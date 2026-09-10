"""
یک نقطه‌ی ورودی واحد (WSGI) برای همه‌ی API ها — چون رانتایم پایتون Vercel
دنبال یک entrypoint مشخص (مثل api/index.py) می‌گرده، نه چند فایل جدا.

مسیرها با کوئری‌پارامتر ?route=... مشخص می‌شن تا هیچ وابستگی‌ای به نحوه‌ی
Routing داخلی Vercel نداشته باشیم:

  POST /api/index?route=webhook            -> آپدیت‌های تلگرام
  GET  /api/index?route=random             -> یک ترک رندوم
  GET  /api/index?route=stream&id=...      -> پخش زنده‌ی فایل صوتی
  GET  /api/index?route=download&id=...    -> دانلود فایل صوتی
  GET  /api/index?route=thumb&id=...       -> کاور آرت
"""

import json
import os
import urllib.request
import urllib.error
from urllib.parse import parse_qs

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

JSON_HEADERS = [("Content-Type", "application/json")]


# ---------------------------------------------------------------- helpers --

def redis_cmd(*args):
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return None
    data = json.dumps(list(args)).encode("utf-8")
    req = urllib.request.Request(UPSTASH_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {UPSTASH_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read()
    except Exception:
        return None
    try:
        return json.loads(body).get("result")
    except Exception:
        return None


def flat_to_dict(flat_list):
    if not flat_list:
        return {}
    it = iter(flat_list)
    return dict(zip(it, it))


def get_track(track_id):
    raw = redis_cmd("HGETALL", f"track:{track_id}")
    return flat_to_dict(raw)


def get_telegram_file_path(file_id):
    url = f"{TELEGRAM_API}/getFile?file_id={file_id}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
    if not data.get("ok"):
        return None
    return data["result"]["file_path"]


def fetch_telegram_file_bytes(file_id):
    file_path = get_telegram_file_path(file_id)
    if not file_path:
        return None
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    with urllib.request.urlopen(file_url, timeout=25) as resp:
        return resp.read()


def send_message(chat_id, text, web_app_url=None):
    payload = {"chat_id": chat_id, "text": text}
    if web_app_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "🎧 پخش رندوم موزیک", "web_app": {"url": web_app_url}}
            ]]
        }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{TELEGRAM_API}/sendMessage", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def index_audio_message(msg):
    audio = msg.get("audio")
    if not audio:
        return
    file_id = audio.get("file_id")
    file_unique_id = audio.get("file_unique_id")
    if not file_id or not file_unique_id:
        return

    thumb = audio.get("thumb") or audio.get("thumbnail") or {}
    track = {
        "id": file_unique_id,
        "file_id": file_id,
        "title": audio.get("title") or "بدون‌نام",
        "performer": audio.get("performer") or "ناشناس",
        "duration": str(audio.get("duration") or 0),
        "mime_type": audio.get("mime_type") or "audio/mpeg",
        "file_size": str(audio.get("file_size") or 0),
        "thumb_file_id": thumb.get("file_id") or "",
    }

    hset_args = ["HSET", f"track:{file_unique_id}"]
    for k, v in track.items():
        hset_args.extend([k, v])
    redis_cmd(*hset_args)
    redis_cmd("SADD", "track_ids", file_unique_id)


# ----------------------------------------------------------- route logic --

def handle_webhook(environ):
    secret_header = environ.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN", "")
    if not WEBHOOK_SECRET or secret_header != WEBHOOK_SECRET:
        return 401, JSON_HEADERS, b'{"ok":false,"error":"invalid secret"}'

    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    raw = environ["wsgi.input"].read(length) if length else b"{}"

    try:
        update = json.loads(raw)
    except Exception:
        update = {}

    message = update.get("message")
    channel_post = update.get("channel_post")

    if message and str(message.get("text", "")).startswith("/start"):
        send_message(
            message["chat"]["id"],
            "سلام! 👋\nآماده‌ای یک موزیک رندوم و سورپرایزکننده گوش بدی؟",
            web_app_url=WEB_APP_URL,
        )

    if channel_post:
        index_audio_message(channel_post)

    return 200, JSON_HEADERS, b'{"ok":true}'


def handle_random():
    track_id = redis_cmd("SRANDMEMBER", "track_ids")
    if not track_id:
        body = json.dumps({"ok": False, "error": "no tracks indexed yet"}).encode()
        return 404, JSON_HEADERS, body

    track = get_track(track_id)
    result = {
        "ok": True,
        "id": track.get("id", track_id),
        "title": track.get("title", "بدون‌نام"),
        "performer": track.get("performer", "ناشناس"),
        "duration": int(track.get("duration", 0) or 0),
        "stream_url": f"/api/index?route=stream&id={track_id}",
        "download_url": f"/api/index?route=download&id={track_id}",
        "cover_url": f"/api/index?route=thumb&id={track_id}" if track.get("thumb_file_id") else "",
    }
    headers = JSON_HEADERS + [("Cache-Control", "no-store")]
    return 200, headers, json.dumps(result).encode()


def handle_media(track_id, as_download):
    if not track_id:
        return 400, JSON_HEADERS, b'{"ok":false,"error":"missing id"}'

    track = get_track(track_id)
    if not track:
        return 404, JSON_HEADERS, b'{"ok":false,"error":"track not found"}'

    try:
        data = fetch_telegram_file_bytes(track["file_id"])
    except Exception:
        data = None

    if data is None:
        return 502, JSON_HEADERS, b'{"ok":false,"error":"could not fetch file from telegram"}'

    mime_type = track.get("mime_type", "audio/mpeg")
    headers = [("Content-Type", mime_type), ("Cache-Control", "public, max-age=3600")]
    if as_download:
        safe_name = f"{track.get('performer','track')} - {track.get('title','audio')}.mp3"
        headers.append(("Content-Disposition", f'attachment; filename="{safe_name}"'))

    return 200, headers, data


def handle_thumb(track_id):
    if not track_id:
        return 400, JSON_HEADERS, b'{"ok":false,"error":"missing id"}'

    track = get_track(track_id)
    thumb_file_id = track.get("thumb_file_id")
    if not thumb_file_id:
        return 404, JSON_HEADERS, b'{"ok":false,"error":"no thumbnail"}'

    try:
        data = fetch_telegram_file_bytes(thumb_file_id)
    except Exception:
        data = None

    if data is None:
        return 502, JSON_HEADERS, b'{"ok":false,"error":"could not fetch thumbnail"}'

    headers = [("Content-Type", "image/jpeg"), ("Cache-Control", "public, max-age=86400")]
    return 200, headers, data


# ------------------------------------------------------------------- WSGI --

def app(environ, start_response):
    qs = parse_qs(environ.get("QUERY_STRING", ""))
    route = (qs.get("route") or [""])[0]
    track_id = (qs.get("id") or [None])[0]
    method = environ.get("REQUEST_METHOD", "GET")

    if not route:
        path = environ.get("PATH_INFO", "")
        for candidate in ("webhook", "random", "stream", "download", "thumb"):
            if path.rstrip("/").endswith(candidate):
                route = candidate
                break

    try:
        if route == "webhook" and method == "POST":
            status, headers, body = handle_webhook(environ)
        elif route == "random":
            status, headers, body = handle_random()
        elif route == "stream":
            status, headers, body = handle_media(track_id, as_download=False)
        elif route == "download":
            status, headers, body = handle_media(track_id, as_download=True)
        elif route == "thumb":
            status, headers, body = handle_thumb(track_id)
        else:
            status, headers, body = 404, JSON_HEADERS, b'{"ok":false,"error":"unknown route"}'
    except Exception as e:
        status, headers, body = 500, JSON_HEADERS, json.dumps({"ok": False, "error": str(e)}).encode()

    status_text = {
        200: "200 OK", 400: "400 Bad Request", 401: "401 Unauthorized",
        404: "404 Not Found", 502: "502 Bad Gateway", 500: "500 Internal Server Error",
    }.get(status, f"{status} OK")

    headers = list(headers) + [("Access-Control-Allow-Origin", "*")]
    start_response(status_text, headers)
    return [body]
