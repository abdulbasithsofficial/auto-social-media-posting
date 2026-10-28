# SocialPost-Agent

Draft, approve, queue and publish social posts — without posting anything live by accident.

## How it works (the rule)
1. **Add** a post → it is a **draft**, nothing is posted.
2. **Draft** → see the exact Facebook/Instagram, Threads and LinkedIn versions.
3. **Approve** → only then can it go live.
4. **Post --dry-run** → shows the exact connector commands, posts nothing.
5. **Post --live** → you still run each platform publish separately, because Facebook, Instagram and Threads each need their own fresh approval.

## Quick start
```bash
python3 agent.py add --text "Build your own AI agent in 3 steps with EasyAIAgents — no code needed." --platforms facebook,instagram,threads --topic EasyAIAgents
python3 agent.py draft
python3 agent.py approve --id 1
python3 agent.py post --id 1 --dry-run
```

## Platforms
- **Facebook** — personal text posts and Page posts/schedules via `facebook-cli` (see its Page publishing docs). Each post needs fresh approval.
- **Instagram** — feed media / stories via `instagram-cli` (`post-feed`, `post-story`). Check `instagram-cli --help` for media flags for your account.
- **Threads** — `threads-cli publish-post --account-id <id> --text "..."` (max 500 characters — this agent caps short versions at ~420 chars). One approval per post.

LinkedIn and X have no connector configured here yet — the agent still writes their draft versions in `drafts/` so you can post them manually.

## Spam guard
Max 5 live posts per day per platform in `config.json`. Do not bulk-post; accounts get blocked for spam.

## Setup
1. Connect Facebook, Instagram and Threads in Muse (Accounts Center).
2. Put your numeric account IDs in `config.json` (replace the `<..._ACCOUNT_ID>` placeholders).
3. Never put passwords or tokens in this repo, in `config.json`, or in chat.

## Files
- `agent.py` — the agent
- `queue.json` — post queue (draft / approved / posted)
- `drafts/` — generated per-platform draft texts
- `config.json` — hashtags, limits, account IDs
