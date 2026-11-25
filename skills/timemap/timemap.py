#!/usr/bin/env python3
"""Map a calendar day's Claude Code sessions to billable time.

  timemap.py [yesterday|today|YYYY-MM-DD]                 list sessions as JSON
  timemap.py [day] --groups groups.json                   render the Time Map

groups.json: {"ABC-25": {"desc": "Responsive nav fixes", "client": "ABC", "sessions": ["<id>", ...]}, ...}
"client" is optional and defaults to the key's first word before "-" or a space.
Sessions not listed in any group get a line of their own under their session name, client "Other".
Optional: --idle MIN (default 15) sets how long a quiet stretch ends a block.
          --attended MIN (default 15) sets how long after your last input a session still counts.
"""
import json, sys, glob, os, re
from datetime import datetime, timedelta, date

MIN_LINE_H = 5 / 60     # lines under 5 minutes are dropped
MIN_NOTE_H = 0.1        # uncounted agent time shown only at 0.1 h or more
MIN_GAP = timedelta(minutes=30)
PAD = timedelta(minutes=1)  # credit for a lone prompt/reply
ROOT = os.path.expanduser("~/.claude/projects")
NOT_HUMAN = ("<task-notification", "<system-reminder", "<bash-notification")

args = sys.argv[1:]
if {"-h", "--help"} & set(args):
    print(__doc__.strip()); sys.exit()
def opt(name, default=None):
    if name not in args: return default
    i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
IDLE = timedelta(minutes=float(opt("--idle", 15)))
ATTEND = float(opt("--attended", 15))
AFTER = timedelta(minutes=ATTEND)
GROUPS = opt("--groups")
which = args[0].lower() if args else "yesterday"
day = {"today": date.today(), "yesterday": date.today() - timedelta(days=1)}.get(which) or date.fromisoformat(which)
start = datetime.combine(day, datetime.min.time()).astimezone()  # local offset for that date, not today's
end = datetime.combine(day + timedelta(days=1), datetime.min.time()).astimezone()

r = lambda h: round(round(h / 0.025) * 0.025, 3)
hrs = lambda a, b: (b - a).total_seconds() / 3600
measure = lambda blocks: sum(hrs(a, b) for a, b in blocks)

def hm(h):
    """0.025 h steps as h:mm, in integer seconds so 0.675 is 0:41, not 0:40."""
    m = (round(h / 0.025) * 90 + 30) // 60
    return f"{m // 60}:{m % 60:02d}"

def span(a, b):
    m = round((b - a).total_seconds() / 60)
    return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m}m"

def merge(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1]: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return [tuple(x) for x in out]

def clip(blocks, windows):
    return [(max(a, c), min(b, d)) for a, b in blocks for c, d in windows if max(a, c) < min(b, d)]

def prompt_text(rec):
    c = rec.get("message", {}).get("content")
    if isinstance(c, list):
        if any(p.get("type") == "tool_result" for p in c): return None
        c = " ".join(p.get("text", "") for p in c if p.get("type") == "text")
    if not isinstance(c, str): return None
    c = re.sub(r"\s+", " ", c).strip()
    if not c or c.startswith(("<", "[Image", "[Request interrupted", "Base directory for this skill")): return None
    return c[:200]

def from_you(rec):
    """A record you made: a prompt, slash command, interrupt, pasted image or answer to a question.
    Not task notifications, system reminders, meta records or headless (claude -p / SDK) runs."""
    if rec.get("isMeta") or rec.get("entrypoint") == "sdk-cli": return False
    c = rec.get("message", {}).get("content")
    if isinstance(c, list):
        if any(p.get("type") == "tool_result" for p in c):
            return isinstance(rec.get("toolUseResult"), dict) and "answers" in rec["toolUseResult"]
        c = " ".join(p.get("text", "") for p in c if p.get("type") == "text") or "[image]"
    return isinstance(c, str) and not c.lstrip().startswith(NOT_HUMAN)

def load_sessions():
    sessions = {}
    for path in glob.glob(f"{ROOT}/*/*.jsonl") + glob.glob(f"{ROOT}/*/*/subagents/*.jsonl"):
        if os.path.getmtime(path) < start.timestamp(): continue
        folder, file = path[len(ROOT) + 1:].split("/")[:2]
        sid = file.removesuffix(".jsonl")
        sub = "/subagents/" in path
        project = re.sub(r"^-Users-[^-]+(-repos)?-?", "", folder, flags=re.I) or "(root)"
        s = sessions.setdefault(sid, {"id": sid, "project": project, "times": [], "inputs": [], "prompts": [],
                                      "title": None, "ai_title": None})
        with open(path) as fh:
            for line in fh:
                try: rec = json.loads(line)
                except ValueError: continue
                t = rec.get("type")
                if t == "custom-title": s["title"] = rec.get("customTitle") or s["title"]
                elif t in ("ai-title", "agent-name"): s["ai_title"] = rec.get("aiTitle") or rec.get("agentName") or s["ai_title"]
                if t not in ("user", "assistant") or not rec.get("timestamp"): continue
                when = datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00")).astimezone()
                if not start <= when < end: continue
                s["times"].append(when)
                if t == "user" and not sub:
                    if from_you(rec): s["inputs"].append(when)
                    if p := prompt_text(rec): s["prompts"].append((when.strftime("%H:%M"), p))
    out = []
    for s in sessions.values():
        if not s["times"]: continue
        blocks = []
        for t in sorted(s["times"]):
            if blocks and t - blocks[-1][1] <= IDLE: blocks[-1][1] = t
            else: blocks.append([t, t])
        s["raw"] = [(a, b + PAD) for a, b in blocks]
        s["blocks"] = clip(s["raw"], merge((t - IDLE, t + AFTER) for t in s["inputs"]))
        s["name"] = s["title"] or s["ai_title"] or (s["prompts"][0][1][:60] if s["prompts"] else sid[:8])
        out.append(s)
    return sorted(out, key=lambda s: s["raw"][0][0])

def sweep(units):
    """Split each moment evenly across the units live in it; collect gaps."""
    for u in units: u["hours"] = 0.0
    points = sorted({p for u in units for b in u["blocks"] for p in b})
    gaps = []
    for a, b in zip(points, points[1:]):
        live = [u for u in units if any(x <= a and b <= y for x, y in u["blocks"])]
        if not live:
            gaps.append((a, b)); continue
        for u in live: u["hours"] += hrs(a, b) / len(live)
    return gaps

sessions = load_sessions()
for s in sessions: s["key"] = s["id"]

if not GROUPS:
    sweep(sessions)
    print(json.dumps({"date": str(day), "sessions": [{
        "id": s["id"], "project": s["project"], "name": s["name"],
        "blocks": [f"{a:%H:%M}-{b:%H:%M}" for a, b in s["raw"]],
        "hours": r(s["hours"]), "unattended": r(measure(s["raw"]) - measure(s["blocks"])),
        "prompts": s["prompts"][:12]} for s in sessions]}, indent=1))
    sys.exit()

with open(GROUPS) as fh: spec = json.load(fh)
by_id = {s["id"]: s for s in sessions}
units, claimed = [], set()
def unit(key, desc, client, members):
    raw, blocks = merge(b for m in members for b in m["raw"]), merge(b for m in members for b in m["blocks"])
    return {"key": key, "desc": desc, "client": client, "blocks": blocks, "unattended": measure(raw) - measure(blocks)}
for key, g in spec.items():
    for i in g.get("sessions", []):
        if i not in by_id: sys.exit(f"{key}: no session {i} on {day}")
        if i in claimed: sys.exit(f"{key}: session {i} is listed twice")
        claimed.add(i)
    members = [by_id[i] for i in g.get("sessions", [])]
    if members:
        units.append(unit(key, g.get("desc", ""), g.get("client") or re.split(r"[-\s]", key)[0], members))
for s in sessions:
    if s["id"] not in claimed:
        units.append(unit(s["name"][:10], s["name"], "Other", [s]))

gaps = sweep(units)
shown = [u for u in units if u["hours"] >= MIN_LINE_H]
clients = {}
for u in shown: clients[u["client"]] = clients.get(u["client"], 0) + r(u["hours"])
shown.sort(key=lambda u: (-clients[u["client"]], u["client"], -u["hours"]))
total = sum(clients.values())
counted = [b for u in units for b in u["blocks"]]
kw = max([len(u["key"]) for u in shown] + [8])
cw = max([len(c) for c in clients] + [8])

if counted:
    first, last = min(a for a, _ in counted), max(b for _, b in counted)
    print(f"Time Map — {day:%a %b %-d} · {total:.3f} h ({hm(total)}) · {first:%-H:%M}–{last:%-H:%M}\n")
else:
    print(f"Time Map — {day:%a %b %-d} · {total:.3f} h ({hm(total)})\n")
for u in shown:
    print(f" {r(u['hours']):.3f}  {hm(r(u['hours'])):>5}  {u['key']:<{kw}}  {u['desc']}".rstrip())
print(f" ─────\n {total:.3f}  {hm(total):>5}  total\n")
if 1 < len(clients) < len(shown):  # only when some client has two or more lines
    print("By client")
    for c, h in sorted(clients.items(), key=lambda x: -x[1]):
        print(f" {h:.3f}  {hm(h):>5}  {c}")
    print()
big = [(a, b) for a, b in gaps if b - a >= MIN_GAP]
print("Gaps 30 min+" + ("" if big else ":  none"))
for a, b in big:
    print(f" {a:%H:%M}–{b:%H:%M}  {span(a, b):>7}")
skipped = sorted((u for u in units if r(u["unattended"]) >= MIN_NOTE_H), key=lambda u: -u["unattended"])
if skipped:
    print(f"\nNot counted: agent ran {ATTEND:g}+ min past your last input (clock time)")
    for u in skipped:
        print(f" {r(u['unattended']):.3f}  {hm(r(u['unattended'])):>5}  {u['key']}")
