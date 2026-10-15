---
name: ok
description: Generate an operation card (ОК) from a welding бриф — author ok.json, lint it against the бриф, render the xlsx for приёмка.
disable-model-invocation: true
---

# ОК: бриф → ok.json → lint → render

One run = one operation card. The бриф is the only input; приёмка (the
engineer's review) is the only judge of engineering correctness. You author
content (`ok.json`), never layout — the renderer owns the ГОСТ form
(ADR 0001). Run every command from the repo root.

## 1. Read the бриф

- Real plant work: `briefs/<name>/brief.md`. Gitignored (ADR 0002): never
  stage, commit, or paste its contents outside this session.
- Synthetic dry-run: `examples/` — committed pairs; never overwrite them.
- Fixed sections: Детали, Расположение-база, Швы, Ограничения. Weld ids come
  from «Швы» only.

Done when all four sections are found. A missing or unreadable section,
including «Швы», is critical ambiguity (step 3).

## 2. Load the knowledge files

Read all four before making any engineering decision:

| File | Fills |
| ---- | ----- |
| `knowledge/transitions_rd.md` | формулировки `transitions[]` |
| `knowledge/modes_uoni_13_55.md` | `params` (режимы) |
| `knowledge/sequencing_rules.md` | порядок швов и операций |
| `knowledge/graph_dictionary.md` | куда попадает каждое поле (content only — layout belongs to the renderer) |

Every knowledge file opens with the ⚠ banner: values are agent-drafted until
приёмка confirms them. When a knowledge file conflicts with the golden
example, flag the conflict instead of silently matching it.

Done when the files are read **and** the v1 scope is checked: процесс РД,
ст3/09Г2С, 3–16 мм, электрод УОНИ-13/55. A бриф outside v1 scope is critical
ambiguity (step 3) — extending scope is a deliberate contract/knowledge edit,
never improvisation.

## 3. Triage ambiguity

- **Critical** — safety-relevant, technology-breaking, outside v1 scope, or a
  missing section: ask in chat and wait for the engineer. No draft is written.
- **Secondary** — the knowledge files cover it: decide, and record one Russian
  string per decision in `assumptions[]`.

The draft is always complete (GLOSSARY.md, «Черновик»): `assumptions[]` is a
mandatory field and may be empty.

## 4. Author ok.json

`contract/README.md` is normative — read it before writing. Keys are latin
`snake_case`; values are Russian, ГОСТ terminology preserved. Canonical file
form: `json.dumps(..., ensure_ascii=False, indent=2)` plus a trailing newline.

- Real work: `briefs/<name>/ok.json` (stays gitignored with the бриф).
- Synthetic dry-run: a scratch path outside `examples/`.

## 5. Validate and lint until clean

```
python3 contract/validate_ok.py <ok.json>
python3 linter/lint_ok.py <brief.md> <ok.json>
```

Findings are consistency errors: fix the contract or re-read the knowledge
files — never reinterpret the бриф to make a finding go away; an engineering
call you cannot ground is step 3. Re-run both until each exits 0. The lint
report lists `assumptions[]` prominently — keep it for step 6.

## 6. Render and hand over for приёмка

```
python3 renderer/render.py <ok.json> [out.xlsx]
```

Hand the engineer the xlsx path **and** the `assumptions[]` list — приёмка
must read them (they also land on the card as «Примечания:»). Графы left
blank on the form are filled by hand at приёмка (renderer/README.md).

Never edit the xlsx by hand. Приёмка corrections go into the бриф or the
contract, then re-run steps 4–6 — the renderer is the only owner of the file
(ADR 0001).
