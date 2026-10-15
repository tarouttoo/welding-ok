#!/usr/bin/env python3
"""Linter CLI: brief ↔ ok.json consistency checks (issue #3).

Usage:
    python3 linter/lint_ok.py <brief.md> <ok.json>

Exit codes:
    0  clean — the brief and the contract agree
    1  findings or malformed JSON (each finding printed as one line
       ``error: <check>: <message>``; check ids in linter/README.md)
    2  usage or file-read error

The report always surfaces ``assumptions[]`` prominently — инженерная
приёмка must read them; assumptions never fail the lint. Findings go to
stderr, the report to stdout. Structural checks delegate to
contract/ok_schema.py (see contract/README.md, «Граница ответственности»).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from lint_schema import extract_assumptions, lint, ok_welds


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if len(args) != 2:
        print("usage: python3 linter/lint_ok.py <brief.md> <ok.json>", file=sys.stderr)
        return 2

    texts: list[str] = []
    for arg in args:
        path = Path(arg)
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except OSError as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            return 2
    brief_text, ok_text = texts
    brief_path, ok_path = Path(args[0]), Path(args[1])

    try:
        ok_data: Any = json.loads(ok_text)
    except json.JSONDecodeError as exc:
        print(f"error: {ok_path} is not valid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        return 1

    findings = lint(brief_text, ok_data)
    _print_assumptions(ok_data)

    if findings:
        for finding in findings:
            print(f"error: {finding}", file=sys.stderr)
        failed = ", ".join(sorted({finding.check for finding in findings}))
        print(f"invalid: {len(findings)} finding(s); failed checks: {failed}", file=sys.stderr)
        return 1

    welds = ", ".join(ok_welds(ok_data))
    print(f"ok: {brief_path} ↔ {ok_path}: consistent (welds {welds})")
    return 0


def _print_assumptions(ok_data: Any) -> None:
    """Surface assumptions prominently in the report (issue item 4)."""
    assumptions = extract_assumptions(ok_data)
    if assumptions is None:
        return  # not well-formed: already a structure finding
    if not assumptions:
        print("assumptions: none")
        return
    print(f"assumptions ({len(assumptions)}) — must be read at приёмка:")
    for i, assumption in enumerate(assumptions, 1):
        print(f"  {i}. {assumption}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
