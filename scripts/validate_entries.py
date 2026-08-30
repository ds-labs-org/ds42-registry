#!/usr/bin/env python3
"""Validate every changed entries/**/*.jsonld file against
schema/ontology.ttl + schema/shapes.ttl (SHACL, via pySHACL), plus a
lightweight reachability probe of the entry's declared URL.

Usage: validate_entries.py <file> [<file> ...]

Skips anything under entries/_examples/ (documentation only, not a real
entry). Fails (non-zero exit) on the first violation found, printing a
clear message per file. Checks, per file:
  - valid JSON-LD (parses as an RDF graph)
  - conforms to schema/shapes.ttl (SHACL, with rdfs subclass inference
    against schema/ontology.ttl so e.g. a ds:Authority individual is also
    validated against the shared ds:RegistrantShape)
  - @type / slug match the file's own path (entries/<role>/<slug>.jsonld)
  - no other existing file under entries/<role>/ already uses the same
    slug
  - reachability probe (see probe_reachable()) of onboardingUrl
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

import rdflib
from pyshacl import validate as shacl_validate

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = REPO_ROOT / "schema" / "ontology.ttl"
SHAPES_PATH = REPO_ROOT / "schema" / "shapes.ttl"
REGISTRY_NS = "https://ds42.org/ns/registry#"
PROBE_TIMEOUT_SECONDS = 8

# entries/<ROLE_DIR>/ <-> @type local name.
ROLE_DIR_TO_TYPE = {
    "connector": "Connector",
    "authority": "Authority",
    "federation-list": "FederationList",
    "service": "Service",
}


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


def entry_role(data: dict) -> str | None:
    """Local role name (e.g. 'authority') from a parsed JSON-LD dict's
    @type, expanded against @vocab if the type is a bare compact term."""
    type_value = data.get("@type")
    if isinstance(type_value, list):
        type_value = type_value[0] if type_value else None
    if not isinstance(type_value, str):
        return None
    local = type_value.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    for role_dir, type_name in ROLE_DIR_TO_TYPE.items():
        if local == type_name:
            return role_dir
    return None


def main() -> int:
    files = [pathlib.Path(f) for f in sys.argv[1:]]
    entry_files = [
        f for f in files
        if f.parts[:1] == ("entries",) and "_examples" not in f.parts and f.suffix == ".jsonld"
    ]
    if not entry_files:
        print("No entries/**/*.jsonld files changed (outside entries/_examples/) — nothing to validate.")
        return 0

    ontology_graph = rdflib.Graph()
    ontology_graph.parse(ONTOLOGY_PATH, format="turtle")
    shapes_graph = rdflib.Graph()
    shapes_graph.parse(SHAPES_PATH, format="turtle")

    any_failed = False
    for path in entry_files:
        if not path.exists():
            # Deleted file — nothing to validate.
            continue

        file_failed = False

        try:
            raw = path.read_text()
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL {path}: not valid JSON: {exc}")
            any_failed = True
            continue

        if not isinstance(data, dict):
            print(f"FAIL {path}: must be a JSON-LD object, got {type(data).__name__}")
            any_failed = True
            continue

        try:
            data_graph = rdflib.Graph()
            data_graph.parse(data=raw, format="json-ld")
        except Exception as exc:  # noqa: BLE001 - any JSON-LD parse failure is a validation failure
            print(f"FAIL {path}: not valid JSON-LD: {exc}")
            any_failed = True
            continue

        conforms, _results_graph, results_text = shacl_validate(
            data_graph,
            shacl_graph=shapes_graph,
            ont_graph=ontology_graph,
            inference="rdfs",
            abort_on_first=False,
        )
        if not conforms:
            print(f"FAIL {path}: does not conform to schema/shapes.ttl:")
            print(results_text)
            any_failed = True
            continue

        # Path must match role/slug declared inside the file.
        expected_role, expected_name = path.parts[1], path.stem
        actual_role = entry_role(data)
        if actual_role != expected_role:
            print(f"FAIL {path}: @type resolves to role '{actual_role}', not its directory 'entries/{expected_role}/'")
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
            for other in role_dir.glob("*.jsonld"):
                if other.resolve() == path.resolve():
                    continue
                try:
                    other_data = json.loads(other.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                if isinstance(other_data, dict) and other_data.get("slug") == data.get("slug"):
                    print(f"FAIL {path}: slug '{data.get('slug')}' already used by {other}")
                    file_failed = True

        # Reachability probe: onboardingUrl for authority, endpoint for
        # the other three roles (schema/shapes.ttl already guarantees one
        # of these is present and an IRI by this point).
        probe_url = data.get("onboardingUrl") if expected_role == "authority" else data.get("endpoint")
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
