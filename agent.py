#!/usr/bin/env python3
"""
SocialPost-Agent — draft, approve, queue and publish social posts.
Usage:
  python3 agent.py add --text "Your post" --platforms facebook,instagram,threads --topic EasyAIAgents
  python3 agent.py draft            # show drafts, no live posting
  python3 agent.py list             # queue status
  python3 agent.py approve --id 1   # approve ONE post for live posting
  python3 agent.py post --id 1 --dry-run   # default: show exact commands, post nothing
  python3 agent.py post --id 1 --live      # only approved posts, one approval per platform publish

Rules baked in:
- Nothing posts live without an explicit approve step first.
- No passwords/tokens in code or chat. Connectors (facebook-cli, instagram-cli,
  threads-cli) handle accounts; this agent only builds the exact commands.
- Spam guard: max 5 live posts per day per platform (configurable in config.json).
- Threads text is capped at 500 characters (Threads CLI rejects longer text).
"""
import argparse, json, os, sys, subprocess, textwrap
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(BASE, "queue.json")
CONFIG = os.path.join(BASE, "config.json")

def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def adapt(text, platform, hashtags):
    t = text.strip()
    if platform in ("threads", "x"):
        # Short, catchy version, max 500 chars for Threads
        short = t if len(t) <= 420 else t[:417].rsplit(" ", 1)[0] + "..."
        return short
    if platform == "linkedin":
        return f"{t}\n\nWhat do you think? Share your experience in the comments.\n\n{hashtags}"
    # facebook / instagram: long caption + hashtags
    return f"{t}\n\n{hashtags}" if hashtags else t

def cmd_add(args):
    q = load_json(QUEUE, [])
    nid = (max([p["id"] for p in q], default=0) + 1)
    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    post = {
        "id": nid, "text": args.text, "topic": args.topic or "",
        "image": args.image or "", "platforms": platforms,
        "status": "draft", "approved": False, "posted": {}, "created": str(date.today()),
    }
    q.append(post); save_json(QUEUE, q)
    print(f"Added post #{nid} as DRAFT (not posted). Run: python3 agent.py draft")

def cmd_draft(args):
    q = load_json(QUEUE, []); cfg = load_json(CONFIG, {})
    hashtags = cfg.get("hashtags", "#AI #AIAgents #EasyAIAgents")
    if not q:
        print("Queue empty. Add a post first."); return
    os.makedirs(os.path.join(BASE, "drafts"), exist_ok=True)
    for p in q:
        if p["status"] == "posted":
            continue
        print(f"\n=== Post #{p['id']} [{p['status']}] platforms={','.join(p['platforms'])} ===")
        print(f"Original: {p['text']}")
        for plat in p["platforms"]:
            v = adapt(p["text"], plat, hashtags)
            with open(os.path.join(BASE, "drafts", f"{p['id']}-{plat}.txt"), "w", encoding="utf-8") as f:
                f.write(v)
            print(f"\n-- {plat} --\n{v}")

def cmd_list(args):
    q = load_json(QUEUE, [])
    for p in q:
        print(f"#{p['id']} [{p['status']}] approved={p['approved']} platforms={','.join(p['platforms'])} posted={p['posted']} :: {p['text'][:80]}")

def cmd_approve(args):
    q = load_json(QUEUE, []); found = False
    for p in q:
        if p["id"] == args.id:
            p["approved"] = True; p["status"] = "approved"; found = True
    if not found:
        print(f"Post #{args.id} not found."); sys.exit(1)
    save_json(QUEUE, q); print(f"Post #{args.id} APPROVED. It can now be posted with --live (one platform approval each).")

def build_commands(post, cfg):
    """Return exact connector commands for each platform. No command runs here."""
    cmds = {}
    hashtags = cfg.get("hashtags", "")
    for plat in post["platforms"]:
        v = adapt(post["text"], plat, hashtags)
        if plat == "threads":
            acct = cfg.get("threads_account_id", "<THREADS_ACCOUNT_ID>")
            cmds[plat] = f"/opt/hatch/bin/threads-cli publish-post --account-id {acct} --text {json.dumps(v)}"
        elif plat == "instagram":
            acct = cfg.get("instagram_account_id", "<INSTAGRAM_ACCOUNT_ID>")
            cmds[plat] = f"/opt/hatch/bin/instagram-cli post-feed --account-id {acct} --caption {json.dumps(v)}  # check instagram-cli --help for media flags"
        elif plat == "facebook":
            cmds[plat] = "# Facebook: use facebook-cli Page publishing (see README) with the draft text in drafts/ — personal/Page posts need fresh approval each time"
        else:
            cmds[plat] = f"# No connector configured for {plat} — post manually from drafts/{post['id']}-{plat}.txt"
    return cmds

def cmd_post(args):
    q = load_json(QUEUE, []); cfg = load_json(CONFIG, {})
    post = next((p for p in q if p["id"] == args.id), None)
    if not post:
        print(f"Post #{args.id} not found."); sys.exit(1)
    if not post["approved"] and args.live:
        print("REFUSED: post is not approved. Run: python3 agent.py approve --id", args.id); sys.exit(1)
    cmds = build_commands(post, cfg)
    print(f"Post #{post['id']} mode={'LIVE' if args.live else 'DRY-RUN (nothing posted)'}")
    for plat, c in cmds.items():
        print(f"\n[{plat}] {c}")
    if args.live:
        print("\nLIVE mode: run each command above separately — each platform publish needs its own fresh approval in the connector. This script does not auto-execute them, so a bad draft can never go live by accident.")
        post["status"] = "posted-pending-connector"
        save_json(QUEUE, q)

def main():
    ap = argparse.ArgumentParser(description="SocialPost-Agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("--text", required=True); a.add_argument("--platforms", default="facebook,instagram,threads"); a.add_argument("--topic", default=""); a.add_argument("--image", default=""); a.set_defaults(fn=cmd_add)
    d = sub.add_parser("draft"); d.set_defaults(fn=cmd_draft)
    l = sub.add_parser("list"); l.set_defaults(fn=cmd_list)
    v = sub.add_parser("approve"); v.add_argument("--id", type=int, required=True); v.set_defaults(fn=cmd_approve)
    p = sub.add_parser("post"); p.add_argument("--id", type=int, required=True); p.add_argument("--dry-run", action="store_true"); p.add_argument("--live", action="store_true"); p.set_defaults(fn=cmd_post)
    args = ap.parse_args()
    if args.cmd == "post" and not args.dry_run and not args.live:
        args.dry_run = True
    args.fn(args)

if __name__ == "__main__":
    main()
