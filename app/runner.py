import json, os, pathlib, re, subprocess, tempfile, shutil, requests
from datetime import datetime, timezone
TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]; CHAT=os.environ["TELEGRAM_CHAT_ID"]
CONFIG=pathlib.Path("config/sources.json"); STATE=pathlib.Path("state.json")
OUT=pathlib.Path("outputs"); OUT.mkdir(exist_ok=True)

def tg(method, **data):
    r=requests.post(f"https://api.telegram.org/bot{TOKEN}/{method}",data=data,timeout=120)
    r.raise_for_status(); j=r.json()
    if not j.get("ok"): raise RuntimeError(str(j))
    return j["result"]
def cmd(args,timeout=900):
    if args and pathlib.Path(args[0]).name == "yt-dlp":
        cookie_file = os.environ.get("YOUTUBE_COOKIES_FILE")
        if cookie_file and pathlib.Path(cookie_file).is_file():
            args = [args[0], "--remote-components", "ejs:github", "--cookies", cookie_file, *args[1:]]
    try:
        return subprocess.check_output(
            args, text=True, stderr=subprocess.PIPE, timeout=timeout
        )
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.output or "").strip()
        raise RuntimeError(
            f"Command failed (exit {e.returncode}): "
            f"{' '.join(args[:3])}\\n{detail[-3000:]}"
        ) from e
def safe(s): return re.sub(r"[^A-Za-z0-9._-]+","_",s)[:60] or "video"
def load(path,default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default
def entries(source):
    out = cmd([
        "yt-dlp", "--flat-playlist", "--no-warnings",
        "--ignore-errors", "--print",
        "%(id)s|%(webpage_url)s|%(title)s",
        source["url"]
    ], 180)

    result = []
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) < 2 or not parts[0].strip():
            continue

        video_id = parts[0].strip()
        video_url = parts[1].strip()
        title = parts[2].strip() if len(parts) > 2 else video_id

        if not video_url:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        result.append({
            "key": video_id,
            "url": video_url,
            "title": title or video_id
        })

    if not result and source.get("type") == "youtube":
        if "list=" not in source["url"]:
            result = [{
                "key": source["url"],
                "url": source["url"],
                "title": "YouTube video"
            }]

    return result

def make_video(entry,sid):
    tmp=pathlib.Path(tempfile.mkdtemp(prefix="reelflow_"))
    try:
        cmd(["yt-dlp","--no-warnings","--no-progress","-f","bv*+ba/b","--merge-output-format","mp4","-o",str(tmp/"source.%(ext)s"),"--max-filesize","250M","--no-playlist",entry["url"]],900)
        candidates=list(tmp.glob("source.*")) or [p for p in tmp.iterdir() if p.is_file()]
        if not candidates: raise RuntimeError("Downloaded file not found")
        out=OUT/f"{safe(sid)}_{safe(entry['key'])}.mp4"
        vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        cmd(["ffmpeg","-y","-i",str(candidates[0]),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","128k","-movflags","+faststart","-t","180",str(out)],900)
        return out
    finally: shutil.rmtree(tmp,ignore_errors=True)
def send(path, title, url):
    title = (title or "New video").strip()
    caption = f"{title}\\n\\n#Reels #Shorts #Video\\nSource: {url}"
    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendVideo",
            data={
                "chat_id": CHAT,
                "caption": caption[:1024],
                "supports_streaming": "true",
            },
            files={"video": (path.name, f, "video/mp4")},
            timeout=300,
        )
    result = r.json()
    if not r.ok or not result.get("ok"):
        raise RuntimeError(f"Telegram sendVideo failed: {result}")

def main():
    cfg=load(CONFIG,{"sources":[]}); state=load(STATE,{"sources":{}}); state.setdefault("sources",{})
    sources=[s for s in cfg.get("sources",[]) if s.get("enabled",True) and s.get("id") and s.get("url")]
    if not sources:
        tg("sendMessage",chat_id=CHAT,text="Koi source configured nahi hai. config/sources.json mein Instagram profile ya YouTube playlist add karein.")
        return
    sent=0
    for s in sources:
        sid=s["id"]; hist=state["sources"].setdefault(sid,{"sent":[]}); seen=set(hist.get("sent",[]))
        try:
            fresh=next((e for e in entries(s) if e["key"] not in seen),None)
            if not fresh:
                print("No new item:",sid); continue
            path=make_video(fresh,sid); send(path,fresh.get("title") or sid,fresh["url"])
            hist["sent"].append(fresh["key"]); hist["sent"]=hist["sent"][-5000:]; sent+=1
        except Exception as e:
            print("Source error",sid,repr(e))
            try: tg("sendMessage",chat_id=CHAT,text=f"Source {sid} se video nahi bhej paya.\n{str(e)[:500]}")
            except Exception: pass
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tg("sendMessage",chat_id=CHAT,text=f"Run complete: {sent}/{len(sources)} videos sent. {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
if __name__=="__main__": main()
