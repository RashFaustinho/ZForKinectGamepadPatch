"""LOCAL: exercise pad groups and audit geometry in a null-GPU battle.

Only virtual pad input is sent. Records queried/accepted native action IDs and
finite coordinate checks. Context-inactive commands are reported, not forced.
"""
import argparse
import fcntl
import json
import struct
import subprocess
import time
from pathlib import Path
import battle_state as b
from coordinate_audit import snapshot,request

p=argparse.ArgumentParser(description=__doc__);p.add_argument('session')
a=p.parse_args();b.connect(a.session)
command=json.loads((b.endpoint.parent/'command.json').read_text())
if '--gpu=null' not in command:p.error('Use null GPU for this logic-only audit')
lock=open(b.input_lock_path(),'a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
main=Path(__file__).with_name('x11_input.py')
def key(kind,name):subprocess.run(['python3',str(main),kind,name,'--display',b.display_name()],check=True)
def activity():
    w=struct.unpack('>12I',b.read(0x8266E1D0,48))
    def ids(v):return [i for i in range(67) if v[i//32] & (1<<(i%32))]
    return {'queried':ids(w[:3]),'accepted':ids(w[3:6]),'last_accepted':w[6],
            'accepted_frame':w[7],'last_queried':w[8],'query_frame':w[9],
            'caller':hex(w[10])}
plan=[('punch','j',.3,2,{0,5,7,0x13,0x17}),
      ('upper_or_hook','q',.3,2,{1,0x15,0x1E}),
      ('kick','k',.3,2,{2,0x10,0x2B}),
      ('elbow','e',.3,2,{4,0x1F,0x24}),
      ('guard','b',2,1,{9,0xB,0x14,0x2A,0x2C}),
      ('left','a',2,1,{0xD,0x18,0x1B,0x26,0x42}),
      ('right','d',2,1,{0xC,0xE,0x1C,0x25,0x29}),
      ('crouch_or_response','1',2,1,{0x20,0x23,0x26,0x28}),
      ('approach','space',.3,2,{0x12,0x1A,0x27}),
      ('charged_attack','3',3,8,{3,6,8,0xA,0xF,0x16,0x1D,0x21,0x22}),
      ('aura_charge','c',20,1,{0x11,0x19}),
      ('lower_super','Down',.3,15,set(range(0x2D,0x31))),
      ('aura_recharge','c',20,1,{0x11,0x19}),
      ('upper_super','Up',.3,20,set(range(0x31,0x42))),
      ('ranged_or_close_x','j',.3,3,{0,5,7,0x13,0x17})]
output=b.endpoint.parent/'action-coordinate-audit.json'
if output.exists():raise RuntimeError('Capture exists')
results=[];request({'command':'resume'})
# Finish the native opening animation through elapsed frames, without changes
# to timers or animation state. This is only a delay before input testing.
initial=b.word(0x8266E184);deadline=time.monotonic()+30
while b.word(0x8266E184)-initial<150 and time.monotonic()<deadline:time.sleep(.1)
try:
    for name,button,hold,after,expected in plan:
        frames=[];full=[];accepted=False;all_finite=True;all_bases=True
        start=time.monotonic();first_frame=b.word(0x8266E184)
        key('down',button);released=False;last_signature=None
        try:
            while time.monotonic()-start<hold+after:
                if not released and time.monotonic()-start>=hold:key('up',button);released=True
                audit=snapshot();act=activity();state=audit['state']
                fresh=act['accepted_frame']>first_frame and act['last_accepted'] in expected
                accepted=accepted or fresh;all_finite=all_finite and audit['all_finite']
                all_bases=all_bases and audit['bases_nondegenerate']
                signature=(state['mode'],state['players'][0]['state'],act['last_accepted'])
                if signature!=last_signature and len(full)<32:
                    full.append(audit);last_signature=signature
                frames.append({'seconds':round(time.monotonic()-start,3),
                               'mode':state['mode'],'actor_state':state['players'][0]['state'],
                               'native_last_action':state['players'][0]['last_action'],
                               'input':act,'finite':audit['all_finite'],
                               'invalid_regions':audit['invalid_regions'],
                               'bases_nondegenerate':audit['bases_nondegenerate']})
                time.sleep(.06)
        finally:key('up',button)
        item={'group':name,'key':button,'native_input_observed':accepted,
              'all_finite':all_finite,'bases_nondegenerate':all_bases,
              'samples':frames,'coordinate_snapshots':full}
        results.append(item)
        print(json.dumps({'group':name,'native_input_observed':accepted,
                          'all_finite':all_finite,'samples':len(frames)}),flush=True)
finally:
    request({'command':'pause'})
    report={'scope':'Null GPU, virtual pad; no visual gameplay claim',
            'groups':results,'coverage':activity(),
            'all_finite':all(x['all_finite'] for x in results),
            'bases_nondegenerate':all(x['bases_nondegenerate'] for x in results)}
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
