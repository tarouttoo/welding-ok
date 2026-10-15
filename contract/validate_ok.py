#!/usr/bin/env python3
"""Validation CLI for the ok.json contract (issue #1).

Usage:
    python3 contract/validate_ok.py <ok.json>

Exit codes:
    0  valid contract
    1  invalid contract or malformed JSON (every error printed as one line)
    2  usage or file-read error

Error lines use the shape ``error: documents[0].operations[1].welds[2]: ...``
so each failure points at its field. The normative contract spec (Russian) is
contract/README.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ok_schema import validate_ok


def main(argv: list[str]) -> int:
    args = argv[1:]
    if len(args) != 1:
        print("usage: python3 contract/validate_ok.py <ok.json>", file=sys.stderr)
        return 2
    if args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    path = Path(args[0])
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        return 2

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"error: {path} is not valid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        return 1

    errors = validate_ok(data)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        print(f"invalid: {len(errors)} error(s) in {path}", file=sys.stderr)
        return 1

    operations = data["documents"][0]["operations"]
    welds = sorted({weld for operation in operations for weld in operation["welds"]})
    print(
        f"valid ok.json: product {data['product']['name']!r} "
        f"({data['product']['material']}, {data['product']['process']}), "
        f"1 document, {len(operations)} operation(s), welds {', '.join(welds)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
