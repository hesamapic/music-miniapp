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

HTML_PAGE = '<!DOCTYPE html>\n<html lang="fa" dir="rtl">\n<head>\n<meta charset="UTF-8" />\n<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />\n<title>موزیک رندوم</title>\n<script src="https://telegram.org/js/telegram-web-app.js"></script>\n<style>\n  :root {\n    color-scheme: dark;\n    --bg-1: #0f0c1d;\n    --bg-2: #1a1533;\n    --accent: #7c5cff;\n    --accent-2: #ff5c9a;\n    --text: #f2f0fb;\n    --text-dim: #9d97c4;\n    --glass: rgba(255,255,255,0.06);\n    --glass-border: rgba(255,255,255,0.14);\n  }\n  * { box-sizing: border-box; }\n  html, body {\n    margin: 0; padding: 0; height: 100%;\n    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Vazirmatn, Tahoma, sans-serif;\n    background: radial-gradient(circle at 20% 0%, var(--bg-2), var(--bg-1) 60%);\n    color: var(--text);\n  }\n  .app {\n    min-height: 100vh;\n    display: flex; flex-direction: column;\n    align-items: center; justify-content: center;\n    padding: 24px;\n  }\n  .player-card {\n    width: 100%; max-width: 380px;\n    background: var(--glass);\n    border: 1px solid var(--glass-border);\n    backdrop-filter: blur(20px);\n    -webkit-backdrop-filter: blur(20px);\n    border-radius: 28px;\n    padding: 28px 24px;\n    box-shadow: 0 20px 60px rgba(0,0,0,0.4);\n    text-align: center;\n  }\n  .cover {\n    width: 220px; height: 220px;\n    margin: 0 auto 22px;\n    border-radius: 22px;\n    background: linear-gradient(135deg, var(--accent), var(--accent-2));\n    display: flex; align-items: center; justify-content: center;\n    box-shadow: 0 10px 30px rgba(124,92,255,0.35);\n    overflow: hidden;\n    position: relative;\n  }\n  .cover img { width: 100%; height: 100%; object-fit: cover; }\n  .cover svg { width: 72px; height: 72px; opacity: 0.9; }\n  .cover.spinning { animation: spin 8s linear infinite; }\n  @keyframes spin { from { filter: brightness(1);} to { filter: brightness(1);} }\n\n  .title { font-size: 19px; font-weight: 700; margin: 4px 0 2px; line-height: 1.5; }\n  .performer { font-size: 14px; color: var(--text-dim); margin-bottom: 22px; }\n\n  .controls { display: flex; align-items: center; justify-content: center; gap: 18px; margin-bottom: 18px; }\n  .btn-circle {\n    width: 60px; height: 60px; border-radius: 50%;\n    background: linear-gradient(135deg, var(--accent), var(--accent-2));\n    border: none; color: white; font-size: 22px;\n    display: flex; align-items: center; justify-content: center;\n    cursor: pointer; box-shadow: 0 8px 20px rgba(124,92,255,0.4);\n    transition: transform 0.15s ease;\n  }\n  .btn-circle:active { transform: scale(0.92); }\n  .btn-small {\n    width: 46px; height: 46px; border-radius: 50%;\n    background: var(--glass); border: 1px solid var(--glass-border);\n    color: var(--text); font-size: 18px;\n    display: flex; align-items: center; justify-content: center;\n    cursor: pointer;\n  }\n  .btn-small:active { transform: scale(0.92); }\n\n  .row { display: flex; gap: 12px; margin-top: 6px; }\n  .action-btn {\n    flex: 1; padding: 12px 14px; border-radius: 14px;\n    border: 1px solid var(--glass-border); background: var(--glass);\n    color: var(--text); font-size: 14px; font-weight: 600;\n    display: flex; align-items: center; justify-content: center; gap: 6px;\n    cursor: pointer; text-decoration: none;\n  }\n  .action-btn:active { transform: scale(0.97); }\n\n  .status { margin-top: 16px; font-size: 13px; color: var(--text-dim); min-height: 18px; }\n  audio { display: none; }\n</style>\n</head>\n<body>\n  <div class="app">\n    <div class="player-card">\n      <div class="cover" id="cover">\n        <svg viewBox="0 0 24 24" fill="white"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>\n        <img id="coverImg" style="display:none" />\n      </div>\n      <div class="title" id="title">برای شروع دکمه\u200cی پخش رو بزن</div>\n      <div class="performer" id="performer">🎧 موزیک رندوم</div>\n\n      <div class="controls">\n        <button class="btn-small" id="btnNext" title="بعدی">⏭</button>\n        <button class="btn-circle" id="btnPlay" title="پخش/توقف">▶</button>\n        <button class="btn-small" id="btnRandom" title="یکی دیگه">🔀</button>\n      </div>\n\n      <div class="row">\n        <a class="action-btn" id="btnDownload" href="#" target="_blank" rel="noopener">⬇️ دانلود</a>\n      </div>\n\n      <div class="status" id="status"></div>\n      <audio id="audio"></audio>\n    </div>\n  </div>\n\n<script>\n  const tg = window.Telegram ? window.Telegram.WebApp : null;\n  if (tg) { tg.ready(); tg.expand(); }\n\n  const els = {\n    cover: document.getElementById(\'cover\'),\n    coverImg: document.getElementById(\'coverImg\'),\n    title: document.getElementById(\'title\'),\n    performer: document.getElementById(\'performer\'),\n    btnPlay: document.getElementById(\'btnPlay\'),\n    btnNext: document.getElementById(\'btnNext\'),\n    btnRandom: document.getElementById(\'btnRandom\'),\n    btnDownload: document.getElementById(\'btnDownload\'),\n    status: document.getElementById(\'status\'),\n    audio: document.getElementById(\'audio\'),\n  };\n\n  let current = null;\n  let isPlaying = false;\n\n  function setStatus(text) { els.status.textContent = text || \'\'; }\n\n  function formatTrack(track) {\n    els.title.textContent = track.title || \'بدون\u200cنام\';\n    els.performer.textContent = track.performer || \'ناشناس\';\n    els.btnDownload.href = track.download_url;\n\n    if (track.cover_url) {\n      els.coverImg.src = track.cover_url;\n      els.coverImg.style.display = \'block\';\n    } else {\n      els.coverImg.style.display = \'none\';\n    }\n  }\n\n  async function fetchRandomTrack() {\n    setStatus(\'در حال گرفتن یک آهنگ تصادفی...\');\n    els.btnPlay.disabled = true;\n    try {\n      const res = await fetch(\'/api/index?route=random\');\n      const data = await res.json();\n      if (!data.ok) {\n        setStatus(data.error === \'no tracks indexed yet\'\n          ? \'هنوز هیچ آهنگی ایندکس نشده — اول اسکریپت ایندکس\u200cساز رو اجرا کن.\'\n          : \'خطا در دریافت آهنگ.\');\n        return null;\n      }\n      current = data;\n      formatTrack(data);\n      setStatus(\'\');\n      return data;\n    } catch (e) {\n      setStatus(\'اتصال برقرار نشد. دوباره امتحان کن.\');\n      return null;\n    } finally {\n      els.btnPlay.disabled = false;\n    }\n  }\n\n  async function playNewRandom() {\n    isPlaying = false;\n    els.btnPlay.textContent = \'▶\';\n    els.cover.classList.remove(\'spinning\');\n    const track = await fetchRandomTrack();\n    if (track) {\n      els.audio.src = track.stream_url;\n      togglePlay(true);\n    }\n  }\n\n  function togglePlay(forcePlay) {\n    const shouldPlay = forcePlay !== undefined ? forcePlay : !isPlaying;\n    if (!current) { playNewRandom(); return; }\n\n    if (shouldPlay) {\n      els.audio.play().catch(() => setStatus(\'برای پخش، دوباره روی دکمه بزن.\'));\n      isPlaying = true;\n      els.btnPlay.textContent = \'⏸\';\n      els.cover.classList.add(\'spinning\');\n    } else {\n      els.audio.pause();\n      isPlaying = false;\n      els.btnPlay.textContent = \'▶\';\n      els.cover.classList.remove(\'spinning\');\n    }\n  }\n\n  els.btnPlay.addEventListener(\'click\', () => togglePlay());\n  els.btnNext.addEventListener(\'click\', playNewRandom);\n  els.btnRandom.addEventListener(\'click\', playNewRandom);\n  els.audio.addEventListener(\'ended\', playNewRandom);\n\n  // اولین بار خودکار یک آهنگ رو آماده کن (بدون پخش خودکار، چون مرورگرها/تلگرام معمولاً autoplay صدا رو مسدود می\u200cکنن)\n  fetchRandomTrack();\n</script>\n</body>\n</html>\n'


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

    # سازگاری: اگر روت مستقیماً در PATH_INFO باشه (بدون کوئری‌پارامتر)
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
        elif not route and method == "GET":
            status = 200
            headers = [("Content-Type", "text/html; charset=utf-8")]
            body = HTML_PAGE.encode("utf-8")
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
