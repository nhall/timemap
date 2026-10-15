#!/usr/bin/env python3
"""Map a calendar day's Claude Code sessions to billable time.

  timemap.py [yesterday|today|YYYY-MM-DD]                 list sessions as JSON
  timemap.py [day] --groups groups.json                   render the Time Map

groups.json: {"ABC-25": {"desc": "Responsive nav fixes", "sessions": ["<id>", ...]}, ...}
Sessions not listed in any group get a line of their own under their session name.
Optional: --idle MIN (default 15) sets how long a quiet stretch ends a block.
"""
import json, sys, glob, os, re
from datetime import datetime, timedelta, date

MIN_LINE_H = 5 / 60     # lines under 5 minutes are dropped
MIN_OVERLAP_H = 0.1     # overlap partners shown only at 0.1 h or more
MIN_GAP = timedelta(minutes=30)
PAD = timedelta(minutes=1)  # credit for a lone prompt/reply
ROOT = os.path.expanduser("~/.claude/projects")

args = sys.argv[1:]
if {"-h", "--help"} & set(args):
    print(__doc__.strip()); sys.exit()
def opt(name, default=None):
    if name not in args: return default
    i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
IDLE = timedelta(minutes=float(opt("--idle", 15)))
GROUPS = opt("--groups")
which = args[0].lower() if args else "yesterday"
day = {"today": date.today(), "yesterday": date.today() - timedelta(days=1)}.get(which) or date.fromisoformat(which)
start = datetime.combine(day, datetime.min.time()).astimezone()  # local offset for that date, not today's
end = datetime.combine(day + timedelta(days=1), datetime.min.time()).astimezone()

r = lambda h: round(round(h / 0.025) * 0.025, 3)
hrs = lambda a, b: (b - a).total_seconds() / 3600

def prompt_text(rec):
    c = rec.get("message", {}).get("content")
    if isinstance(c, list):
        if any(p.get("type") == "tool_result" for p in c): return None
        c = " ".join(p.get("text", "") for p in c if p.get("type") == "text")
    if not isinstance(c, str): return None
    c = re.sub(r"\s+", " ", c).strip()
    if not c or c.startswith(("<", "[Image", "[Request interrupted", "Base directory for this skill")): return None
    return c[:200]

def load_sessions():
    sessions = {}
    for path in glob.glob(f"{ROOT}/*/*.jsonl") + glob.glob(f"{ROOT}/*/*/subagents/*.jsonl"):
        if os.path.getmtime(path) < start.timestamp(): continue
        folder, file = path[len(ROOT) + 1:].split("/")[:2]
        sid = file.removesuffix(".jsonl")
        project = re.sub(r"^-Users-[^-]+(-repos)?-?", "", folder, flags=re.I) or "(root)"
        s = sessions.setdefault(sid, {"id": sid, "project": project, "times": [], "prompts": [],
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
                if t == "user" and "/subagents/" not in path and (p := prompt_text(rec)):
                    s["prompts"].append((when.strftime("%H:%M"), p))
    out = []
    for s in sessions.values():
        if not s["times"]: continue
        blocks = []
        for t in sorted(s["times"]):
            if blocks and t - blocks[-1][1] <= IDLE: blocks[-1][1] = t
            else: blocks.append([t, t])
        s["blocks"] = [(a, b + PAD) for a, b in blocks]
        s["name"] = s["title"] or s["ai_title"] or (s["prompts"][0][1][:60] if s["prompts"] else sid[:8])
        out.append(s)
    return sorted(out, key=lambda s: s["blocks"][0][0])

def sweep(units):
    """Split each moment evenly across the units live in it; collect overlap partners and gaps."""
    for u in units: u["hours"] = 0.0; u["with"] = {}
    points = sorted({p for u in units for b in u["blocks"] for p in b})
    gaps = []
    for a, b in zip(points, points[1:]):
        live = [u for u in units if any(x <= a and b <= y for x, y in u["blocks"])]
        if not live:
            gaps.append((a, b)); continue
        h = hrs(a, b)
        for u in live:
            u["hours"] += h / len(live)
            for o in live:
                if o is not u: u["with"][o["key"]] = u["with"].get(o["key"], 0) + h
    return gaps

sessions = load_sessions()
for s in sessions: s["key"] = s["id"]

if not GROUPS:
    sweep(sessions)
    print(json.dumps({"date": str(day), "sessions": [{
        "id": s["id"], "project": s["project"], "name": s["name"],
        "blocks": [f"{a:%H:%M}-{b:%H:%M}" for a, b in s["blocks"]],
        "hours": r(s["hours"]), "prompts": s["prompts"][:12]} for s in sessions]}, indent=1))
    sys.exit()

with open(GROUPS) as fh: spec = json.load(fh)
by_id = {s["id"]: s for s in sessions}
units, claimed = [], set()
for key, g in spec.items():
    for i in g.get("sessions", []):
        if i not in by_id: sys.exit(f"{key}: no session {i} on {day}")
        if i in claimed: sys.exit(f"{key}: session {i} is listed twice")
        claimed.add(i)
    members = [by_id[i] for i in g.get("sessions", [])]
    if members:
        units.append({"key": key, "desc": g.get("desc", ""), "blocks": [b for m in members for b in m["blocks"]]})
for s in sessions:
    if s["id"] not in claimed:
        units.append({"key": s["name"][:10], "desc": s["name"], "blocks": s["blocks"]})

gaps = sweep(units)
shown = sorted((u for u in units if u["hours"] >= MIN_LINE_H), key=lambda u: -u["hours"])
keys = {u["key"] for u in shown}
total = sum(r(u["hours"]) for u in shown)
first = min(b[0] for u in units for b in u["blocks"])
last = max(b[1] for u in units for b in u["blocks"])
kw = max([len(u["key"]) for u in shown] + [8])
dw = max([len(u["desc"]) for u in shown] + [20])

print(f"Time Map — {day:%a %b %-d} · {total:.3f} h · {first:%-H:%M}–{last:%-H:%M}\n")
for u in shown:
    partners = sorted(((k, h) for k, h in u["with"].items() if k in keys and r(h) >= MIN_OVERLAP_H), key=lambda x: -x[1])
    ovl = "‖ " + ", ".join(f"{k} {r(h):.3f}" for k, h in partners) if partners else ""
    print(f" {r(u['hours']):.3f}  {u['key']:<{kw}}  {u['desc']:<{dw}}  {ovl}".rstrip())
print(f" ─────\n {total:.3f}\n")
big = [(a, b) for a, b in gaps if b - a >= MIN_GAP]
print("Gaps 30 min+:  " + (" · ".join(f"{a:%H:%M}–{b:%H:%M}" for a, b in big) or "none"))
