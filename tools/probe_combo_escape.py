"""LOCAL: wait for a native combo prompt and supply its pad response.

Read-only guest observations and XTest input; no changes to coefficients,
timers, HP, native phases or outcomes. A filled defender gauge is recorded
separately from merely sending the mapped command.
"""
import argparse
import ctypes
import ctypes.util
import fcntl
import json
import struct
import time
import battle_state as b
from coordinate_audit import request
from debug_session import runner

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('session');p.add_argument('--seconds',type=float,default=120)
p.add_argument('--name',default='live-combo-escape')
p.add_argument('--left-for-front',action='store_true',help='Test the LS-left alternative for the front-sway response')
p.add_argument('--only-choice',type=int,choices=(0,1,2),help='Respond only to this native prompt, for isolated directional coverage')
p.add_argument('--require-success-choice',type=int,choices=(0,1,2),help='Answer all prompts, but stop only on a gauge filled during this choice')
a=p.parse_args();b.connect(a.session)
if not a.name.replace('-','').isalnum():p.error('Invalid capture name')
lock=open(b.input_lock_path(),'a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
output=b.endpoint.parent/(a.name+'.json')
if output.exists():raise RuntimeError('Capture exists')
x=runner.x11();display=x.XOpenDisplay(b.display_name().encode())
x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong
x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_ubyte
x.XFlush.argtypes=[ctypes.c_void_p]
t=ctypes.CDLL(ctypes.util.find_library('Xtst'))
t.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
def key(name,down):
    code=x.XKeysymToKeycode(display,x.XStringToKeysym(name.encode()))
    t.XTestFakeKeyEvent(display,code,int(down),0);x.XFlush(display)
rows=[];held=None;full=False;filled_at=None;defending_seen=False;start=time.monotonic()
request({'command':'resume'})
try:
    while time.monotonic()-start<a.seconds:
        state=b.sample()
        if state['battle_kind']!=0:break
        ctx=int(state['context'],16);phase=b.read(ctx+0x3134,0x64)
        step=int.from_bytes(phase[4:8],'big');variant=int.from_bytes(phase[0x34:0x38],'big')
        choice=int.from_bytes(phase[0x54:0x58],'big');flags=phase[0x18]
        window_code=(1 if flags&4 else 5 if variant==1 and phase[0x50]&2 else 2 if flags&1 else 3 if flags&2 else -1) if step==1 and variant in (0,1) else -1
        owner=b.word(0x82649298);ui=b.word(owner+0x64)
        gauges=[]
        for off in (0x40,0x44):
            ptr=b.word(ui+off);data=b.read(ptr,0x84)
            gauges.append({'address':hex(ptr),'state':int.from_bytes(data[0x28:0x2c],'big'),
                           'success':int.from_bytes(data[0x44:0x48],'big'),
                           'progress':struct.unpack_from('>f',data,0x64)[0],
                           'attacker_increment':struct.unpack_from('>f',data,0x7c)[0],
                           'defender_increment':struct.unpack_from('>f',data,0x80)[0]})
        # The mash/escape window occurs during contact as well as cinematic
        # phases. Its own native object, rather than global battle mode 8,
        # identifies the window. The UI widget returns to state 0 while the
        # prompt remains active, so widget animation state must not gate input.
        active=step==1 and variant in (0,1) and bool(flags&1) and choice<3
        if active:defending_seen=True
        responding=active and (a.only_choice is None or choice==a.only_choice)
        desired=(('a' if a.left_for_front else '1'),'a','d')[choice] if responding else None
        if desired!=held:
            if held:key(held,False)
            if desired:key(desired,True)
            held=desired
        now=round(time.monotonic()-start,3)
        row={'seconds':now,'state':state,'combo_phase':{'step':step,'variant':variant,'flags':flags,'choice':choice},
             'native_window_code_snapshot':window_code,'native_phase_raw':phase.hex(),
             'key':held,'gauges':gauges}
        rows.append(row)
        if (gauges[1]['progress']>=1 and gauges[1]['success']==1 and defending_seen
                and (a.require_success_choice is None or choice==a.require_success_choice)):
            if not full:filled_at=now
            full=True
        if len(rows)%300==0:print(json.dumps(row),flush=True)
        if full and now-filled_at>3:break
        if state['players'][0]['hp']<=1 and state['mode']==0:break
        time.sleep(.02)
finally:
    if held:key(held,False)
    x.XCloseDisplay(display);request({'command':'pause'})
    output.write_text(json.dumps({'scope':__doc__.strip(),'only_choice':a.only_choice,
                                 'require_success_choice':a.require_success_choice,'samples':rows,
                                 'defender_gauge_filled':full},indent=2)+'\n')
print(output)
