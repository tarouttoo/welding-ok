# Run 0001: golden run (v1 DoD, issue #7)

First end-to-end run of the full pipeline: agent authored `ok.json` from the
synthetic golden brief and pushed it through the deterministic half. Evidence
record for the v1 Definition of Done; ground truth itself remains the
engineer-authored golden pair (ADR 0002). Comparison is structural JSON ↔
JSON, never xlsx ↔ xlsx (ADR 0001).

- Date: 2026-10-15
- Brief: [`examples/golden/brief.md`](../../examples/golden/brief.md) (Направляющая, 09Г2С, 16 мм, вертикальное положение, Ш1–Ш4 — угловые У5, катет 8 мм, РД, УОНИ-13/55)
- Procedure: `.agents/skills/ok/SKILL.md` (brief → knowledge files → triage → draft → validate/lint → render)
- Run artifacts (`ok.json`, `ok.xlsx`) live in a scratch directory outside git — agent drafts never enter `examples/` and never overwrite the golden pair; the draft is reproduced below so the run is reproducible with the three commands listed.

## Pipeline trace

| Step | Command | Result |
| ---- | ------- | ------ |
| Validate | `python3 contract/validate_ok.py <run>/ok.json` | exit 0 — `valid ok.json: product 'Направляющая' (09Г2С, РД), 1 document, 1 operation(s), welds Ш1, Ш2, Ш3, Ш4` |
| Lint | `python3 linter/lint_ok.py examples/golden/brief.md <run>/ok.json` | exit 0 — `ok: ... consistent (welds Ш1, Ш2, Ш3, Ш4)`, assumptions (2) surfaced for приёмка |
| Render | `python3 renderer/render.py <run>/ok.json <run>/ok.xlsx` | exit 0 — `rendered <run>/ok.xlsx: 'Направляющая', 1 sheet(s) (форма 1), 12 content line(s)` |

Knowledge-file derivation of the режимы block: постоянный ток / обратная
полярность (УОНИ-13/55, основное покрытие); катет 8 мм → Ø 4–5 мм, 1–2
прохода ⚠ (`knowledge/modes_uoni_13_55.md`); вертикальное положение → ток
снижен на ~10–20 % ⚠ от нижнего положения (Ø 4: 100–130 А → 80–117 А,
принято 95 А); одна операция на все четыре шва — одинаковые положение и
режимы (`knowledge/sequencing_rules.md`, правило 7); нумерация с 1 — до
закрепления конвенции агент следует эталону.

## Agent draft (scratch copy — not the golden pair)

```json
{
  "product": {
    "name": "Направляющая",
    "material": "09Г2С",
    "process": "РД"
  },
  "documents": [
    {
      "assumptions": [
        "Диаметр электрода принят 4 мм (файл знаний для катета 7–8 мм допускает 4–5 мм): в вертикальном положении электрод меньшего диаметра ведётся устойчивее, ток ниже.",
        "Число проходов принято 2 (файл знаний для катета 7–8 мм допускает 1–2 ⚠): катет 8 мм — верхняя граница диапазона, в вертикальном положении два прохода обеспечивают полный катет и провар. Требует подтверждения инженера при приёмке."
      ],
      "operations": [
        {
          "number": 1,
          "position": "вертикальное",
          "equipment": {
            "electrode_type": "УОНИ-13/55"
          },
          "params": {
            "current_type": "постоянный",
            "current_a": 95,
            "polarity": "обратная",
            "electrode_diameter_mm": 4,
            "pass_count": 2
          },
          "welds": [
            "Ш1",
            "Ш2",
            "Ш3",
            "Ш4"
          ],
          "sketch_refs": [
            "КЭ1"
          ],
          "transitions": [
            {
              "number": 1,
              "description": "Сварить швы Ш1, Ш2, Ш3, Ш4 в вертикальном положении. Шлак и брызги удалить."
            }
          ]
        }
      ]
    }
  ]
}
```

## Structural comparison vs [`examples/golden/ok.json`](../../examples/golden/ok.json)

Deep walk of both trees: **3 differences**, everything else identical —
product block, operation numbering, position, equipment, род тока/полярность,
ток (95 А both), welds, sketch_refs, and the transition text verbatim
(«Сварить швы Ш1, Ш2, Ш3, Ш4 в вертикальном положении. Шлак и брызги
удалить.»).

| Path | Agent | Golden | Triage |
| ---- | ----- | ------ | ------ |
| `documents[0].operations[0].params.electrode_diameter_mm` | 4 | 5 | **Golden example gap.** Knowledge file allows Ø 4–5 for катет 7–8; agent picked Ø 4 (vertical position), recorded in `assumptions[]`. Not an agent error. Engineer should pin the practice for катет 7–8. |
| `documents[0].operations[0].params.pass_count` | 2 | 1 | **Golden example gap.** Knowledge file allows 1–2 ⚠ (unconfirmed); agent picked 2 (upper end of the катет bracket, vertical position), recorded in `assumptions[]`. Same class as the known катет-4 conflict flagged in `knowledge/modes_uoni_13_55.md` («Расхождение с эталоном»). Engineer adjudicates. |
| `documents[0].assumptions` | 2 entries | `[]` | **Not a discrepancy** — draft vs accepted (GLOSSARY «Черновик»/«Приёмка»): a draft must carry its спорные решения; the hand-authored golden, being the accepted answer, carries none. |

**Agent errors found: none.** The remaining fields agree with the golden pair
exactly.

Additional observation for the engineer (surfaced by the comparison, not a
tree difference): the golden's 95 А is arithmetically consistent with Ø 4
(100–130 А нижнее, −10–20 % → 80–117 А), but below the vertical band the
knowledge file derives for Ø 5 (130–160 А → 104–144 А). So the golden pair
itself reads as Ø 4 practice with Ø 5 written — either the golden's diameter
is a typo, or Ø 5 at 95 А in vertical position is intentional practice that
contradicts the file's reduction rule ⚠. Pinning the катет 7–8 practice
(first row of the triage) resolves this automatically.

## Open items for приёмка (maintainer)

1. **Accept the xlsx as work-usable**: regenerate locally with
   `python3 renderer/render.py <run>/ok.json` from the draft above (the
   renderer is deterministic, ADR 0001) and review the форма against ГОСТ
   3.1118-82 / 3.1404-86.
2. **Adjudicate the triage table**: pin диаметр and число проходов for
   катет 7–8 (and reconcile the golden's Ø 5 @ 95 А arithmetic); the outcome
   is an edit to `knowledge/modes_uoni_13_55.md` and/or the golden example —
   the contract stays untouched.
3. **Real run (issue spec item 2)**: local only (ADR 0002) — not executable
   in the agent sandbox (`briefs/` does not exist there and must never enter
   git). The maintainer runs the first real plant brief through the `ok`
   skill; no code changes are expected or made.
4. On 1–3 the maintainer declares v1 done (acceptance, issue #7).
