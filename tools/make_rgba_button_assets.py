"""Author compact RGBA8 faces without BC3's block color contamination.

The transport uses 128 RGBA palette entries plus raw-LZ4 byte indices. Its
expanded GPU pixels exactly match the authored PNG. Sixty opaque RGB colors
and sixty-four neutral-edge alpha levels fit the checked source padding.
Nine non-face BC3 resources retain their existing decoded bytes.
"""

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path
import lz4.block
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--out", type=Path, default=ROOT / "assets/controller-rgba")
args = p.parse_args()
out = args.out
out.mkdir(parents=True, exist_ok=True)
source = ROOT / "assets/controller-hd256"
previous = json.loads((source / "manifest.json").read_text())
oldblob = (source / "buttons.lz4").read_bytes()
assert hashlib.sha256(oldblob).hexdigest() == previous["sha256"]
blob = bytearray()
rows = []
metrics = []
for old in previous["textures"]:
    t = dict(old)
    label = t["label"]
    shutil.copyfile(source / (label + ".svg"), out / (label + ".svg"))
    if t["index"] in (2, 3, 4, 5):
        original = Image.open(source / (label + ".png")).convert("RGBA")
        pixels = list(original.get_flattened_data())
        opaque = [v[:3] for v in pixels if v[3] == 255]
        sample = Image.new("RGB", (len(opaque), 1))
        sample.putdata(opaque)
        quantized = sample.quantize(
            colors=60, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        )
        colors = quantized.getpalette()[:180]
        palette = [(17, 24, 32, i * 4) for i in range(64)]
        palette += [(*colors[i : i + 3], 255) for i in range(0, 180, 3)]
        palette += [(0, 0, 0, 0)] * (128 - len(palette))
        opaque_indices = iter(quantized.get_flattened_data())
        indices = bytes(
            min(63, (v[3] + 2) // 4) if v[3] != 255 else 64 + next(opaque_indices)
            for v in pixels
        )
        raw = bytes(c for index in indices for c in palette[index])
        rendered = Image.frombytes("RGBA", (256, 256), raw)
        rendered.save(out / (label + ".png"))
        (out / (label + ".rgba")).write_bytes(raw)
        packed = bytes(c for color in palette for c in color) + lz4.block.compress(
            indices, store_size=False, mode="high_compression", compression=12
        )
        t.pop("bc3_sha256")
        t.update(
            format="RGBA8",
            gpu_format=6,
            decoded_bytes=len(raw),
            rgba8_sha256=hashlib.sha256(raw).hexdigest(),
            palette_bytes=512,
            index_bytes=65536,
            palette_entries=128,
        )
        opaque_quant = list(quantized.convert("RGB").get_flattened_data())
        rms = math.sqrt(
            sum(
                (a - b) ** 2 for u, v in zip(opaque, opaque_quant) for a, b in zip(u, v)
            )
            / (len(opaque) * 3)
        )
        maxalpha = max(abs(pixels[i][3] - raw[i * 4 + 3]) for i in range(len(pixels)))
        assert maxalpha <= 3 and rms < 2
        # Every partially transparent contour texel is neutral, never red.
        assert all(
            raw[i * 4 : i * 4 + 3] == bytes((17, 24, 32))
            for i, pixel in enumerate(pixels)
            if pixel[3] != 255
        )
        metrics.append(
            {
                "label": label,
                "opaque_rgb_rmse_0_255": rms,
                "maximum_alpha_error_0_255": maxalpha,
                "transport_decodes_exactly_to_authored_png": True,
            }
        )
    else:
        packed = oldblob[t["offset"] : t["offset"] + t["packed_bytes"]]
        for suffix in (".png", ".dds"):
            shutil.copyfile(source / (label + suffix), out / (label + suffix))
    t.update(offset=len(blob), packed_bytes=len(packed))
    blob.extend(packed)
    rows.append(t)
(out / "buttons.lz4").write_bytes(blob)
manifest = {
    **previous,
    "format": "RGBA8 faces, unchanged BC3 other glyphs",
    "packing": "Faces: 512-byte RGBA palette + raw LZ4 8-bit indices; others: raw LZ4 BC3",
    "packed_bytes": len(blob),
    "sha256": hashlib.sha256(blob).hexdigest(),
    "textures": rows,
    "face_art_metrics": metrics,
}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Packed", len(blob), "bytes; four uncompressed RGBA8 GPU faces")
