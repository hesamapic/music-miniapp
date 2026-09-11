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

HTML_PAGE = '<!DOCTYPE html>\n<html lang="en" dir="ltr">\n<head>\n<meta charset="UTF-8" />\n<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />\n<title>Random Music</title>\n<script src="https://telegram.org/js/telegram-web-app.js"></script>\n<style>\n  :root {\n    color-scheme: dark;\n    --bg: #000000;\n    --surface: #121212;\n    --text: #ffffff;\n    --text-dim: #a7a7a7;\n    --text-faint: #6a6a6a;\n    --accent: #1ed760;\n    --track: #2a2a2a;\n    --ghost-btn: #1c1c1c;\n  }\n  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }\n  html, body {\n    margin: 0; padding: 0; height: 100%;\n    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;\n    background: radial-gradient(120% 100% at 50% 0%, #161616 0%, #000000 62%);\n    color: var(--text);\n    -webkit-font-smoothing: antialiased;\n  }\n  .app {\n    min-height: 100vh;\n    display: flex; flex-direction: column;\n    align-items: center; justify-content: center;\n    padding: 32px 24px;\n  }\n  .stage {\n    width: 100%;\n    max-width: 340px;\n    display: flex;\n    flex-direction: column;\n    align-items: center;\n  }\n\n  .eyebrow {\n    font-size: 12px;\n    font-weight: 600;\n    letter-spacing: 0.12em;\n    text-transform: uppercase;\n    color: var(--text-faint);\n    margin-bottom: 22px;\n  }\n\n  .cover {\n    width: 78vw;\n    max-width: 300px;\n    aspect-ratio: 1 / 1;\n    border-radius: 18px;\n    background: linear-gradient(160deg, #2a2a2a, #0d0d0d);\n    display: flex; align-items: center; justify-content: center;\n    box-shadow: 0 30px 60px -20px rgba(0,0,0,0.7);\n    overflow: hidden;\n    position: relative;\n  }\n  .cover img { width: 100%; height: 100%; object-fit: cover; }\n  .cover svg { width: 30%; height: 30%; opacity: 0.35; }\n  .cover.spinning svg { animation: pulse 2.4s ease-in-out infinite; }\n  @keyframes pulse { 0%,100% { opacity: 0.35; } 50% { opacity: 0.6; } }\n\n  .meta { width: 100%; margin-top: 26px; text-align: center; }\n  .title {\n    font-size: 20px; font-weight: 700; letter-spacing: -0.01em;\n    line-height: 1.35; margin: 0;\n    overflow: hidden; text-overflow: ellipsis;\n    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;\n  }\n  .artist { font-size: 14px; color: var(--text-dim); margin: 6px 0 0; }\n\n  .progress-wrap { width: 100%; margin-top: 26px; }\n  .progress-track {\n    width: 100%; height: 3px; border-radius: 3px;\n    background: var(--track); position: relative; cursor: pointer;\n    padding-block: 8px; margin-block: -8px;\n    background-clip: content-box;\n  }\n  .progress-fill {\n    position: absolute; top: 8px; left: 0; height: 3px; border-radius: 3px;\n    background: var(--text); width: 0%;\n  }\n  .time-row {\n    display: flex; justify-content: space-between;\n    margin-top: 8px; font-size: 11px; color: var(--text-faint);\n    font-variant-numeric: tabular-nums;\n  }\n\n  .controls {\n    display: flex; align-items: center; justify-content: center;\n    gap: 22px; margin-top: 30px;\n  }\n  .btn-ghost {\n    width: 44px; height: 44px; border-radius: 50%;\n    background: var(--ghost-btn); border: none; color: var(--text);\n    display: flex; align-items: center; justify-content: center;\n    cursor: pointer; transition: transform 0.12s ease, background 0.12s ease;\n  }\n  .btn-ghost:active { transform: scale(0.9); background: #262626; }\n  .btn-play {\n    width: 64px; height: 64px; border-radius: 50%;\n    background: var(--text); border: none; color: #000;\n    display: flex; align-items: center; justify-content: center;\n    cursor: pointer; transition: transform 0.12s ease;\n    box-shadow: 0 8px 24px rgba(255,255,255,0.12);\n  }\n  .btn-play:active { transform: scale(0.92); }\n  .btn-play svg, .btn-ghost svg { width: 20px; height: 20px; }\n  .btn-play svg { width: 24px; height: 24px; }\n\n  .download-btn {\n    margin-top: 28px;\n    display: inline-flex; align-items: center; gap: 8px;\n    padding: 10px 18px; border-radius: 999px;\n    border: 1px solid #2e2e2e; background: transparent;\n    color: var(--text-dim); font-size: 13px; font-weight: 600;\n    text-decoration: none; cursor: pointer;\n    transition: border-color 0.15s ease, color 0.15s ease;\n  }\n  .download-btn:active { border-color: #4a4a4a; color: var(--text); }\n  .download-btn svg { width: 14px; height: 14px; }\n\n  .status {\n    margin-top: 22px; font-size: 12.5px; color: var(--text-faint);\n    min-height: 16px; text-align: center; max-width: 280px;\n  }\n\n  audio { display: none; }\n</style>\n</head>\n<body>\n  <div class="app">\n    <div class="stage">\n      <div class="eyebrow">Random Music</div>\n\n      <div class="cover" id="cover">\n        <svg viewBox="0 0 24 24" fill="white"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>\n        <img id="coverImg" style="display:none" />\n      </div>\n\n      <div class="meta">\n        <p class="title" id="title">Tap play to start</p>\n        <p class="artist" id="performer">A random track from the channel</p>\n      </div>\n\n      <div class="progress-wrap">\n        <div class="progress-track" id="progressTrack">\n          <div class="progress-fill" id="progressFill"></div>\n        </div>\n        <div class="time-row">\n          <span id="timeCurrent">0:00</span>\n          <span id="timeTotal">0:00</span>\n        </div>\n      </div>\n\n      <div class="controls">\n        <button class="btn-ghost" id="btnPrev" title="Previous">\n          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="19 20 9 12 19 4 19 20"/><line x1="5" y1="19" x2="5" y2="5"/></svg>\n        </button>\n        <button class="btn-play" id="btnPlay" title="Play/Pause">\n          <svg id="iconPlay" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>\n        </button>\n        <button class="btn-ghost" id="btnNext" title="Next">\n          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19"/></svg>\n        </button>\n      </div>\n\n      <a class="download-btn" id="btnDownload" href="#" target="_blank" rel="noopener">\n        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>\n        Download\n      </a>\n\n      <div class="status" id="status"></div>\n      <audio id="audio"></audio>\n    </div>\n  </div>\n\n<script>\n  const tg = window.Telegram ? window.Telegram.WebApp : null;\n  if (tg) { tg.ready(); tg.expand(); }\n\n  const els = {\n    cover: document.getElementById(\'cover\'),\n    coverImg: document.getElementById(\'coverImg\'),\n    title: document.getElementById(\'title\'),\n    performer: document.getElementById(\'performer\'),\n    btnPlay: document.getElementById(\'btnPlay\'),\n    iconPlay: document.getElementById(\'iconPlay\'),\n    btnNext: document.getElementById(\'btnNext\'),\n    btnPrev: document.getElementById(\'btnPrev\'),\n    btnDownload: document.getElementById(\'btnDownload\'),\n    status: document.getElementById(\'status\'),\n    audio: document.getElementById(\'audio\'),\n    progressTrack: document.getElementById(\'progressTrack\'),\n    progressFill: document.getElementById(\'progressFill\'),\n    timeCurrent: document.getElementById(\'timeCurrent\'),\n    timeTotal: document.getElementById(\'timeTotal\'),\n  };\n\n  const ICON_PLAY = \'<path d="M8 5v14l11-7z"/>\';\n  const ICON_PAUSE = \'<rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/>\';\n\n  let current = null;\n  let isPlaying = false;\n  let history = [];\n  let historyIndex = -1;\n\n  function setStatus(text) { els.status.textContent = text || \'\'; }\n\n  function formatTime(sec) {\n    if (!isFinite(sec) || sec < 0) sec = 0;\n    const m = Math.floor(sec / 60);\n    const s = Math.floor(sec % 60).toString().padStart(2, \'0\');\n    return `${m}:${s}`;\n  }\n\n  function formatTrack(track) {\n    els.title.textContent = track.title || \'Untitled\';\n    els.performer.textContent = track.performer || \'Unknown artist\';\n    els.btnDownload.href = track.download_url;\n    els.timeTotal.textContent = formatTime(track.duration || 0);\n    els.timeCurrent.textContent = \'0:00\';\n    els.progressFill.style.width = \'0%\';\n\n    if (track.cover_url) {\n      els.coverImg.src = track.cover_url;\n      els.coverImg.style.display = \'block\';\n    } else {\n      els.coverImg.style.display = \'none\';\n    }\n  }\n\n  async function fetchRandomTrack() {\n    setStatus(\'Finding a random track…\');\n    els.btnPlay.disabled = true;\n    try {\n      const res = await fetch(\'/api/index?route=random\');\n      const data = await res.json();\n      if (!data.ok) {\n        setStatus(data.error === \'no tracks indexed yet\'\n          ? \'No tracks indexed yet — run the indexer script first.\'\n          : \'Could not load a track.\');\n        return null;\n      }\n      current = data;\n      formatTrack(data);\n      setStatus(\'\');\n      return data;\n    } catch (e) {\n      setStatus(\'Connection failed. Try again.\');\n      return null;\n    } finally {\n      els.btnPlay.disabled = false;\n    }\n  }\n\n  function resetPlayIcon() {\n    isPlaying = false;\n    els.iconPlay.outerHTML = `<svg id="iconPlay" viewBox="0 0 24 24" fill="currentColor">${ICON_PLAY}</svg>`;\n    els.iconPlay = document.getElementById(\'iconPlay\');\n    els.cover.classList.remove(\'spinning\');\n  }\n\n  function loadTrack(track) {\n    current = track;\n    formatTrack(track);\n    els.audio.src = track.stream_url;\n    togglePlay(true);\n  }\n\n  async function playNewRandom() {\n    resetPlayIcon();\n    const track = await fetchRandomTrack();\n    if (track) {\n      // discard any "forward" history past this point, then append\n      history = history.slice(0, historyIndex + 1);\n      history.push(track);\n      historyIndex = history.length - 1;\n      loadTrack(track);\n    }\n  }\n\n  function playPrevious() {\n    if (historyIndex <= 0) {\n      setStatus("This is the first track.");\n      return;\n    }\n    resetPlayIcon();\n    historyIndex -= 1;\n    loadTrack(history[historyIndex]);\n  }\n\n  function togglePlay(forcePlay) {\n    const shouldPlay = forcePlay !== undefined ? forcePlay : !isPlaying;\n    if (!current || !els.audio.src) { playNewRandom(); return; }\n\n    if (shouldPlay) {\n      els.audio.play().catch(() => setStatus(\'Tap play again to start playback.\'));\n      isPlaying = true;\n      els.iconPlay.outerHTML = `<svg id="iconPlay" viewBox="0 0 24 24" fill="currentColor">${ICON_PAUSE}</svg>`;\n      els.iconPlay = document.getElementById(\'iconPlay\');\n      els.cover.classList.add(\'spinning\');\n    } else {\n      els.audio.pause();\n      isPlaying = false;\n      els.iconPlay.outerHTML = `<svg id="iconPlay" viewBox="0 0 24 24" fill="currentColor">${ICON_PLAY}</svg>`;\n      els.iconPlay = document.getElementById(\'iconPlay\');\n      els.cover.classList.remove(\'spinning\');\n    }\n  }\n\n  els.btnPlay.addEventListener(\'click\', () => togglePlay());\n  els.btnNext.addEventListener(\'click\', playNewRandom);\n  els.btnPrev.addEventListener(\'click\', playPrevious);\n  els.audio.addEventListener(\'ended\', playNewRandom);\n\n  els.audio.addEventListener(\'timeupdate\', () => {\n    const d = els.audio.duration || (current && current.duration) || 0;\n    if (d > 0) {\n      els.progressFill.style.width = `${(els.audio.currentTime / d) * 100}%`;\n      els.timeCurrent.textContent = formatTime(els.audio.currentTime);\n    }\n  });\n  els.audio.addEventListener(\'loadedmetadata\', () => {\n    if (isFinite(els.audio.duration)) {\n      els.timeTotal.textContent = formatTime(els.audio.duration);\n    }\n  });\n\n  els.progressTrack.addEventListener(\'click\', (e) => {\n    const d = els.audio.duration || (current && current.duration) || 0;\n    if (!d) return;\n    const rect = els.progressTrack.getBoundingClientRect();\n    const ratio = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);\n    els.audio.currentTime = ratio * d;\n  });\n\n  // Preload a random track on load (and wire it into history + audio.src),\n  // but don\'t autoplay — browsers/Telegram usually block audio autoplay anyway.\n  (async function preload() {\n    const track = await fetchRandomTrack();\n    if (track) {\n      history = [track];\n      historyIndex = 0;\n      els.audio.src = track.stream_url;\n    }\n  })();\n</script>\n</body>\n</html>\n'


# ---------------------------------------------------------------- helpers --

LAST_REDIS_ERROR = None


def redis_cmd(*args):
    global LAST_REDIS_ERROR
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        LAST_REDIS_ERROR = "missing UPSTASH_URL or UPSTASH_TOKEN"
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
        LAST_REDIS_ERROR = f"HTTPError {e.code}: {body[:200]}"
    except Exception as e:
        LAST_REDIS_ERROR = f"Exception: {e}"
        return None
    try:
        parsed = json.loads(body)
        if "error" in parsed:
            LAST_REDIS_ERROR = f"Upstash error: {parsed['error']}"
        return parsed.get("result")
    except Exception as e:
        LAST_REDIS_ERROR = f"JSON parse error: {e}"
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
        elif route == "debug":
            redis_ping_result = redis_cmd("PING")
            track_count = redis_cmd("SCARD", "track_ids")
            info = {
                "bot_token_set": bool(BOT_TOKEN),
                "bot_token_len": len(BOT_TOKEN),
                "webhook_secret_set": bool(WEBHOOK_SECRET),
                "webhook_secret_len": len(WEBHOOK_SECRET),
                "web_app_url": WEB_APP_URL,
                "upstash_url_set": bool(UPSTASH_URL),
                "upstash_url_preview": (UPSTASH_URL[:25] + "...") if UPSTASH_URL else "",
                "upstash_token_set": bool(UPSTASH_TOKEN),
                "upstash_token_len": len(UPSTASH_TOKEN),
                "redis_ping_result": redis_ping_result,
                "redis_reachable": redis_ping_result == "PONG",
                "track_count_in_redis": track_count,
                "last_redis_error": LAST_REDIS_ERROR,
                "received_secret_header_len": len(environ.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN", "")),
            }
            status, headers, body = 200, JSON_HEADERS, json.dumps(info).encode()
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
