"""Tests for the linter (issue #3).

Pass case: examples/minimal/brief.md ↔ ok.json — the synthetic pair
(ADR 0002, invented product). Fail cases mutate the ok.json in code (same
pattern as contract/test_ok_contract.py) or use fixture briefs from
linter/fixtures/. CLI behaviour (exit codes, report lines) is covered
through subprocess runs, per the issue's acceptance.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lint_schema import extract_assumptions, extract_brief_welds, lint

REPO = Path(__file__).resolve().parents[1]
LINTER = Path(__file__).resolve().parent
BRIEF = REPO / "examples" / "minimal" / "brief.md"
OK = REPO / "examples" / "minimal" / "ok.json"
CLI = LINTER / "lint_ok.py"
BRIEF_NO_WELDS_SECTION = LINTER / "fixtures" / "brief_no_welds_section.md"


def _load_ok() -> dict:
    return json.loads(OK.read_text(encoding="utf-8"))


def _ok_json(mutate) -> str:
    data = _load_ok()
    mutate(data)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _run_cli(brief: Path, ok_text: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    ok_file = tmp_path / "ok.json"
    ok_file.write_text(ok_text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(CLI), str(brief), str(ok_file)],
        capture_output=True,
        text=True,
    )


# --- pass: the synthetic pair is consistent ---------------------------------


def test_clean_pair_passes(tmp_path: Path) -> None:
    result = _run_cli(BRIEF, OK.read_text(encoding="utf-8"), tmp_path)
    assert result.returncode == 0, result.stderr
    assert f"ok: {BRIEF} ↔ {tmp_path / 'ok.json'}: consistent (welds Ш1, Ш2)" in result.stdout


def test_clean_run_surfaces_assumptions_prominently(tmp_path: Path) -> None:
    result = _run_cli(BRIEF, OK.read_text(encoding="utf-8"), tmp_path)
    assert "assumptions (1) — must be read at приёмка:" in result.stdout
    assumption = _load_ok()["documents"][0]["assumptions"][0]
    assert assumption in result.stdout


def test_lint_clean_pair_has_no_findings() -> None:
    assert lint(BRIEF.read_text(encoding="utf-8"), _load_ok()) == []


# --- brief welds: extraction from the «Швы» section --------------------------


def test_welds_are_read_from_shvy_section_only() -> None:
    text = "# Бриф\n\n## Швы\n\n- Ш1 — угловой\n- Ш2 — угловой\n\n## Ограничения\n\nШвы Ш1, Ш2 и Ш5 не переворачивать.\n"
    brief = extract_brief_welds(text)
    # Ш5 is mentioned outside «Швы»: a reference, not a definition.
    assert brief.welds == ["Ш1", "Ш2"]
    assert brief.problems == []


def test_weld_ids_are_canonicalized_and_sorted() -> None:
    brief = extract_brief_welds("## Швы\n\nШ10 и Ш02\n")
    assert brief.welds == ["Ш2", "Ш10"]


def test_glued_tokens_are_not_welds() -> None:
    brief = extract_brief_welds("## Швы\n\nМарка СШ1 швом не является.\n")
    assert brief.welds == []


def test_missing_shvy_section_is_a_brief_problem() -> None:
    brief = extract_brief_welds("# Бриф\n\n## Детали\n\n- Материал: ст3.\n")
    assert brief.welds == []
    assert any('"Швы" not found' in problem for problem in brief.problems)


def test_empty_shvy_section_is_a_brief_problem() -> None:
    brief = extract_brief_welds("## Швы\n\n(раздел не заполнен)\n")
    assert brief.welds == []
    assert any("no welds" in problem for problem in brief.problems)


# --- check 1 / 6: weld coverage both ways ------------------------------------


def test_uncovered_brief_weld_fails(tmp_path: Path) -> None:
    def mutate(d: dict) -> None:
        d["documents"][0]["operations"][0]["welds"].remove("Ш2")

    result = _run_cli(BRIEF, _ok_json(mutate), tmp_path)
    assert result.returncode == 1
    assert "error: weld_coverage: weld Ш2 from the brief is not covered by any operation" in result.stderr


def test_hallucinated_weld_fails(tmp_path: Path) -> None:
    def mutate(d: dict) -> None:
        d["documents"][0]["operations"][0]["welds"].append("Ш9")

    result = _run_cli(BRIEF, _ok_json(mutate), tmp_path)
    assert result.returncode == 1
    assert "error: no_extra_welds: weld Ш9 in ok.json is not defined in the brief" in result.stderr


def test_weld_mismatch_reports_both_checks() -> None:
    def mutate(d: dict) -> None:
        d["documents"][0]["operations"][0]["welds"] = ["Ш1", "Ш9"]

    findings = lint(BRIEF.read_text(encoding="utf-8"), json.loads(_ok_json(mutate)))
    checks = {finding.check for finding in findings}
    assert checks >= {"weld_coverage", "no_extra_welds"}


def test_brief_without_shvy_section_skips_weld_comparisons(tmp_path: Path) -> None:
    result = _run_cli(BRIEF_NO_WELDS_SECTION, OK.read_text(encoding="utf-8"), tmp_path)
    assert result.returncode == 1
    assert "error: brief:" in result.stderr
    assert "weld_coverage" not in result.stderr
    assert "no_extra_welds" not in result.stderr


# --- checks 2 / 3 / 5: delegated to the contract validator -------------------


def test_non_monotonic_operation_numbers_fail(tmp_path: Path) -> None:
    def mutate(d: dict) -> None:
        operations = d["documents"][0]["operations"]
        operations[0]["number"] = 3
        operations.append(dict(operations[0], number=2))

    result = _run_cli(BRIEF, _ok_json(mutate), tmp_path)
    assert result.returncode == 1
    assert "error: structure:" in result.stderr
    assert "strictly increase" in result.stderr


def test_operation_without_position_or_equipment_or_params_fails(tmp_path: Path) -> None:
    for key in ("position", "equipment", "params"):
        def mutate(d: dict, key: str = key) -> None:
            d["documents"][0]["operations"][0].pop(key)

        result = _run_cli(BRIEF, _ok_json(mutate), tmp_path)
        assert result.returncode == 1, key
        assert f"error: structure: documents[0].operations[0].{key}: required field is missing" in result.stderr


def test_ill_formed_sketch_ref_fails(tmp_path: Path) -> None:
    def mutate(d: dict) -> None:
        d["documents"][0]["operations"][0]["sketch_refs"] = ["эскиз 1"]

    result = _run_cli(BRIEF, _ok_json(mutate), tmp_path)
    assert result.returncode == 1
    assert "КЭ<n>" in result.stderr


# --- check 4: assumptions are surfaced, never a failure ----------------------


def test_assumptions_are_surfaced_even_when_findings_exist(tmp_path: Path) -> None:
    def mutate(d: dict) -> None:
        d["documents"][0]["operations"][0]["welds"].remove("Ш2")

    result = _run_cli(BRIEF, _ok_json(mutate), tmp_path)
    assert result.returncode == 1
    assert "assumptions (1) — must be read at приёмка:" in result.stdout


def test_extract_assumptions() -> None:
    data = _load_ok()
    assert extract_assumptions(data) == data["documents"][0]["assumptions"]
    data["documents"][0]["assumptions"] = []
    assert extract_assumptions(data) == []
    assert extract_assumptions({}) is None
    assert extract_assumptions([]) is None
    data["documents"][0]["assumptions"] = "none"
    assert extract_assumptions(data) is None


def test_empty_assumptions_report_says_none(tmp_path: Path) -> None:
    result = _run_cli(BRIEF, _ok_json(lambda d: d["documents"][0].__setitem__("assumptions", [])), tmp_path)
    assert result.returncode == 0, result.stderr
    assert "assumptions: none" in result.stdout


# --- CLI: malformed input and usage ------------------------------------------


def test_malformed_json_exits_one(tmp_path: Path) -> None:
    result = _run_cli(BRIEF, "{not json", tmp_path)
    assert result.returncode == 1
    assert "is not valid JSON" in result.stderr


def test_unreadable_file_exits_two(tmp_path: Path) -> None:
    result = _run_cli(tmp_path / "absent.md", OK.read_text(encoding="utf-8"), tmp_path)
    assert result.returncode == 2
    assert "cannot read" in result.stderr


def test_wrong_argc_exits_two() -> None:
    result = subprocess.run([sys.executable, str(CLI)], capture_output=True, text=True)
    assert result.returncode == 2
    assert "usage:" in result.stderr
