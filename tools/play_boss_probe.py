"""Timed diagnostic input driver for the LOCAL boss-query logging patch.

Reads the game's requested action and presses its mapped pad input. It never
writes HP, phase counters, animation flags, or guest memory. This is a probe,
not part of the distributed patch and not evidence of normal playability.
"""
import argparse
import ctypes
import ctypes.util
import fcntl
import json
import struct
import time
from pathlib import Path
import battle_state as b
from debug_session import request,runner

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('session');p.add_argument('--seconds',type=float,default=180)
p.add_argument('--name',default='automatic-input-probe')
p.add_argument('--stop-on-unlock',action='store_true',help='Pause once the previously locked next saga becomes available')
args=p.parse_args()
if not args.name.replace('-','').isalnum():p.error('Invalid capture name')
b.connect(args.session)
lock=open(b.input_lock_path(),'a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
output=b.endpoint.parent/(args.name+'.json')
if output.exists():raise SystemExit('Output already exists')
bindings=json.loads((Path(__file__).resolve().parents[1]/'experiments/gamepad-layout-v2/bindings.json').read_text())
key_masks=[(2,'c'),(0x10,'k'),(0x20,'b'),(0x40,'space'),(0x80,'j'),
           (0x100,'q'),(0x200,'e'),(0x400,'1'),(0x800,'3'),
           (0x4000,'a'),(0x8000,'d'),(0x10000,'Up'),(0x20000,'Down')]
held=None;rows=[];events=[];started=time.monotonic()
x=runner.x11();display=x.XOpenDisplay(b.display_name().encode())
x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong
x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_ubyte
x.XFlush.argtypes=[ctypes.c_void_p]
t=ctypes.CDLL(ctypes.util.find_library('Xtst'))
t.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
def key(kind,name):
    code=x.XKeysymToKeycode(display,x.XStringToKeysym(name.encode()))
    t.XTestFakeKeyEvent(display,code,int(kind=='down'),0);x.XFlush(display)
try:
    time.sleep(5)
    owner=b.word(0x82649298)
    if not owner or not b.word(owner+0x54):
        for i in range(60):
            request(args.session,{'command':'key','key':'space' if i%2==0 else 'j','duration':.2})
            owner=b.word(0x82649298)
            if owner and b.word(owner+0x54):break
            time.sleep(2)
    request(args.session,{'command':'resume'})
    state=b.sample()
    if state['battle_kind']!=1:raise RuntimeError('The diagnostic did not enter the boss')
    progress=b.word(b.word(0x8264920c))
    next_saga_before=b.word(progress+0x494+0x28)
    print('Boss input probe started',flush=True)
    begin=time.monotonic();last_sample=-1;last_pulse=-10;previous_query=None
    while time.monotonic()-begin<args.seconds:
        now=time.monotonic()-begin
        observed_query=b.word(0x8266e1b8)
        query=observed_query
        owner=b.word(0x82649298);context=b.word(owner+0x54)
        qte=b.word(context+0x2fd0)
        qwords=struct.unpack('>20I',b.read(qte,0x50))
        step=qwords[13]
        # Prefer the explicit boss QTE when active. Other story interactions
        # and the closing regular-combat prompt use separate native consumers.
        if qwords[1]==2:
            # Type 6 reads a separate camera flag, now translated from RT by
            # the patch; type 7 reads public action 1D, also bound to RT.
            query=0x1d if qwords[2] in (6,7) else (qwords[3+step] if step<5 else 0xffffffff)
        else:query=observed_query
        if now-last_sample>=.5:
            state=b.sample();state.update(seconds=round(now,3),requested_action=hex(query))
            state['qte']={'state':qwords[1],'type':qwords[2],'step':step,'actions':list(qwords[3:8]),
                          'progress':struct.unpack('>f',struct.pack('>I',qwords[17]))[0]}
            rows.append(state);last_sample=now
            if len(rows)%20==0:print('phase',state.get('boss_phase',{}).get('index'),'query',hex(query),'Ki',state['players'][0]['energy'],flush=True)
            if (args.stop_on_unlock and next_saga_before==0
                    and b.word(progress+0x494+0x28)&1):
                print('Native next-saga unlock observed',flush=True);break
        target=None;continuous=False
        if query<len(bindings):
            item=bindings[query];mask=int(item['pad_mask'],16)
            target=next((name for bit,name in key_masks if mask&bit),None)
            continuous=item['source']=='held'
        if qwords[1]!=2 and state['mode']==7 and state['players'][0]['energy']<100:
            target='c';continuous=True # Native boss free-battle charge, not a forced Ki value.
        if (qwords[1]!=2 and state.get('boss_phase',{}).get('index',0)>=24
                and observed_query in (1,2,3,4,0x13)):
            # The closing clash uses the regular attack-mash prompt, not the
            # boss gesture-sequence object. Native code accepts charged attack.
            target='3';continuous=True;query=3
        if query!=previous_query:
            last_pulse=-10;previous_query=query
        desired=target if continuous or now-last_pulse<.08 else None
        if target and not continuous and now-last_pulse>=.16:
            last_pulse=now;desired=target
        if desired!=held:
            if held:key('up',held)
            if desired:key('down',desired)
            events.append({'seconds':round(now,3),'query':hex(query),'key':desired})
            held=desired
        time.sleep(.015)
finally:
    if held:key('up',held)
    x.XCloseDisplay(display)
    try:request(args.session,{'command':'pause'})
    finally:
        progress=b.word(b.word(0x8264920c))
        flags={'fifth_stage':b.word(progress+0x28+4*0x94),
               'next_saga_first_stage':b.word(progress+0x494+0x28)}
        output.write_text(json.dumps({'elapsed':time.monotonic()-started,'samples':rows,'inputs':events,
                                     'native_progress_flags':flags},indent=2)+'\n')
