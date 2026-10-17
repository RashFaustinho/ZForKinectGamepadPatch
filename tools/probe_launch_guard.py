"""Observe a real launched-strike choice and answer only with B.

Native pad events and read-only observations, without changing AI, health,
phases or outcomes. A requested input alone is never counted as acceptance.
"""
import argparse
import fcntl
import json
import struct
import time

import battle_state as b
from coordinate_audit import request
from virtual_pad import VirtualPad


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('session')
p.add_argument('name')
p.add_argument('--seconds', type=float, default=150)
p.add_argument('--successes', type=int, default=2)
p.add_argument('--approach', action='store_true', help='Use normal aura/approach controls to return to close combat')
a = p.parse_args()
if not a.name.replace('-', '').isalnum() or a.seconds <= 0 or a.successes < 1:
    p.error('Invalid report name or limits')
b.connect(a.session)
lock = open(b.input_lock_path(), 'a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
out = b.endpoint.parent / (a.name + '.json')
if out.exists():
    p.error('Report already exists')
rows, hits = [], []
first = b.word(0x8266E184)
started = time.monotonic()
last = None
last_approach = -1000
seen = set()
request({'command': 'resume'})
try:
    with VirtualPad(b.display_name()) as pad:
        while time.monotonic() - started < a.seconds:
            owner = b.word(0x82649298)
            if not owner or not b.word(owner + 0x54):
                if rows:
                    break
                pad.key('j', b.word(0x8266E184) % 12 < 4)
                time.sleep(.1)
                continue
            s = b.sample()
            ui = b.word(owner + 0x64)
            widget = b.word(ui + 0x90)
            panels = []
            if widget:
                for off in range(0x34, 0x44, 4):
                    panel = b.word(widget + off)
                    panels.append({'choice': b.word(panel + 0x68),
                                   'latched': b.word(panel + 0x6C)})
            # Cinematic modes contain several response types. B is sent
            # there, but counted only if the native guard caller and UI latch
            # actually accept it; no guessed phase pointer gates the input.
            window = s['mode'] in (5, 8)
            frame = s['bridge']['frame']
            # Pulse X only while the native battle is still initializing.
            starting = (s['mode'] == 4 and s['players'][0]['state'] == 0
                        and s['players'][0]['pending_state'] == 114)
            desired = 'b' if window else 'j' if starting and frame % 12 < 4 else None
            if a.approach and desired is None and s['mode'] == 6 and s['players'][0]['state'] == 20:
                if s['players'][0]['energy'] < 25:
                    desired = 'c'
                elif frame - last_approach > 100:
                    last_approach = frame
                if frame - last_approach < 4:
                    desired = 'space'
            for key in ('b', 'j', 'c', 'space'):
                pad.key(key, desired == key)
            accepted, stamp, _, _, caller, _ = struct.unpack('>6I', b.read(0x8266E1E8, 24))
            row = {'frame': frame, 'mode': s['mode'],
                   'players': s['players'], 'window': window,
                   'panels': panels, 'key': desired,
                   'accepted': hex(accepted), 'stamp': stamp, 'caller': hex(caller)}
            signature = (s['mode'], s['players'][0]['state'], window,
                         accepted, stamp)
            if signature != last:
                rows.append(row)
                print(json.dumps(row), flush=True)
                last = signature
            guard_stamp = b.word(0x8266E2E0 + 0x2A * 4)
            if (guard_stamp > first and guard_stamp not in seen
                    and any(p['latched'] and p['choice'] == 0 for p in panels)):
                row['guard_accepted_frame'] = guard_stamp
                hits.append(row)
                seen.add(guard_stamp)
                if len(hits) >= a.successes:
                    break
            if s['mode'] == 0 and min(x['hp'] for x in s['players']) <= 1:
                break
            time.sleep(.025)
finally:
    request({'command': 'pause'})
    out.write_text(json.dumps({'scope': __doc__, 'hits': hits, 'samples': rows}, indent=2) + '\n')
print(out)
