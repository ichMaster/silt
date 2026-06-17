# Version v0 — GitHub Issues Report

**Uploaded:** 2026-06-15 (phase v0.1) · 2026-06-17 (phase v0.2)
**Repository:** https://github.com/ichMaster/silt
**Total issues:** 8

## Issue Mapping

| SILT ID | GitHub # | Title | Phase | Labels | URL |
|---------|----------|-------|-------|--------|-----|
| SILT-001 | #1 | Project skeleton + engine package + tooling | v0.1 | v0::version:0, v0::size:S, v0::area:engine | https://github.com/ichMaster/silt/issues/1 |
| SILT-002 | #2 | Conway `step()` over a toroidal binary grid | v0.1 | v0::version:0, v0::size:M, v0::area:engine | https://github.com/ichMaster/silt/issues/2 |
| SILT-003 | #3 | Named seed patterns + placement | v0.1 | v0::version:0, v0::size:S, v0::area:engine | https://github.com/ichMaster/silt/issues/3 |
| SILT-004 | #4 | World record shapes — `Event` / `Organism` / `World` | v0.2 | v0::version:0, v0::size:S, v0::area:world | https://github.com/ichMaster/silt/issues/4 |
| SILT-005 | #5 | Organism tracking via connected components | v0.2 | v0::version:0, v0::size:M, v0::area:world | https://github.com/ichMaster/silt/issues/5 |
| SILT-006 | #6 | `Store` interface + SQLite/blob backend | v0.2 | v0::version:0, v0::size:M, v0::area:store | https://github.com/ichMaster/silt/issues/6 |
| SILT-007 | #7 | Replay — reconstruct any tick from snapshot + event log | v0.2 | v0::version:0, v0::size:M, v0::area:store | https://github.com/ichMaster/silt/issues/7 |
| SILT-008 | #8 | Minimal display metrics + observe/history payload | v0.2 | v0::version:0, v0::size:S, v0::area:evaluator | https://github.com/ichMaster/silt/issues/8 |

## Dependencies

- SILT-002 (#2) blocked by SILT-001 (#1)
- SILT-003 (#3) blocked by SILT-002 (#2)
- SILT-004 (#4) blocked by SILT-003 (#3)
- SILT-005 (#5) blocked by SILT-004 (#4)
- SILT-006 (#6) blocked by SILT-004 (#4)
- SILT-007 (#7) blocked by SILT-006 (#6) and SILT-005 (#5)
- SILT-008 (#8) blocked by SILT-005 (#5) and SILT-007 (#7)

## Labels Created

- v0::version:0
- v0::size:S, v0::size:M
- v0::area:engine (v0.1)
- v0::area:world, v0::area:store, v0::area:evaluator (v0.2)

## Upload History

- **2026-06-15 — phase v0.1:** SILT-001…003 (#1–#3, all since closed via `/execute-issues`).
- **2026-06-17 — phase v0.2:** SILT-004…008 (#4–#8, open). SILT-001…003 already existed and were skipped; area labels `world`, `store`, `evaluator` created.

> Phases v0.3–v0.5 are not yet generated. When appended to `v0-issues.md`, re-run `/upload-issues`
> to add the remaining issues; `SILT-xxx` numbering continues from SILT-008 and new area labels
> (`api`, `web`, `client`, `tests`) will be created as those phases land.
