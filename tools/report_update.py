"""Export scoped 1.1.0 evidence from retained, owned-session observations.

No original binaries, account data or raw memory dumps are copied. The report
keeps input acceptance, attack states, geometry, rendering and load checks
separate and pins every result to the actual public regional artifact.
"""

import hashlib
import json
import shutil
from pathlib import Path
from patch_format import effective_bytes, read

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path("/workspace/artifacts/zforkinect/runtime")
PROBES = Path("/workspace/artifacts/zforkinect/update11-probes")
FAR = {"europe": "update11-europe-null-ranged", "usa": "update11-usa-null-final"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def native_case(path, state):
    d = load(path)
    events = d["accepted"]
    assert d["complete"] and len(events) >= 4
    sides = [x["side"] for x in events]
    assert set(sides) == {0, 1} and all(a != b for a, b in zip(sides, sides[1:]))
    assert all(x["side_verified_in_native_actor"] for x in events)
    states = [
        r
        for r in d["samples"]
        if r["state"] == state and r["mode"] == (4 if state == 10 else 6)
    ]
    observed = {r["accepted_stamp"] for r in states if r["side"] in (0, 1)}
    assert all(x["accepted_stamp"] in observed for x in events)
    result = {
        "session": d["session"],
        "source_report": path.name,
        "source_sha256": digest(path),
        "accepted_count": len(events),
        "native_sides": sides,
        "alternates": True,
        "all_sides_verified_in_native_actor": True,
        "all_requests_entered_native_attack_state": state,
        "first_opponent_hp": events[0]["opponent_hp"],
        "last_observed_opponent_hp": d["samples"][-1]["opponent_hp"],
        "events": events,
    }
    return result, d


def build(region):
    folder = ROOT / f"experiments/gamepad-v1.1.0-{region}"
    patch = folder / "4E4D084E.gamepad.patch.toml"
    sha = digest(patch)
    public = load(RUNTIME / f"update11-{region}-public/runtime-patch-verification.json")
    textures = load(RUNTIME / f"update11-{region}-public/hd-textures-runtime.json")
    assert (
        public["passed"] and public["patch_sha256"] == sha and textures["passed"] == 13
    )
    suites = load(folder / "suite-results.json")
    arms = load(folder / "alternating-arms-cpu.json")
    assert len(suites) == 15 and all(
        x["exit_code"] == 0 and x["patch_sha256"] == sha for x in suites
    )
    assert arms["passed"] and arms["patch_sha256"] == sha
    near_session = f"update11-{region}-vulkan-final"
    near, near_data = native_case(RUNTIME / near_session / "near-x.json", 10)
    far, far_data = native_case(RUNTIME / FAR[region] / "far-x.json", 29)
    assert all(
        x["all_finite"] and x["joint_buffers_equal"]
        for x in near_data["geometry_audits"]
    )
    assert len(near_data["capture_context"]) == 2 and all(
        x["selected_hand_further_forward"] for x in near_data["capture_context"]
    )
    # The graphical scenario differs only by the selector-pointer logger.
    variant = PROBES / f"{region}-final-nav/4E4D084E.local-navigation.patch.toml"
    meta = load(variant.parent / "manifest.json")
    assert meta["base_sha256"] == sha
    a, b = effective_bytes(read(patch)), effective_bytes(read(variant))
    site = 0x8211A720
    if region == "usa":
        site = int(
            load(folder / "address-map.json")["native_anchors"][hex(site)]["target"], 16
        )
    allowed = set(range(site, site + 4)) | set(range(0x825EB780, 0x825EB798))
    changed = {x for x in set(a) | set(b) if a.get(x) != b.get(x)}
    assert changed <= allowed
    readback = load(RUNTIME / near_session / "runtime-patch-verification.json")
    assert readback["passed"] and readback["patch_sha256"] == digest(variant)
    native_textures = load(RUNTIME / near_session / "hd-textures-runtime.json")
    assert native_textures["passed"] == 13
    previews = folder / "previews"
    previews.mkdir(exist_ok=True)
    for item in near_data["screenshots"]:
        original = Path(item["path"])
        shutil.copy2(original, previews / original.name)
    command = load(RUNTIME / near_session / "command.json")
    visual = {
        "session": near_session,
        "backend": "Vulkan/Lavapipe",
        "virtual_display_capture_size": [1280, 720],
        "requested_internal_display_options": [
            x for x in command if x.startswith("--custom_internal_display_resolution")
        ],
        "actual_render_target_resolution_independently_measured": False,
        "local_selector_logger_only": True,
        "local_payload_readback_passed": True,
        "public_code_changes_limited_to_selector_hook_and_reserved_logger": True,
        "native_textures_verified": 13,
        "geometry_regions": [len(x["regions"]) for x in near_data["geometry_audits"]],
        "all_geometry_finite": True,
        "three_joint_buffers_equal": True,
        "selected_hand_moves_forward_after_native_side_reset": near_data[
            "capture_context"
        ],
        "screenshots": [x.name for x in previews.glob("*.png")],
    }
    public_summary = {
        "passed": True,
        "patch_sha256": sha,
        "exact_public_hooks_and_payloads_read_back": True,
        "local_diagnostic_patch_loaded": False,
        "native_textures_verified": 13,
        "face_sampling_word3": "0x01280D10",
    }
    report = {
        "version": "1.1.0",
        "region": region,
        "patch_sha256": sha,
        "passed": True,
        "cpu_regression_suites_passed": 15,
        "additional_native_side_and_idle_tail_suite_passed": True,
        "native_attacks": {"near": near, "far": far},
        "native_attack_backend": {
            "near": "Vulkan/Lavapipe",
            "far": "Null GPU: logic only, no rendering claim",
        },
        "public_startup": public_summary,
        "visual_melee_and_idle_tail": visual,
        "limits": [
            "No exhaustive campaign, character/variant, every-QTE or every-power-up effect playthrough.",
            "Windows/D3D12 and physical USB controllers were not tested.",
            "Four ranged X requests, their native sides/state 29 and damage are verified through the Null backend. Final 1.1.0 ranged Vulkan projectile rendering is not independently confirmed.",
            "A separate USA software-Vulkan ranged attempt timed out during the automated transition; it is not counted as a successful ranged visual test.",
            "Native QTE favorable/unfavorable outcome rules, health, Ki, scoring and timing are retained.",
        ],
    }
    (folder / "runtime-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    m = load(folder / "manifest.json")
    m.update(
        status="validated 1.1.0: sixteen CPU suites, native melee/ranged sides, graphical melee/idle tail and exact public startup readback",
        validation={
            "version": "1.1.0",
            "cpu_suites": 16,
            "native_melee_and_ranged_alternation": True,
            "public_runtime_readback": True,
            "native_textures_verified": 13,
            "scope": "runtime-checks.json and docs/update-1.1.0.md",
        },
    )
    (folder / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    # Account-free complete side-event lists are useful to future researchers.
    (folder / "native-input-events.json").write_text(
        json.dumps(
            {
                "patch_sha256": sha,
                "near": near["events"],
                "far": far["events"],
                "scope": "Real virtual-pad requests and read-only native actor observations; no forced combat data.",
            },
            indent=2,
        )
        + "\n"
    )
    print(region, sha, "validated")


if __name__ == "__main__":
    for region in ("europe", "usa"):
        build(region)
