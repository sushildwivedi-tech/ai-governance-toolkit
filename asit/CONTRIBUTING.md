# Contributing to ASIT

ASIT is reference material. Contributions are held to a documentation-grade
evidence bar, not a marketing one. Read this before opening a proposal.

## Ground rules

1. **No invented incidents.** Every `incidents.yaml` entry needs a real,
   retrievable public source. If you cannot source a failure mode, the category
   stays `anticipated` with empty `incident_refs` — that is honest and
   acceptable.
2. **Categories must be mutually distinguishable.** If a real incident could be
   filed under your proposed category *or* an existing one, sharpen the
   definitions or merge. Overlap is a defect.
3. **Ids are permanent.** Never renumber or reuse an id. Retire a category by
   setting `status: deprecated` (optionally `deprecated_by`), never by deleting
   it. `validate.py` enforces this against `id_registry.yaml`.
4. **No marketing language, no vendor names as solutions, no consulting
   framing.** Describe failure modes and controls, not products.
5. **Don't pad for volume.** A well-defined category beats three vague ones.

## The evidence bar

An `incidents.yaml` entry requires all of:

- `url` — a canonical, retrievable source of one of these `source_type`s:
  `postmortem`, `cve`, `vendor_advisory`, `vendor_report`, `aiid`,
  `research_paper`, `reputable_reporting`.
- `date` — ISO date of the event or first public disclosure.
- `summary` — one factual line of what happened.
- `agentic` — one line on the coding agent's role (why it is in scope).

Scope reminder: ASIT covers failures where an autonomous or semi-autonomous
**coding agent** is the *proximate* cause of an SDLC defect, breach, outage, or
governance failure. A model output a human copied by hand is out of scope.

`evidence_status` on the category must match its `incident_refs`:

| evidence_status | incident_refs |
|-----------------|---------------|
| `documented` | at least one |
| `reported_anecdotally` | optional |
| `anticipated` | **must be empty** |

## Proposing a new category

Open an issue or PR using this template. Do not write it straight into
`taxonomy.yaml` before discussion — the id is permanent once adopted.

```yaml
# PROPOSAL — not yet an id. Maintainers assign the ASIT id on acceptance.
name: <short noun phrase>
lifecycle_stage: <PLAN|DESIGN|BUILD|TEST|REL|OPS|FOUND>
causal_locus: <model_error|injected_instruction|overbroad_permission|
               tool_misuse|supply_chain|oversight_failure|
               context_corruption|identity_gap>
definition: >
  1-2 sentences, testable. End with an explicit "Test:" question a reader of an
  incident report can answer yes/no.
detection_point: <pre_execution|pre_commit|ci|human_review|runtime|
                  post_incident|undetected>
blast_radius: <1-5, justified against the rubric in taxonomy.yaml>
preconditions:
  - <what must be true for this failure to be possible>
mitigating_controls: [<CTL-NN>, ...]   # from controls.yaml; [] if a real gap
related: [<ASIT-...>, ...]
external_mappings:                       # only genuine correspondences
  owasp_llm: []
  mitre_atlas: []
  cwe: []
evidence_status: <documented|reported_anecdotally|anticipated>
incident_refs: [<INC-NNNN>, ...]         # empty if anticipated

# Why this is distinct from every existing category (required):
distinctness: >
  Name the nearest existing category and state the test that separates a real
  incident of yours from one of theirs.
```

## Before you open the PR

```bash
pip install pyyaml jsonschema
python asit/scripts/validate.py        # must pass
python asit/scripts/build.py           # regenerate docs/
git add asit/docs asit/README.md       # commit the regenerated output
```

Adopting a genuinely new id into the ledger is a deliberate step:

```bash
python asit/scripts/validate.py --register-new-ids
```

CI runs `validate.py` and asserts `docs/` is in sync on every push touching
`asit/`. A PR that changes the YAML without regenerating `docs/` will fail.

## What maintainers check

- The category is distinct (rule 2) and testable.
- Sources meet the evidence bar and actually resolve.
- External mappings are genuine, not forced.
- Coverage: if the category has no mitigating control, that gap is intended and
  called out — not an oversight.
