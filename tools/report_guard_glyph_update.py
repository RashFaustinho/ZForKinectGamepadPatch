"""Export scoped, account-free evidence for the exact 1.1.1 regional payloads."""

import hashlib
import json
import shutil
from pathlib import Path
from patch_format import effective_bytes, read

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path("/workspace/artifacts/zforkinect/runtime")
PROBES = Path("/workspace/artifacts/zforkinect/fix12-probes")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def build(region):
    folder = ROOT / f"experiments/gamepad-v1.1.1-{region}"
    patch = folder / "4E4D084E.gamepad.patch.toml"
    digest = sha(patch)
    baseline = ROOT / f"experiments/gamepad-v1.1.0-{region}/4E4D084E.gamepad.patch.toml"
    old, new = effective_bytes(read(baseline)), effective_bytes(read(patch))
    unchanged = []
    for address, size in (
        (0x825EB100, 0x800),
        (0x825EC000, 1400),
        (0x825ED200, 260),
        (0x825ED400, 236),
        (0x825ED680, 92),
        (0x825EC800, 1632),
        (0x825EE600, 304),
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
    for item in read(baseline)["patch"][0]["be32"]:
        assert all(
            old[item["address"] + i] == new[item["address"] + i] for i in range(4)
        )
    public_session = RUNTIME / f"fix12-final-{region}-public"
    public = load(public_session / "runtime-patch-verification.json")
    textures = load(public_session / "hd-textures-runtime.json")
    assert (
        public["passed"]
        and public["patch_sha256"] == digest
        and textures["passed"] == 13
    )
    assert [x["native_size"] for x in textures["textures"][:4]] == [[256, 256]] * 4
    suites = load(folder / "suite-results.json")
    assert len(suites) == 15 and all(
        x["exit_code"] == 0 and x["patch_sha256"] == digest for x in suites
    )
    for name in (
        "alternating-arms-cpu.json",
        "guard-pose-cpu.json",
        "texture-ownership-cpu.json",
    ):
        result = load(folder / name)
        assert result["passed"] is True and result["patch_sha256"] == digest
    runtime = RUNTIME / (
        "fix12-final-europe-vulkan" if region == "europe" else "fix12-final-usa-null"
    )
    guard = load(runtime / "guard-runtime.json")
    assert guard["passed"] and len(guard["cases"]) == 3
    assert all(
        x["guard_flag"]
        and x["finite"]
        and x["joint_buffers_equal"]
        and x["native_action"] == 12
        for x in guard["cases"]
    )
    variant = (
        PROBES
        / ("guard-glyph-final" if region == "europe" else "usa-final")
        / "4E4D084E.local-navigation.patch.toml"
    )
    assert load(variant.parent / "manifest.json")["base_sha256"] == digest
    local = effective_bytes(read(variant))
    site = 0x8211A720
    if region == "usa":
        site = int(
            load(folder / "address-map.json")["native_anchors"][hex(site)]["target"], 16
        )
    changed = {a for a in set(local) | set(new) if local.get(a) != new.get(a)}
    assert changed <= set(range(site, site + 4)) | set(range(0x825EB780, 0x825EB798))
    local_readback = (
        load(runtime / "runtime-patch-verification.json")
        if (runtime / "runtime-patch-verification.json").exists()
        else None
    )
    if local_readback:
        assert local_readback["passed"] and local_readback["patch_sha256"] == sha(
            variant
        )
    if region == "europe":
        assert local_readback is not None
        (folder / "previews").mkdir(exist_ok=True)
        for name in ("guard-idle.png", "guard-after_x_2.png"):
            shutil.copyfile(runtime / name, folder / "previews" / name)
    for name, data in (
        ("public-startup-readback.json", public),
        ("native-textures.json", textures),
        ("native-guard.json", guard),
    ):
        (folder / name).write_text(json.dumps(data, indent=2) + "\n")
    report = {
        "version": "1.1.1",
        "region": region,
        "patch_sha256": digest,
        "passed": True,
        "public_startup": {
            "passed": True,
            "patch_sha256": digest,
            "session": public_session.name,
            "native_textures_verified": 13,
            "face_dimensions": [256, 256],
            "other_dimensions": [128, 128],
        },
        "cpu_suites": 18,
        "native_guard": {
            **guard,
            "backend": "Vulkan/Lavapipe" if region == "europe" else "Null",
        },
        "normal_X_payloads_unchanged_from_1_1_0": True,
        "unchanged_code_and_motion": unchanged,
        "baseline_patch_sha256": sha(baseline),
        "historical_native_attack_evidence": f"../gamepad-v1.1.0-{region}/runtime-checks.json",
        "local_guard_probe": {
            "base_patch_sha256": digest,
            "probe_sha256": sha(variant),
            "only_extra_selector_hook_and_logger": True,
            "live_memory_writes": False,
        },
        "guard_reported_regression": "The reported straight-arm appearance was not reproduced with the prior European Goku pose, which also rendered raised. The new full guard is deliberately tucked and symmetric. No diagnosed regression cause is claimed.",
        "visual_scope": "Europe Goku vs Raditz, Score Attack, Vulkan 1280x720 window; raised guard and B/X glyphs inspected. All four face sources and loaded resources verified. USA guard uses Null GPU; no new USA screenshot or every-character claim.",
        "limits": [
            "Not an exhaustive character/campaign/QTE playthrough.",
            "Windows/D3D12 and physical controllers not tested.",
            "Native guard entry/history is observed; every defensive damage result is not revalidated.",
            "Normal X runtime findings from 1.1.0 remain historical, supported here by byte equality and new native-setter CPU regressions.",
        ],
    }
    (folder / "runtime-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    m = load(folder / "manifest.json")
    m.update(
        status="validated 1.1.1: 18 CPU suites, public startup and native textures, native guard, European Vulkan guard/glyph screenshots",
        validation={
            "version": "1.1.1",
            "cpu_suites": 18,
            "public_runtime_readback": True,
            "native_textures_verified": 13,
            "guard_runtime": True,
            "scope": "runtime-checks.json and docs/update-1.1.1.md",
        },
    )
    (folder / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    print(region, digest, "validated")


if __name__ == "__main__":
    for region in ("europe", "usa"):
        build(region)
