"""Package only the verified final patch and self-contained English guides.

No game files, profiles, private saves or diagnostic variants are included.
Archive timestamps, order, permissions and contents are deterministic.
"""
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from patch_format import read

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / 'experiments/gamepad-final-v1.0.0'
PATCH_NAME = '4E4D084E.gamepad.patch.toml'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def guide(name):
    text = (ROOT / 'docs' / name).read_text()
    replacements = {
        '../experiments/gamepad-final-v1.0.0/' + PATCH_NAME: 'patches/' + PATCH_NAME,
        '../experiments/gamepad-final-v1.0.0/suite-results.json': 'validation.json',
        '../experiments/gamepad-final-v1.0.0/runtime-checks.json': 'validation.json',
        '../experiments/gamepad-feedback-v19/4E4D084E.gamepad-feedback.patch.toml': 'patches/' + PATCH_NAME,
    }
    replacements['../experiments/gamepad-feedback-v19/powerup-catalog-runtime.json'] = 'validation.json'
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('utf-8')


def build(output):
    source = FINAL / PATCH_NAME
    patch_bytes = source.read_bytes()
    patch = read(source)
    manifest = json.loads((FINAL / 'manifest.json').read_text())
    validation = json.loads((FINAL / 'runtime-checks.json').read_text())
    suites = json.loads((FINAL / 'suite-results.json').read_text())
    sha = digest(patch_bytes)
    if manifest.get('version') != '1.0.0' or manifest.get('patch_sha256') != sha:
        raise ValueError('Final manifest does not identify this patch')
    if validation.get('patch_sha256') != sha or validation.get('passed') is not True:
        raise ValueError('Final validation is missing or belongs to another patch')
    if len(suites) != 15 or any(x['exit_code'] != 0 or x['patch_sha256'] != sha for x in suites):
        raise ValueError('All fifteen CPU suites must pass on the packaged patch')
    startup = validation['public_startup']
    if startup.get('passed') is not True or startup.get('patch_sha256') != sha:
        raise ValueError('Public startup readback is not verified')
    files = {
        'README.md': guide('release-readme.md'),
        'CARD_READER.md': guide('powerup-cards.md'),
        'VERIFICATION.md': guide('final-review.md'),
        'patches/' + PATCH_NAME: patch_bytes,
        'validation.json': (json.dumps(validation, indent=2, ensure_ascii=False) + '\n').encode(),
    }
    for name, data in files.items():
        if name.endswith('.md'):
            for link in re.findall(r'\]\(([^)]+)\)', data.decode()):
                if not re.match(r'https?://|#', link) and link not in files:
                    raise ValueError(f'Unpackaged documentation link: {name}: {link}')
    package_manifest = {
        'package': 'ZForKinectGamepadPatch', 'version': manifest['version'],
        'region': 'Europe', 'languages': ['En', 'Fr', 'De', 'Es', 'It'],
        'title_id': patch['title_id'], 'module_hash': patch['hash'],
        'patch_sha256': sha, 'byte_identical_to_validated_final_patch': True,
        'tested_emulator': {'name': 'Xenia Canary', 'revision': 'b735063', 'platform': 'Linux'},
        'files': {name: {'bytes': len(data), 'sha256': digest(data)}
                  for name, data in sorted(files.items())},
    }
    files['manifest.json'] = (json.dumps(package_manifest, indent=2) + '\n').encode()
    files['SHA256SUMS'] = ''.join(f'{digest(data)}  {name}\n'
                                for name, data in sorted(files.items())).encode()
    package = 'ZForKinectGamepadPatch-' + manifest['version']
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(package + '/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    raw = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != len(files):
            raise ValueError('Archive CRC or file count mismatch')
        for name, data in files.items():
            if archive.read(package + '/' + name) != data:
                raise ValueError('Archive differs from validated input: ' + name)
    output.mkdir(parents=True, exist_ok=True)
    target = output / (package + '.zip')
    if target.exists():
        if target.read_bytes() != raw:
            raise FileExistsError('A different release already exists: ' + str(target))
    else:
        with target.open('xb') as f:
            f.write(raw)
    target.with_suffix('.zip.sha256').write_text(f'{digest(raw)}  {target.name}\n')
    print(json.dumps({'archive': str(target), 'sha256': digest(raw),
                      'patch_sha256': sha, 'files': len(files)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    build(parser.parse_args().output.resolve())
