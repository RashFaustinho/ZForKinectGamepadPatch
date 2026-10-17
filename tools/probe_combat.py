"""Record an actual combat input and read-only HP/energy observations.

The owned session is resumed for the probe and paused afterwards. This drives
Xenia's diagnostic keyboard pad on its owned display; no guest memory is written.
"""
import argparse
import fcntl
import json
import socket
import subprocess
import time
from pathlib import Path

import battle_state as battle


def request(payload):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(10)
        client.connect(str(battle.endpoint))
        client.sendall(json.dumps(payload).encode() + b'\n')
        data = b''
        while not data.endswith(b'\n'):
            part = client.recv(65536)
            if not part:
                raise RuntimeError('Supervisor disconnected')
            data += part
    response = json.loads(data)
    if not response['ok']:
        raise RuntimeError(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    parser.add_argument('name')
    parser.add_argument('key')
    parser.add_argument('--hold', type=float, default=1)
    parser.add_argument('--after', type=float, default=5)
    parser.add_argument('--interval', type=float, default=.25)
    parser.add_argument('--wait-ready', action='store_true', help='Wait up to 60 seconds for an idle, interactive combat state')
    parser.add_argument('--release-at-energy', type=float, help='Release as soon as the observed native energy reaches this value')
    args = parser.parse_args()
    if not args.name.replace('-', '').replace('_', '').isalnum():
        parser.error('Invalid capture name')
    if not .005 <= args.interval <= 1:
        parser.error('Sample interval must be between .005 and 1 seconds')
    if not 0.05 <= args.hold <= 120 or not 0 <= args.after <= 120:
        parser.error('Probe durations must be between 0.05 and 120 seconds')
    if args.release_at_energy is not None and not 0 < args.release_at_energy <= 100:
        parser.error('Energy threshold must be between 0 and 100')
    battle.connect(args.session)
    # XTest targets one shared display. Refuse overlapping input drivers,
    # including drivers testing a different Xenia session on display :99.
    input_lock = open(battle.input_lock_path(), 'a')
    fcntl.flock(input_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    output = battle.endpoint.parent / (args.name + '.json')
    if output.exists():
        parser.error('Capture already exists')
    rows = []
    input_tool = Path(__file__).with_name('x11_input.py')

    def key(kind):
        subprocess.run(['python3', str(input_tool), kind, args.key,'--display',battle.display_name()], check=True)

    started = time.monotonic()

    def record(phase):
        row = battle.sample()
        row.update(seconds=round(time.monotonic() - started, 3), phase=phase)
        rows.append(row)
        print(json.dumps(row), flush=True)
        return row

    request({'command': 'resume'})
    try:
        if args.wait_ready:
            deadline = time.monotonic() + 60
            while True:
                state = battle.sample()
                player = state['players'][0]
                if (state['mode'] in (4, 6) and player['state'] in (0, 1, 20)
                        and not player['input_suppressed']):
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('No idle combat state within 60 seconds')
                time.sleep(0.25)
            started = time.monotonic()
        record('before')
        key('down')
        try:
            deadline = time.monotonic() + args.hold
            while time.monotonic() < deadline:
                row = record('held')
                if (args.release_at_energy is not None
                        and row['players'][0]['energy'] >= args.release_at_energy):
                    break
                time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
        finally:
            key('up')
        record('released')
        deadline = time.monotonic() + args.after
        while time.monotonic() < deadline:
            record('after')
            time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
        record('completed')
    finally:
        request({'command': 'pause'})
        output.write_text(json.dumps({'key': args.key, 'hold': args.hold,
                                      'after': args.after, 'release_at_energy':args.release_at_energy,
                                      'samples': rows}, indent=2) + '\n')


if __name__ == '__main__':
    main()
