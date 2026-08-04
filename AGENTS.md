# scipion-em — developer manual for AI agents

Read this before making changes here. Written for an AI coding agent, not end users — see `README.rst` for that.

For deeper, less-frequently-needed context, see:
- [`.ai/tech-debt.md`](.ai/tech-debt.md) — known problem areas, with file:line
- [`.ai/roadmap.md`](.ai/roadmap.md) — planned/likely future work (draft, pending team review)

## What this repo is

The electron-microscopy domain layer of Scipion. Depends on `scipion-pyworkflow` (the domain-agnostic workflow engine below it), and is itself depended on by `scipion-app` (installer/launcher) and every external EM plugin (scipion-em-xmipp, scipion-em-relion, etc. — not in this workspace, but real and load-bearing, see below).

## Architecture map

- `pwem/objects/data.py` (~2800 lines) — the EM domain object hierarchy: `EMObject → Image → Micrograph/Particle/Volume/Movie`, `EMSet(Set, EMObject) → SetOfImages → SetOfMicrographs/SetOfParticles/...` (40+ classes). This is what every EM protocol reads/writes.
- `pwem/protocols/` — ~30 `protocol_*.py` files, all inheriting from `pyworkflow.protocol.Protocol`.
- `pwem/emlib/` — optional binding to Xmipp (`emlib/lib.py` tries `from xmippLib import *`, falls back to `_libNone.py` with a warning if Xmipp isn't installed — expect reduced functionality, not a hard error, when it's absent).
- `pwem/viewers/` — includes a substantial amount of GUI code (`wizards/wizard.py` 1481 lines, `viewers/viewer_coordinates.py` 1275 lines, plus more) even though this is nominally the "domain" layer, not the UI layer (`scipion-app` is). Not necessarily wrong — viewers are part of the plugin contract — but a real cross-cutting responsibility worth knowing about.
- `pwem/tests/` — 43 files / 275+ test items, `unittest.TestCase`-style. **`TestWorkflow`, `TestImportBase`-style base classes here are treated the same as `pyworkflow`'s `BaseTest` — do not rewrite the class hierarchy.** Confirmed (GitHub code search) that `pwem.tests.workflows.TestWorkflow` specifically is subclassed by real external plugins: `I2PC/scipion-em-xmipp`, `scipion-em-relion`, `scipion-em-prody`, `scipion-em-spider`, `scipion-em-imagic`. New test coverage should be additive (new files, new conftest-level infra), never a restructure of existing test classes.
- `pwem/tests/conftest.py` — purely additive test infra (doesn't touch the classes above): bootstraps a global `hosts.conf` (missing otherwise — `BaseTest.setUpClass` doesn't call `setupTestProject(..., writeLocalConfig=True)`), triggers plugin/dataset discovery (`pw.Config.getDomain().getPlugins()` — never happens automatically under plain pytest/unittest), and wraps `DataSet.getDataSet` to skip cleanly (not error) when a real EM dataset isn't locally synced and `SCIPION_TEST_NOSYNC=1`.

## Conventions actually used here

- camelCase throughout the public API, same as pyworkflow.
- GPL header block on every file.
- Deferred/inline imports inside methods used deliberately in several places in `pwem/objects/data.py` (e.g. lines 615, 879, 1078, 1186 — `from pwem import Domain`) to avoid import cycles.
- Default to writing no comments explaining *what*; only *why* when genuinely non-obvious.

## Testing

- `pwem/tests/*` is **not** rewritten to pytest-native style (see Architecture map above for why) — it runs fine under pytest as-is since pytest collects `unittest.TestCase` natively.
- Default CI-gating job runs a **hermetic subset only**: `pwem/tests/` minus `workflows/` (needs Xmipp/Relion/EMAN2/Chimera/Coot/Refmac + sometimes GPU — not installable in lightweight CI), minus 3 files with a hard `from xmipp3 import ...` (the real `scipion-em-xmipp` plugin, a separate heavy repo — not the lightweight `pyxmipp3` bindings package), minus `test_projection_edit.py` (hardcodes network downloads, bypasses the `SCIPION_TEST_NOSYNC` convention), with `test_notifier.py::test_projectNotifier` deselected (hits a live external analytics endpoint). All of this is explicit in `pyproject.toml`'s `addopts`, not silent.
- Tests needing real EM datasets show up as clearly-labeled `SKIPPED`, not failures, when the data isn't locally synced (see conftest.py above) — currently ~101 of the suite.
- A separate `collect-smoke` CI job does `pytest --collect-only` across the *whole* tree (workflows included) to catch import/syntax breakage across Python versions cheaply, without needing any of the external tools.
- Run locally: `pip install -e .[test]` then `pytest pwem/tests`.

## Known gotchas

- Same `SCIPION_HOME`-before-first-import rule as pyworkflow applies here too.
- `emlib/lib.py` degrades silently (not an error) if Xmipp isn't installed — don't assume a missing-Xmipp-feature bug is actually a bug; check whether it's this fallback first.
- `pwem/viewers/viewers_data.py:266,304` has a `# FIXME: Remove dependency on xmipp3 plugin to visualize coordinates` — core-layer code coupled to one specific external plugin.
- If you're extending `pwem/tests/`, prefer new standalone test files or conftest-level infra over touching existing test classes — see the ecosystem-reuse note above, it's not hypothetical.

## Real EM dependencies mixed in

`pwem/emlib/` and several viewer modules assume domain-specific tools (Xmipp, PDB/atomic-structure libraries) may or may not be present. This repo is explicitly designed to degrade gracefully rather than hard-fail when they're missing — keep that pattern when adding anything that touches an optional external tool.

## Keeping this document current

This file describes the repo as of the last time someone updated it — it will drift out of date as the code changes. If your change touches anything described above (architecture map, conventions, testing setup, gotchas), update the relevant section in this file as part of the same change, not as a separate follow-up. Don't wait to be asked.
