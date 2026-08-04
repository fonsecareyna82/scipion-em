# Roadmap — scipion-em

**Status: draft, pending review with Yunior (repo co-owner).** Seeded from a rough team Google Doc plus findings surfaced while doing the test/CI/Python-3.8-3.12 work on this repo (2026-08-04). Treat as a starting point, not a committed plan.

## This repo specifically

- **Audit `pwem/tests/workflows/*`'s dependency on external plugins.** Scipion the framework is meant to be independent of its plugins — plugins depend on it, not the other way around — so this repo's own tests hard-requiring Xmipp/Relion/EMAN2/Chimera/Coot/Refmac is backwards, and those tools could disappear without this repo noticing. Go through each workflow test, understand why it needs the specific external plugin, evaluate whether the same coverage is achievable without it, and where it isn't, question whether that test belongs in `scipion-em` at all vs. the dependent plugin's own repo.
- **Audit dataset-dependent tests similarly.** For the ~101 tests currently skipped for needing real EM data: download the datasets, look at what the referenced files actually contain and how each test uses them, and evaluate case-by-case whether a small synthetic fixture could replace the real dataset.
- Consider a real-dataset-sync CI job (currently deferred - network dependency on an external CNB-hosted server, slow/heavy) if the above audit concludes some tests are worth running for real in CI.
- `pwem/viewers/viewers_data.py:266,304`'s FIXME about the xmipp3 coupling — worth resolving alongside the workflows-tests audit above, since it's the same underlying "core depends on a specific plugin" pattern.

## Ecosystem-wide (applies to all 5 repos, not just this one)

- **Branch/release cleanup**: drop the redundant `master` branch, rename `devel` → `main`, replace push-triggered publish with a manual `workflow_dispatch` release gated by a protected GitHub deployment environment. `I2PC/scipion-em-xmipp`'s `.github/workflows/release.yml` is a concrete reference.
- **Remove Tkinter entirely** once ScipionAPI + ScipionWeb fully replace it (ScipionWeb replaces both the legacy Tkinter GUI and an intermediate NiceGUI attempt).
- **Convert buildbot to a GitHub Actions self-hosted runner.**
- **Set up a dependency manager (Renovate)** across all 5 repos.
