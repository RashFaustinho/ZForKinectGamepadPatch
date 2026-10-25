"""Package regional content-complete saves from verified player release ZIPs.

No account, profile, content header or original game file is included. The
existing game-data bytes and regional native-load evidence remain unchanged.
"""

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path
from create_content_save import valid

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(region, version, source, output):
    label = "Europe" if region == "europe" else "USA"
    package = f"ZForKinectGamepadPatch-{version}"
    source_zip = source / f"{package}-{label}.zip"
    with zipfile.ZipFile(source_zip) as z:
        if z.testzip() is not None:
            raise ValueError("Player ZIP CRC failure")
        prefix = f"{package}-{label}/"
        for line in z.read(prefix + "SHA256SUMS").decode().splitlines():
            digest, name = line.split("  ", 1)
            if sha(z.read(prefix + name)) != digest:
                raise ValueError("Player ZIP checksum mismatch")
        save_prefix = prefix + "optional-save/"
        files = {
            name[len(save_prefix) :]: z.read(name)
            for name in z.namelist()
            if name.startswith(save_prefix)
        }
    if set(files) != {
        "DB_SAVE",
        "README.md",
        "manifest.json",
        "native-load-check.json",
        "SHA256SUMS",
    }:
        raise ValueError("Unexpected standalone save contents")
    data = files["DB_SAVE"]
    metadata = json.loads(files["manifest.json"])
    evidence = json.loads(files["native-load-check.json"])
    if (
        not valid(data)
        or len(data) != 150000
        or sha(data) != metadata["sha256"]
        or metadata["region"] != label
        or metadata["active_powerup"] is not None
        or not evidence["loaded_buffer_exact_match"]
        or evidence["loaded_buffer_sha256"] != sha(data)
        or int.from_bytes(data[0x2EEC:0x2EF0], "big") != 1
        or data[0x2F00:0x2F18] != bytes([255]) * 24
    ):
        raise ValueError(
            "Save identity, native load, checksum or inactive-card mismatch"
        )
    for line in files["SHA256SUMS"].decode().splitlines():
        digest, name = line.split("  ", 1)
        if sha(files[name]) != digest:
            raise ValueError("Nested save checksum mismatch")
    name = f"{package}-Content-Complete-Save-{label}"
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as z:
        for filename, contents in sorted(files.items()):
            info = zipfile.ZipInfo(
                name + "/" + filename, date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, contents, compresslevel=9)
    payload = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        assert z.testzip() is None
        assert all(z.read(name + "/" + n) == v for n, v in files.items())
    output.mkdir(parents=True, exist_ok=True)
    path = output / (name + ".zip")
    if path.exists() and path.read_bytes() != payload:
        raise FileExistsError("Different standalone save archive exists")
    path.write_bytes(payload)
    path.with_suffix(".zip.sha256").write_text(sha(payload) + "  " + path.name + "\n")
    print(
        json.dumps(
            {
                "archive": str(path),
                "bytes": len(payload),
                "sha256": sha(payload),
                "save_sha256": sha(data),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="1.1.2", choices=("1.1.2",))
    parser.add_argument("--source", type=Path, default=ROOT / "releases/v1.1.2")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/1.1.2")
    args = parser.parse_args()
    for region in ("europe", "usa"):
        build(region, args.version, args.source, args.output)
