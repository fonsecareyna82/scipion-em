# Tech debt — scipion-em

Findings from a real audit of this repo (2026-08-04), not a wishlist. Cited so they're checkable, not just asserted.

## Explicit TODO/FIXME markers worth knowing about

- `pwem/protocols/protocol_particles.py:419,429` — `# TODO: this takes forever` / `# FIXME: Temporary to avoid loadAllPropertiesFail` — real performance concern, unresolved.
- `pwem/viewers/viewers_data.py:266,304` — `# FIXME: Remove dependency on xmipp3 plugin to visualize coordinates` — core-layer code coupled to one specific external plugin (see AGENTS.md).
- `pwem/protocols/protocol_base_flexhub.py:35` — `# FIXME: Do not use this methods and remove in the future`
- `pwem/convert/symmetry.py:1457-1463` — 4 branches marked `# TODO: Untested`.

71 total TODO/FIXME/XXX/HACK markers repo-wide as of this audit — the above are the ones describing a concrete, non-noise problem.

## Cross-cutting responsibility

- `pwem/viewers/` and `pwem/wizards/` contain a substantial amount of GUI (Tkinter) code — `wizards/wizard.py` (1481 lines), `viewers/viewer_coordinates.py` (1275 lines), plus `views.py`/`viewer_volumes.py` and several 3D wizards, roughly 3800 lines total. `scipion-em` is nominally the domain/data layer, not the UI layer (`scipion-app` is) — this isn't necessarily wrong (viewers are part of the plugin contract every EM plugin implements) but it's a real cross-cutting responsibility worth being aware of before assuming "GUI code belongs in scipion-app, full stop."

## Duplication

- `pwem/convert/utils.py:60-112` (`downloadPdb`/`__unzipPdb`) is one of three independent download/HTTP implementations across the ecosystem (the others are in `pyworkflow/webservices/` and `scipion-app/scipion/install/plugin_funcs.py`) — no shared helper exists.

## Largest files

`pwem/objects/data.py` (2811 lines — the core EM object hierarchy, expect wide blast radius from any change), `pwem/convert/transformations.py` (1964 lines), `pwem/wizards/wizard.py` (1481 lines), `pwem/convert/symmetry.py` (1480 lines), `pwem/viewers/viewer_coordinates.py` (1275 lines).

## Test suite state (context, not new debt — see AGENTS.md for the full picture)

271 test items in `pwem/tests/`, hermetic subset (97 tests as of the last CI run) actually gates PRs; 103 skip cleanly for needing real EM datasets; `workflows/` (7 remaining files, down from 10) needs external EM tools not installable in lightweight CI. The `workflows/` plugin-dependency audit itself is done - see [`.ai/roadmap.md`](roadmap.md) for what was resolved, what's a follow-up (fake local queue, `ProtCreateStreamData`'s hidden xmipp3 dependency), and the still-open dataset-dependent-tests audit.

## `ProtCreateStreamData`'s "synthetic data" mode isn't actually plugin-free (Fixed 2026-08-27)

`SET_OF_RANDOM_MICROGRAPHS` mode (`pwem/protocols/protocol_create_stream_data.py`'s `createRandomMicStep`) used to call `Domain.importFromPlugin('xmipp3', 'Plugin', ...)` and run `xmipp_transform_filter` just to apply a CTF - despite being the one mode that doesn't need a real pre-existing input Set, it still needed Xmipp installed. Found while trying to build a plugin-free streaming test (2026-08-04). Fixed by switching to `emlib.applyCTF`, a base `xmippLib` binding already bundled with `pwem` (not the `xmipp3` plugin) - see `.ai/roadmap.md`.

## `pwem/tests/conftest.py`'s SCIPION_HOME teardown isn't concurrency-safe

The `pytest_sessionfinish` hook `shutil.rmtree`s the shared `SCIPION_HOME` (`~/.cache/scipion_pwem_test_home` by default) unconditionally. If two pytest invocations run against this repo at the same time, whichever finishes first deletes the directory out from under the other, causing cascading `SystemExit: Missing file .../hosts.conf` failures. Only bites when someone (or some tooling) runs concurrent test invocations - happened once during this session's own work. Not urgent, but a real, reproducible footgun - see `.ai/roadmap.md`.

## Runtime deprecation check

`python -W error::DeprecationWarning -c "import pwem"` (Python 3.8, `scipion-devel` env) exits clean — no active `DeprecationWarning`s fire on import as of this audit.
