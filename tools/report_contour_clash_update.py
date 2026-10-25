"""Export exact 1.1.2 evidence, distinguishing UI fixtures from full gameplay."""

import hashlib, json, shutil
from pathlib import Path
from patch_format import effective_bytes, read

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path("/workspace/artifacts/zforkinect/runtime")
PROBES = Path("/workspace/artifacts/zforkinect/update112-probes")


def load(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(region):
    folder = ROOT / f"experiments/gamepad-v1.1.2-{region}"
    patch = folder / "4E4D084E.gamepad.patch.toml"
    digest = sha(patch)
    base = ROOT / f"experiments/gamepad-v1.1.1-{region}/4E4D084E.gamepad.patch.toml"
    old, new = effective_bytes(read(base)), effective_bytes(read(patch))
    unchanged = []
    for address, size in (
        (0x825EB100, 0x800),
        (0x825EC000, 1400),
        (0x825ED200, 260),
        (0x825ED400, 236),
        (0x825ED680, 92),
        (0x825EC800, 1632),
        (0x825EE600, 304),
        (0x825EE800, 448),
        (0x8266E900, 576),
        (0x825EFE00, 128),
    ):
        before = bytes(old[address + i] for i in range(size))
        after = bytes(new[address + i] for i in range(size))
        assert before == after
        unchanged.append(
            {
                "address": hex(address),
                "bytes": size,
                "sha256": hashlib.sha256(after).hexdigest(),
            }
        )
    for item in read(base)["patch"][0]["be32"]:
        assert all(
            new[item["address"] + i] == old[item["address"] + i] for i in range(4)
        )
    suites = load(folder / "suite-results.json")
    assert len(suites) == 15 and all(
        x["exit_code"] == 0 and x["patch_sha256"] == digest for x in suites
    )
    for name in (
        "alternating-arms-cpu.json",
        "guard-pose-cpu.json",
        "texture-ownership-cpu.json",
        "clash-prompt-cpu.json",
    ):
        d = load(folder / name)
        assert d["passed"] is True and d["patch_sha256"] == digest
    clash_cpu = load(folder / "clash-prompt-cpu.json")
    assert len(clash_cpu["cases"]) == 168
    hd = load(folder / "hd-prompts-cpu.json")
    assert hd["patch_sha256"] == digest and hd["passed"] == 13
    public = RUNTIME / f"update112-final-{region}-public"
    startup = load(public / "runtime-patch-verification.json")
    textures = load(public / "hd-textures-runtime.json")
    assert (
        startup["passed"]
        and startup["patch_sha256"] == digest
        and textures["passed"] == 13
    )
    assert all(x["native_size"] == [256, 256] for x in textures["textures"][:4])
    for name, data in (
        ("public-startup-readback.json", startup),
        ("native-textures.json", textures),
    ):
        (folder / name).write_text(json.dumps(data, indent=2) + "\n")
    visual_session = RUNTIME / "update112-clash-display-vulkan"
    visual = load(visual_session / "clash-runtime.json")
    assert (
        visual["passed"]
        and visual["final"]["X_mapped"]
        and visual["final"]["visibility_state"] == 2
    )
    assert visual["full_N18_vs_N17_match_reproduced"] is False
    display = PROBES / "europe-clash-display/4E4D084E.local-clash-display.patch.toml"
    display_m = load(display.parent / "manifest.json")
    lesson = PROBES / "europe-clash-tutorial/4E4D084E.local-super-defense.patch.toml"
    lesson_m = load(lesson.parent / "manifest.json")
    nav = PROBES / "europe-final-nav/4E4D084E.local-navigation.patch.toml"
    nav_m = load(nav.parent / "manifest.json")
    eu_patch = ROOT / "experiments/gamepad-v1.1.2-europe/4E4D084E.gamepad.patch.toml"
    assert (
        display_m["input_sha256"] == sha(lesson)
        and lesson_m["base_patch_sha256"] == sha(nav)
        and nav_m["base_sha256"] == sha(eu_patch)
    )
    expected = effective_bytes(read(eu_patch))
    actual = effective_bytes(read(display))
    allowed = (
        set(range(0x8211A720, 0x8211A724))
        | set(range(0x825EB780, 0x825EB798))
        | set(range(0x822F9430, 0x822F9434))
        | set(range(0x825ECE80, 0x825ECE80 + lesson_m["bytes"]))
        | set(range(0x822F0F80, 0x822F0F84))
        | set(range(0x825EFA80, 0x825EFA80 + display_m["bytes"]))
    )
    assert {
        a for a in set(expected) | set(actual) if expected.get(a) != actual.get(a)
    } <= allowed
    readback = load(visual_session / "runtime-patch-verification.json")
    assert readback["passed"] and readback["patch_sha256"] == sha(display)
    if region == "europe":
        previews = folder / "previews"
        previews.mkdir(exist_ok=True)
        shutil.copyfile(
            visual_session / "clash-X-settled.png", previews / "clash-X-UI-fixture.png"
        )
        # Earlier candidate differs only at the two final Super-widget hooks;
        # its identical RGBA path was captured during genuine guard gameplay.
        prototype = Path(
            "/workspace/artifacts/zforkinect/update112-pre-super-clash/europe/4E4D084E.gamepad.patch.toml"
        )
        proto = effective_bytes(read(prototype))
        diff = {a for a in set(new) | set(proto) if new.get(a) != proto.get(a)}
        proto_allowed = (
            set(range(0x822F1608, 0x822F160C))
            | set(range(0x822F0F80, 0x822F0F84))
            | set(range(0x825EF940, 0x825EFA38))
        )
        assert diff <= proto_allowed
        shutil.copyfile(
            RUNTIME / "update112-europe-vulkan/guard-after_x_2.png",
            previews / "RGBA-B-X-gameplay.png",
        )
        prototype_evidence = {
            "patch_sha256": sha(prototype),
            "only_difference_two_Super_widget_hooks_and_wrappers": True,
            "RGBA_path_identical_to_final": True,
        }
    else:
        prototype_evidence = None
    report = {
        "version": "1.1.2",
        "region": region,
        "patch_sha256": digest,
        "passed": True,
        "cpu_suites": 19,
        "public_startup": {
            "passed": True,
            "patch_sha256": digest,
            "native_textures_verified": 13,
            "session": public.name,
            "face_format": "RGBA8, native format 6, 256x256, 262144 bytes each",
            "other_format": "nine unchanged BC3 textures",
        },
        "guard_and_X_payloads_unchanged_from_1_1_1": True,
        "unchanged_payloads": unchanged,
        "baseline_patch_sha256": sha(base),
        "clash_CPU_cases": 168,
        "native_mash_selectors_executed": clash_cpu["native_mash_selectors_executed"],
        "clash_panel_visual_fixture": {
            "passed": True,
            "region": "Europe",
            "public_base_patch_sha256": sha(eu_patch),
            "LOCAL_patch_sha256": sha(display),
            "scope": "Native UI panel display, not an organically reached Super clash or completed N18/N17 encounter. LOCAL code selects existing tutorial group 4 and requests its UI show animation only.",
            "scene_report": visual,
            "only_declared_LOCAL_changes_verified": True,
            "screenshot": (
                "previews/clash-X-UI-fixture.png"
                if region == "europe"
                else "../gamepad-v1.1.2-europe/previews/clash-X-UI-fixture.png"
            ),
        },
        "RGBA_gameplay_preview_candidate": prototype_evidence,
        "limits": [
            "Full N18 versus N17 encounter and an organically initiated Super clash were not reproduced.",
            "Direct tutorial group 4 selection did not initialize a full clash; its Null-GPU probe did not count as passing.",
            "The Vulkan UI fixture verifies the real widget art and cleanup, without claiming native clash progress, victory or damage.",
            "USA has exact startup/resource readback and mapped native CPU checks; its graphics were not separately captured.",
            "No new all-character, campaign, Windows/D3D12 or physical-controller claim.",
        ],
    }
    (folder / "runtime-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    m = load(folder / "manifest.json")
    m.update(
        status="validated 1.1.2: nineteen CPU suites, public RGBA resource readback, European native-widget UI display fixture; full N18/N17 clash not replayed",
        validation={
            "version": "1.1.2",
            "cpu_suites": 19,
            "public_runtime_readback": True,
            "native_textures_verified": 13,
            "clash_CPU_cases": 168,
            "scope": "runtime-checks.json and docs/update-1.1.2.md",
        },
    )
    (folder / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    print(region, digest, "validated with scoped UI evidence")


if __name__ == "__main__":
    for region in ("europe", "usa"):
        build(region)
