"""
یک‌بار اجرا کن تا به تلگرام بگی آپدیت‌ها رو به کجا (Vercel) بفرسته.
نیازی به نصب چیزی نداره، فقط پایتون استاندارد.

اجرا:
    BOT_TOKEN=xxx WEBHOOK_SECRET=yyy WEB_APP_URL=https://your-app.vercel.app python set_webhook.py
"""
import os
import urllib.request
import urllib.parse
import json

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
WEB_APP_URL = os.environ["WEB_APP_URL"].rstrip("/")

webhook_url = f"{WEB_APP_URL}/api/webhook"
api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

params = urllib.parse.urlencode({
    "url": webhook_url,
    "secret_token": WEBHOOK_SECRET,
    "allowed_updates": json.dumps(["message", "channel_post"]),
})

with urllib.request.urlopen(f"{api_url}?{params}") as resp:
    print(resp.read().decode())

print(f"\nوبهوک روی این آدرس ست شد: {webhook_url}")
