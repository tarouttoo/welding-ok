---
status: accepted
---

# Issue-driven AFK pipeline via Sandcastle (ported)

Ported from `real-engineering-skills` (see its ADR 0001 for the full history).
Tool development happens through GitHub issues implemented unattended by
[mattpocock/sandcastle](https://github.com/mattpocock/sandcastle) driving the
`pi` agent (`glm-5.3-flash` on `zai`), in a rootless Podman sandbox, from the
hosted workflow `.github/workflows/agent-implement.yml`. Each run implements
one issue on its own branch, reports on the issue, and opens a pull request.

Differences from the source repo:

- **Real ОК generation is NOT issue-driven.** When the engineer needs an
  operation card at work, they run the pi skill locally and interactively;
  sandcastle exists here only to develop the tool itself.
- **Containerfile installs Python 3 + openpyxl + pytest** alongside Node/pi,
  because the renderer and linter are Python.
- **The AFK prompt forbids committing anything from `briefs/`** (ADR 0002).

Operational quirks carried over verbatim: the image is named after the checkout
directory (`sandcastle:welding-ok`) and there is no unsandboxed fallback; only
`GH_TOKEN`, `GH_REPO`, `ZAI_API_KEY` enter the container; opening PRs works
only while the repo setting "Allow GitHub Actions to create and approve pull
requests" is enabled — when that step fails, re-check the checkbox in the UI
(Settings → Actions → General → Workflow permissions), the API PATCH does not
persist.
