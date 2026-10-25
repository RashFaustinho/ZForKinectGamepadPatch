"""Package verified 1.1.0 regional artifacts with English guides and checksums.

Fixed allowlist, deterministic ZIP metadata, exact patch identity and recorded
CPU/native checks. Original game data, profiles and LOCAL probes are excluded.
"""

import argparse
import hashlib
import io
import json
import posixpath
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit
from patch_format import read

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(region, output, version="1.1.0"):
    folder = ROOT / f"experiments/gamepad-v{version}-{region}"
    source = folder / "4E4D084E.gamepad.patch.toml"
    raw = source.read_bytes()
    doc = read(source)
    digest = sha(raw)
    m = json.loads((folder / "manifest.json").read_text())
    run = json.loads((folder / "runtime-checks.json").read_text())
    suites = json.loads((folder / "suite-results.json").read_text())
    arms = json.loads((folder / "alternating-arms-cpu.json").read_text())
    expected = "C9561ED1F9AFFED4" if region == "europe" else "8FDD4F4AB147612A"
    if (
        doc["hash"] != expected
        or m["patch_sha256"] != digest
        or run["patch_sha256"] != digest
    ):
        raise ValueError("Regional identity mismatch")
    if len(suites) != 15 or any(
        x["exit_code"] != 0 or x["patch_sha256"] != digest for x in suites
    ):
        raise ValueError("Fifteen regional CPU regressions must pass")
    if arms["patch_sha256"] != digest or arms["passed"] is not True:
        raise ValueError("Native-setter/idle-tail suite must pass")
    if (
        run["passed"] is not True
        or not run["public_startup"]["passed"]
        or run["public_startup"]["patch_sha256"] != digest
        or run["public_startup"]["native_textures_verified"] != 13
    ):
        raise ValueError("Public startup and texture verification required")
    if version == "1.1.0":
        for kind in ("near", "far"):
            if (
                run["native_attacks"][kind]["accepted_count"] < 4
                or not run["native_attacks"][kind]["alternates"]
            ):
                raise ValueError(
                    "Native close and ranged alternation must be confirmed"
                )
    else:
        for report in ("guard-pose-cpu.json", "texture-ownership-cpu.json"):
            result = json.loads((folder / report).read_text())
            if result["patch_sha256"] != digest or result["passed"] is not True:
                raise ValueError("Guard and native ownership regressions must pass")
        if version == "1.1.1" and (
            not run["normal_X_payloads_unchanged_from_1_1_0"]
            or not run["native_guard"]["passed"]
        ):
            raise ValueError(
                "Unchanged attack payloads and native guard evidence required"
            )
        if version == "1.1.2":
            result = json.loads((folder / "clash-prompt-cpu.json").read_text())
            if (
                not result["passed"]
                or result["patch_sha256"] != digest
                or len(result["cases"]) != 168
            ):
                raise ValueError("Native clash-selector regressions must pass")
            if (
                not run["guard_and_X_payloads_unchanged_from_1_1_1"]
                or not run["clash_panel_visual_fixture"]["passed"]
            ):
                raise ValueError(
                    "Unchanged guard/attacks and scoped native UI evidence required"
                )
    label = "Europe" if region == "europe" else "USA"
    patch_name = f"4E4D084E.gamepad.{region}.patch.toml"
    package = f"ZForKinectGamepadPatch-{version}-{label}"
    controls = (
        (ROOT / "README.md")
        .read_text()
        .split("## Xbox 360 controls\n", 1)[1]
        .split("## Card Reader:", 1)[0]
    )
    guide = f"""# IMPORTANT DISCLAIMER: BUILT PRIMARILY WITH AI

Most reverse engineering, patch code, automation and documentation was produced
by OpenAI Codex under human direction and with gameplay feedback from
RashFaustinho. AI-generated findings can contain mistakes. This is an unofficial
fan project; original project work is MIT-licensed in the source repository.

# Dragon Ball Z for Kinect — Gamepad Patch 1.1.0 ({label})

**For the {'EUROPEAN edition (En/Fr/De/Es/It)' if region=='europe' else 'American (USA) edition'} of the Xbox 360 game.**
Title ID: `4E4D084E`. Executable module hash: `{expected}`.
Other builds and Title Updates are unverified. Tested with Xenia Canary b735063
on Linux. Physical USB controllers and Windows/D3D12 were not tested here.

## Install

1. Close Xenia and back up your save.
2. Find its Storage root in the startup log. Remove older versions of this
   project's patch from its `patches` directory.
3. Copy `patches/{patch_name}` into that directory.
4. Enable `apply_patches = true` under `[General]` in Xenia's configuration.
5. Select your local profile, configure the controller normally and launch
   your own copy of this edition.

The log should show `Gamepad conversion 1.1.0 ({label})`.
No ISO editing, executable replacement or Python installation is required.
Use one current regional version of the project at a time.

## Changes

A/B/X/Y retain their compact size, with improved edge rasterization and linear
sampling. X alternates the native hand for nearby punches and distant Ki Blasts.
A new actor starts on the right; the sequence continues across range changes.
The selected hand stays consistent through the visual follow-through after the
native action record is cleared. Charged Y and all other controls are retained.

## Controls

{controls}
## Card Reader and verification

[CARD_READER.md](CARD_READER.md) contains the power-up button map and the required
read → B → save → re-enter cycle for each counted press.
To remove a power-up: **Options → Reset Power-Up Card → Yes**.

[VERIFICATION.md](VERIFICATION.md), `validation.json`, `manifest.json` and
`SHA256SUMS` describe this exact regional artifact and the limits of its checks.
Source and research: https://github.com/RashFaustinho/ZForKinectGamepadPatch

Patch size: {len(raw):,} bytes. SHA-256: `{digest}`.
"""
    verification = f"""# Regional verification — {label} 1.1.0

Patch SHA-256: `{digest}`. Module: `{expected}`.

- Fifteen PPC regression suites passed on this exact patch.
- The added side/idle-tail suite executes the original native melee and ranged
  setters, checks eight alternating attacks of each type, and verifies the
  selected hand survives native action/side reset in all joint buffers.
- The exact public startup payload was read back in Xenia, without LOCAL
  diagnostic hooks. All thirteen native 128×128 texture resources matched.
- Genuine pad navigation entered Score Attack. Native X requests alternated
  sides in close and ranged combat. Read-only geometry checks and Vulkan
  captures support the scoped visual findings in `validation.json`.

The native side sequence is shared across close and ranged attacks, so a later
ranged sample can start on the left after an odd number of nearby requests.
A selected input, rendered effect and successful damage avoidance are distinct.
Favorable/unfavorable QTE rules and native timing remain in force.

Vulkan and Null findings are identified separately in the report. Some software
Vulkan runs request smaller internal display dimensions; command-line settings
are recorded separately from window size and native glyph dimensions. Actual
render-target resolution has not been independently measured.
No exhaustive every-character/campaign, physical-controller or Windows claim.
"""
    if version == "1.1.1":
        guide = guide.replace("1.1.0", "1.1.1")
        start = guide.index("A/B/X/Y retain their compact size")
        end = guide.index("\n## Controls", start)
        guide = (
            guide[:start]
            + """A/B/X/Y now use actual 256×256 BC3 textures (four times the previous pixel
count), with linear filtering and the same compact drawing footprint.
Separate buffers are owned and released by the game's native texture system.
B uses a symmetric tucked guard with raised fists near the face. Normal X
right/left attack selection and motion tables remain byte-identical to 1.1.0.
"""
            + guide[end:]
        )
        verification = f"""# Regional verification — {label} {version}

Patch SHA-256: `{digest}`. Module: `{expected}`.

- Fifteen regression suites plus alternating-arm, guard-pose and native texture
  ownership suites passed on this exact patch (eighteen suites in total).
- All public startup code/data was read back without LOCAL diagnostic hooks.
  Thirteen loaded textures match their sources: A/B/X/Y at 256×256, nine others
  at 128×128. Allocation failure and truncated-stream cleanup are checked.
- Native B guard activation and matching joint buffers were observed in Xenia.
  European Vulkan screenshots show the tucked stance and the new B glyph;
  American guard data uses Null GPU, without a USA graphical claim.
- Normal X code and motion tables are byte-identical to 1.1.0. That version's
  native melee/ranged observations are historical evidence; the new patch's
  native setters are rechecked by the alternating-arm CPU suite.

The reported straight-arm defect was not reproduced in the original European
Goku scenario: the old guard was also raised there. This update supplies a
tighter symmetric pose; it does not claim a diagnosed cause for that report.
See `validation.json` for exact observations. No exhaustive every-character,
campaign, Windows/D3D12 or physical-controller verification is claimed.
"""
    if version == "1.1.2":
        guide = guide.replace("1.1.0", "1.1.2")
        start = guide.index("A/B/X/Y retain their compact size")
        end = guide.index("\n## Controls", start)
        guide = (
            guide[:start]
            + """A/B/X/Y retain their compact 256×256 canvases, using uncompressed RGBA8
GPU pixels. This removes the BC3 block-color errors that contaminated their
outlines. Startup storage uses a compact palette/index transport, expanded into
native-owned buffers before drawing. The authored PNG and GPU pixels match.

The separate Super-mash/clash widget now displays X. The replacement no longer
depends on the old Kinect icon catalog being ready, and final cleanup hides
the pose groups after native animations. Native OK/NG effects, progress and
inputs remain unchanged. The working guard and alternating X payloads are
byte-identical to 1.1.1.
"""
            + guide[end:]
        )
        verification = f"""# Regional verification — {label} {version}

Patch SHA-256: `{digest}`. Module: `{expected}`.

- Nineteen CPU suites passed on this exact regional patch, including 168
  clash/catalog/fallback cases and the actual native mash selectors.
- Public startup bytes and all thirteen GPU resources were read back in Xenia.
  Four faces are 256×256 RGBA8; nine other glyphs retain their BC3 bytes.
- The old B texture had 285 reddish contour texels in the measured annulus;
  the new authored RGBA texture has zero under the same color predicate.
- European Vulkan captured the native Super-mash UI with X and hidden poses.
  This is a LOCAL display fixture that selects an existing tutorial group and
  requests its panel's native show animation. It does not reproduce a real
  Super clash, its progress/victory, or the whole N18 versus N17 encounter.
- Regular B/X gameplay was captured on an earlier candidate with the exact
  same RGBA path; only the two final Super-widget hooks were subsequently added.
- The validated guard and attack payloads remain byte-identical to 1.1.1.

See `validation.json` for scope and artifact hashes. No new every-character,
campaign, Windows/D3D12, physical-controller or USA graphical claim is made.
"""
    files = {
        "README.md": guide.encode(),
        "CARD_READER.md": (ROOT / "docs/card-reader-1.1.0.md").read_bytes(),
        "VERIFICATION.md": verification.encode(),
        "patches/" + patch_name: raw,
        "validation.json": (json.dumps(run, indent=2) + "\n").encode(),
        "LICENSE": (ROOT / "LICENSE").read_bytes(),
    }
    if region == "usa" or (region == "europe" and version == "1.1.2"):
        save_folder = ROOT / (
            "releases/v1.1.0/content-complete-save-USA"
            if region == "usa"
            else "releases/v1.0.0/content-complete-save"
        )
        save_manifest = json.loads((save_folder / "manifest.json").read_text())
        save = (save_folder / "DB_SAVE").read_bytes()
        if (
            sha(save) != save_manifest["sha256"]
            or save_manifest["active_powerup"] is not None
        ):
            raise ValueError("Save identity or inactive power-up mismatch")
        evidence_name = (
            "published-usa-save-runtime.json"
            if region == "usa"
            else "published-save-runtime.json"
        )
        evidence = json.loads((ROOT / "research" / evidence_name).read_text())
        if (
            not evidence["loaded_buffer_exact_match"]
            or evidence.get(
                "automatic_content_unlock_hook_loaded",
                evidence.get("automatic_content_unlock_patch_loaded", True),
            )
            or evidence["file_sha256"] != sha(save)
            or evidence["loaded_buffer_sha256"] != sha(save)
            or not evidence["local_native_format_checksum_valid"]
            or (region == "usa" and not evidence["native_root_menu_reached"])
        ):
            raise ValueError("Native save check without automatic unlock required")
        files["optional-save/DB_SAVE"] = save
        save_manifest["runtime_evidence"] = "native-load-check.json"
        files["optional-save/manifest.json"] = (
            json.dumps(save_manifest, indent=2) + "\n"
        ).encode()
        files["optional-save/native-load-check.json"] = (
            json.dumps(evidence, indent=2) + "\n"
        ).encode()
        # Package installation guide uses the existing profile/header; no profile
        # identifiers, account file or pre-bound content header are included.
        save_guide = (save_folder / "README.md").read_text()
        save_guide = (
            save_guide.replace(
                "../../../research/" + evidence_name,
                "native-load-check.json",
            )
            .replace(
                "../../../tools/create_content_save.py",
                "https://github.com/RashFaustinho/ZForKinectGamepadPatch/blob/main/tools/create_content_save.py",
            )
            .replace(
                "../../../docs/content-unlock.md",
                "https://github.com/RashFaustinho/ZForKinectGamepadPatch/blob/main/docs/content-unlock.md",
            )
        )
        files["optional-save/README.md"] = save_guide.encode()
        files["optional-save/SHA256SUMS"] = "".join(
            sha(value) + "  " + name.split("/", 1)[1] + "\n"
            for name, value in sorted(files.items())
            if name.startswith("optional-save/")
        ).encode()
        if region == "usa":
            files[
                "README.md"
            ] += b"\n## Optional USA save\n\nSee [the save guide](optional-save/README.md) before replacing DB_SAVE. Back up your existing save first. No power-up is active.\n"
        else:
            files[
                "README.md"
            ] += b"\n## Optional European save\n\nSee [the save guide](optional-save/README.md) before replacing DB_SAVE. Back up your existing save first. No power-up is active.\n"
    for name, content in files.items():
        if not name.endswith(".md"):
            continue
        for link in re.findall(r"\]\(([^)]+)\)", content.decode()):
            if urlsplit(link).scheme or link.startswith("#"):
                continue
            destination = posixpath.normpath(
                posixpath.join(posixpath.dirname(name), unquote(link.split("#", 1)[0]))
            )
            if destination not in files:
                raise ValueError(f"Unpackaged documentation link: {name}: {link}")
    manifest = {
        "package": package,
        "version": version,
        "region": label,
        "title_id": doc["title_id"],
        "module_hash": expected,
        "patch_sha256": digest,
        "patch_bytes": len(raw),
        "files": {
            n: {"bytes": len(v), "sha256": sha(v)} for n, v in sorted(files.items())
        },
    }
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    files["SHA256SUMS"] = "".join(
        sha(v) + "  " + n + "\n" for n, v in sorted(files.items())
    ).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as z:
        for n, v in sorted(files.items()):
            info = zipfile.ZipInfo(package + "/" + n, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, v, compresslevel=9)
    data = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None and len(z.namelist()) == len(files)
        for n, v in files.items():
            assert z.read(package + "/" + n) == v
    output.mkdir(parents=True, exist_ok=True)
    target = output / (package + ".zip")
    if target.exists() and target.read_bytes() != data:
        raise FileExistsError("Different release package exists")
    target.write_bytes(data)
    target.with_suffix(".zip.sha256").write_text(sha(data) + "  " + target.name + "\n")
    print(
        json.dumps(
            {
                "archive": str(target),
                "bytes": len(data),
                "sha256": sha(data),
                "patch_sha256": digest,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", choices=("europe", "usa", "both"), default="both")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/1.1.0")
    parser.add_argument(
        "--version", choices=("1.1.0", "1.1.1", "1.1.2"), default="1.1.0"
    )
    args = parser.parse_args()
    for region in ("europe", "usa") if args.region == "both" else (args.region,):
        build(region, args.output, args.version)
