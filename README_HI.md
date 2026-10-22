# ReelFlow Bot

Repo: `reelflow-bot`  
Telegram display name: `ReelFlow Bot`  
Suggested BotFather username: `ReelFlowBot` (availability must be checked; Telegram usernames end in `bot`).

This is separate from `yt_fb_bot`.

## Behavior
- Add one source per Instagram public profile/Reel or YouTube playlist in `config/sources.json`.
- Each enabled source gets at most ONE previously-unsent video per run.
- 5 sources => up to 5 videos/run; 6 sources => up to 6.
- Sends processed vertical 1080x1920 MP4, title-based caption draft and source URL to Telegram.
- Successful sends are recorded in `state.json`; workflow commits the history to GitHub.
- Cloudflare Cron triggers GitHub Actions. Cloudflare Worker does not download/encode videos itself.

## GitHub setup
Create a new repository named `reelflow-bot`. Upload these files.
Add repository Actions secrets:
- `TELEGRAM_BOT_TOKEN` = BotFather token
- `TELEGRAM_CHAT_ID` = your numeric Telegram chat ID
- Optional `GH_PUSH_TOKEN` = token with Contents read/write if the workflow cannot push state using its built-in token.

## Add sources
Edit `config/sources.json`, then push with Termux:
```json
{
  "sources": [
    {"id":"insta-main","type":"instagram","url":"https://www.instagram.com/USERNAME/","enabled":true},
    {"id":"yt-playlist-1","type":"youtube","url":"https://www.youtube.com/playlist?list=PLAYLIST_ID","enabled":true}
  ]
}
```
Use unique stable `id` values. To start fresh history for a source, give it a new id. Use only content you own or have permission to reuse.

## Cloudflare Cron
Deploy `cloudflare/worker.js` as a Worker. Add Worker secrets/variables:
- `GH_OWNER` = GitHub username/org
- `GH_REPO` = `reelflow-bot`
- `GH_WORKFLOW` = `daily-reels.yml`
- `GH_TOKEN` = GitHub token with permission to dispatch Actions workflows

Add Cron Trigger: `0 3 * * *` (03:00 UTC = about 08:30 India time). Cloudflare triggers the GitHub workflow; GitHub Actions still needs available usage/quota.

Test first from GitHub → Actions → Daily Reels to Telegram → Run workflow.
Instagram profile enumeration can fail due to platform changes/rate limits; it is best-effort. No login/private-content bypass is included. Respect copyright and platform rules.
