# ds42-registry

The participant registry for [ds42.org](https://ds42.org) — an open,
volunteer-run, implementation-neutral experimentation hub for the
Dataspace Protocol, modelled on [dn42](https://dn42.dev/Home)'s
git-managed whois database. Membership on ds42 is conformance to DSP and
nothing else, in any of four roles: **connector**, **authority**,
**catalog broker**, or **service** (originally named "federation list",
renamed by [ADR-0011](https://ds42.org/adr/0011) so the name doesn't
read as a directory of who's in the federation — this registry is
that). This repository is where a member says so — a stranger opens a
pull request adding a file describing
themselves, CI checks it against the vocabulary below, and a well-formed,
new-entry-only PR merges on its own. No central authority approves an
entry by hand; that would contradict the hub's whole premise.

Entries are **JSON-LD**, described by an **OWL ontology in Turtle**
([`schema/ontology.ttl`](schema/ontology.ttl)) and enforced by
**SHACL shapes** ([`schema/shapes.ttl`](schema/shapes.ttl)) — not plain
YAML/JSON Schema. This isn't decoration: ds42's own domain (DSP
catalogs, DCAT, ODRL policies) is already RDF-based, so a registry that
describes participants the same way is consistency with what it's a
registry *for*, not an added dependency.

See [ds42.org](https://ds42.org)'s
[ADR-0009](https://ds42.org/adr/0009) (why the hub exists, the four
roles) and
[ADR-0010](https://ds42.org/adr/0010) (why this specific registry design)
for the full reasoning. Both live in the
[`dataspace`](https://labs.deepthought-solutions.net/Deepthought-Solutions/dataspace)
repository.

## Vocabulary grounding

`schema/ontology.ttl` doesn't mint everything from scratch — every
class/property is checked against, and where a genuine correspondence
exists, linked to, a real term from a vocabulary this hub's own domain
already depends on:

- **[DCAT](http://www.w3.org/ns/dcat#)** — `ds:endpoint` is
  `dcat:endpointURL` by another name, because the Dataspace Protocol
  itself reuses DCAT for exactly this.
- **[The Dataspace Protocol's own vocabulary](https://w3id.org/dspace/2025/1/)**
  — `ds:slug`/`ds:CatalogBroker` are related to (not asserted equal to)
  DSP's own `dspace:participantId`/`dspace:CatalogService`.
- **[International Data Spaces (IDS) Information Model](https://w3id.org/idsa/core/)**
  — DSP's direct ancestor, and the source of the closest actual naming
  echo to check for: IDS defines its own `ids:Participant` — confirmed
  from the published ontology — as a *certified, legally-named* entity
  (`legalName`, `jurisdiction`, `participantCertification`). This is
  exactly why this vocabulary's base class is named `ds:Registrant` — the
  same term a domain registry's WHOIS record uses for its record-holder,
  matching this registry's own dn42-style WHOIS-inspired design — rather
  than any `Participant`-rooted name: it carries none of IDS's
  certification/legal-entity baggage, and a genuinely different word
  avoids the naming echo outright instead of merely disclaiming it. Still
  linked to `ids:Participant` via `rdfs:seeAlso`, since the *kind* of
  thing both name is real kinship even though the two aren't equivalent.
- **[W3C DID Core](https://www.w3.org/ns/did#)** — `ds:onboardingUrl` is a
  `did:serviceEndpoint`, the same term DSP's own context reuses for
  identity-associated endpoints.
- **[Gaia-X](https://w3id.org/gaia-x/2404#)** — the closest existing
  prior art for this registry's whole approach: JSON-LD self-descriptions
  validated by SHACL, built on DCAT and the W3C Organization Ontology.
  `ds:Registrant` is related to Gaia-X's `gx:LegalParticipant` by
  `rdfs:seeAlso`, not equivalence — a ds42 entry is a much lighter-weight
  role declaration, not a full legal-entity self-description.
- **[W3C Organization Ontology](http://www.w3.org/ns/org#)** and
  **[FOAF](http://xmlns.com/foaf/0.1/)** — what Gaia-X itself grounds
  participant modelling in, linked the same way for the same reason.

`schema/ontology.ttl`'s own header comment has the full reasoning per
term, including why these are `rdfs:seeAlso`/`rdfs:subPropertyOf` links
rather than `owl:imports` (none of these are fetched by this repo's own
tooling, and none of their long-term URL stability was verified as part
of this work — asserting a hard dependency on them would overclaim).

## Layout

One JSON-LD file per participant entry, under:

```
entries/<role>/<slug>.jsonld
```

where `<role>` is one of `connector`, `authority`, `catalog-broker`,
`service`, and `<slug>` is a short, URL-safe identifier for the
participant (`^[a-z0-9-]+$`) — matching both the entry's `slug` property
and the last path segment of its `@id`. Each entry is typed (`@type`) as
one of `ds:Connector`, `ds:Authority`, `ds:CatalogBroker`, `ds:Service`
from [`schema/ontology.ttl`](schema/ontology.ttl), which is what CI
checks against the entry's directory. The vocabulary and its per-role
required properties are described in that same file; what CI actually
*enforces* is [`schema/shapes.ttl`](schema/shapes.ttl) (SHACL — see "How a
PR gets merged" for why the two are separate files). Filled-in examples
for each role live under [`entries/_examples/`](entries/_examples/) (not
validated or merged — documentation only). `authority` entries carry
`trustModel`/`claimsIssued`/`onboardingUrl`; the other three roles carry
an `endpoint` — see "How a PR gets merged" below for what that's used
for.

Every entry file is self-contained: its `@context` is inlined (a
`@vocab` pointing at `https://ds42.org/ns/registry#`, matching
`ontology.ttl`'s namespace), so validating one doesn't depend on
dereferencing anything over the network.

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
   (including this very workflow file), parses every changed file as
   JSON-LD into an RDF graph, and validates it with **pySHACL** against
   [`schema/shapes.ttl`](schema/shapes.ttl) (with rdfs subclass inference
   over [`schema/ontology.ttl`](schema/ontology.ttl) turned on, so e.g. a
   `ds:Authority` individual is also checked against the shared
   `ds:RegistrantShape`, not only `ds:AuthorityShape`) — required
   properties, datatypes, the slug pattern, IRI-typed URLs. It also checks
   the entry's `@type` and `slug` match its own directory/file name and
   that no other entry in the same role directory reuses the slug. Then
   it runs a **reachability probe**: a plain HTTP GET against the entry's
   `onboardingUrl` (authority) or `endpoint` (the other three roles), with
   any non-5xx response counting as reachable. This is *not* a Dataspace
   Protocol conformance check — just "does something answer here" — a
   real DSP conformance probe (e.g. via the
   [DataspaceTCK](https://ds42.org/spikes/2026-08-27-dataspacetck-compliance-suites))
   is deferred; see [ADR-0010](https://ds42.org/adr/0010)'s Consequences.
   Note this means CI makes an outbound call to a URL the PR author
   supplies — accepted as a public-runner-egress-only risk (no internal
   resources reachable, no secrets in the request), see ADR-0010.
2. **verify-edit-authorship** — for any file this PR *modifies* (not
   adds), checks whether every line it removes or changes was itself
   originally authored by the same person opening this PR. Authorship is
   never taken from anything inside the entry itself (a self-declared
   `registeredBy` property would be trivially spoofable) — it's derived
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
