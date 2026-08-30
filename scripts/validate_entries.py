#!/usr/bin/env python3
"""Validate every changed entries/**/*.yaml file against schema/entry.schema.json,
plus a lightweight reachability probe of the entry's declared URL.

Usage: validate_entries.py <file> [<file> ...]

Skips anything under entries/_examples/ (documentation only, not a real
entry). Fails (non-zero exit) on the first violation found, printing a
clear message per file. Checks, per file:
  - valid YAML, a mapping
  - matches schema/entry.schema.json (required fields, role enum, the
    role-conditional fields — trust_model/claims_issued/onboarding_url for
    authority, endpoint for connector/federation-list/service)
  - role/slug match the file's own path (entries/<role>/<slug>.yaml)
  - no other existing file under entries/<role>/ already uses the same slug
  - reachability probe (see probe_reachable()) of onboarding_url
    (authority) or endpoint (connector/federation-list/service) — this is
    NOT a Dataspace Protocol conformance check, just "does something
    answer at this URL". A real DSP conformance probe is deferred, see
    docs/adr/0010-*.md's Consequences.
"""
import json
import pathlib
import sys
import urllib.error
import urllib.request

import jsonschema
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "entry.schema.json"
PROBE_TIMEOUT_SECONDS = 8


def probe_reachable(url: str) -> tuple[bool, str]:
    """Best-effort liveness probe: did *something* answer at this URL?

    Any HTTP response (even 4xx — the host exists and speaks HTTP) counts
    as reachable. Only a connection failure, DNS failure, timeout, or a
    5xx response counts as unreachable. This is deliberately weak — it is
    not a protocol conformance check, just a sanity check that the
    declared URL isn't dead/fabricated.
    """
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "ds42-registry-ci"})
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT_SECONDS) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        if exc.code >= 500:
            return False, f"server error HTTP {exc.code}"
        return True, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - any network failure is a probe failure
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    files = [pathlib.Path(f) for f in sys.argv[1:]]
    entry_files = [
        f for f in files
        if f.parts[:1] == ("entries",) and "_examples" not in f.parts and f.suffix in (".yaml", ".yml")
    ]
    if not entry_files:
        print("No entries/**/*.yaml files changed (outside entries/_examples/) — nothing to validate.")
        return 0

    schema = json.loads(SCHEMA_PATH.read_text())
    validator = jsonschema.Draft202012Validator(schema)

    any_failed = False
    for path in entry_files:
        if not path.exists():
            # Deleted file — nothing to validate.
            continue

        file_failed = False

        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            print(f"FAIL {path}: not valid YAML: {exc}")
            any_failed = True
            continue

        if not isinstance(data, dict):
            print(f"FAIL {path}: must be a YAML mapping, got {type(data).__name__}")
            any_failed = True
            continue

        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        for err in errors:
            loc = "/".join(str(p) for p in err.path) or "<root>"
            print(f"FAIL {path}: {loc}: {err.message}")
        if errors:
            any_failed = True
            continue

        # Path must match role/slug declared inside the file.
        expected_role, expected_name = path.parts[1], path.stem
        if data.get("role") != expected_role:
            print(f"FAIL {path}: role '{data.get('role')}' does not match its directory 'entries/{expected_role}/'")
            file_failed = True
        if data.get("slug") != expected_name:
            print(f"FAIL {path}: slug '{data.get('slug')}' does not match its file name '{expected_name}'")
            file_failed = True
        if file_failed:
            any_failed = True
            continue

        # Slug collision check within the same role directory.
        role_dir = REPO_ROOT / "entries" / expected_role
        if role_dir.is_dir():
            for other in role_dir.glob("*.y*ml"):
                if other.resolve() == path.resolve():
                    continue
                try:
                    other_data = yaml.safe_load(other.read_text())
                except yaml.YAMLError:
                    continue
                if isinstance(other_data, dict) and other_data.get("slug") == data.get("slug"):
                    print(f"FAIL {path}: slug '{data.get('slug')}' already used by {other}")
                    file_failed = True

        # Reachability probe: onboarding_url for authority, endpoint for
        # the other three roles (schema already guarantees one of these
        # is present and a well-formed URI by this point).
        probe_url = data.get("onboarding_url") if expected_role == "authority" else data.get("endpoint")
        if probe_url:
            ok, detail = probe_reachable(probe_url)
            if ok:
                print(f"OK {path}: {probe_url} reachable ({detail})")
            else:
                print(f"FAIL {path}: {probe_url} not reachable ({detail})")
                file_failed = True

        if file_failed:
            any_failed = True
        else:
            print(f"OK {path}")

    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
