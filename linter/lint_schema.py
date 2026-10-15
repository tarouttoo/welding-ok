"""Brief ↔ ok.json consistency checks for the linter (issue #3).

The linter is the deterministic half of validation: given the brief and the
contract produced from it, it checks that they agree. Engineering correctness
stays with инженерная приёмка; the linter never makes engineering decisions
(ADR 0001).

Structural validity is *not* re-implemented here: monotonic operation numbers
(issue item 2), required position/equipment/режимы (item 3) and well-formed
`КЭ<n>` sketch refs (item 5) delegate to contract/ok_schema.validate_ok and
are re-surfaced as ``structure`` findings. The boundary is fixed by
contract/README.md («Граница ответственности»).

Check ids:

- ``structure``      — contract validation failures (delegated, see above)
- ``brief``          — the brief is not parsable as a fixed-section brief
- ``weld_coverage``  — every weld of the brief is covered by some operation
- ``no_extra_welds`` — no welds in ok.json that the brief does not define

``assumptions[]`` is not a check: extract_assumptions feeds the CLI report,
which surfaces it prominently because приёмка must read it.

Welds are read from the brief's «Швы» section only: briefs are
semi-structured with fixed sections (GLOSSARY.md), and «Швы» is where welds
are defined — mentions in other sections are references, not definitions.
Weld ids are canonicalized to ``Ш<n>`` (``Ш01`` ≡ ``Ш1``) before comparison.

Keys are latin snake_case; values that land in the ОК are Russian. Infra
messages (findings, CLI) are English and quote Russian domain values.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_CONTRACT_DIR = Path(__file__).resolve().parents[1] / "contract"
if str(_CONTRACT_DIR) not in sys.path:
    sys.path.insert(0, str(_CONTRACT_DIR))

from ok_schema import WELD_RE, validate_ok  # noqa: E402

CHECK_STRUCTURE = "structure"
CHECK_BRIEF = "brief"
CHECK_WELD_COVERAGE = "weld_coverage"
CHECK_NO_EXTRA_WELDS = "no_extra_welds"

# Fixed brief sections (GLOSSARY.md); the linter needs exactly this one.
WELDS_SECTION = "Швы"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$", re.MULTILINE)
# Ш<n> as a standalone token in running text: not glued to letters (СШ1, ША5).
_BRIEF_WELD_RE = re.compile(r"(?<![A-Za-zА-ЯЁа-яё])Ш(\d+)(?![A-Za-zА-ЯЁа-яё])")


@dataclass
class Finding:
    """One lint failure, attributed to the check that produced it."""

    check: str
    message: str

    def __str__(self) -> str:
        return f"{self.check}: {self.message}"


@dataclass
class BriefWelds:
    """Welds defined by the brief, plus problems that made them unusable."""

    welds: list[str]  # canonical Ш<n>, sorted by number
    problems: list[str]


def extract_brief_welds(text: str) -> BriefWelds:
    """Extract the welds defined by the brief's «Швы» section."""
    section = _extract_section(text, WELDS_SECTION)
    if section is None:
        return BriefWelds([], [f'required section "{WELDS_SECTION}" not found in the brief'])
    welds = sorted({f"Ш{int(m.group(1))}" for m in _BRIEF_WELD_RE.finditer(section)}, key=_weld_sort_key)
    problems = [] if welds else [f'no welds (Ш<n>) found in section "{WELDS_SECTION}"']
    return BriefWelds(welds, problems)


def ok_welds(ok_data: Any) -> list[str]:
    """Canonical welds referenced by ok.json (well-formed entries only; the
    rest are reported by the contract validator)."""
    if not isinstance(ok_data, dict):
        return []
    documents = ok_data.get("documents")
    if not isinstance(documents, list):
        return []
    welds: set[str] = set()
    for document in documents:
        if not isinstance(document, dict):
            continue
        operations = document.get("operations")
        if not isinstance(operations, list):
            continue
        for operation in operations:
            if not isinstance(operation, dict):
                continue
            weld_list = operation.get("welds")
            if not isinstance(weld_list, list):
                continue
            for weld in weld_list:
                if isinstance(weld, str) and WELD_RE.match(weld):
                    welds.add(f"Ш{int(weld[1:])}")
    return sorted(welds, key=_weld_sort_key)


def extract_assumptions(ok_data: Any) -> list[str] | None:
    """``assumptions[]`` of the single document; None when not well-formed
    (malformed assumptions are already a ``structure`` finding)."""
    if not isinstance(ok_data, dict):
        return None
    documents = ok_data.get("documents")
    if not isinstance(documents, list) or len(documents) != 1 or not isinstance(documents[0], dict):
        return None
    assumptions = documents[0].get("assumptions")
    if not isinstance(assumptions, list) or not all(isinstance(item, str) for item in assumptions):
        return None
    return assumptions


def lint(brief_text: str, ok_data: Any) -> list[Finding]:
    """Run every check. Returns all findings; empty list = consistent."""
    findings = [Finding(CHECK_STRUCTURE, str(error)) for error in validate_ok(ok_data)]

    brief = extract_brief_welds(brief_text)
    if brief.problems:
        # Without the brief's welds a coverage comparison would mislead.
        return findings + [Finding(CHECK_BRIEF, problem) for problem in brief.problems]

    ok = ok_welds(ok_data)
    findings += [
        Finding(CHECK_WELD_COVERAGE, f"weld {weld} from the brief is not covered by any operation")
        for weld in brief.welds
        if weld not in ok
    ]
    findings += [
        Finding(CHECK_NO_EXTRA_WELDS, f"weld {weld} in ok.json is not defined in the brief")
        for weld in ok
        if weld not in brief.welds
    ]
    return findings


# ---------------------------------------------------------------------------
# helpers


def _extract_section(text: str, title: str) -> str | None:
    """Body of the first markdown section titled ``title`` (any heading level);
    the section ends at the next heading."""
    headings = list(_HEADING_RE.finditer(text))
    for i, heading in enumerate(headings):
        if heading.group(2).strip() != title:
            continue
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        return text[heading.end() : end]
    return None


def _weld_sort_key(weld: str) -> int:
    return int(weld[1:])
