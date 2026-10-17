# Contributing and continuing the research

Start with the README's AI disclaimer and European build identifiers, then
read [the research handover](docs/research-index.md). Original project work
is MIT-licensed; do not commit game binaries, extracted assets, account
profiles, process dumps or credentials.

Record the patch SHA-256, emulator revision, backend and input method for
new results. Distinguish an input request, CPU result, native acceptance,
rendered sample and completed gameplay sequence. Describe any fixture or
forced setup explicitly. Do not force health, energy, phases, scores or
results to present a control fix as validated.

Historical generators are retained for reproducibility. Avoid changing the
frozen 1.0.0 artifact in place: use a new candidate directory and version.
Run the relevant CPU tests with your verified private European image, and
exercise changed native callers in Xenia. Publication-only CI cannot replace
these game-dependent checks. Preserve known regressions as evidence.

Run `python3 tools/validate_publication.py` and `python3 tools/package_patch.py`
for publication metadata and deterministic release-package checks. Explain
what was changed, why, the exact checks run and their practical limits in a
pull request. Write public documentation and reports in English.
