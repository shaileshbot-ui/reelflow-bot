import json
import os
import sys
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "sources.json"
TOKEN_FILE = Path.home() / ".reelflow_token"
ADMIN_FILE = Path.home() / ".reelflow_admin"
BASE = "https://api.telegram.org/bot{}"

token = ""
admin = ""
offset = 0
pending = {}
http = requests.Session()


def api(method, **data):
    r = http.post(BASE.format(token) + "/" + method,
                  json=data, timeout=40)
    r.raise_for_status()
    result = r.json()
    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API error"))
    return result["result"]


def load():
    if not CONFIG.exists():
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        save({"sources": []})
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def save(data):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temp = CONFIG.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    temp.replace(CONFIG)


def send(chat, text, rows=None):
    args = {"chat_id": chat, "text": text}
    if rows:
        args["reply_markup"] = {"inline_keyboard": rows}
    api("sendMessage", **args)


def menu(chat):
    send(chat, "ReelFlow Bot\n\nOption chunein:",
         [[{"text": "⬇️ Download videos", "callback_data": "download"}],
          [{"text": "➕ Instagram link", "callback_data": "add:instagram"}],
          [{"text": "➕ YouTube link", "callback_data": "add:youtube"}],
          [{"text": "📋 Sources list", "callback_data": "list"}],
          [{"text": "🗑 Remove source", "callback_data": "remove"}]])


def allowed_url(url, kind):
    try:
        u = urlparse(url.strip())
        host = (u.hostname or "").lower()
        if u.scheme != "https":
            return False
        if kind == "instagram":
            return host in {"instagram.com", "www.instagram.com"}
        return host in {"youtube.com", "www.youtube.com",
                        "m.youtube.com", "youtu.be"}
    except Exception:
        return False



def sync_github_config():
    """Commit and push only the playlist configuration."""
    def run(args):
        return subprocess.run(
            args, cwd=str(ROOT), capture_output=True,
            text=True, timeout=120
        )

    # Never include state.json or backup files in this commit.
    r = run(["git", "add", "--", "config/sources.json"])
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout)[-1200:])

    r = run([
        "git", "commit", "--only", "-m",
        "Sync Telegram playlist configuration", "--",
        "config/sources.json"
    ])
    if r.returncode:
        check = run(["git", "diff", "--cached", "--", "config/sources.json"])
        if check.returncode == 0 and not check.stdout.strip():
            # No config change to commit.
            return "No new config changes to push."
        raise RuntimeError((r.stderr or r.stdout)[-1200:])

    r = run(["git", "push", "origin", "main"])
    if r.returncode:
        raise RuntimeError(
            "GitHub push failed. Config local mein saved hai, "
            "lekin GitHub sync nahi hua. " +
            (r.stderr or r.stdout)[-1200:]
        )
    return "GitHub main par sync successful."

def add(chat, kind, url):
    url = url.strip()
    if not allowed_url(url, kind):
        send(chat, "Valid public HTTPS Instagram/YouTube URL bhejein.")
        return

    data = load()
    for item in data["sources"]:
        if item.get("url", "").rstrip("/") == url.rstrip("/"):
            send(chat, "Yeh URL pehle se saved hai.")
            return

    prefix = "insta" if kind == "instagram" else "youtube"
    existing = {x.get("id") for x in data["sources"]}
    n = 1
    while f"{prefix}-{n}" in existing:
        n += 1
    sid = f"{prefix}-{n}"

    data["sources"].append({
        "id": sid, "type": kind, "url": url, "enabled": True
    })
    save(data)
    try:
        status = sync_github_config()
        send(chat, f"✅ Saved: {sid}\n{url}\n\n{status}")
    except Exception as e:
        send(chat, f"⚠️ Local save hua, GitHub sync fail hua:\n{str(e)[:1200]}")


def show_list(chat, deleting=False):
    sources = load()["sources"]
    if not sources:
        send(chat, "Koi source saved nahi hai.")
        return
    if deleting:
        rows = [[{"text": "🗑 " + s["id"],
                  "callback_data": "del:" + s["id"]}]
                for s in sources]
        rows.append([{"text": "⬅️ Menu", "callback_data": "menu"}])
        send(chat, "Remove karne ke liye ID chunein:", rows)
    else:
        lines = ["Saved sources:"]
        for s in sources:
            state = "ON" if s.get("enabled", True) else "OFF"
            lines.append(f"\n{s['id']} | {s['type']} | {state}\n{s['url']}")
        send(chat, "\n".join(lines))


def callback(q):
    chat = q["message"]["chat"]["id"]
    try:
        api("answerCallbackQuery", callback_query_id=q["id"])
    except Exception as e:
        print("Callback acknowledgement warning:", str(e)[:200])
    if str(chat) != admin:
        send(chat, "Access denied.")
        return

    data = q.get("data", "")
    if data == "menu":
        menu(chat)
    elif data == "download":
        send(chat, "⏳ Download run shuru ho raha hai. Kripya intezar karein.")
        env = os.environ.copy()
        env["TELEGRAM_BOT_TOKEN"] = token
        env["TELEGRAM_CHAT_ID"] = str(chat)
        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "app" / "runner.py")],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=1800,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "Unknown error")[-2500:]
                send(chat, "❌ Downloader fail hua:\n" + detail)
            else:
                print("Downloader finished.")
                if result.stdout.strip():
                    print(result.stdout[-2000:])
        except subprocess.TimeoutExpired:
            send(chat, "⚠️ Download run 30 minute baad timeout ho gaya.")
        except Exception as e:
            send(chat, "❌ Downloader error: " + str(e)[:1000])
    elif data.startswith("add:"):
        kind = data.split(":", 1)[1]
        pending[str(chat)] = kind
        send(chat, f"{kind} ka public URL bhejein. Cancel: /cancel")
    elif data == "list":
        show_list(chat)
    elif data == "remove":
        show_list(chat, deleting=True)
    elif data.startswith("del:"):
        sid = data.split(":", 1)[1]
        obj = load()
        before = len(obj["sources"])
        obj["sources"] = [s for s in obj["sources"] if s.get("id") != sid]
        if len(obj["sources"]) != before:
            save(obj)
            try:
                status = sync_github_config()
                send(chat, f"Removed: {sid}\\n{status}")
            except Exception as e:
                send(chat, f"⚠️ Local remove hua, GitHub sync fail hua:\\n{str(e)[:1200]}")
        else:
            send(chat, "ID nahi mili.")
        menu(chat)


def message(msg):
    chat = msg["chat"]["id"]
    if str(chat) != admin:
        send(chat, "Access denied.")
        return
    text = msg.get("text", "").strip()
    if text in {"/start", "/menu"}:
        pending.pop(str(chat), None)
        menu(chat)
    elif text == "/cancel":
        pending.pop(str(chat), None)
        menu(chat)
    elif str(chat) in pending and text:
        kind = pending.pop(str(chat))
        add(chat, kind, text)
        menu(chat)
    else:
        send(chat, "/start bhejkar menu kholein.")


def main():
    global token, admin, offset
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
    else:
        token = input("Telegram Bot Token: ").strip()
        if not token:
            print("Token required.")
            return
        TOKEN_FILE.write_text(token)
        TOKEN_FILE.chmod(0o600)

    if ADMIN_FILE.exists():
        admin = ADMIN_FILE.read_text().strip()
    else:
        admin = input("Apna numeric Telegram Chat ID: ").strip()
        if not admin.isdigit():
            print("Chat ID numeric hona chahiye.")
            return
        ADMIN_FILE.write_text(admin)
        ADMIN_FILE.chmod(0o600)

    print("Bot:", api("getMe").get("username"))
    print("Running. Telegram par /start bhejein. Stop: Ctrl+C")
    while True:
        try:
            updates = api("getUpdates", offset=offset, timeout=25,
                          allowed_updates=["message", "callback_query"])
            for u in updates:
                offset = u["update_id"] + 1
                if "message" in u:
                    message(u["message"])
                elif "callback_query" in u:
                    callback(u["callback_query"])
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Temporary error:", str(e)[:200])
            time.sleep(5)


if __name__ == "__main__":
    main()
