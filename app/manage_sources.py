import json
from pathlib import Path
from urllib.parse import urlparse

CONFIG = Path("config/sources.json")
CONFIG.parent.mkdir(parents=True, exist_ok=True)

def load():
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"sources": []}
    if not isinstance(data.get("sources"), list):
        data["sources"] = []
    return data

def save(data):
    CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nSaved to config/sources.json")

def valid_url(kind, url):
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return False
    host = (p.hostname or "").lower()
    if kind == "instagram":
        return host in ("instagram.com", "www.instagram.com")
    return host in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be")

def add_source(kind):
    data = load()
    url = input("Paste public profile/Reel URL or YouTube playlist/video URL: ").strip()
    if not valid_url(kind, url):
        print("URL domain/type is not supported. Please check the URL.")
        return
    default_id = (("insta-" if kind == "instagram" else "youtube-") + str(len(data["sources"]) + 1))
    sid = input(f"Unique source ID [{default_id}]: ").strip() or default_id
    if any(s.get("id") == sid for s in data["sources"]):
        print("This ID already exists. Choose a different unique ID.")
        return
    data["sources"].append({"id": sid, "type": kind, "url": url, "enabled": True})
    save(data)
    print(f"Added {kind} source: {sid}")

def list_sources():
    src = load()["sources"]
    if not src:
        print("No sources yet.")
        return
    for i, s in enumerate(src, 1):
        print(f'{i}. id={s.get("id")} | type={s.get("type")} | enabled={s.get("enabled", True)} | {s.get("url")}')

def toggle_source():
    data = load()
    list_sources()
    sid = input("Enter exact source ID to toggle: ").strip()
    for s in data["sources"]:
        if s.get("id") == sid:
            s["enabled"] = not s.get("enabled", True)
            save(data)
            print(f'{sid} enabled={s["enabled"]}')
            return
    print("Source ID not found.")

def delete_source():
    data = load()
    list_sources()
    sid = input("Enter exact source ID to delete: ").strip()
    before = len(data["sources"])
    data["sources"] = [s for s in data["sources"] if s.get("id") != sid]
    if len(data["sources"]) == before:
        print("Source ID not found.")
        return
    save(data)
    print("Source removed from configuration. Existing sent-history is retained in state.json.")

def main():
    while True:
        print("\n=== ReelFlow Source Manager ===")
        print("1. Add Instagram public profile/Reel URL")
        print("2. Add YouTube playlist/video URL")
        print("3. List sources")
        print("4. Enable/disable source")
        print("5. Delete source")
        print("0. Exit")
        choice = input("Choose: ").strip()
        if choice == "1": add_source("instagram")
        elif choice == "2": add_source("youtube")
        elif choice == "3": list_sources()
        elif choice == "4": toggle_source()
        elif choice == "5": delete_source()
        elif choice == "0": break
        else: print("Invalid choice.")
if __name__ == "__main__":
    main()
