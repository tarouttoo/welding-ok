# Knowledge files (файлы знаний)

Curated Russian knowledge files — the agent's source of engineering knowledge
when authoring `ok.json` from a brief ([GLOSSARY.md](../GLOSSARY.md), «Файлы
знаний»). The agent reads these before drafting; the linter and renderer never
consume them (engineering knowledge fills the contract *from inside*; the
contract constrains it *from outside* — see
[contract/README.md](../contract/README.md), «Расширение v1»).

## Files

| File | Covers |
| ---- | ------ |
| [transitions_rd.md](transitions_rd.md) | Типовые переходы сварки: формулировки для `transitions[]` (v1 — сварка, без сборочных переходов). |
| [modes_uoni_13_55.md](modes_uoni_13_55.md) | Режимная таблица: род тока, полярность, диаметр электрода, ток и число проходов по толщинам 3–16 мм, ст3 и 09Г2С. |
| [sequencing_rules.md](sequencing_rules.md) | Правила последовательности сварки: деформации, доступность, порядок швов и операций. |
| [graph_dictionary.md](graph_dictionary.md) | Словарь граф: какое поле контракта попадает в какое место формы ОК (по содержанию). |

## Scope and status

- **v1 scope only**: РД, ст3/09Г2С, 3–16 мм, электрод УОНИ-13/55. New
  processes/electrodes mean new files, not edits to these.
- **Welding-only**: the v1 ОК describes the welding operation only — no
  установить/прихватить transitions, no приспособления (see
  [GLOSSARY.md](../GLOSSARY.md), «ОК»/«Бриф»; пример «005 Сварка» в
  `docs/Методические указания.pdf`). Tacking parameters are deliberately out
  of the repo until a сборочно-сварочная card enters scope.

## ⚠ convention

Values the engineer has **not yet confirmed** carry an inline `⚠` marker, and
every file opens with a verification banner. Nothing here is authoritative
until the maintainer signs off: агент черновик готовит, инженер при приёмке
подтверждает. When knowledge conflicts with a golden example, the knowledge
file flags the conflict instead of silently matching it.
