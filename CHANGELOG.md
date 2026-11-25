# Changelog

## 1.1.0 - 2026-11-25

### Changed

- The map no longer prints the `‖` overlap column. Running sessions in parallel is normal, so the column was mostly noise. Parallel time is still split evenly, and the lines still add up to the total.
- Gaps are listed one per line, each with its length.
- Agent work more than 15 minutes after your last input no longer counts as billable time. It's listed under "Not counted", and that stretch shows up as a gap. `--attended MIN` changes the 15 minutes. Headless runs (`claude -p`, the SDK) never count. This lowers the hours on days with long agent runs.

### Added

- Every hour figure now has h:mm next to it.
- "By client" subtotals, from an optional `client` field in the groups file. Without the field, the client is the key's first word.

## 1.0.1 - 2026-10-14

### Fixed

- Days on the other side of a daylight saving change from today now start and end at local midnight, and change days count their full 23 or 25 hours. Before, the day was shifted by an hour and always 24 hours long.
- A groups file that lists an unknown session ID, or the same session in two groups, now stops with an error naming the session. Before, a mistyped ID put that session's hours on a line of its own instead of its group's, and a duplicate split its hours between both groups, with no warning either way.

## 1.0.0 - 2026-10-05

Initial release.
