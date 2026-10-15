# timemap

A Claude Code skill that turns a day of Claude Code sessions into a **Time Map** for time tracking: hours per ticket, overlap between sessions you ran in parallel, and the gaps where Claude wasn't in use.

```
Time Map — Wed Oct 1 · 6.450 h · 8:52–17:31

 2.375  WEB-123   Checkout form validation + tests      ‖ ABC-25 0.400
 1.850  ABC-25    Responsive nav fixes + ticket update   ‖ WEB-123 0.400
 1.300  API       Rate-limit middleware refactor
 0.925  Admin     Shell and editor setup
 ─────
 6.450

Gaps 30 min+:  12:05–12:50 · 15:10–15:45
```

## Install

```sh
claude plugin marketplace add nhall/timemap
claude plugin install timemap@timemap
```

Then ask Claude "how did I spend yesterday?", or run `/timemap:timemap` with `yesterday` (the default), `today` or a date (`2026-10-01`).

Requires Python 3 (the one that ships with macOS works).

## How it works

1. A bundled script reads your session transcripts in `~/.claude/projects/` and finds each session's active stretches on that day. A quiet stretch of 15 minutes ends a stretch.
2. Claude reads each session's title, repo and prompts, and groups sessions by ticket ID (`ABC-25`). Work with no ticket gets a short project name, and setup or tooling work goes under `Admin`.
3. The script renders the map:
   - Hours are rounded to 0.025 h (90 seconds).
   - Time when two sessions overlap is split evenly between them, and the `‖` column shows who each line overlapped with.
   - Lines under 5 minutes, overlaps under 0.1 h and gaps under 30 minutes are left out.

Claude only does the grouping. Every number comes from the script, so the totals don't drift between runs.

Everything stays on your machine. The script reads local transcript files and prints to the terminal.

## Running the script directly

```sh
python3 skills/timemap/timemap.py yesterday                       # sessions as JSON
python3 skills/timemap/timemap.py yesterday --groups groups.json  # render the map
python3 skills/timemap/timemap.py 2026-10-01 --idle 10            # end stretches after 10 quiet minutes
```

`groups.json` maps each line's key to a description and its session IDs:

```json
{"ABC-25": {"desc": "Responsive nav fixes", "sessions": ["<session id>", "..."]}}
```

Sessions not in any group get a line of their own. An unknown or duplicate session ID stops with an error.

## License

MIT
