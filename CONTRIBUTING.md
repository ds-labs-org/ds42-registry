# Contributing an entry

Anyone whose implementation speaks the Dataspace Protocol (or who's
running a supporting service for it) is welcome to add themselves here,
in any of ds42's four roles: `connector`, `authority`, `federation-list`,
`service`. See [ds42.org](https://ds42.org) and its
[ADR-0009](https://ds42.org/adr/0009) for what each role means.

## Authority role: use the wizard instead

If you're registering as an **authority**, it's faster to use
[ds42.org's Get started wizard](https://ds42.org/get-started) — its
Authority path logs you in with GitHub (OAuth Device Flow — no password,
no client secret ever leaves your browser) and opens this exact PR for
you automatically. Use the manual steps below only if you'd rather not
use the wizard, or if you're registering as a connector, federation list,
or service (no wizard for those roles yet).

## Manual steps

1. Fork this repository.
2. Add `entries/<role>/<slug>.yaml`, matching
   [`schema/entry.schema.json`](schema/entry.schema.json) — see
   [`entries/_examples/`](entries/_examples/) for a filled-in example per
   role. `<slug>` must be a short, URL-safe identifier
   (`^[a-z0-9-]+$`) and must match the `slug` field inside the file.
3. Open a pull request. CI (`.github/workflows/validate.yml`) checks the
   file against the schema and, if your PR adds exactly that one new file
   and touches nothing else, merges it automatically — no human approval
   needed. If your PR is broader than that (e.g. it also edits an
   existing entry, or touches files outside `entries/`), it's left open
   for manual review instead.

Don't edit someone else's entry in the same PR as your own — that always
routes to manual review, and it isn't yours to change anyway. If your own
details change, open a follow-up PR that only touches your own file.
