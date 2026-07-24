# Agentic SDLC Incident Taxonomy (ASIT)

A public, citable taxonomy of failure modes in which an autonomous or
semi-autonomous **coding agent** is the proximate cause of a software
development lifecycle (SDLC) defect, breach, outage, or governance failure.

## Why this exists

Adjacent references cover different ground:

| Reference | Scope | Not this |
|-----------|-------|----------|
| OWASP LLM Top 10 | Application-layer LLM vulnerabilities | SDLC process failures |
| MITRE ATLAS | Adversarial ML tactics against models | Agent-caused build/release defects |
| CWE | Weaknesses in code | Who/what introduced them and how |
| AI Incident Database | General AI harms | Coding-agent-specific SDLC failures |

ASIT's scope is narrower and, as far as we can tell, unclaimed: failures where
the coding **agent's own action or omission** — not merely a model output a
human copied — is the proximate cause.

## Evidence discipline

Every category carries an `evidence_status`:

- **documented** — backed by one or more real, retrievable public sources in
  [`incidents/incidents.yaml`](incidents/incidents.yaml) (postmortem, CVE,
  vendor advisory, AI Incident Database entry, peer-reviewed paper, or
  reputable reporting).
- **reported_anecdotally** — described in public but without a rigorous source.
- **anticipated** — plausible and structurally derived, but with no public
  incident yet. These carry an empty `incident_refs`, and that is honest.

The documented-vs-anticipated split is a **feature**, surfaced here and in the
generated docs. Categories are never invented to pad volume, and incidents are
never inferred — an unsourced failure mode stays `anticipated`.

## Repository layout

```
asit/
  taxonomy/
    taxonomy.yaml      # single source of truth (categories)
    schema.json        # JSON Schema for taxonomy.yaml
    controls.yaml      # the 13-control governance map ASIT cross-references
    id_registry.yaml   # permanent ledger of assigned ids (stability check)
  incidents/
    incidents.yaml     # sourced real-world instances
  scripts/
    validate.py        # schema + referential integrity + ID stability
    build.py           # emits docs from YAML
  docs/                # generated — never hand-edited
```

## Identifiers

- Category ids are `ASIT-<STAGE>-<NN>`, stage in
  `PLAN | DESIGN | BUILD | TEST | REL | OPS | FOUND`.
- **Ids are permanent.** Deprecate a category (`status: deprecated`), never
  renumber or reuse it. `validate.py` enforces this against `id_registry.yaml`.

## Validating

```bash
pip install pyyaml jsonschema
python asit/scripts/validate.py
```

CI runs the same check on every push touching `asit/`, and also asserts that
`docs/` is in sync with the source YAML.

## Generated documents

Run `python asit/scripts/build.py` after any change to the YAML. It regenerates,
and these are the only places to read the taxonomy as prose (never hand-edit):

- [`docs/index.md`](docs/index.md) — full taxonomy, one section per category.
- [`docs/quick-reference.md`](docs/quick-reference.md) — id / name / stage /
  causal locus / controls table.
- [`docs/coverage.md`](docs/coverage.md) — control-to-category matrix with gaps
  surfaced.
- [`docs/asit.json`](docs/asit.json) — machine-readable, versioned.

<!-- BEGIN GENERATED TOC -->
### Taxonomy at a glance

- **Plan**
  - [ASIT-PLAN-01](docs/index.md#asit-plan-01) Under-scoped Task Authorization
- **Design**
  - [ASIT-DESIGN-01](docs/index.md#asit-design-01) Autonomy-Risk Tier Mismatch
  - [ASIT-DESIGN-02](docs/index.md#asit-design-02) Overbroad Permission or Tool Grant
- **Build**
  - [ASIT-BUILD-01](docs/index.md#asit-build-01) Insecure Code Generation
  - [ASIT-BUILD-02](docs/index.md#asit-build-02) Hallucinated Dependency (Slopsquatting Exposure)
  - [ASIT-BUILD-03](docs/index.md#asit-build-03) Indirect Prompt Injection via Untrusted Content
  - [ASIT-BUILD-04](docs/index.md#asit-build-04) Poisoned Agent Configuration
  - [ASIT-BUILD-05](docs/index.md#asit-build-05) Unrequested Scope Expansion
- **Test**
  - [ASIT-TEST-01](docs/index.md#asit-test-01) Verification Integrity Failure
- **Release**
  - [ASIT-REL-01](docs/index.md#asit-rel-01) Change-Freeze or Approval-Gate Violation
  - [ASIT-REL-02](docs/index.md#asit-rel-02) Compromised Agent Distribution
- **Operate**
  - [ASIT-OPS-01](docs/index.md#asit-ops-01) Destructive Action Beyond Authorization
  - [ASIT-OPS-02](docs/index.md#asit-ops-02) Action on Corrupted Context or Hallucinated State
  - [ASIT-OPS-03](docs/index.md#asit-ops-03) Constraint Self-Modification or Guardrail Evasion
  - [ASIT-OPS-04](docs/index.md#asit-ops-04) Installed Agent Weaponized by Host Malware
- **Foundational plane**
  - [ASIT-FOUND-01](docs/index.md#asit-found-01) Unaccountable Agent Action
  - [ASIT-FOUND-02](docs/index.md#asit-found-02) Model or Weight Supply-Chain Compromise

<!-- END GENERATED TOC -->

## Status

Version 0.1.0 — 17 categories across the seven stages, of which 12 are
`documented` against sourced incidents and 5 are `anticipated`. Contributions
follow [`CONTRIBUTING.md`](CONTRIBUTING.md); cite via
[`CITATION.cff`](CITATION.cff).

> Note on the control map: the five foundational controls come from the
> maintainer's brief; the eight stage controls in `controls.yaml` are a draft
> reconstruction pending confirmation. The coverage analysis is only as
> accurate as that file.
