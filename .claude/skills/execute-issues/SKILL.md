---
name: execute-issues
description: Execute GitHub issues for a version sequentially - implement, validate, commit, push, and generate a report.
---

# Skill: Execute GitHub Issues

Execute GitHub issues for a version sequentially: implement, validate, commit, push, and generate a report.

## Usage

```
/execute-issues <label> [--issue SILT-xxx] [--dry-run]
```

The `<label>` is the GitHub version label exactly as it appears (e.g., `v1::version:1`).

- `/execute-issues v1::version:1` -- execute all issues labeled `v1::version:1`
- `/execute-issues v1::version:1 --issue SILT-003` -- execute a single issue from that version
- `/execute-issues v1::version:1 --dry-run` -- show execution plan without making changes

> Note: the spec directory is spelled `specfication/` on disk (a typo kept for consistency) — reference it as-is.

## Instructions

### Step 0: Verify prerequisites

1. Confirm we are on the expected branch (e.g., `main` or the user's working branch)
2. Confirm working tree is clean (`git status`)
3. Confirm `gh` is authenticated
4. Parse the label to determine version:
   - Label `v1::version:1` -> version `n=1`
5. Fetch issues from GitHub:
   ```bash
   gh issue list --label "{label}" --state open --limit 100
   ```
6. Read the version issues file for detailed descriptions: `specfication/roadmap/implementation/v{n}-issues.md`
7. If a GitHub report exists (`specfication/roadmap/implementation/v{n}-github-report.md`), read the SILT-to-GitHub# mapping
8. Read [specfication/ROADMAP.md](../../../specfication/ROADMAP.md) for the version goal and the phase (`vA.B`) DoD, [specfication/ARCHITECTURE.md](../../../specfication/ARCHITECTURE.md) for the contracts the issue must honor (the `step()` seam, the genome, `Metrics`, the event log, the determinism invariant, the REST/WS API), and [specfication/MISSION.md](../../../specfication/MISSION.md) for the principles

### Step 1: Build execution queue

From the GitHub issue list, build an ordered queue based on dependencies:
- Parse SILT-xxx IDs from issue titles (format: `SILT-xxx: {title}`)
- Determine dependency order from the version issues file dependency tree
- Issues with no unmet dependencies go first
- Skip issues already closed on GitHub
- If `--issue SILT-xxx` is specified, execute only that issue (but verify its dependencies are closed)

Show the user the execution plan and ask for confirmation.

### Step 2: Execute each issue (loop)

For each issue in the queue:

#### 2a. Assign and announce

Print: `--- Starting SILT-xxx: {title} ---`

#### 2b. Read issue details

Read the full issue description from the version issues file (the detailed section for this SILT-xxx).

#### 2c. Implement

Execute the tasks described in the issue. Follow the project conventions in `CLAUDE.md` and the principles in `specfication/MISSION.md`. **The central invariant: nothing outside `step()` and the genome may know which automaton runs inside** — write everything else substrate-agnostically. Route by component:

- **Engine** (`/engine`): `step(field, genome) -> field` and the genetic operations `mutate`/`cross`. Vanilla Conway (v0, fixed rule, no genome), the parametrized `GolGenome` (v1+), then the Lenia genome (v3) — all behind the **same `step()` seam**. Pure, headless, numpy; deterministic under a seeded RNG (pin FFT/precision mode for Lenia).
- **Evaluator** (`/evaluator`): `evaluate(history) -> Metrics`, `predict` (hit/miss), and the v2 classifier — **pure functions over a recorded run**, substrate-agnostic. The model/UI never compute metrics.
- **Store** (`/store`): the `Store` interface + SQLite/blob backend — periodic snapshots + an append-only event log + replay. Reconstruct any tick exactly.
- **World** (`/world`): world state, organisms (connected components), lineage, and the **tick loop** with an **injected clock**. Actions apply as timestamped events at tick boundaries; weak natural pressure is part of the deterministic `step`, never a random cull.
- **API** (`/api`): FastAPI — REST actions/queries + `WS /stream`; auth (gardener id + token; equal capabilities; isolates identity, not the shared field). Лілі connects over REST + WS — **no bespoke TCP server**.
- **Web** (`/web`): the static canvas/WebGL UI (render → act → inspect → feed). Binary canvas in v0–v2; float WebGL in v3.
- **Client** (`/client`): the thin client library — the tools (`seed, mutate, cross, observe, cull, set_goal`, `predict`) + `events_since`. **No Silt module may import Lumi** (the boundary is hard; pin it with a test).
- **Contract changes:** any change to a stable seam (the `step()` signature, the genome type, the `Metrics` set, the `Event`/`Organism`/`World` shapes, the determinism invariant `pure(seed, initial_field, event_log)`, or the REST/WS API) updates `specfication/ARCHITECTURE.md` **AND** its contract test, in the same commit.
- Follow existing code style and patterns; keep each version self-contained (don't pull later-version concerns in early — "simplicity first"; no genome before v1, no Lenia/WebGL before v3).

#### 2d. Validate

Run validation checks (Python only — Silt is **pure simulation: no model, no paid APIs, no live network anywhere**, so tests are hermetic by construction):

1. **Unit + contract tests:** `pytest` for the changed packages — including the **determinism contract tests**: engine field pinned exactly after K ticks from a fixed `(seed, genome)`; every metric pinned against fixed recorded runs; `mutate`/`cross` reproducible under a seeded RNG.
2. **Replay / integration:** the relevant end-to-end test — **replay-equivalence** (snapshot + event log reconstructs the exact world state on a frozen clock), action events applying at tick boundaries, and the REST/WS contract.
3. **Lint:** `ruff check {changed paths}`
4. **Syntax/import (Python):** `python3 -m py_compile {changed_py_files}` and an import check for changed modules
5. **Contract consistency:** verify the `step()`/genome/`Metrics`/event-log/API seams match ARCHITECTURE.md and their contract tests; verify **no Silt module imports Lumi**
6. **Acceptance criteria:** go through each criterion from the issue and verify against the phase DoD in ROADMAP.md

Record pass/fail for each check. **Tests are part of the work** — a feature lands with the tests that encode its acceptance (see ARCHITECTURE §Testing and CI).

#### 2e. Commit

```bash
git add {specific files created/modified}
git commit -m "$(cat <<'EOF'
SILT-xxx: {title}

{1-2 sentence summary of what was implemented}

Closes #{github-issue-number}

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

#### 2f. Push

```bash
git push
```

#### 2g. Close issue with summary

```bash
gh issue close {issue-number} --comment "$(cat <<'EOF'
## Implementation Summary

**Commit:** {commit-hash}
**Files changed:** {count}

### What was done
{bullet list of key changes}

### Validation
{pass/fail status for each check}

### Acceptance criteria
{checklist with pass/fail}
EOF
)"
```

#### 2h. Log progress

Append to the in-memory execution log:
- Issue ID, title
- Commit hash
- Files changed (list)
- Validation results (including test pass/fail)
- Status: success/partial/failed

### Step 3: Handle failures

If implementation or validation fails for an issue:

1. Do NOT commit broken code
2. Stash or revert changes: `git checkout -- .`
3. Add a comment to the GitHub issue explaining what failed
4. Log the failure
5. Ask the user: continue to next issue (if no dependency), or stop?

### Step 3b: Version bump on completion

**Do NOT bump the version automatically.** Never change the version (VERSION file, RELEASE.txt, or git tag) without explicit user confirmation. When a phase/version's issues are all done, report completion and let the user decide whether/when to release.

If — and only if — the user confirms a release:

1. Determine the target semver from the version notation `A.B.C` (`A` = roadmap version v0→0…v3→3, `B` = phase, `C` = post-release fix). Roadmap phase `vA.B` → semver `A.B.0` (e.g. v1.1 → `1.1.0`).
2. Update `VERSION` and `README.md` with the new version if present.
3. Update or create `RELEASE.txt` -- prepend a new version entry:

```
Version {version} ({YYYY-MM-DD})
---------------------------
- {SILT-xxx title}: {1-sentence summary of what was implemented}
- {SILT-xxx title}: {1-sentence summary}
...
```

4. Commit the version bump:

```bash
git add VERSION README.md RELEASE.txt
git commit -m "$(cat <<'EOF'
Release v{version} -- Silt {vN} phase complete

All {count} issues implemented and validated.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

5. Tag the release:

```bash
git tag -a v{version} -m "{version summary from ROADMAP}"
```

6. Report to user: `version bumped to {version}, tagged v{version}`

If some issues failed or were skipped, do NOT bump the version. Note in the execution report that the version is incomplete.

### Step 4: Generate execution report

After all issues are processed (or on stop), generate:
`specfication/roadmap/implementation/v{n}-execution-report.md`

```markdown
# Version v{n} -- Execution Report

**Date:** {date}
**Branch:** {branch name}
**Label:** {label}
**Target version:** {version}
**Executed by:** Claude Code

## Summary

| Status | Count |
|--------|-------|
| Completed | {n} |
| Failed | {n} |
| Skipped | {n} |
| Remaining | {n} |

## Issues

| # | SILT ID | Title | Phase | Status | Commit | Files | Tests |
|---|---------|-------|-------|--------|--------|-------|-------|
| 1 | SILT-001 | Engine: vanilla Conway | v0.1 | completed | a1b2c3d | 4 | pass |
| ... | ... | ... | ... | ... | ... | ... | ... |

## Detailed Results

### SILT-001: Engine: vanilla Conway

**Status:** completed
**Commit:** a1b2c3d
**Files changed:**
- `engine/...` (added)

**Validation:**
- [x] Unit + contract tests (incl. determinism pin): pass
- [x] Lint (ruff): pass
- [x] Acceptance criteria: all pass

---

### SILT-002: ...

## Next Steps

{List of remaining issues not yet executed, with their dependencies}
```

Commit and push this report:

```bash
git add specfication/roadmap/implementation/v{n}-execution-report.md
git commit -m "$(cat <<'EOF'
Add v{n} execution report

{n} issues completed, {n} failed, {n} remaining.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
git push
```

## Important Rules

- **One issue at a time.** Never work on multiple issues simultaneously.
- **Dependency order.** Never start an issue whose dependencies are not closed.
- **Clean commits.** Each issue = one commit. No mixing work across issues.
- **No broken code.** Only commit code that passes validation (tests + ruff included).
- **Tests ship with the feature.** Every issue lands with the tests that encode its acceptance — no "tests later."
- **The engine seam is sacred.** Nothing outside `step()` and the genome knows which automaton runs inside; write everything else substrate-agnostically so the Lenia swap (v3) touches nothing else.
- **Determinism is non-negotiable.** The world is a pure function of `(seed, initial_field, ordered_event_log)`; actions apply at tick boundaries; weak natural pressure is part of the deterministic `step`. Pin it with tests (engine state, metrics, replay equivalence).
- **Clean boundary with Lumi.** No Silt module imports Lumi; no Lumi state leaks into Silt. Pin it with a test.
- **Pure simulation.** No model, no paid APIs, no randomness outside the seeded RNG anywhere — CI is hermetic by construction.
- **Contracts stay stable.** A seam change updates ARCHITECTURE.md and its contract test in the same commit.
- **Ask on ambiguity.** If an issue description is unclear, ask the user rather than guessing.
- **Progress updates.** Print a short status line after each issue completes.
