"""Compare a supplied generated save with Xenia's native loaded save buffer.

Read-only observation in an owned debug_session. No profile data is exported.
A byte match and local checksum are distinct from a full gameplay test.
"""
import argparse
import hashlib
import json
from pathlib import Path

import battle_state as b
from coordinate_audit import request
from create_content_save import valid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    parser.add_argument('save', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('Report already exists')
    expected = args.save.read_bytes()
    if not valid(expected):
        parser.error('Expected a valid 150000-byte generated game-data file')
    b.connect(args.session)
    was_paused = request({'command': 'status'})['paused']
    request({'command': 'pause'})
    try:
        manager = b.word(0x8264920C)
        buffer = b.word(manager) if manager else 0
        if not buffer:
            raise RuntimeError('Native save buffer is unavailable')
        loaded = b.read(buffer, len(expected))
        result = {
            'session': args.session,
            'scope': 'Read-only comparison with the native loaded save buffer; no live writes. Not a full gameplay test.',
            'startup_patches': [
                {'name': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted((b.endpoint.parent / 'storage/patches').glob('*.patch.toml'))
            ],
            'file_bytes': len(expected),
            'file_sha256': hashlib.sha256(expected).hexdigest(),
            'loaded_buffer_sha256': hashlib.sha256(loaded).hexdigest(),
            'loaded_buffer_exact_match': loaded == expected,
            'local_native_format_checksum_valid': valid(loaded),
            'powerup_flags': int.from_bytes(loaded[0x2EEC:0x2EF0], 'big'),
            'active_powerup': bool(int.from_bytes(loaded[0x2EEC:0x2EF0], 'big') & 4),
            'selected_item_slots': [int.from_bytes(loaded[i:i+4], 'big') for i in range(0x2F00, 0x2F18, 4)],
        }
    finally:
        if not was_paused:
            request({'command': 'resume'})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))
    if not result['loaded_buffer_exact_match'] or not result['local_native_format_checksum_valid']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
