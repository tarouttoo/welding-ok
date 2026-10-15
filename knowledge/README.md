# Knowledge files

Curated Russian knowledge files — the agent's engineering source when authoring
`ok.json` (see «Файлы знаний» in [`GLOSSARY.md`](../GLOSSARY.md)). Consumed by
the agent only; the renderer and linter never read this directory.

Filenames are Latin `snake_case` (infrastructure); all content is Russian, ГОСТ
terminology is never translated (same split as the contract's key/value rule).

## File map

| File | Answers |
| ---- | ------- |
| [`assembly_transitions.md`](assembly_transitions.md) | Типовые переходы сборки и сварки, прихватки, формулировки для `transitions[]`. |
| [`modes_uoni_13_55.md`](modes_uoni_13_55.md) | Режимная таблица УОНИ-13/55: ток, полярность, диаметр, проходы по толщинам 3–16 мм, ст3/09Г2С. |
| [`sequencing_rules.md`](sequencing_rules.md) | Правила последовательности: деформации, доступность, что варить раньше чего. |
| [`graph_dictionary.md`](graph_dictionary.md) | Словарь граф: поле контракта → графа формы ОК (справочно, для агента и рендерера). |

## Status

These files are an **agent draft, pending engineer verification** (issue #4
acceptance): режимные таблицы and sequencing rules must be confirmed by the
maintainer before the first agent run. Anything the agent was not sure about is
marked with `⚠` inline, never silently invented.
