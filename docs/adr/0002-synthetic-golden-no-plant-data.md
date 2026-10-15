---
status: accepted
---

# Synthetic golden examples only; plant data never enters git

The system needs golden examples (`brief.md` → `ok.json`) to validate the agent and renderer, but real products are plant property and cannot be committed, even to a private repo. Decision: every committed example is synthetic — an invented but realistic product, hand-authored by the engineer. Real briefs live only in the gitignored `briefs/` directory and must never be staged, committed, or pasted into issues.

## Consequences

- The confidentiality guarantee reduces to one `.gitignore` line, and it survives the repo ever becoming public.
- The first real end-to-end run happens locally and validates nothing permanently; the synthetic golden example is the only durable ground truth.
