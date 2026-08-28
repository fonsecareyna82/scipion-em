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

## `ProtCreateStreamData`'s "synthetic data" mode isn't actually plugin-free

`SET_OF_RANDOM_MICROGRAPHS` mode (`pwem/protocols/protocol_create_stream_data.py`'s `createRandomMicStep`) calls `Domain.importFromPlugin('xmipp3', 'Plugin', ...)` and runs `xmipp_transform_filter` - despite being the one mode that doesn't need a real pre-existing input Set, it still needs Xmipp installed. Found while trying to build a plugin-free streaming test (2026-08-04) - see `.ai/roadmap.md`.

## Core code hard-locked to one specific EM plugin (audit, 2026-08-27)

Full audit of `Domain.importFromPlugin(...)` across `pwem/` (excluding tests), triggered by the `ProtCreateStreamData` fix above raising the same question more broadly: where else does supposedly plugin-agnostic core code actually require one specific plugin (xmipp3/eman2/cistem/relion/...) to be installed? Triaged into three buckets:

**Confirmed problem - generic operation locked to one arbitrary plugin, should not need any:**
- `pwem/emlib/image/image_handler.py`'s `ImageHandler` - **the single most central image class in `pwem`** - has **6 methods** (`createCircularMask`, `rotateVolume`, `addNoise`, `truncateMask` [2 xmipp calls: threshold, optional resize], `computeThumbnail`, `scaleFourier`/downsample) that are thin wrappers around private `__runXmippProgram`/`__runEman2Program` helpers, i.e. they shell out to xmipp3 (5 methods) or eman2 (`computeThumbnail`) command-line binaries. Any pwem protocol or test calling e.g. `ImageHandler().createCircularMask(...)` fails without xmipp3 installed, despite `ImageHandler` being pwem's own core image utility. **Biggest single finding, still not fixed** - each method needs a real numpy/emlib-native reimplementation (or, for 2 of them, just rewiring to an already-native emlib method - see the plan), not a one-line swap like `ProtCreateStreamData`'s was. A phased, per-method plan (ordered by real algorithmic difficulty, not alphabetically) is in `.ai/roadmap.md`.
- `pwem/protocols/parallel.py` (`ProtTestParallel`) - **[Fixed 2026-08-27]** legacy test protocol shelling to `xmipp_work_test`. Confirmed dead: no test or workflow referenced it, and it wasn't even hidden from the GUI (`Protocol` base, not `ProtTests`) unlike its modern replacement. Deleted - `ProtTestQueue` (`pwem/protocols/protocol_tests.py`, built 2026-08-04) already covers the same parallel/queue-testing need, plugin-free and properly hidden.
- `pwem/protocols/protocol_align_movies.py`'s `ProtAlignMovies.computeThumbnail()` - **[Fixed 2026-08-27]** a second, independent copy of the same anti-pattern: this base class (inherited by every plugin's movie-alignment protocol) shelled out to eman2's `e2proc2d.py --meanshrink --fixintscaling=sane` just to mean-shrink and contrast-normalize a preview image. Also carried a dead, unused duplicate of `ImageHandler`'s `__runXmippProgram` helper (copy-pasted, never called - removed too). Reimplemented in-process: numpy block-mean downsampling + percentile-based contrast stretch to uint8, written via PIL (already a pwem dependency, same pattern `ImageHandler.scale2DStack` already uses elsewhere in the codebase). New test: `pwem/tests/protocols/test_protocol_align_movies.py`. `ImageHandler.computeThumbnail` (a *different*, still-eman2-coupled method with different args - `--fouriershrink`/`--process normalize`) is a separate, still-open instance of the same problem, tracked as one of the 8 `ImageHandler` methods above.
- `pwem/viewers/showj.py:302` (`runJavaIJapp`) - **[Investigated 2026-08-27, legitimate]** needs `xmipp3.Plugin.getEnviron()` to launch `xmipp.viewer.scipion.ScipionViewer` - confirmed via the module's own docstring ("This data visualization tool was first called xmipp_show... became xmipp_showj") that "showj" **is** Xmipp-authored Java software, not a generic pwem feature that happens to reach for xmipp3. Not independently fixable without replacing the whole legacy Tkinter+Java viewer stack - tied to the ecosystem-wide "Remove Tkinter entirely" item, not a standalone bug.
- `pwem/viewers/viewers_data.py:266,304` - **[Investigated 2026-08-27, legitimate, same root cause as showj.py above]** the coordinate-picking GUIs these lines feed (`xmipp.viewer.particlepicker.training.SupervisedPickerRunner`, `.tiltpair.TiltPairPickerRunner`) are also Xmipp-authored Java applications; `writeSetOfCoordinates`/`writeSetOfMicrographs` just prepare the input format that tool expects. `pwem/protocols/protocol_particles_picking.py:168`'s `readSetOfCoordinates` is the read-back half of the same flow (registers coordinates after the user picks in that same Xmipp GUI) - same category, also legitimate. None of these are fixable without replacing the picker UI itself - same "Remove Tkinter" dependency as showj.py.

**Confirmed legitimate - format-specific I/O, not an arbitrary lock-in (verified 2026-08-27, not just assumed):**
- `image_handler.py`'s narrow eman2 fallback for `.img`/dm4 format conversion (xmippLib can't read that format at all).
- `pwem/protocols/protocol_import/{coordinates,ctfs,particles,micrographs}.py` - each uses a clean `IMPORT_FROM_<TOOL>` enum dispatcher (`getImportClass()` etc.), gated behind the user's explicit "import from" choice in the form, each branch with its own descriptive `errorMsg` (e.g. "Relion is needed to import .star files"). Only ever requires the one plugin matching the format the user actually selected - correct design, not a bug.
- `pwem/cmd/convert.py` - a CLI tool explicitly for converting coordinate formats *to* Xmipp's (`--fromType {eman2,relion,dogpicker,gautomatch} --toType xmipp`, per its own `--help` text) - coupling is the tool's entire purpose, not incidental.
- `pwem/utils.py:67`'s `runProgram` - turned out to be a generic, symmetric multi-plugin dispatcher (routes to xmipp3/relion/eman2/bsoft's `getEnviron()` based on the program name's prefix) - not locked to one plugin at all, the earlier grep just caught one branch out of context.

**Not a core issue:** the 84 `ccp4.protocols`/`chimera.protocols`/`phenix.protocols` hits are all in test files (`test_protocol_export2DB.py`, `test_workflow_modeling.py`), not production code - out of scope for this finding.

## `pwem/tests/conftest.py`'s SCIPION_HOME teardown isn't concurrency-safe

The `pytest_sessionfinish` hook `shutil.rmtree`s the shared `SCIPION_HOME` (`~/.cache/scipion_pwem_test_home` by default) unconditionally. If two pytest invocations run against this repo at the same time, whichever finishes first deletes the directory out from under the other, causing cascading `SystemExit: Missing file .../hosts.conf` failures. Only bites when someone (or some tooling) runs concurrent test invocations - happened once during this session's own work. Not urgent, but a real, reproducible footgun - see `.ai/roadmap.md`.

## Runtime deprecation check

`python -W error::DeprecationWarning -c "import pwem"` (Python 3.8, `scipion-devel` env) exits clean — no active `DeprecationWarning`s fire on import as of this audit.
