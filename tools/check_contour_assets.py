"""Verify the RGBA transport and measure old/new authored contour errors.

Requires only project-owned assets, Pillow and LZ4, never the original game.
The reddish-texel predicate applies to B; it is not a universal color metric.
"""

import hashlib, json, math
from pathlib import Path
import lz4.block
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / "assets/controller-rgba"
manifest = json.loads((folder / "manifest.json").read_text())
blob = (folder / "buttons.lz4").read_bytes()
assert hashlib.sha256(blob).hexdigest() == manifest["sha256"]
rows = []
old_manifest = json.loads((ROOT / "assets/controller-hd256/manifest.json").read_text())
for t, previous in zip(manifest["textures"], old_manifest["textures"]):
    if t["index"] not in (2, 3, 4, 5):
        assert t["bc3_sha256"] == previous["bc3_sha256"]
        continue
    label = t["label"]
    block = blob[t["offset"] : t["offset"] + t["packed_bytes"]]
    palette = [block[i : i + 4] for i in range(0, 512, 4)]
    indices = lz4.block.decompress(block[512:], uncompressed_size=65536)
    assert max(indices) < 128
    raw = b"".join(palette[i] for i in indices)
    expected = (folder / (label + ".rgba")).read_bytes()
    new = Image.open(folder / (label + ".png")).convert("RGBA")
    assert (
        raw == expected == new.tobytes()
        and hashlib.sha256(raw).hexdigest() == t["rgba8_sha256"]
    )
    original = Image.open(ROOT / "assets/controller-hd256" / (label + ".png")).convert(
        "RGBA"
    )
    old = Image.open(ROOT / "assets/controller-hd256" / (label + ".dds")).convert(
        "RGBA"
    )
    changes = []
    for texture in (old, new):
        red = 0
        peak = 0
        for y in range(256):
            for x in range(256):
                radius = math.hypot(x + 0.5 - 128, y + 0.5 - 128)
                v = texture.getpixel((x, y))
                a = original.getpixel((x, y))
                if 62.7 < radius < 66 and v[3] > 8:
                    if v[0] > 50 and v[0] > v[1] * 1.5 and v[0] > v[2] * 1.5:
                        red += 1
                    peak = max(peak, abs(v[0] - a[0]))
        changes.append(
            {"red_contour_pixels": red, "max_contour_red_channel_error": peak}
        )
    rows.append({"label": label, "BC3": changes[0], "RGBA8": changes[1]})
assert (
    rows[0]["BC3"]["red_contour_pixels"] > 0
    and rows[0]["RGBA8"]["red_contour_pixels"] == 0
)
report = {
    "scope": __doc__
    + " The annulus is radius 62.7..66 on 256px authored canvases; alpha <= 8 is excluded.",
    "source_sha256": manifest["sha256"],
    "passed": True,
    "results": rows,
    "transport_roundtrip_exact": True,
    "other_nine_decoded_textures_unchanged": True,
}
(ROOT / "research/update112-contours.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(
    "RGBA transport exact; B reddish contour texels:",
    rows[0]["BC3"]["red_contour_pixels"],
    "->",
    rows[0]["RGBA8"]["red_contour_pixels"],
)
