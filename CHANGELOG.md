# Changelog

## Unreleased

### Changed

- The map no longer prints the `‖` overlap column. Running sessions in parallel is normal, so the column was mostly noise. Parallel time is still split evenly, and the lines still add up to the total.
- Each gap now shows its length, such as `11:18–12:11 (53m)`.

## 1.0.1 - 2026-10-14

### Fixed

- Days on the other side of a daylight saving change from today now start and end at local midnight, and change days count their full 23 or 25 hours. Before, the day was shifted by an hour and always 24 hours long.
- A groups file that lists an unknown session ID, or the same session in two groups, now stops with an error naming the session. Before, a mistyped ID put that session's hours on a line of its own instead of its group's, and a duplicate split its hours between both groups, with no warning either way.

## 1.0.0 - 2026-10-05

Initial release.
