"""Capture the virtual player's data from an owned debug_session, read-only."""
import argparse
import json
import socket
import struct
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('session')
parser.add_argument('name')
args = parser.parse_args()
for value in (args.session, args.name):
    if not value.replace('-', '').replace('_', '').isalnum():
        parser.error('Use an alphanumeric session and capture name')
root = Path('/workspace/artifacts/zforkinect')
directory = root / 'runtime' / args.session
out = directory / ('state-' + args.name)
out.mkdir(exist_ok=False)


def request(payload):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(10)
        client.connect(str(directory / 'control.sock'))
        client.sendall(json.dumps(payload).encode() + b'\n')
        data = b''
        while not data.endswith(b'\n'):
            chunk = client.recv(65536)
            if not chunk:
                raise RuntimeError('Supervisor disconnected')
            data += chunk
    result = json.loads(data)
    if not result['ok']:
        raise RuntimeError(result)
    return result


def read(address, size):
    result = request({'command': 'read', 'address': hex(address), 'size': size})
    data = bytes.fromhex(result['hex'])
    if len(data) != size:
        raise RuntimeError('Incomplete guest read')
    return data


def word(address):
    return struct.unpack('>I', read(address, 4))[0]


manager = word(0x826491D8)
context = word(manager + 0x1c)
controller = word(word(0x826490DC) + 0x98)
regions = {'manager': (manager, 0x480), 'context': (context, 0x27c0),
           'controller': (controller, 0x98), 'diagnostic': (0x8266E180, 64)}
metadata = {'status': request({'command': 'status'}), 'regions': {}}
for name, (address, size) in regions.items():
    data = read(address, size)
    (out / (name + '.bin')).write_bytes(data)
    metadata['regions'][name] = {'address': hex(address), 'size': size}
metadata['screenshot'] = request({'command': 'screenshot', 'name': args.name})['path']
(out / 'capture.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(out)
