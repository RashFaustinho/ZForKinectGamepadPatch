"""Consolidate the reviewed revision and scope B priority to launch choices.

The immutable input digest is pinned here, independently of editable reports.
The output has no overlapping writes and excludes local diagnostic fixtures.
All baseline bytes survive except the input entry redirected to the adapter.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from patch_format import consolidate_arrays, effective_bytes, read, serialize
from ppc_emit import Assembler

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'experiments/gamepad-feedback-v19/4E4D084E.gamepad-feedback.patch.toml'
SOURCE_SHA256 = '110b42a0918eceb834e3ee8a91f37a9868020414211a119171c333539514d735'
VERSION = '1.0.0'
IMAGE = Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin')
IMAGE_SHA256 = '72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
GUARD_ENTRY = 0x825EFE00
GUARD_CALLERS = (0x8220E788, 0x8220E81C, 0x82210FA8, 0x82210FC8)


def add_guard_priority(document, image_path=IMAGE):
    """Prefer B over a lingering stick only in native launch-choice callers."""
    image = image_path.read_bytes()
    if hashlib.sha256(image).hexdigest() != IMAGE_SHA256:
        raise ValueError('Unsupported original executable image')
    p = document['patch'][0]
    hook = next(x for x in p['be32'] if x['address'] == 0x82197118)
    displacement = hook['value'] & 0x3FFFFFC
    if displacement & 0x2000000:
        displacement -= 0x4000000
    original_target = hook['address'] + displacement
    for i, caller in enumerate(GUARD_CALLERS):
        native = image[caller - 12 - 0x82000000:caller - 0x82000000]
        call = Assembler(caller - 4)
        call.branch(0x82197118, True)
        expected = struct.pack('>II', 0x38800028 + i % 2,
                               0x7FC3F378 if i < 2 else 0x7FA3EB78) + call.finish()
        if native != expected:
            raise ValueError('Native launch-choice caller differs from analysis')
    a = Assembler(GUARD_ENTRY)
    a.emit(0x7D4802A6)  # mflr r10; LR itself is never changed.
    for caller in GUARD_CALLERS:
        a.pointer(9, caller)
        a.emit(0x7C0A4800)  # cmpw r10,r9 (the Xenon guest address's low word).
        a.jump('choice')
    a.jump('original', 0x48000000)
    a.label('choice')
    a.pointer(11, 0x826490DC)
    a.lwz(11, 0, 11)
    a.cmp(11, 0)
    a.jump('original')
    a.lwz(11, 0x98, 11)
    a.cmp(11, 0)
    a.jump('original')
    a.lwz(9, 0x20, 11)
    a.andi(9, 9, 0x20)
    a.jump('original')
    a.li(3, 0)  # Skip this lateral choice; the original next query reads B.
    a.emit(0x4E800020)
    a.label('original')
    a.branch(original_target)
    code = a.finish()
    memory = effective_bytes(document)
    if len(code) > 0x100 or any(image[GUARD_ENTRY - 0x82000000:GUARD_ENTRY - 0x82000000 + len(code)]):
        raise ValueError('Guard adapter exceeds verified empty executable padding')
    if any(GUARD_ENTRY + i in memory for i in range(len(code))):
        raise ValueError('Guard adapter overlaps another payload')
    p['array'].append({'address': GUARD_ENTRY, 'value': code.hex()})
    a = Assembler(hook['address'])
    a.branch(GUARD_ENTRY)
    hook['value'] = a.words[0]
    return {'entry': hex(GUARD_ENTRY), 'bytes': len(code),
            'callers': [hex(c) for c in GUARD_CALLERS],
            'scope': 'Only the four native lateral queries before B in launch choices; no phase or result fields are written.'}


def build(output, image_path=IMAGE):
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Revision 19 differs from the reviewed input')
    source = read(SOURCE)
    final = consolidate_arrays(source)
    guard_priority = add_guard_priority(final, image_path)
    p = final['patch'][0]
    p['name'] = 'Gamepad conversion 1.0.0'
    p['desc'] = ('Gamepad combat and menus, first-person arms, compact Xbox prompts, '
                 'native-timed Super defenses, content unlocks and optional power-up cards.')
    ranges = sorted((x['address'], x['address'] + (4 if kind == 'be32' else len(x['value']) // 2))
                    for kind in ('be32', 'array') for x in p[kind])
    if any(end > start for (_, end), (start, _) in zip(ranges, ranges[1:])):
        raise ValueError('Final patch contains overlapping writes')
    memory = effective_bytes(final)
    # The final artifact must not contain any locally injected counters,
    # prompt wrappers, per-action logging, or the tutorial lesson shortcut.
    for start, end in [(0x825EB780, 0x825EB800), (0x825ECE80, 0x825ED000),
                       (0x825ED200, 0x825ED800), (0x825EF700, 0x825EF800),
                       (0x8266E1D0, 0x8266E3EC)]:
        if any(memory.get(a, 0) for a in range(start, end)):
            raise ValueError(f'Local diagnostics present at {start:08X}')
    baseline = effective_bytes(source)
    if any(value != memory.get(address) for address, value in baseline.items()
           if not 0x82197118 <= address < 0x8219711C):
        raise ValueError('Unrelated reviewed bytes changed')
    text = serialize(final)
    digest = hashlib.sha256(text.encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    target = output / '4E4D084E.gamepad.patch.toml'
    # Rebuilds may reproduce an artifact, but never silently replace another.
    if target.exists() and target.read_text() != text:
        raise FileExistsError('A different final patch already exists: ' + str(target))
    target.write_text(text)
    manifest_path = output / 'manifest.json'
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text())
        if existing.get('patch_sha256') == digest and existing.get('input_sha256') == SOURCE_SHA256:
            print(json.dumps({'patch': str(target), 'sha256': digest,
                              'reproduced': True, 'validation_preserved': True}))
            return
    manifest = json.loads((SOURCE.parent / 'manifest.json').read_text())
    manifest.update(version=VERSION, status='release candidate: validation required after consolidation',
                    input_sha256=SOURCE_SHA256, patch_sha256=digest,
                    loaded_bytes_identical_to_revision19=False,
                    reviewed_bytes_preserved_except_guard_priority=True,
                    launch_guard_priority=guard_priority,
                    overlapping_writes=0, records=len(ranges),
                    runtime_report='runtime-checks.json', validation_report='docs/final-review.md')
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'patch': str(target), 'sha256': digest,
                      'reviewed_bytes_preserved': True, 'records': len(ranges)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'experiments/gamepad-final-v1.0.0')
    parser.add_argument('--image', type=Path, default=IMAGE,
                        help='Decoded, hash-verified European image from your own game copy')
    args = parser.parse_args()
    build(args.output, args.image)
