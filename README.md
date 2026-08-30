# ds42-registry

The participant registry for [ds42.org](https://ds42.org) — an open,
volunteer-run, implementation-neutral experimentation hub for the
Dataspace Protocol, modelled on [dn42](https://dn42.dev/Home)'s
git-managed whois database. Membership on ds42 is conformance to DSP and
nothing else, in any of four roles: **connector**, **authority**,
**federation list**, or **service**. This repository is where a member
says so — a stranger opens a pull request adding a file describing
themselves, CI checks it against the schema below, and a well-formed,
new-entry-only PR merges on its own. No central authority approves an
entry by hand; that would contradict the hub's whole premise.

See [ds42.org](https://ds42.org)'s
[ADR-0009](https://ds42.org/adr/0009) (why the hub exists, the four
roles) and
[ADR-0010](https://ds42.org/adr/0010) (why this specific registry design)
for the full reasoning. Both live in the
[`dataspace`](https://labs.deepthought-solutions.net/Deepthought-Solutions/dataspace)
repository.

## Layout

One YAML file per participant entry, under:

```
entries/<role>/<slug>.yaml
```

where `<role>` is one of `connector`, `authority`, `federation-list`,
`service`, and `<slug>` is a short, URL-safe identifier for the
participant (`^[a-z0-9-]+$`). Every entry's shape is defined by
[`schema/entry.schema.json`](schema/entry.schema.json); filled-in examples
for each role live under [`entries/_examples/`](entries/_examples/) (not
validated or merged — documentation only). `authority` entries carry
`trust_model`/`claims_issued`/`onboarding_url`; the other three roles
carry an `endpoint` — see "Reachability check" below for what that's
used for.

## How an entry gets in

- **Authority role:** use ds42.org's
  [Get started wizard](https://ds42.org/get-started) — its Authority path
  logs you in with GitHub (OAuth Device Flow, no password or client
  secret involved), then forks this repo, commits your entry, and opens
  the PR for you.
- **Any role, by hand:** see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## How a PR gets merged

`.github/workflows/validate.yml` runs on every PR touching `entries/**`,
across three jobs:

1. **validate** — asserts the PR touches nothing outside `entries/**`
   (including this very workflow file), then parses every changed file as
   YAML and checks it against the schema (required fields, valid `role`,
   no slug collision within its role), then runs a **reachability probe**:
   a plain HTTP GET against the entry's `onboarding_url` (authority) or
   `endpoint` (the other three roles), with any non-5xx response counting
   as reachable. This is *not* a Dataspace Protocol conformance check —
   just "does something answer here" — a real DSP conformance probe (e.g.
   via the [DataspaceTCK](https://ds42.org/spikes/2026-08-27-dataspacetck-compliance-suites))
   is deferred; see [ADR-0010](https://ds42.org/adr/0010)'s Consequences.
   Note this means CI makes an outbound call to a URL the PR author
   supplies — accepted as a public-runner-egress-only risk (no internal
   resources reachable, no secrets in the request), see ADR-0010.
2. **verify-edit-authorship** — for any file this PR *modifies* (not
   adds), checks whether every line it removes or changes was itself
   originally authored by the same person opening this PR. Authorship is
   never taken from anything inside the YAML (a self-declared
   `registered_by` field would be trivially spoofable) — it's derived
   from `git blame` against the base branch plus GitHub's own
   commit-to-account resolution (`GET /repos/.../commits/{sha}`'s
   `.author.login`, which GitHub only sets when a commit's email matches
   a *verified* email on a real account). If GitHub can't resolve either
   the original or the new commit to a verified profile, or the two don't
   match, this job fails — the PR is not auto-merge-eligible, full stop.
   Every commit the Get started wizard makes goes through GitHub's own
   Contents API with no custom author/committer set, so GitHub creates
   and signs that commit itself on the authenticated user's behalf — it's
   both correctly attributed and shown as "Verified" for free. A
   hand-authored PR only clears this check if its own git commits' author
   email matches a verified email on the PR-opener's GitHub account.
   **A stronger future guarantee** — requiring every entry-touching
   commit to carry a cryptographic signature (GPG/SSH) rather than
   relying on GitHub's account-email matching — is named as a deferred
   hardening step in ADR-0010, not implemented yet.
3. **auto-merge** — only runs after both jobs above succeed, then checks
   the PR's diff *shape*: nothing outside `entries/**`/`entries/_examples/`,
   and at most `MAX_NEW_ENTRIES` (currently `2`, set in the workflow's
   `env:`) newly added files. If the shape check also passes, the PR is
   auto-merged. Anything broader — too many new entries at once, an edit
   whose authorship didn't clear, a change outside `entries/` — is left
   open for manual review instead. That combination of restrictions is
   what makes "no human gatekeeper" a safe default.
