"""LOCAL: audit boss geometry while driving its explicit native QTE inputs.

This is an automated pad probe, not a feature of the distributed patch. Reads
QTE requests and native phase state; never writes guest memory or outcomes.
"""
import argparse
import ctypes
import ctypes.util
import fcntl
import json
import struct
import time
import tomllib
from pathlib import Path
import battle_state as b
from coordinate_audit import snapshot,request
from debug_session import runner

p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');p.add_argument('--seconds',type=float,default=120)
p.add_argument('--name',default='boss-coordinate-audit')
p.add_argument('--contextual-query',action='store_true',help='Use the diagnostic query excluding global super-preparation polls')
p.add_argument('--stop-on-unlock',action='store_true')
p.add_argument('--capture-prompts',action='store_true',help='Capture active native QTEs before answering, after eight bridge updates')
p.add_argument('--patch',type=Path,help='Use this patch binding table for diagnostic pad input')
a=p.parse_args();b.connect(a.session)
if not a.name.replace('-','').replace('_','').isalnum():p.error('Invalid capture name')
lock=open(b.input_lock_path(),'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
root=Path(__file__).resolve().parents[1]
patch=tomllib.loads((a.patch or root/'experiments/gamepad-feedback-v4/4E4D084E.gamepad-feedback.patch.toml').read_text())['patch'][0]
payload=bytes.fromhex(next(v['value'] for v in patch['array'] if v['address']==0x825EB100))
bindings=[struct.unpack_from('>II',payload,0xA00+i*8) for i in range(67)]
keys=[(2,'c'),(0x10,'k'),(0x20,'b'),(0x40,'space'),(0x80,'j'),(0x100,'q'),(0x200,'e'),(0x400,'1'),(0x800,'3'),(0x4000,'a'),(0x8000,'d'),(0x10000,'Up'),(0x20000,'Down')]
x=runner.x11();display=x.XOpenDisplay(b.display_name().encode())
x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong
x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_ubyte
x.XFlush.argtypes=[ctypes.c_void_p]
t=ctypes.CDLL(ctypes.util.find_library('Xtst'));t.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
def key(name,down):
    code=x.XKeysymToKeycode(display,x.XStringToKeysym(name.encode()));t.XTestFakeKeyEvent(display,code,int(down),0);x.XFlush(display)
output=b.endpoint.parent/(a.name+'.json')
if output.exists():raise RuntimeError('Capture exists')
rows=[];full=[];screens=[];captured=set();pending_capture=None;active_capture=None;held=None;last_signature=None;start=time.monotonic();last_pulse_frame=-100;previous=None;completed=False
termination='time limit'
def progress_flags():
    progress=b.word(b.word(0x8264920C))
    return {'fifth_stage':b.word(progress+0x28+4*0x94),
            'next_saga_first_stage':b.word(progress+0x494+0x28)}
before=progress_flags();native_unlock=False
if a.stop_on_unlock and before['next_saga_first_stage']!=0:
    raise RuntimeError('Next saga is already unlocked; this fixture cannot prove progression')
request({'command':'resume'})
try:
    while time.monotonic()-start<a.seconds:
        if a.stop_on_unlock and progress_flags()['next_saga_first_stage']&1:
            native_unlock=True;termination='native next-saga unlock observed';break
        try:state=b.sample()
        except SystemExit as exc:
            termination=str(exc)
            break
        if state['battle_kind']!=1:
            termination='left boss battle kind'
            break
        now=time.monotonic()-start;ctx=int(state['context'],16)
        qte=b.word(ctx+0x2FD0)
        if not qte:
            time.sleep(.07)
            continue
        q=struct.unpack('>20I',b.read(qte,0x50))
        phase=state.get('boss_phase',{});index=phase.get('index',0)
        if phase.get('count',0)>0 and index>=phase['count']:
            completed=True;termination='native phase table exhausted';break
        observed=b.word(0x8266E1FC if a.contextual_query else 0x8266E1F0)
        action=None;button=None;continuous=False
        if q[1] in (1,2):
            action=0x1D if q[2] in (6,7) else (q[3+q[13]] if q[13]<5 else None)
        elif observed<67:action=observed
        if action is not None and action<67:
            mask,source=bindings[action];button=next((name for bit,name in keys if bit&mask),None);continuous=source==0x20
        if q[1]==1:button=None # Let the native opening prompt appear before answering it.
        if q[1]!=2 and state['mode']==7 and state['players'][0]['energy']<100:button='c';continuous=True
        if q[1]!=2 and index>=24 and observed in (1,2,3,4,0x13):button='3';continuous=True
        signature=(index,q[1],q[2],q[13],action)
        frame=state['bridge']['frame']
        capture_id=(index,q[2],action)
        if a.capture_prompts and q[1]==2 and capture_id not in captured:
            if active_capture is None or active_capture[0]!=capture_id:active_capture=(capture_id,frame)
            if frame-active_capture[1]<12:button=None
        if signature!=previous:last_pulse_frame=frame-100;previous=signature
        if button and not continuous and frame-last_pulse_frame>=6:last_pulse_frame=frame
        desired=button if continuous or frame-last_pulse_frame<3 else None
        if held!=desired:
            if held:key(held,False)
            if desired:key(desired,True)
            held=desired
        if a.capture_prompts and q[1]==2 and capture_id not in captured:
            if pending_capture is None or pending_capture[0]!=capture_id:pending_capture=(capture_id,frame)
            elif frame-pending_capture[1]>=8:
                request({'command':'pause'})
                screen=request({'command':'screenshot','name':a.name+'-phase-'+str(index)+'-type-'+str(q[2])+'-action-'+str(action)})
                screens.append({'phase':index,'qte_type':q[2],'action':action,'frame':frame,'screen':screen})
                captured.add(capture_id);pending_capture=None;request({'command':'resume'})
        audit=snapshot()
        if signature!=last_signature:
            full.append(audit);last_signature=signature
        rows.append({'seconds':round(now,3),'phase':index,'qte_state':q[1],'qte_type':q[2],
                     'qte_step':q[13],'requested_action':action,'key':held,
                     'all_finite':audit['all_finite'],'invalid_regions':audit['invalid_regions'],
                     'joint_buffers_equal':audit['joint_buffers_equal'],
                     'bases_nondegenerate':audit['bases_nondegenerate']})
        if len(rows)%100==0:print(json.dumps(rows[-1]),flush=True)
        time.sleep(.07)
except KeyboardInterrupt:
    termination='operator interrupted the diagnostic; no completion claim'
finally:
    if held:key(held,False)
    x.XCloseDisplay(display);request({'command':'pause'})
    output.write_text(json.dumps({'scope':__doc__.strip(),'samples':rows,'coordinate_snapshots':full,
                                 'screenshots':screens,'pulse_timing':'3 native frames down, 3 up; held mappings remain held',
                                 'all_finite':all(v['all_finite'] for v in rows),
                                 'bases_nondegenerate':all(v['bases_nondegenerate'] for v in rows),
                                 'termination':termination,
                                 'progress_flags_before':before,'progress_flags_after':progress_flags(),
                                 'native_next_saga_unlock_observed':native_unlock,
                                 'native_phase_table_completed':completed},indent=2,allow_nan=False)+'\n')
print(output)
