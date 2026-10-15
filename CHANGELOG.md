# Changelog

## 1.0.1 - 2026-10-14

### Fixed

- Days on the other side of a daylight saving change from today now start and end at local midnight, and change days count their full 23 or 25 hours. Before, the day was shifted by an hour and always 24 hours long.
- A groups file that lists an unknown session ID, or the same session in two groups, now stops with an error naming the session. Before, a mistyped ID put that session's hours on a line of its own instead of its group's, and a duplicate split its hours between both groups, with no warning either way.

## 1.0.0 - 2026-10-05

Initial release.
