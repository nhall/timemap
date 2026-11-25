# timemap

A Claude Code skill that turns a day of Claude Code sessions into a **Time Map** for time tracking: hours per ticket and client, and the gaps where you weren't working with Claude.

```
Time Map — Wed Oct 1 · 5.750 h (5:45) · 8:52–17:31

 2.375   2:23  WEB-123   Checkout form validation + tests
 0.600   0:36  WEB-130   Cache headers on staging
 1.850   1:51  ABC-25    Responsive nav fixes + ticket update
 0.925   0:56  Admin     Shell and editor setup
 ─────
 5.750   5:45  total

By client
 2.975   2:59  WEB
 1.850   1:51  ABC
 0.925   0:56  Admin

Gaps 30 min+
 12:05–12:50      45m
 15:10–15:45      35m

Not counted: agent ran 15+ min past your last input (clock time)
 0.800   0:48  WEB-130
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
2. Only time near your own input counts: from 15 minutes before each prompt, slash command, interrupt or answer to Claude's question, to 15 minutes after it. An agent that keeps working long after your last input isn't billed. That time is listed under "Not counted" instead, and shows up as a gap you can fill in unless another session was counting then. "Not counted" is the clock time the agent ran on its own, not a share of parallel time, so it can be more than the hours a line lost. Headless runs (`claude -p`, the SDK) never count.
3. Claude reads each session's title, repo and prompts, and groups sessions by ticket ID (`ABC-25`). Work with no ticket gets a short project name, and setup or tooling work goes under `Admin`. Each line also gets a client, for the "By client" subtotals.
4. The script renders the map:
   - Hours are rounded to 0.025 h (90 seconds), with h:mm alongside. The decimals are the real figures; an h:mm can be a minute off from the sum of the lines above it.
   - Time when sessions run in parallel is split evenly between them, so the lines add up to the total.
   - Lines under 5 minutes, "Not counted" entries under 0.1 h and gaps under 30 minutes are left out. "By client" appears only when a client has two or more lines.

Permission prompts you approve aren't recorded in the transcript, so a stretch where you only approved tool calls counts as unattended.

Claude only does the grouping. Every number comes from the script, so the totals don't drift between runs.

Everything stays on your machine. The script reads local transcript files and prints to the terminal.

## Running the script directly

```sh
python3 skills/timemap/timemap.py yesterday                       # sessions as JSON
python3 skills/timemap/timemap.py yesterday --groups groups.json  # render the map
python3 skills/timemap/timemap.py 2026-10-01 --idle 10            # end stretches after 10 quiet minutes
python3 skills/timemap/timemap.py 2026-10-01 --attended 30        # count agent time up to 30 min after your input
```

`groups.json` maps each line's key to a description, an optional client and its session IDs:

```json
{"ABC-25": {"desc": "Responsive nav fixes", "client": "ABC", "sessions": ["<session id>", "..."]}}
```

The client defaults to the key's first word before `-` or a space. Sessions not in any group get a line of their own under the client `Other`. An unknown or duplicate session ID stops with an error.

## License

MIT
