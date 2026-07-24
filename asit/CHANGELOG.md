# Changelog

All notable changes to the Agentic SDLC Incident Taxonomy (ASIT) are recorded
here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the taxonomy version tracks `taxonomy/taxonomy.yaml`.

Ids are permanent: categories are added or deprecated, never renumbered or
removed.

## [0.2.0] — 2026-07-24

### Changed
- Confirmed the eight stage controls (CTL-06…13) and fleshed them out with
  `objective` and `requires` fields in `controls.yaml`.

### Added
- `CTL-14` Release Artifact Attestation (REL) — SLSA-style provenance for
  artifacts an agent produces or consumes. Wired into `ASIT-BUILD-02`,
  `ASIT-REL-02`, and `ASIT-FOUND-02`, relieving those categories' reliance on
  `CTL-04` alone.

## [0.1.0] — 2026-07-24

### Added
- Initial taxonomy of 17 categories across the seven stages
  (PLAN, DESIGN, BUILD, TEST, REL, OPS, FOUND): 12 `documented`, 5 `anticipated`.
- `taxonomy/schema.json` — JSON Schema (Draft 2020-12) for `taxonomy.yaml`.
- `taxonomy/taxonomy.yaml` — single source of truth, with an explicit 1–5
  blast-radius rubric.
- `taxonomy/controls.yaml` — the 13-control governance map (five foundational
  controls from the brief; eight stage controls reconstructed, flagged as draft).
- `taxonomy/id_registry.yaml` — permanent id ledger backing the stability check.
- `incidents/incidents.yaml` — 10 sourced, retrievable public incidents.
- `scripts/validate.py` — schema, referential integrity, and id-stability checks.
- `scripts/build.py` — generates `docs/index.md`, `docs/quick-reference.md`,
  `docs/coverage.md`, `docs/asit.json`, and the README table of contents.
- CI (`.github/workflows/asit-validate.yml`) — validates and asserts docs are in
  sync on every push touching `asit/`.
- `CONTRIBUTING.md`, `CITATION.cff` (placeholder author/DOI), and this changelog.

### Known limitations
- `external_mappings.vaiss` is intentionally unpopulated pending confirmation of
  the target VAISS guardrail taxonomy.
