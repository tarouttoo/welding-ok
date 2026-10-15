"""Structural validation for the ok.json contract (ADR 0001, issue #1).

The agent emits ok.json; the linter and renderer consume it. This module owns
*structural* validity only: field presence, types, value patterns and
intra-document invariants (monotonic numbering, weld uniqueness, current type
vs polarity). Checks that need the brief (weld coverage, режимы plausibility,
material range) belong to the linter; see contract/README.md for the boundary.

Keys are latin snake_case; values that land in the ОК are Russian. The
normative field reference is contract/README.md (Russian, ГОСТ terms intact).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# v1 scope (AGENTS.md, issue #1): РД only, УОНИ-13/55 only, one ОК per product.
V1_PROCESS = "РД"
V1_ELECTRODE_TYPE = "УОНИ-13/55"

# Род тока / полярность: values land in the ОК, so they are Russian.
CURRENT_TYPES = ("постоянный", "переменный")
POLARITIES = ("прямая", "обратная")

# Шов по нумерации чертежа (Ш1, Ш2, …); заглушка-ссылка на эскиз КЭ (КЭ1, КЭ2, …).
WELD_RE = re.compile(r"^Ш\d+$")
SKETCH_RE = re.compile(r"^КЭ\d+$")

PRODUCT_KEYS = {"name", "material", "process"}
DOCUMENT_KEYS = {"operations", "assumptions"}
OPERATION_KEYS = {"number", "position", "equipment", "params", "welds", "sketch_refs", "transitions"}
PARAMS_KEYS = {"current_type", "current_a", "polarity", "electrode_diameter_mm", "pass_count"}
EQUIPMENT_KEYS = {"electrode_type"}
TRANSITION_KEYS = {"number", "description"}
TOP_LEVEL_KEYS = {"product", "documents"}


@dataclass
class ContractError:
    """One validation failure, located by a JSON-path-like string.

    ``path`` uses the shape ``documents[0].operations[1].welds[2]``; the top
    level is the empty string.
    """

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}" if self.path else self.message


def validate_ok(data: Any) -> list[ContractError]:
    """Validate decoded ok.json. Returns every structural error; empty = valid."""
    errors: list[ContractError] = []
    if not isinstance(data, dict):
        _fail(errors, "", f"top level must be a JSON object, got {_typename(data)}")
        return errors
    _check_keys(data, "", TOP_LEVEL_KEYS, errors)

    product = data.get("product")
    if isinstance(product, dict):
        _validate_product(product, errors)
    elif "product" in data:
        _fail(errors, "product", f"must be a JSON object, got {_typename(product)}")

    documents = data.get("documents")
    if isinstance(documents, list):
        if len(documents) != 1:
            _fail(
                errors,
                "documents",
                f"v1 requires exactly one ОК document (one ОК per product), got {len(documents)}",
            )
        for i, document in enumerate(documents):
            if isinstance(document, dict):
                _validate_document(document, f"documents[{i}]", errors)
            else:
                _fail(errors, f"documents[{i}]", f"must be a JSON object, got {_typename(document)}")
    elif "documents" in data:
        _fail(errors, "documents", f"must be an array, got {_typename(documents)}")
    return errors


# ---------------------------------------------------------------------------
# product


def _validate_product(product: dict, errors: list[ContractError]) -> None:
    _check_keys(product, "product", PRODUCT_KEYS, errors)
    _str_field(product, "product", errors, "name")
    _str_field(product, "product", errors, "material")
    process = _str_field(product, "product", errors, "process")
    if process is not None and process != V1_PROCESS:
        _fail(errors, "product.process", f"v1 supports only {V1_PROCESS!r}, got {process!r}")


# ---------------------------------------------------------------------------
# document


def _validate_document(document: dict, path: str, errors: list[ContractError]) -> None:
    _check_keys(document, path, DOCUMENT_KEYS, errors)

    assumptions = _list_field(document, path, errors, "assumptions")
    if assumptions is not None:
        for i, item in enumerate(assumptions):
            if not _is_nonempty_str(item):
                _fail(errors, f"{path}.assumptions[{i}]", f"must be a non-empty string, got {_typename(item)}")

    operations = _list_field(document, path, errors, "operations")
    if operations is None:
        return
    if not operations:
        _fail(errors, f"{path}.operations", "at least one operation is required")
        return

    prev_number: int | None = None
    weld_owner: dict[str, str] = {}  # weld -> operation label that already covers it
    for i, operation in enumerate(operations):
        op_path = f"{path}.operations[{i}]"
        if not isinstance(operation, dict):
            _fail(errors, op_path, f"must be a JSON object, got {_typename(operation)}")
            continue
        _validate_operation(operation, op_path, errors)

        number = operation.get("number")
        if _is_int(number):
            if prev_number is not None and number <= prev_number:
                _fail(
                    errors,
                    f"{op_path}.number",
                    f"operation numbers must strictly increase, got {number} after {prev_number}",
                )
            prev_number = number
            label = f"operation {number}"
        else:
            label = f"operations[{i}]"

        welds = operation.get("welds")
        if isinstance(welds, list):
            for k, weld in enumerate(welds):
                if not (isinstance(weld, str) and WELD_RE.match(weld)):
                    continue  # pattern errors are reported by _validate_operation
                owner = weld_owner.get(weld)
                if owner is not None and owner != label:
                    _fail(
                        errors,
                        f"{op_path}.welds[{k}]",
                        f"weld {weld} is already covered by {owner}; each weld is covered by exactly one operation",
                    )
                elif owner is None:
                    weld_owner[weld] = label


# ---------------------------------------------------------------------------
# operation


def _validate_operation(operation: dict, path: str, errors: list[ContractError]) -> None:
    _check_keys(operation, path, OPERATION_KEYS, errors)

    number = _int_field(operation, path, errors, "number")
    if number is not None and number < 1:
        _fail(errors, f"{path}.number", "must be >= 1")
    _str_field(operation, path, errors, "position")

    equipment = _object_field(operation, path, errors, "equipment")
    if equipment is not None:
        _check_keys(equipment, f"{path}.equipment", EQUIPMENT_KEYS, errors)
        electrode_type = _str_field(equipment, f"{path}.equipment", errors, "electrode_type")
        if electrode_type is not None and electrode_type != V1_ELECTRODE_TYPE:
            _fail(
                errors,
                f"{path}.equipment.electrode_type",
                f"v1 supports only {V1_ELECTRODE_TYPE!r}, got {electrode_type!r}",
            )

    params = _object_field(operation, path, errors, "params")
    if params is not None:
        _validate_params(params, f"{path}.params", errors)

    _pattern_list(operation, path, errors, "welds", WELD_RE, "Ш<n>", "Ш1")
    _pattern_list(operation, path, errors, "sketch_refs", SKETCH_RE, "КЭ<n>", "КЭ1")

    transitions = _list_field(operation, path, errors, "transitions")
    if transitions is not None:
        if not transitions:
            _fail(errors, f"{path}.transitions", "at least one transition is required")
        else:
            _validate_transitions(transitions, f"{path}.transitions", errors)


def _validate_params(params: dict, path: str, errors: list[ContractError]) -> None:
    _check_keys(params, path, PARAMS_KEYS, errors)

    current_type = _enum_str(params, path, "current_type", CURRENT_TYPES, errors)
    if current_type == "постоянный":
        _enum_str(params, path, "polarity", POLARITIES, errors)
    elif current_type == "переменный" and params.get("polarity") is not None:
        _fail(
            errors,
            f"{path}.polarity",
            'must be omitted when current_type is "переменный" (полярность задаётся только для постоянного тока)',
        )

    current_a = _num_field(params, path, errors, "current_a")
    if current_a is not None and current_a <= 0:
        _fail(errors, f"{path}.current_a", "must be > 0")
    diameter = _num_field(params, path, errors, "electrode_diameter_mm")
    if diameter is not None and diameter <= 0:
        _fail(errors, f"{path}.electrode_diameter_mm", "must be > 0")
    passes = _int_field(params, path, errors, "pass_count")
    if passes is not None and passes < 1:
        _fail(errors, f"{path}.pass_count", "must be >= 1")


def _validate_transitions(transitions: list, path: str, errors: list[ContractError]) -> None:
    prev_number: int | None = None
    for i, transition in enumerate(transitions):
        tr_path = f"{path}[{i}]"
        if not isinstance(transition, dict):
            _fail(errors, tr_path, f"must be a JSON object, got {_typename(transition)}")
            continue
        _check_keys(transition, tr_path, TRANSITION_KEYS, errors)
        number = _int_field(transition, tr_path, errors, "number")
        if number is not None:
            if number < 1:
                _fail(errors, f"{tr_path}.number", "must be >= 1")
            elif prev_number is not None and number <= prev_number:
                _fail(
                    errors,
                    f"{tr_path}.number",
                    f"transition numbers must strictly increase, got {number} after {prev_number}",
                )
            prev_number = number
        _str_field(transition, tr_path, errors, "description")


# ---------------------------------------------------------------------------
# field helpers: every failure becomes a per-field ContractError


def _fail(errors: list[ContractError], path: str, message: str) -> None:
    errors.append(ContractError(path, message))


def _typename(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _check_keys(obj: dict, path: str, allowed: set[str], errors: list[ContractError]) -> None:
    for key in sorted(allowed):
        if key not in obj:
            _fail(errors, _join(path, key), "required field is missing")
    for key in sorted(obj):
        if key not in allowed:
            _fail(errors, _join(path, key), f"unknown field (allowed: {', '.join(sorted(allowed))})")


def _str_field(container: dict, path: str, errors: list[ContractError], key: str) -> str | None:
    if key not in container:
        return None  # missing-field already reported by _check_keys
    value = container[key]
    field = _join(path, key)
    if not isinstance(value, str):
        _fail(errors, field, f"must be a string, got {_typename(value)}")
        return None
    if not value.strip():
        _fail(errors, field, "must be a non-empty string")
        return None
    return value


def _enum_str(container: dict, path: str, key: str, allowed: tuple[str, ...], errors: list[ContractError]) -> str | None:
    value = _str_field(container, path, errors, key)
    if value is None:
        return None
    if value not in allowed:
        options = ", ".join(repr(option) for option in allowed)
        _fail(errors, _join(path, key), f"must be one of {options}, got {value!r}")
        return None
    return value


def _num_field(container: dict, path: str, errors: list[ContractError], key: str) -> float | None:
    if key not in container:
        return None
    value = container[key]
    if not _is_num(value):
        _fail(errors, _join(path, key), f"must be a number, got {_typename(value)}")
        return None
    return value


def _int_field(container: dict, path: str, errors: list[ContractError], key: str) -> int | None:
    if key not in container:
        return None
    value = container[key]
    if not _is_int(value):
        _fail(errors, _join(path, key), f"must be an integer, got {_typename(value)}")
        return None
    return value


def _list_field(container: dict, path: str, errors: list[ContractError], key: str) -> list | None:
    if key not in container:
        return None
    value = container[key]
    if not isinstance(value, list):
        _fail(errors, _join(path, key), f"must be an array, got {_typename(value)}")
        return None
    return value


def _object_field(container: dict, path: str, errors: list[ContractError], key: str) -> dict | None:
    if key not in container:
        return None
    value = container[key]
    if not isinstance(value, dict):
        _fail(errors, _join(path, key), f"must be an object, got {_typename(value)}")
        return None
    return value


def _pattern_list(
    container: dict,
    path: str,
    errors: list[ContractError],
    key: str,
    pattern: re.Pattern[str],
    expected: str,
    example: str,
) -> list[str] | None:
    items = _list_field(container, path, errors, key)
    if items is None:
        return None
    field = _join(path, key)
    if not items:
        _fail(errors, field, f"must contain at least one entry ({expected})")
        return None
    valid: list[str] = []
    for i, item in enumerate(items):
        if isinstance(item, str) and pattern.match(item):
            valid.append(item)
        else:
            _fail(errors, f"{field}[{i}]", f"must be {expected}, got {_typename(item)} {item!r} (e.g. {example!r})")
    duplicates = sorted({item for item in valid if valid.count(item) > 1})
    if duplicates:
        _fail(errors, field, f"duplicate entries in one list: {', '.join(duplicates)}")
    return valid
