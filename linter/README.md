# Linter: brief ↔ ok.json consistency

The deterministic half of validation (issue #3): given a brief and the
contract produced from it, the linter checks that they agree. It never makes
engineering decisions (ADR 0001) — инженерная приёмка stays the judge of
engineering correctness; the linter enforces consistency and surfaces
`assumptions[]` so приёмка cannot miss them.

## CLI

```
python3 linter/lint_ok.py <brief.md> <ok.json>
```

Codes: `0` — clean; `1` — findings or malformed JSON (every finding as one
line `error: <check>: <message>`); `2` — usage or file-read error. Findings
go to stderr, the report to stdout; the report always lists `assumptions[]`
prominently (приёмка must read them), so they are visible on clean runs and
on failures alike. Assumptions never fail the lint.

## Checks

| Check | Issue #3 item | What it does |
| ----- | ------------- | ------------ |
| `structure` | 2, 3, 5 | Delegates to `contract/ok_schema.validate_ok` and re-surfaces its errors: monotonic operation numbers, required position/equipment/режимы, `КЭ<n>` sketch refs, `Ш<n>` weld patterns, v1 limits. Structural rules are not re-implemented here — the contract validator owns them (см. [`contract/README.md`](../contract/README.md), «Граница ответственности»). |
| `brief` | — | The brief must contain a «Швы» section with at least one `Ш<n>` weld. Welds are read from that section only: briefs are semi-structured with fixed sections ([`GLOSSARY.md`](../GLOSSARY.md)), «Швы» defines them, mentions elsewhere are references. On a `brief` finding the weld comparisons are skipped (they would mislead). |
| `weld_coverage` | 1 | Every weld of the brief is covered by some operation. |
| `no_extra_welds` | 6 | Every weld of ok.json is defined in the brief — no hallucinated швы. |

Item 4 of the issue (assumptions surfaced) is the report block, not a
finding. Weld ids are canonicalized to `Ш<n>` (`Ш01` ≡ `Ш1`) before
comparison.

## Not in scope yet

Реалистичность режимов and the v1 material range need the knowledge files
(issue #4); the linter grows those checks when the files land.

## Tests

```
python3 -m pytest
```

The pass case pairs [`examples/minimal/brief.md`](../examples/minimal/brief.md)
with [`examples/minimal/ok.json`](../examples/minimal/ok.json) (synthetic
pair, ADR 0002). Fail cases mutate the ok.json in code (same pattern as
`contract/test_ok_contract.py`) or use fixture briefs from `fixtures/`;
CLI exit codes are covered through subprocess runs.
