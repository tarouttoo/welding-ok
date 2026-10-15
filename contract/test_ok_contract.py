"""Tests for the ok.json contract validator (issue #1).

Acceptance: the valid synthetic example passes, malformed input fails with
clear per-field errors, and the example round-trips. The example file must
stay in canonical form: ``json.dumps(data, ensure_ascii=False, indent=2) + "\\n"``.
"""

from __future__ import annotations

import json
from pathlib import Path

from ok_schema import ContractError, validate_ok

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "minimal" / "ok.json"


def _load_example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _validate_mutated(mutate) -> list[ContractError]:
    data = _load_example()
    mutate(data)
    return validate_ok(data)


# --- acceptance: the valid example passes and round-trips -------------------


def test_minimal_example_is_valid() -> None:
    assert validate_ok(_load_example()) == []


def test_minimal_example_round_trips() -> None:
    data = _load_example()
    canonical = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    assert EXAMPLE.read_text(encoding="utf-8") == canonical  # file is canonical
    assert validate_ok(json.loads(canonical)) == []  # round-trip is valid
    assert json.loads(canonical) == data  # round-trip is lossless


def test_empty_assumptions_list_is_valid() -> None:
    errors = _validate_mutated(lambda d: d["documents"][0].__setitem__("assumptions", []))
    assert errors == []


# --- malformed input fails with per-field errors ----------------------------


def test_missing_required_field_reports_path() -> None:
    errors = _validate_mutated(lambda d: d["product"].pop("name"))
    assert any(e.path == "product.name" and "missing" in e.message for e in errors)


def test_unknown_field_is_rejected() -> None:
    errors = _validate_mutated(lambda d: d["product"].__setitem__("thikness_mm", 4))
    assert any(e.path == "product.thikness_mm" and "unknown field" in e.message for e in errors)


def test_bad_weld_reference_pattern() -> None:
    errors = _validate_mutated(lambda d: d["documents"][0]["operations"][0].__setitem__("welds", ["ш1"]))
    assert any(e.path == "documents[0].operations[0].welds[0]" and "Ш<n>" in e.message for e in errors)


def test_operation_numbers_must_strictly_increase() -> None:
    def mutate(d: dict) -> None:
        d["documents"][0]["operations"][0]["number"] = 2
        d["documents"][0]["operations"].append(dict(d["documents"][0]["operations"][0], number=2, welds=["Ш3"]))

    errors = _validate_mutated(mutate)
    assert any("strictly increase" in e.message for e in errors)


def test_weld_covered_by_two_operations_is_rejected() -> None:
    def mutate(d: dict) -> None:
        d["documents"][0]["operations"][0]["number"] = 2
        d["documents"][0]["operations"].append(dict(d["documents"][0]["operations"][0], number=3))

    errors = _validate_mutated(mutate)
    assert any("already covered by operation 2" in e.message for e in errors)


def test_polarity_with_ac_current_is_rejected() -> None:
    def mutate(d: dict) -> None:
        params = d["documents"][0]["operations"][0]["params"]
        params["current_type"] = "переменный"

    errors = _validate_mutated(mutate)
    assert any(e.path == "documents[0].operations[0].params.polarity" for e in errors)


def test_wrong_electrode_is_rejected_in_v1() -> None:
    def mutate(d: dict) -> None:
        d["documents"][0]["operations"][0]["equipment"]["electrode_type"] = "МР-3"

    errors = _validate_mutated(mutate)
    assert any(e.path == "documents[0].operations[0].equipment.electrode_type" and "v1" in e.message for e in errors)


def test_second_document_is_rejected_in_v1() -> None:
    errors = _validate_mutated(lambda d: d["documents"].append(d["documents"][0]))
    assert any(e.path == "documents" and "exactly one" in e.message for e in errors)


def test_bad_sketch_reference_pattern() -> None:
    errors = _validate_mutated(lambda d: d["documents"][0]["operations"][0].__setitem__("sketch_refs", ["эскиз 1"]))
    assert any(e.path == "documents[0].operations[0].sketch_refs[0]" and "КЭ<n>" in e.message for e in errors)


def test_non_object_top_level_is_rejected() -> None:
    errors = validate_ok([])
    assert errors == [ContractError("", "top level must be a JSON object, got array")]


def test_product_of_wrong_type_is_rejected() -> None:
    errors = _validate_mutated(lambda d: d.__setitem__("product", "кронштейн"))
    assert any(e.path == "product" and "must be a JSON object" in e.message for e in errors)


def test_documents_of_wrong_type_is_rejected() -> None:
    errors = _validate_mutated(lambda d: d.__setitem__("documents", {}))
    assert any(e.path == "documents" and "must be an array" in e.message for e in errors)


def test_transition_without_description_is_rejected() -> None:
    errors = _validate_mutated(lambda d: d["documents"][0]["operations"][0]["transitions"][0].pop("description"))
    assert any(e.path == "documents[0].operations[0].transitions[0].description" and "missing" in e.message for e in errors)
