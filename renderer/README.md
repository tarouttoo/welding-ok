# Renderer: `ok.json` → `ok.xlsx`

Deterministic renderer per [ADR 0001](../docs/adr/0001-agent-json-deterministic-renderer.md):
it maps a **valid** ok.json contract into the ГОСТ 3.1118-82 форма 1/1а
workbook. It makes zero engineering decisions — it never invents, infers or
rewrites content; every value it places comes verbatim from the contract,
composed into record lines by pure formatting (joining, Russian plural forms,
number formatting). Layout (fonts, borders, merges, pagination) lives here
and in `template.py` only — never in the contract.

## Usage

```
python3 renderer/render.py examples/minimal/ok.json [out.xlsx]
```

The CLI validates through `contract/validate_ok` first and refuses to render
an invalid contract (refusal is pipeline safety, not a renderer check — the
rendering core itself validates nothing, see «Граница ответственности» in
[`contract/README.md`](../contract/README.md)). Default output: `<input>.xlsx`.

## Files

```
renderer/
├── template.py     # форма 1/1а builder: рамка, графы, основная надпись (layout only)
├── render.py       # contract → cell mapping + CLI
└── test_render.py  # JSON→cell mapping tests + round-trip sanity (no layout tests, ADR 0001)
```

## Field → графа mapping (normative for tests)

| Contract field | Графа |
| -------------- | ----- |
| `product.name` | шапка «Наименование изделия» + основная надпись (наименование) |
| `product.material` | основная надпись, графа «материал» |
| `product.process` | содержание: «Способ сварки: …» |
| `operations[i].number` | основная таблица, графа «Номер операции» + содержание: «Операция N» |
| `operations[i].position` | содержание: «Положение сварки: …» |
| `operations[i].transitions[j]` | содержание: «Переходы:» + «\<n\>. \<description\>» |
| `operations[i].welds` | содержание: «Швы: Ш1, Ш2.» |
| `operations[i].sketch_refs` | содержание: «Ссылки на эскизы: КЭ1.» (заглушки-ссылки на КЭ) |
| `operations[i].equipment.electrode_type` | содержание: «Электроды: …» |
| `operations[i].params` | содержание: «Режим: …» (polarity line only when the contract carries it) |
| `documents[0].assumptions[k]` | содержание, блок «Примечания:» |

Graphы with no contract field stay **blank** and are filled by hand at
приёмка: обозначение изделия / документа, код и наименование операции,
оборудование (станочное), СМ/Проф./Р/УТ/КР/КОИД/ЕН/ОП/Кшт/Т пз/Т шт,
таблица изменений, подписи.

## Layout provenance

`template.py` reconstructs форма 1/1а from scratch (альбомный A4, поле
подшивки 20 мм, шапка изделия, основная таблица Цех…Т шт, зона содержания,
основная надпись по ГОСТ 3.1103-83 в правом нижнем углу, малая основная
надпись на листах 1а). Dimensions are a documented best-faith reading of the
standard on a 2 mm column grid; the university-supplied xlsx is a filling
reference only ([ADR 0002](../docs/adr/0002-synthetic-golden-no-plant-data.md)),
never the template. The maintainer should verify the reconstruction against
the ГОСТ text — there are deliberately no geometry/vision tests anywhere
(ADR 0001); tests assert only which value landed in which графа.

## v1 limitations (by design)

- All `operations[i].number` таблица rows are drawn on форма 1; a card whose
  таблица alone overflows the first sheet is rejected loudly (needs a
  template extension, not a silent squeeze).
- Content overflow paginates onto форма 1а sheets slot by slot; a content
  line is one fixed-height slot (tall text wraps inside it).
- `assumptions[]` are rendered on the card as «Примечания:» so the contract
  field has a defined графа; whether примечания belong on the released card
  is an engineering call reserved for приёмка.
