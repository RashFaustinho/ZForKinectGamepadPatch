"""Check public sources and recorded evidence; does not rerun game-dependent tests."""
import ast
import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

from patch_format import read
from create_content_save import valid as valid_save

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / 'experiments/gamepad-final-v1.0.0'
EXPECTED = 'bcf6ee7b2f92c4f416cb3c8625487f4f345937c91f0b7cb0b525f1186ef5fb50'


def main():
    names = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=ROOT).decode().split('\0')
    files = sorted({ROOT / name for name in names if name})
    errors = []
    release_zip = ROOT / 'releases/v1.0.0/ZForKinectGamepadPatch-1.0.0.zip'
    if hashlib.sha256(release_zip.read_bytes()).hexdigest() != 'f63e598c14f141e22cfb8039378329b1bc3d853b45026892d0449298e025e1eb':
        errors.append('Frozen English release archive changed')
    save_dir = ROOT / 'releases/v1.0.0/content-complete-save'
    save = (save_dir / 'DB_SAVE').read_bytes()
    save_manifest = json.loads((save_dir / 'manifest.json').read_text())
    if (not valid_save(save)
            or hashlib.sha256(save).hexdigest() != save_manifest['sha256']
            or int.from_bytes(save[0x2EEC:0x2EF0], 'big') != 1
            or save[0x2F00:0x2F18] != bytes([255]) * 24):
        errors.append('Generated save checksum, identity or inactive power-up mismatch')
    counts = {'files': len(files), 'python': 0, 'json': 0, 'toml': 0, 'markdown': 0}
    for path in files:
        rel = path.relative_to(ROOT)
        if (path.suffix.lower() in {'.iso', '.xex', '.torrent', '.7z', '.log'}
                or (path.suffix.lower() == '.zip' and path != release_zip)
                or rel.parts[0] in {'saves', 'private', 'dist', 'runtime', 'analysis'}):
            errors.append(f'Private/distribution-only file: {rel}')
        try:
            if path.suffix == '.py':
                ast.parse(path.read_text(), filename=str(rel))
                counts['python'] += 1
            elif path.suffix == '.json':
                json.loads(path.read_text())
                counts['json'] += 1
            elif path.suffix == '.toml':
                # Historical failed experiments retain their original writes.
                # Enforce the release schema only on the artifact for players.
                tomllib.loads(path.read_text())
                if path.parent == FINAL:
                    read(path)
                counts['toml'] += 1
            elif path.suffix == '.md':
                counts['markdown'] += 1
                for dest in re.findall(r'\]\(([^)\n]+)\)', path.read_text()):
                    dest = dest.strip('<>')
                    if urlsplit(dest).scheme or dest.startswith('#'):
                        continue
                    target = path.parent / unquote(dest.split('#', 1)[0])
                    if rel.as_posix() == 'docs/release-readme.md':
                        # This template's links resolve inside the release ZIP.
                        target = ROOT / {'CARD_READER.md': 'docs/powerup-cards.md',
                                         'VERIFICATION.md': 'docs/final-review.md'}.get(dest, str(target))
                    if not target.exists():
                        errors.append(f'Broken documentation link: {rel}: {dest}')
        except (ValueError, SyntaxError, OSError) as exc:
            errors.append(f'{rel}: {exc}')
    patch_path = FINAL / '4E4D084E.gamepad.patch.toml'
    raw = patch_path.read_bytes()
    if len(raw) != 64441 or hashlib.sha256(raw).hexdigest() != EXPECTED:
        errors.append('Released patch bytes changed')
    manifest = json.loads((FINAL / 'manifest.json').read_text())
    runtime = json.loads((FINAL / 'runtime-checks.json').read_text())
    suites = json.loads((FINAL / 'suite-results.json').read_text())
    if manifest.get('version') != '1.0.0' or manifest.get('patch_sha256') != EXPECTED:
        errors.append('Final manifest mismatch')
    if len(suites) != 15 or any(s.get('patch_sha256') != EXPECTED or s.get('exit_code') != 0 or not (ROOT / s['script']).is_file() for s in suites):
        errors.append('Recorded CPU suite metadata mismatch')
    if runtime.get('patch_sha256') != EXPECTED or runtime.get('passed') is not True or runtime.get('public_startup', {}).get('passed') is not True:
        errors.append('Recorded runtime metadata mismatch')
    readme = (ROOT / 'README.md').read_text()
    for marker in ('# ⚠️ IMPORTANT DISCLAIMER', 'PRIMARILY WITH AI', 'EUROPEAN', 'En/Fr/De/Es/It', 'C9561ED1F9AFFED4', 'Double Ki Blast', 'LT ×4', 'Reset Power-Up Card'):
        if marker not in readme:
            errors.append('Missing README requirement: ' + marker)
    print(json.dumps({'passed': not errors, 'checks': counts,
                      'patch_sha256': EXPECTED,
                      'game_dependent_tests_rerun': False, 'errors': errors}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
