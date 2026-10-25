"""Run an existing PPC fixture on the USA image with explicit address mapping.

Only numeric native addresses and the original-image path in project-owned
fixture source are adapted. Assertions and expected behavioral values remain
unchanged. The USA patch and USA original instructions are actually executed.
Native addresses require the same unique-anchor mapper as the reviewed port;
this runner does not substitute European instructions or force test outcomes.
"""

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from region_port import NativeMap, EU_SHA, USA_SHA, port_document
from patch_format import read, serialize, consolidate_arrays

ROOT = Path(__file__).resolve().parents[1]
EU_IMAGE = Path("/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin")
USA_IMAGE = Path("/workspace/artifacts/zforkinect/usa/analysis/Dbkn.image.bin")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    parser.add_argument("--patch", type=Path, required=True)
    args = parser.parse_args()
    script = args.script.resolve()
    patch = args.patch.resolve()
    if script.parent != ROOT / "tools" or not script.name.startswith("check_"):
        parser.error("Select a project CPU fixture")
    report = json.loads((patch.parent / "address-map.json").read_text())
    mapper = NativeMap(
        EU_IMAGE.read_bytes(),
        USA_IMAGE.read_bytes(),
        [
            (int(x["source"], 16), int(x["end"], 16), int(x["target"], 16))
            for x in report["islands"]
        ],
    )
    transformed = []
    baselines = {}
    for revision in (18, 19):
        relative = f"experiments/gamepad-feedback-v{revision}/4E4D084E.gamepad-feedback.patch.toml"
        folder = patch.parent / "negative-baselines"
        folder.mkdir(exist_ok=True)
        target = folder / f"revision{revision}.toml"
        if not target.exists():
            negative, _, _, _ = port_document(
                consolidate_arrays(read(ROOT / relative)),
                EU_IMAGE.read_bytes(),
                USA_IMAGE.read_bytes(),
            )
            target.write_text(serialize(negative))
        (folder / "manifest.json").write_text(
            json.dumps(
                {
                    "region": "USA",
                    "local_only": True,
                    "scope": "Ported historical negative baselines; no final guard-priority adapter.",
                },
                indent=2,
            )
            + "\n"
        )
        baselines[relative] = str(target)

    def imported(value):
        if type(value) is int and 0x82000000 <= value < 0x82700000:
            return mapper(value)
        if isinstance(value, tuple):
            return tuple(imported(x) for x in value)
        return value

    class Adapt(ast.NodeTransformer):
        def visit_ImportFrom(self, node):
            if node.module not in {"build_content_unlock", "build_final_patch"}:
                return node
            return [
                node,
                *[
                    ast.Assign(
                        targets=[ast.Name(id=x.asname or x.name, ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Name(id="__region_imported", ctx=ast.Load()),
                            args=[ast.Name(id=x.asname or x.name, ctx=ast.Load())],
                            keywords=[],
                        ),
                    )
                    for x in node.names
                ],
            ]

        def visit_Constant(self, node):
            value = node.value
            if type(value) is int and 0x82000000 <= value < 0x82700000:
                target = mapper(value)
                if target != value:
                    transformed.append([hex(value), hex(target)])
                    return ast.copy_location(ast.Constant(target), node)
            if isinstance(value, str):
                replacement = (
                    str(USA_IMAGE)
                    if value == str(EU_IMAGE)
                    else USA_SHA if value == EU_SHA else baselines.get(value)
                )
                if replacement is not None:
                    return ast.copy_location(ast.Constant(replacement), node)
            return node

    source = script.read_text()
    tree = ast.fix_missing_locations(
        Adapt().visit(ast.parse(source, filename=str(script)))
    )
    sys.argv = [str(script), "--patch", str(patch)]
    exec(
        compile(tree, str(script), "exec"),
        {
            "__name__": "__main__",
            "__file__": str(script),
            "__region_imported": imported,
        },
    )
    record = {
        "fixture": script.name,
        "fixture_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "original_image_sha256": hashlib.sha256(USA_IMAGE.read_bytes()).hexdigest(),
        "adapted_numeric_addresses": transformed,
        "behavioral_assertions_unchanged": True,
        "image_digest_pin_adapted_to_known_USA_build": True,
        "negative_baselines_ported": True,
        "passed": True,
    }
    (patch.parent / (script.stem + "-port.json")).write_text(
        json.dumps(record, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
