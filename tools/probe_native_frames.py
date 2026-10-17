"""Drive a virtual pad for native frames, useful with slow software Vulkan.

Only pad input and read-only guest inspection. Frame counts make a short press
observable even when one game frame takes longer than a wall-clock pulse.
"""
import argparse
import ctypes
import ctypes.util
import fcntl
import json
import time
import battle_state as b
from coordinate_audit import request,snapshot
from debug_session import runner

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('session');p.add_argument('name');p.add_argument('key')
p.add_argument('--hold-frames',type=int,default=3);p.add_argument('--after-frames',type=int,default=120)
p.add_argument('--warmup-frames',type=int,default=0);p.add_argument('--seconds',type=float,default=600)
p.add_argument('--stop-at-ranged',action='store_true');p.add_argument('--capture-state',type=int)
p.add_argument('--capture-delay',type=int,default=4)
p.add_argument('--capture-offsets',type=int,nargs='+',help='Capture several native frames after the requested actor state')
p.add_argument('--pulse-every',type=int,help='Repeat genuine pad presses with this native-frame period')
p.add_argument('--pulse-width',type=int,default=3)
p.add_argument('--audit-captures',action='store_true',help='Read geometric fields atomically beside each screenshot')
a=p.parse_args();b.connect(a.session)
if not a.name.replace('-','').isalnum() or min(a.hold_frames,a.after_frames,a.warmup_frames,a.capture_delay)<0:p.error('Invalid name or frame count')
if a.pulse_every is not None and not 0<a.pulse_width<a.pulse_every:p.error('Invalid pulse timing')
offsets=sorted(set(a.capture_offsets or [a.capture_delay]))
if min(offsets)<0:p.error('Negative capture offset')
lock=open(b.input_lock_path(),'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
out=b.endpoint.parent/(a.name+'.json')
if out.exists():raise RuntimeError('Capture exists')
x=runner.x11();display=x.XOpenDisplay(b.display_name().encode())
x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong
x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_ubyte
x.XFlush.argtypes=[ctypes.c_void_p]
t=ctypes.CDLL(ctypes.util.find_library('Xtst'));t.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
code=x.XKeysymToKeycode(display,x.XStringToKeysym(a.key.encode()))
if not code:raise RuntimeError('Unknown key')
def key(down):t.XTestFakeKeyEvent(display,code,int(down),0);x.XFlush(display)
rows=[];screens=[];audits=[];held=False;ranged=False;capture_frame=None;last_frame=-1;start=time.monotonic()
initial=b.word(0x8266E184);request({'command':'resume'})
try:
    while b.word(0x8266E184)-initial<a.warmup_frames:
        if time.monotonic()-start>a.seconds:raise RuntimeError('Warmup timed out')
        time.sleep(.1)
    initial=b.word(0x8266E184);key(True);held=True
    while time.monotonic()-start<a.seconds:
        state=b.sample();frame=state['bridge']['frame'];elapsed=frame-initial
        desired=elapsed<a.hold_frames and (a.pulse_every is None or elapsed%a.pulse_every<a.pulse_width)
        if desired!=held:key(desired);held=desired
        if frame!=last_frame:
            state.update(seconds=round(time.monotonic()-start,3),native_elapsed_frames=elapsed)
            rows.append(state);last_frame=frame
            if len(rows)%30==0:print(json.dumps(state),flush=True)
        if a.capture_state is not None and state['players'][0]['state']==a.capture_state and capture_frame is None:capture_frame=frame
        if capture_frame is not None and len(screens)<len(offsets) and frame-capture_frame>=offsets[len(screens)]:
            suffix='-action' if len(offsets)==1 else '-action-'+str(offsets[len(screens)])
            request({'command':'pause'});screens.append(request({'command':'screenshot','name':a.name+suffix}))
            if a.audit_captures:audits.append(snapshot())
            request({'command':'resume'})
        if a.stop_at_ranged and state['mode']==6 and state['players'][0]['state']==20:
            ranged=True;break
        if elapsed>=a.hold_frames+a.after_frames:break
        time.sleep(.08)
finally:
    if held:key(False)
    x.XCloseDisplay(display);request({'command':'pause'})
    out.write_text(json.dumps({'scope':__doc__.strip(),'key':a.key,'hold_frames':a.hold_frames,
                              'warmup_frames':a.warmup_frames,'samples':rows,'screenshots':screens,
                              'pulse_every':a.pulse_every,'pulse_width':a.pulse_width,'capture_audits':audits,
                              'ranged_idle_reached':ranged},indent=2)+'\n')
print(out)
