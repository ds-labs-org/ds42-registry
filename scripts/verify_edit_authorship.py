#!/usr/bin/env python3
"""Decide whether a PR's *edits* to existing entries/**/*.yaml files are
self-service-eligible, i.e. whether every line the PR removes or changes
was itself originally authored by the same person opening this PR.

Usage: verify_edit_authorship.py <base_ref> <head_ref> <owner/repo> <file> [<file> ...]

Exit 0 (all changed files are author-cleared) or 1 (at least one is not,
or authorship couldn't be resolved). Prints one line per file.

Authorship is NOT taken from anything inside the YAML file (e.g. a
self-declared `registered_by` field would be trivially spoofable in a
hand-crafted PR). It is derived from real git history plus GitHub's own
commit-to-account resolution:

  1. For each changed file, find the base-side line ranges the PR removes
     or changes (git diff hunk headers) — pure line *additions* need no
     check, there is no prior author to compare against.
  2. `git blame` those base-side ranges against <base_ref> to find which
     commit(s) originally introduced those lines.
  3. Resolve each such commit's GitHub-verified author login via
     `gh api repos/<owner/repo>/commits/<sha>` (`.author.login` — GitHub
     sets this only when the commit's email matches a *verified* email on
     a real GitHub account; unset otherwise).
  4. Resolve the PR's own touching commit(s) for that file the same way.
  5. The file is cleared only if every one of (2)'s resolved logins is
     non-null and equals every one of (4)'s resolved logins.

Note: every commit made through this registry's own wizard flow
(site/src/authority_registration.rs, via GitHub's Contents API with no
custom author/committer set) is created *by* GitHub itself on behalf of
the authenticated user, so it is both correctly attributed and shown as
"Verified" in GitHub's UI — this check's account resolution lines up with
that for free. A hand-authored PR (plain `git commit`) is only cleared if
its commits' author email matches a verified email on the PR-opener's own
GitHub account.
"""
import re
import subprocess
import sys
from functools import lru_cache

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return result.stdout


def removed_or_changed_ranges(base_ref: str, head_ref: str, path: str) -> list[tuple[int, int]]:
    """Base-side (start, end) 1-indexed line ranges this diff touches."""
    diff = subprocess.run(
        ["git", "diff", "--unified=0", f"{base_ref}...{head_ref}", "--", path],
        capture_output=True, text=True, check=True,
    ).stdout
    ranges = []
    for line in diff.splitlines():
        m = HUNK_RE.match(line)
        if not m:
            continue
        start = int(m.group(1))
        count = int(m.group(2)) if m.group(2) is not None else 1
        if count > 0:
            ranges.append((start, start + count - 1))
    return ranges


def blame_shas(base_ref: str, path: str, start: int, end: int) -> set[str]:
    out = run("git", "blame", "-l", base_ref, "-L", f"{start},{end}", "--", path)
    return {line.split()[0].lstrip("^") for line in out.splitlines() if line.strip()}


def touching_commits(base_ref: str, head_ref: str, path: str) -> set[str]:
    out = run("git", "log", "--format=%H", f"{base_ref}..{head_ref}", "--", path)
    return {sha for sha in out.splitlines() if sha.strip()}


@lru_cache(maxsize=None)
def resolved_author_login(repo: str, sha: str) -> str | None:
    try:
        out = run("gh", "api", f"repos/{repo}/commits/{sha}", "--jq", ".author.login // \"\"")
    except subprocess.CalledProcessError:
        return None
    login = out.strip()
    return login or None


def main() -> int:
    if len(sys.argv) < 5:
        print(__doc__)
        return 2
    base_ref, head_ref, repo = sys.argv[1], sys.argv[2], sys.argv[3]
    files = sys.argv[4:]

    any_failed = False
    for path in files:
        base_shas: set[str] = set()
        for start, end in removed_or_changed_ranges(base_ref, head_ref, path):
            base_shas |= blame_shas(base_ref, path, start, end)

        if not base_shas:
            print(f"OK {path}: edit adds lines only, nothing removed/changed to verify")
            continue

        pr_shas = touching_commits(base_ref, head_ref, path)
        if not pr_shas:
            print(f"FAIL {path}: no commit in this PR range touches it (unexpected)")
            any_failed = True
            continue

        original_logins = {resolved_author_login(repo, sha) for sha in base_shas}
        pr_logins = {resolved_author_login(repo, sha) for sha in pr_shas}

        if None in original_logins:
            print(f"FAIL {path}: an original line's commit author is not a verified GitHub profile")
            any_failed = True
            continue
        if None in pr_logins:
            print(f"FAIL {path}: this PR's commit author is not a verified GitHub profile")
            any_failed = True
            continue
        if original_logins != pr_logins:
            print(
                f"FAIL {path}: original author(s) {sorted(original_logins)} "
                f"!= this PR's author(s) {sorted(pr_logins)}"
            )
            any_failed = True
            continue

        print(f"OK {path}: edit author matches original author ({sorted(pr_logins)[0]})")

    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
