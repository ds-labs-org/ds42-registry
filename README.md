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
validated or merged — documentation only).

## How an entry gets in

- **Authority role:** use ds42.org's
  [Get started wizard](https://ds42.org/get-started) — its Authority path
  logs you in with GitHub (OAuth Device Flow, no password or client
  secret involved), then forks this repo, commits your entry, and opens
  the PR for you.
- **Any role, by hand:** see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## How a PR gets merged

`.github/workflows/validate.yml` runs on every PR touching `entries/**`:

1. **validate** — every changed file is parsed as YAML and checked
   against the schema (required fields, valid `role`, no slug collision
   within its role).
2. **auto-merge** — only if validation passed *and* the PR's entire diff
   is exactly one new file under `entries/**` (no existing entry touched,
   no other path changed), the PR is auto-merged. Anything broader — an
   edit to someone else's entry, a change outside `entries/`, multiple
   files at once — is left open for manual review instead. That
   restriction is what makes "no human gatekeeper" a safe default.
