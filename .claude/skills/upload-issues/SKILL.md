---
name: upload-issues
description: Upload issues from a version issues file to GitHub one by one with proper labels and dependencies.
---

# Skill: Upload Version Issues to GitHub

Upload issues from a version issues file to GitHub one by one, with proper labels (prefixed by version) and dependencies.

## Usage

```
/upload-issues <version-issues-file>
```

Example: `/upload-issues @specfication/roadmap/implementation/v1-issues.md`

A version issues file is the fine-grained breakdown of a ROADMAP version (v0–v3): each phase (`vA.B`) in [specfication/ROADMAP.md](../../../specfication/ROADMAP.md) is split into one or more `SILT-xxx` issues. Generate it first with [`/generate-issues v{N}`](../generate-issues/SKILL.md) if it does not exist.

> Note: the spec directory is spelled `specfication/` on disk (a typo kept for consistency) — reference it as-is.

## Instructions

### Step 1: Read the version issues file

Read the provided file (e.g., `specfication/roadmap/implementation/v{N}-issues.md`).

Determine from the file:
- **Version number** (n): from the filename or heading (e.g., `v1-issues.md` -> n = `1`)
- **Label prefix**: `v{n}::` (e.g., `v1::`)

Parse the **Issues Summary Table** to extract for each issue:
- `ID` (e.g., SILT-001)
- `Title`
- `Size` (S, M, L)
- `Area` (the component: `engine`, `evaluator`, `store`, `world`, `api`, `web`, `client`, `tests`)
- `Phase` (the ROADMAP phase it implements, e.g. `v1.2`)
- `Dependencies` (list of SILT-xxx IDs)

Then parse each **detailed issue section** (heading with SILT-xxx) to extract:
- `Description`
- `What needs to be done` (full content)
- `Dependencies`
- `Expected result`
- `Acceptance criteria` (checklist — should align with the phase DoD in ROADMAP.md)

### Step 2: Confirm with user

Show the user a summary of what will be created:
- Number of issues
- Label prefix (e.g., `v1::`)
- Full list of labels that will be created
- Ask for confirmation before proceeding

### Step 3: Create labels (if they don't exist)

All labels MUST be prefixed with `v{n}::` (version number).

Label format: `v{n}::{category}:{value}`

Use `gh` to create these labels if they don't already exist (version titles: v0 — Pure Game of Life (the platform on vanilla Conway); v1 — Parametrized GOL + evolution; v2 — Challenges (research scaffold); v3 — Lenia):

```bash
# Version label
gh label create "v1::version:1" --color "0E8A16" --description "Version v1 — Parametrized GOL + evolution" 2>/dev/null || true

# Size labels
gh label create "v1::size:S" --color "28A745" --description "Small (1-2 days)" 2>/dev/null || true
gh label create "v1::size:M" --color "FFC107" --description "Medium (3-5 days)" 2>/dev/null || true
gh label create "v1::size:L" --color "DC3545" --description "Large (5-8 days)" 2>/dev/null || true

# Area labels (one per component touched in this version)
gh label create "v1::area:engine"    --color "6F42C1" 2>/dev/null || true
gh label create "v1::area:evaluator" --color "1D76DB" 2>/dev/null || true
gh label create "v1::area:store"     --color "0E8A16" 2>/dev/null || true
# ... world / api / web / client / tests as needed
```

### Step 4: Create issues ONE BY ONE

**IMPORTANT:** Issues must be created one at a time, sequentially. After creating each issue:
1. Show the user the result (issue number, URL)
2. Proceed to the next issue immediately (do not wait for confirmation between issues)

For each issue (in order from the summary table):

1. Build the issue body in markdown:

```markdown
## Description
{description from the detailed section}

## What needs to be done
{full content from the detailed section}

## Dependencies
{dependency list, with references to already-created issue numbers}

## Expected result
{expected result from the detailed section}

## Acceptance criteria
{checklist from the detailed section}

---
**ID:** {SILT-xxx}
**Size:** {S/M/L}
**Version:** v{n}
**Area:** {engine/evaluator/store/world/api/web/client/tests}
**Phase:** {vA.B from ROADMAP}
```

2. Create the issue with a single `gh issue create` command (one issue per command, never batch):

```bash
gh issue create \
  --title "SILT-xxx: {title}" \
  --label "v1::version:1,v1::size:{S/M/L},v1::area:{area}" \
  --body "$(cat <<'BODY'
{issue body}
BODY
)"
```

3. Record the mapping: SILT-xxx -> GitHub issue #number

4. Report to user: `Created SILT-xxx -> #{number}: {title}`

5. If the issue has dependencies on already-created issues, add a comment:

```bash
gh issue comment {issue-number} --body "Blocked by #{dep-issue-number} (SILT-xxx)"
```

6. Move to the next issue.

### Step 5: Generate report

After all issues are created, generate a report file at:
`specfication/roadmap/implementation/v{N}-github-report.md`

Content:

```markdown
# Version v{n} -- GitHub Issues Report

**Uploaded:** {date}
**Repository:** {github repo URL}
**Total issues:** {count}

## Issue Mapping

| SILT ID | GitHub # | Title | Phase | Labels | URL |
|---------|----------|-------|-------|--------|-----|
| SILT-001 | #5 | Engine: vanilla Conway | v0.1 | v0::version:0, v0::size:S, v0::area:engine | {url} |
| ... | ... | ... | ... | ... | ... |

## Labels Created

- v{n}::version:{n}
- v{n}::size:S, v{n}::size:M, v{n}::size:L
- v{n}::area:{list}
```

### Step 6: Report to user

Show the user:
- Total issues created
- Link to the GitHub issues page
- Path to the generated report file

## Error Handling

- If `gh` is not authenticated, tell the user to run `gh auth login`
- If the repo has no GitHub remote yet, tell the user to create one (`gh repo create`) before uploading
- If an issue already exists with the same title, skip it and note in the report
- If label creation fails, continue (labels may already exist)
- On any failure, report what was created so far and what remains
