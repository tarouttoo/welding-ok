# welding-ok

Operation-card generator for welded products: an agent authors the engineering
content as JSON, a deterministic renderer formats it per ГОСТ 3.1118-82 /
ГОСТ 3.1404-86 into xlsx. The agent never touches layout; the renderer never
makes engineering decisions. See `GLOSSARY.md` and `docs/adr/` before working
here.

v1 scope: РД (manual metal arc welding), ст3/09Г2С, 3–16 mm, electrode
УОНИ-13/55 only. Extending to new processes/electrodes means new knowledge
files, not code changes.

## Language

Infrastructure (this file, skills, issues, commits) is English. Domain content
(knowledge files, briefs, golden examples, ОК content, glossary) is Russian —
ГОСТ terminology must not be translated.

## Layout

- `briefs/` — real plant briefs. **Gitignored. Never commit.** (ADR 0002)
- `examples/` — synthetic briefs and golden examples (committed).
- `knowledge/` — curated Russian knowledge files for the agent.
- `contract/` — the `ok.json` contract: normative spec (`contract/README.md`), structural validator and validation CLI (ADR 0001).
- `renderer/`, `linter/` — deterministic Python code.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues in `tarouttoo/welding-ok`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
