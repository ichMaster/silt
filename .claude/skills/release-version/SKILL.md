---
name: release-version
description: Bump project version, update pyproject.toml + version files, add RELEASE.txt entry, commit, tag, and push.
---

# Skill: Release Version

Bump the project version, update all version references, write release notes, commit, tag, and push.

This is the standalone counterpart to the inline release steps in `/execute-issues` (Step 3b) — use
it when releasing a phase independently of an issue run, or to re-cut/fix a release.

## Usage

```
/release-version <version> [changelog line 1; changelog line 2; ...]
```

Examples:
- `/release-version 0.1.0` -- bump to 0.1.0, prompt for changelog
- `/release-version 0.1.0 Engine: vanilla Conway B3/S23; Pin determinism contract tests` -- bump with provided changelog items

If no changelog items are provided, analyze uncommitted or recent commits since the last tag to auto-generate the changelog.

Version notation `A.B.C`: `A` = roadmap version (v0→0, v1→1, v2→2, v3→3), `B` = phase within that version (`v0.1`→B=1), `C` = post-release fix on that phase. So roadmap phase `vA.B` → semver `A.B.0`; a fix after it bumps `C` (e.g. v0.3 → `0.3.0`, a follow-up fix → `0.3.1`; v1.1 → `1.1.0`). Releases are cut per phase. **Never change the version without explicit user confirmation.**

## Instructions

### Step 0: Parse arguments

1. Extract the target version from the first argument (e.g., `0.1.0`)
2. Remaining arguments (separated by `;`) become changelog bullet points
3. Validate version format matches `X.Y.Z` (semver)

### Step 1: Verify prerequisites

1. Confirm we are on the expected branch (usually `main`)
2. Confirm working tree is clean (`git status`) -- if dirty, ask the user whether to include uncommitted changes
3. Find the current version: read `version` in `pyproject.toml` (the authoritative source), falling back to `VERSION`, `RELEASE.txt`, or the latest git tag
4. Verify the new version is greater than the current version

### Step 2: Generate changelog (if not provided)

If no changelog items were given as arguments:

1. Find the most recent version tag: `git describe --tags --abbrev=0` (none yet for the first release — use the full history instead)
2. Collect commits since that tag: `git log --oneline <tag>..HEAD`
3. Summarize the changes into concise bullet points (group related commits; reference the Silt phase `vA.B` and any `SILT-xxx` issues where relevant)
4. Show the generated changelog to the user and ask for confirmation

### Step 3: Update version files

Update the version string in these files:

1. **`pyproject.toml`** (authoritative): set `version = "<version>"`
2. **`VERSION`** (only if it already exists): the bare version string, e.g. `0.1.0` — do not create one; `pyproject.toml` is the source of truth
3. **`README.md`** (if it carries a version reference): update it
4. **`RELEASE.txt`** (create if it doesn't exist): prepend a new version block at the top (after the header if any):

   ```
   Version <version> (YYYY-MM-DD)
   ---------------------------
   - <changelog item 1>
   - <changelog item 2>
   - ...
   ```

   Use today's date. Keep the existing entries below unchanged.

### Step 4: Commit

Stage only the version-related files:

```bash
git add pyproject.toml VERSION README.md RELEASE.txt
```

(`git add` silently ignores paths that don't exist, so this is safe when `VERSION` is absent.)

Commit with message:

```bash
git commit -m "$(cat <<'EOF'
Release v<version>

<1-2 sentence summary of what this release includes>

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Step 5: Tag

Create an annotated tag:

```bash
git tag -a v<version> -m "<one-line summary of the release>"
```

### Step 6: Push

```bash
git push && git push --tags
```

### Step 7: Report

Print a summary:

```
Released v<version>
  Branch: <branch>
  Commit: <short hash>
  Tag:    v<version>
  Files updated:
    - pyproject.toml
    - VERSION        (if present)
    - README.md      (if changed)
    - RELEASE.txt
```

## Important Rules

- **Never downgrade.** Refuse if the target version is less than or equal to the current version.
- **Clean tree first.** If there are uncommitted changes, ask the user before proceeding.
- **Annotated tags only.** Always use `git tag -a`, never lightweight tags.
- **Don't modify source files.** This skill only touches version metadata (`pyproject.toml`, `VERSION`, `README.md`, `RELEASE.txt`), never `engine`, `evaluator`, `store`, `world`, `api`, `web`, `client`, or `tests` code.
- **Confirm changelog.** If auto-generating changelog from commits, show it to the user before committing.
- **Plain-text release notes.** Keep `RELEASE.txt` plain text.
- **Per-phase releases, build-order honored.** Cut one release per ROADMAP phase; don't bump across versions that aren't built yet (no v1 release until the genome exists, no v3 until Lenia).
