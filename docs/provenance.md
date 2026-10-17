# Provenance, reproducibility, and evidence boundaries

The primary implementation/research author was OpenAI Codex, directed by RashFaustinho with iterative human gameplay reports. The README's AI disclaimer applies to the entire research record, including technical interpretations that may later need correction.

## Original inputs and tools

The target is the European En/Fr/De/Es/It `default.xex` (digest in the README), Media ID `320B3C10`, image base `82000000`, decoded-image digest `72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b`. Baseline research began on 2026-10-15; the final iteration and publication preparation took place on 2026-10-17.

The tests used Xenia Canary `b735063` on Linux x86-64; Xvfb; Mesa Lavapipe software Vulkan and the Null backend; Ghidra 12.1.3 with XEXLoaderWV/GhidraXenon and JDK 21; Unicorn 2.1.4 in PPC32 mode with scoped Xenon ABI fixtures; and Capstone 5.0.9. Python/tool versions are recorded in `tools/analysis-requirements.txt` and retained tool-archive hashes in `tools/tool-artifacts.json`.

Generic PowerPC decompilation missed VMX128 details. GhidraXenon improved decoding, but vector pseudocode still needed assembly and runtime checks. Static imports/calls identify research candidates, not proof those routines executed.

## What is public

- All patch-generation source and integer emitters, including unsuccessful approaches and local instrumentation tools.
- The original disc/XEX inspection utilities, focused Ghidra export scripts, runtime supervisors and pad probes.
- The final and historical generated TOMLs, hashes, CPU reports, scoped runtime summaries, and relevant screenshots.
- Native action identifiers/names, factual card/character catalogs, authored controller artwork and its compressed outputs.
- English architecture, address/field references, correction history, validation distinctions, and known limitations.

## What is not distributed

Original disc/executable data, decrypted PE images, extracted game asset archives, full proprietary decompiled routines, account/profile files, raw memory dumps, and private local tool binaries are excluded. These are inputs or environment artifacts, not missing original patch source. The optional generated content-complete DB_SAVE and its source are included; no account/profile or account-bound content header is distributed. Do not expect an old absolute path in a JSON report to be a public downloadable artifact.

The new inspection utilities and [build instructions](building.md) describe how to obtain the verified private image from a user-owned game copy. The committed predecessor patches contain the project's authored generated code needed to reproduce the final build; the optional full historical pipeline additionally needs the described original asset metadata.

## Evidence interpretation

Historical JSON files are retained with their original patch hashes and original wording. A report for revision 4 does not establish a revision-13 behavior unless the relevant payload equality is established separately. Some local paths identify evidence no longer bundled publicly. The final report distinguishes final public readback, PowerPC test results, inherited UI/card validation, and the runtime B selection.

`research/native-input-evidence.json` exports selected complete structured sample sequences for the final launch-guard investigation and Super-defense cases, omitting raw byte dumps, account identifiers and absolute local paths. Numeric geometry audits and per-revision manifests remain in `experiments`. A tutorial lesson-entry rendering fixture is explicitly distinguished from the separate full native tutorial course.

Game screenshots and names remain third-party material; the project license covers original project work. No claim is made that the game's entire source has been recovered or that Kinect has been implemented in Xenia.
