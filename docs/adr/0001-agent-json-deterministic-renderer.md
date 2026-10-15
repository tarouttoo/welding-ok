---
status: accepted
---

# Agent emits JSON; a deterministic renderer owns ГОСТ formatting

The first attempt at automating ОК generation had the agent produce a PDF and iteratively fix element sizes and positions, verified by machine-vision-style tests — a slow feedback loop for what is essentially a text document. We invert the split: the agent's only output is `ok.json`, the engineering content of the operation card with zero layout; a deterministic renderer (Python + openpyxl) maps that JSON into a cleanly rebuilt ГОСТ 3.1118-82 template. Format correctness holds by construction: the template is right once, and no vision or layout tests exist anywhere in the loop.

## Considered Options

- **Agent writes directly into xlsx cells** — rejected: couples the agent to layout, reintroduces a checking problem, and one hallucinated merge can corrupt the form.
- **PDF generation with vision-verification loop** — rejected: the original overkill.
- **JSON intermediary + deterministic renderer** — accepted.

## Consequences

- The JSON contract is the system's stable interface: new output formats mean a new renderer, the agent unchanged; new ГОСТ forms mean template changes, the agent unchanged.
- Comparing golden examples is structural (JSON ↔ JSON), never xlsx ↔ xlsx.
- The ГОСТ 3.1118-82 template is built from scratch; the university-supplied xlsx is kept only as a filling reference, because it was deemed visually poor and is not the spec.
