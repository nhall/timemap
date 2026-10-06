---
name: timemap
description: Build a Time Map of how a calendar day was spent across Claude Code sessions — hours per ticket rounded to 0.025, overlap between parallel sessions, and gaps with no Claude activity — for time tracking. Use when the user runs /timemap or asks how their day/yesterday was spent across sessions.
argument-hint: "[yesterday|today|YYYY-MM-DD]"
---

# Time Map

Argument: `yesterday` (default), `today`, or a date. Convert anything else ("last friday") to `YYYY-MM-DD` using today's date. Always cover the whole calendar day.

## 1. List the sessions

```bash
python3 <skill base directory>/timemap.py <day>
```

Prints JSON: each session's `id`, `project` (repo folder), `name` (session title), active `blocks`, `hours`, and the user's `prompts`.

## 2. Group by ticket

Read each session's name, project and prompts and assign it to one line:

- **Key** = the ticket ID (`ABC-25`, `WEB-123`, `OPS-1328`) from the title, branch/worktree name, or prompts. Sessions on the same ticket share a key.
- Repo work with no ticket gets a short project key (`Web`, `API`).
- Machine setup, tooling, shell/package-manager fixes, and meta work like this time tracking go under `Admin`.
- **desc** = what was actually done, from the prompts, ≤ ~50 chars (`Contact form fix on staging`), not just the session title.

Assign every session, including tiny ones. The script drops lines under 5 minutes itself.

Write the groups to a file in the scratchpad:

```json
{"ABC-25": {"desc": "Responsive nav fixes + ticket update", "sessions": ["<id>", "..."]}}
```

## 3. Render

```bash
python3 <skill base directory>/timemap.py <day> --groups <groups.json>
```

Show the output verbatim in a code block. Do not recompute, round, or edit any number. The script handles the 0.025 rounding, splits overlapping time evenly, and filters: lines under 5 min are dropped, overlaps under 0.1 h hidden, gaps under 30 min hidden.

After the block, add at most one line for anything ambiguous, such as a session you couldn't place or a grouping call the user may want to change. Don't label gaps; the user fills those in.
