---
name: generate-issues
description: Derive a fine-grained issues file (SILT-xxx) for a ROADMAP version from its phases (Goal / Tasks / DoD / Tests).
---

# Skill: Generate Version Issues

Split a ROADMAP version into a fine-grained issues file — the input that [`/upload-issues`](../upload-issues/SKILL.md) pushes to GitHub and [`/execute-issues`](../execute-issues/SKILL.md) implements.

## Usage

```
/generate-issues <version>
```

Example: `/generate-issues v1`

The `<version>` is a ROADMAP version: `v0` (pure-Conway platform), `v1` (parametrized GOL + evolution), `v2` (challenges), or `v3` (Lenia). The skill reads that version's phases from [specfication/ROADMAP.md](../../../specfication/ROADMAP.md) and writes `specfication/roadmap/implementation/v{N}-issues.md`.

> Note: the spec directory is spelled `specfication/` on disk (a typo kept for consistency) — reference it as-is.

## Instructions

### Step 1: Read the sources of truth

- [specfication/ROADMAP.md](../../../specfication/ROADMAP.md) — the version's phases (`vA.B`), each with **Goal / Tasks / DoD / Tests**. These are the raw material; each phase becomes one or more issues.
- [specfication/ARCHITECTURE.md](../../../specfication/ARCHITECTURE.md) — the five components, the `step()` seam, the genome/metrics/event-log/API contracts, and the repo layout (the **Area** values).
- [specfication/MISSION.md](../../../specfication/MISSION.md) — the principles and non-goals each issue must respect.
- Any existing `specfication/roadmap/implementation/v*-issues.md` — to continue the global `SILT-xxx` numbering (do not restart it per version).

### Step 2: Decide the issue breakdown

For each phase `vA.B` in the version:

- Split its **Tasks** into **one or more issues** — usually one issue per task or per cohesive unit of work. A small phase may be a single issue; a large phase (e.g. the web UI) splits along its layers (render / act / inspect / feed).
- Assign each issue:
  - **ID** — the next `SILT-xxx` (zero-padded, global, continuing from the highest existing across all version issue files).
  - **Title** — short, imperative.
  - **Size** — `S` (1–2 days), `M` (3–5 days), `L` (5–8 days).
  - **Area** — the component it touches: `engine`, `evaluator`, `store`, `world`, `api`, `web`, `client`, `tests` (from the ARCHITECTURE layout).
  - **Phase** — the `vA.B` it implements.
  - **Dependencies** — other `SILT-xxx` it needs closed first. Respect the build order: within a version later phases depend on earlier ones; the first phase of a version depends on the last of the previous version. Honor the **engine seam** — never let a non-engine issue assume a genome/automaton that does not exist yet (no genome before v1, no Lenia before v3).
- **Acceptance criteria** for each issue must be a checklist that, taken together across the phase's issues, **covers that phase's DoD** in ROADMAP.md, plus the **Tests** the phase requires (tests ship with the feature — see ARCHITECTURE §Testing and CI).

### Step 3: Write the issues file

Write `specfication/roadmap/implementation/v{N}-issues.md` in **exactly** this shape (so `/upload-issues` can parse it):

```markdown
# Version v{N} Issues — {version title}

Derived from [ROADMAP.md](../../ROADMAP.md) §v{N}. Issue prefix `SILT-xxx`; labels `v{N}::…`.

## Issues Summary Table

| ID | Title | Size | Area | Phase | Dependencies |
|----|-------|------|------|-------|--------------|
| SILT-001 | … | S | engine | v0.1 | — |
| SILT-002 | … | M | store | v0.2 | SILT-001 |
| … | … | … | … | … | … |

---

## SILT-001: {title}

### Description
{1–3 sentences: what this issue delivers and why.}

### What needs to be done
{The concrete tasks — bullets drawn from the phase's Tasks, made specific. Name the modules/contracts touched (the `step()` seam, the genome, `Metrics`, the event log, the REST/WS endpoints).}

### Dependencies
{List of SILT-xxx, or "None".}

### Expected result
{The observable outcome — what works after this issue that did not before.}

### Acceptance criteria
- [ ] {criterion aligned to the phase DoD}
- [ ] {determinism / contract criterion where relevant — pinned engine state, replay equivalence, pinned metric, API shape}
- [ ] {the tests that encode this issue's acceptance exist and pass (pytest + ruff)}

---

## SILT-002: {title}
…
```

### Step 4: Report to the user

Show: the version, the number of issues generated, the `SILT-xxx` range used, the per-area counts, and the path to the file. Suggest reviewing it, then running `/upload-issues @specfication/roadmap/implementation/v{N}-issues.md`.

## Rules

- **Cover the DoD, nothing more.** The issues for a version must collectively satisfy that version's phase DoDs — do not pull later-version scope forward (no genome in v0; no Lenia/WebGL until v3).
- **Honor the contracts.** Every issue that touches a seam (the `step()` signature, the genome, `Metrics`, the event log, the REST/WS API, the determinism invariant, the no-Silt→Lumi-import boundary) must say so and must require the matching contract test.
- **Tests are part of each issue**, never a separate "testing issue" tacked on at the end (a dedicated `tests` issue is fine for cross-cutting harness work, but feature issues carry their own tests).
- **Global, stable IDs.** `SILT-xxx` numbers never get reused or renumbered once written; continue from the highest existing.
- **Ask on ambiguity.** If a phase is under-specified for issue splitting, ask rather than invent scope.
