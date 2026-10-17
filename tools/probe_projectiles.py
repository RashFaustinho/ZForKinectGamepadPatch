"""Inspect a native player shot, with pad input and read-only guest snapshots.

Pauses the owned Xenia child for captures; never writes game memory. Null GPU
captures establish logic only. Screenshots are meaningful only with Vulkan.
"""
import argparse
import ctypes
import ctypes.util
import fcntl
import json
import socket
import struct
import subprocess
import time
from pathlib import Path
import battle_state as b

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('session');p.add_argument('name')
p.add_argument('--seconds',type=float,default=15)
p.add_argument('--hold',type=float,default=1.5)
p.add_argument('--key',default='j',help='Virtual pad key: j = X, k = Y')
p.add_argument('--wait-ranged',type=float,default=0)
p.add_argument('--effect-only',action='store_true',help='Capture after the player projectile exists, not at the start of the shot animation')
p.add_argument('--effect-frames',type=int,nargs='+',default=[0],help='Native-frame offsets after first observed player projectile')
a=p.parse_args();b.connect(a.session)
if not a.name.replace('-', '').replace('_', '').isalnum():
    p.error('Invalid capture name')
lock=open(b.input_lock_path(),'a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def request(payload):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(10);s.connect(str(b.endpoint));s.sendall(json.dumps(payload).encode()+b'\n')
        raw=b''
        while not raw.endswith(b'\n'):raw+=s.recv(65536)
    r=json.loads(raw)
    if not r['ok']:raise RuntimeError(r)
    return r
def snapshot():
    state=b.sample();state['effects']=[]
    manager=b.word(0x82649164)
    base=b.word(manager) if manager else 0
    for actor in state['players']:
        address=int(actor['actor'],16)
        data=b.read(address+0x11F0,0xEEC)
        effects=[]
        for i in range(50):
            ident,kind=struct.unpack_from('>ii',data,8+i*0x4C)
            if ident>=0:
                item={'slot':i,'id':ident,'kind':kind,'record':data[4+i*0x4C:4+(i+1)*0x4C].hex()}
                if base and ident<2048:
                    effect=base+ident*0xA10
                    item['cached_direction']=list(struct.unpack('>4f',b.read(effect+0x350,16)))
                    item['spawn_position']=list(struct.unpack('>4f',b.read(effect+0x7B0,16)))
                    item['target']=list(struct.unpack('>4f',b.read(effect+0x750,16)))
                    item['parameters']=b.read(effect+0x780,0x70).hex()
                effects.append(item)
        state['effects'].append(effects)
    return state
out=b.endpoint.parent/(a.name+'.json')
if out.exists():raise RuntimeError('Capture exists')
rows=[];screens=[]
from debug_session import runner
x=runner.x11();display=x.XOpenDisplay(b.display_name().encode())
x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong
x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_ubyte
x.XFlush.argtypes=[ctypes.c_void_p]
t=ctypes.CDLL(ctypes.util.find_library('Xtst'))
t.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
code=x.XKeysymToKeycode(display,x.XStringToKeysym(a.key.encode()))
if not code:raise RuntimeError('Unknown input key')
def key(kind):t.XTestFakeKeyEvent(display,code,int(kind=='down'),0);x.XFlush(display)
request({'command':'resume'})
if a.wait_ranged:
    deadline=time.monotonic()+a.wait_ranged
    while time.monotonic()<deadline:
        state=b.sample()
        if state['mode']==6 and state['players'][0]['state']==20 and not state['players'][0]['input_suppressed']:break
        time.sleep(.05)
    else:
        request({'command':'pause'});raise RuntimeError('No native ranged idle state')
start=time.monotonic();key('down');released=False
seen=False;first_effect_frame=None;captured_offsets=set()
try:
    while time.monotonic()-start<a.seconds:
        state=snapshot();state['seconds']=round(time.monotonic()-start,3);rows.append(state)
        if not released and time.monotonic()-start>=a.hold:key('up');released=True
        if state['effects'][0] and first_effect_frame is None:first_effect_frame=state['bridge']['frame']
        offset=None
        if a.effect_only and state['effects'][0] and first_effect_frame is not None:
            offset=next((v for v in sorted(a.effect_frames) if v not in captured_offsets and state['bridge']['frame']-first_effect_frame>=v),None)
        capture=(offset is not None) if a.effect_only else ((state['players'][0]['state']==29 or state['effects'][0]) and not seen)
        if capture:
            request({'command':'pause'})
            rows.append(snapshot());screens.append(request({'command':'screenshot','name':a.name+'-shot'+('-'+str(offset) if a.effect_only else '')}))
            if offset is not None:captured_offsets.add(offset)
            seen=True;request({'command':'resume'})
        time.sleep(.01)
finally:
    key('up');x.XCloseDisplay(display);request({'command':'pause'})
    out.write_text(json.dumps({'samples':rows,'screenshots':screens},indent=2)+'\n')
print(out)
