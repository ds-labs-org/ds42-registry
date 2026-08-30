#!/usr/bin/env python3
"""Validate every changed entries/**/*.yaml file against schema/entry.schema.json.

Usage: validate_entries.py <file> [<file> ...]

Skips anything under entries/_examples/ (documentation only, not a real
entry). Fails (non-zero exit) on the first violation found, printing a
clear message per file. Also checks that no OTHER existing file under
entries/<role>/ already uses the same slug.
"""
import json
import pathlib
import sys

import jsonschema
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "entry.schema.json"


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

    failed = False
    for path in entry_files:
        if not path.exists():
            # Deleted file — nothing to validate.
            continue

        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            print(f"FAIL {path}: not valid YAML: {exc}")
            failed = True
            continue

        if not isinstance(data, dict):
            print(f"FAIL {path}: must be a YAML mapping, got {type(data).__name__}")
            failed = True
            continue

        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            for err in errors:
                loc = "/".join(str(p) for p in err.path) or "<root>"
                print(f"FAIL {path}: {loc}: {err.message}")
            failed = True
            continue

        # Path must match role/slug declared inside the file.
        expected_role, expected_name = path.parts[1], path.stem
        if data.get("role") != expected_role:
            print(f"FAIL {path}: role '{data.get('role')}' does not match its directory 'entries/{expected_role}/'")
            failed = True
            continue
        if data.get("slug") != expected_name:
            print(f"FAIL {path}: slug '{data.get('slug')}' does not match its file name '{expected_name}'")
            failed = True
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
                    failed = True

        if not failed:
            print(f"OK {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
