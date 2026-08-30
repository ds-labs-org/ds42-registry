# Contributing an entry

Anyone whose implementation speaks the Dataspace Protocol (or who's
running a supporting service for it) is welcome to add themselves here,
in any of ds42's four roles: `connector`, `authority`, `catalog-broker`,
`service`. See [ds42.org](https://ds42.org) and its
[ADR-0009](https://ds42.org/adr/0009) for what each role means.

## Authority role: use the wizard instead

If you're registering as an **authority**, it's faster to use
[ds42.org's Get started wizard](https://ds42.org/get-started) — its
Authority path logs you in with GitHub (OAuth Device Flow — no password,
no client secret ever leaves your browser) and opens this exact PR for
you automatically. Use the manual steps below only if you'd rather not
use the wizard, or if you're registering as a connector, catalog broker,
or service (no wizard for those roles yet).

## Manual steps

1. Fork this repository.
2. Add `entries/<role>/<slug>.jsonld` — a JSON-LD document typed
   (`@type`) as one of `Connector`, `Authority`, `CatalogBroker`,
   `Service`, matching the vocabulary in
   [`schema/ontology.ttl`](schema/ontology.ttl) and validated against
   [`schema/shapes.ttl`](schema/shapes.ttl) — see
   [`entries/_examples/`](entries/_examples/) for a filled-in example per
   role, including the `@context` block to copy verbatim (it's the same
   in every entry). `<slug>` must be a short, URL-safe identifier
   (`^[a-z0-9-]+$`) and must match both the entry's `slug` property and
   the file name. `authority` entries need
   `trustModel`/`claimsIssued`/`onboardingUrl`; the other three roles
   need an `endpoint` — CI does a plain reachability check against
   whichever one applies (see README.md), so make sure it's actually live
   before you open the PR. `trustModel` must be one of `DidSsi`,
   `Eidas2Pki`, `PkiGovernanceAuthority`, `FromScratch` (CI rejects
   anything else — see README.md's "Vocabulary grounding").
3. Open a pull request. CI (`.github/workflows/validate.yml`) validates
   the file against the SHACL shapes, probes the URL above, and — for a
   new entry — merges automatically if your PR adds at most
   `MAX_NEW_ENTRIES` new files and touches nothing else. No human
   approval needed for that case. Anything broader (too many new entries
   at once, a change outside `entries/`) is left open for manual review
   instead.

You can also open a PR that edits **your own existing entry** — CI checks
this by comparing your PR's git commit authorship against who originally
committed the lines you're changing (via GitHub's own verified-account
resolution, not by trusting anything inside the file), and auto-merges if
they match. Don't edit someone else's entry in the same PR as your own —
it will never match, always routes to manual review, and it isn't yours
to change anyway. See README.md's "How a PR gets merged" for exactly how
that check works.
