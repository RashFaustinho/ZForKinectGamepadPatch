"""Navigate an owned diagnostic session through Score Attack or tutorial menus.

Only gamepad events are sent. The optional selector logger supplies read-only
menu state; no game selection, battle outcome or animation is forced in RAM.
"""
import argparse
import fcntl
import json
import socket
import time
import battle_state as b

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('session');p.add_argument('--timeout',type=float,default=60)
p.add_argument('--key-hold',type=float,default=.25)
p.add_argument('--start-step',type=int,default=0)
p.add_argument('--main-menu-only',action='store_true',help='Pause at the native root menu instead of entering a battle')
p.add_argument('--story-boss',action='store_true',help='Enter the fifth Saiyan story stage for a coordinate audit')
p.add_argument('--skip-intro',action='store_true',help='Try the normal Start/A skip controls during the battle introduction')
p.add_argument('--tutorial',type=int,choices=range(6),help='Enter one of the six native tutorials')
p.add_argument('--saga',type=int,choices=range(4),default=0)
p.add_argument('--stage',type=int,choices=range(6),default=0)
p.add_argument('--character-group',type=int,choices=range(56),default=1,
               help='Native roster group, across pages of seven characters')
p.add_argument('--variant',type=int,choices=range(7),default=0)
args=p.parse_args();b.connect(args.session)
# The control socket precedes executable mapping by a few seconds.
load_deadline=time.monotonic()+args.timeout
while True:
    try:b.word(0x8266E184);break
    except RuntimeError as exc:
        if 'Guest image is not loaded' not in str(exc) or time.monotonic()>=load_deadline:raise
        time.sleep(.2)
input_lock=open(b.input_lock_path(),'a')
fcntl.flock(input_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def req(payload):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(10);s.connect(str(b.endpoint));s.sendall(json.dumps(payload).encode()+b'\n')
        raw=b''
        while not raw.endswith(b'\n'):raw+=s.recv(65536)
    out=json.loads(raw)
    if not out['ok']:raise RuntimeError(out)
    return out
def state():
    ptr=b.word(0x8266E1B8)
    if not ptr:return None
    raw=b.read(ptr,0x44)
    values=[int.from_bytes(raw[o:o+4],'big') for o in (0,4,0x2C,0x34)]
    return dict(ptr=ptr,caller=b.word(0x8266E1BC),kind=values[0],count=values[1],state=values[2],index=values[3])
def key(name):
    req({'command':'key','key':name,'duration':args.key_hold})
    release_deadline=time.monotonic()+15
    while b.word(0x8266E18C) and time.monotonic()<release_deadline:
        time.sleep(.05)
    time.sleep(.15)
def wait(predicate):
    end=time.monotonic()+args.timeout
    while time.monotonic()<end:
        s=state()
        if s and predicate(s):print(json.dumps(s),flush=True);return s
        time.sleep(.1)
    raise RuntimeError(f'Menu timeout: {state()}')
def select(index,expected):
    if expected==6:
        deadline=time.monotonic()+args.timeout
        while time.monotonic()<deadline:
            current=state()
            if current and current['kind']==2 and current['state']==1:
                if current['count']==6:break
                if (index==0 and current['count']==5) or (index==1 and current['count']==4):
                    print(json.dumps(current),flush=True);return current
                if index in (1,2,3) and current['count']==5:
                    # Wait for the child to finish initialization before B;
                    # never repeat B through its fade back to the root menu.
                    frame=b.word(0x8266E184)
                    while b.word(0x8266E184)-frame<3 and time.monotonic()<deadline:time.sleep(.1)
                    key('b');wait(lambda v:v['count']==6 and v['state']==1);break
            time.sleep(.1)
    s=wait(lambda s:s['count']==expected and s['state']==1 and s['kind']<3)
    for _ in range(expected):
        if s['index']==index:break
        key('s');s=wait(lambda v:v['ptr']==s['ptr'] and v['index']!=s['index'])
    if s['index']!=index:raise RuntimeError('Cannot select requested item')
    key('space')
    if expected==2:
        # This message widget stays in the logger after its fade completes;
        # the next scene need not use the selector API at all.
        return state()
    return wait(lambda v:(v['ptr']!=s['ptr'] or v['caller']!=s['caller'])
                and v['kind']<3 and (v['state']==1 or v['count']==0))

if args.start_step == 0:
    deadline=time.monotonic()+args.timeout
    while time.monotonic()<deadline:
        s=state()
        if s and s['count']==6 and s['kind']<3:break
        if s and s['count']==5 and s['kind']==2:
            if args.story_boss:
                args.start_step=1;break
            break  # select() recovers the root after the child initializes.
        key('space')
        s=state()
        if s and s['count']==6 and s['kind']<3:break
        key('j');time.sleep(.5)
    else:raise RuntimeError('Main menu unavailable')
if args.main_menu_only:
    wait(lambda s:s['count']==6 and s['kind']==2 and s['state']==1)
    req({'command':'pause'});raise SystemExit(0)
sequence=([(0,6),(4,5),(args.tutorial,6)] if args.tutorial is not None else
          [(0,6),(0,5),(4,5)] if args.story_boss else [(1,6),(args.saga,4),(args.stage,4 if args.saga==0 else 6),(2,3)])
for index,count in sequence[args.start_step:]:
    select(index,count)
if args.tutorial is None and not args.story_boss:
    for _ in range(args.character_group//7):
        s=wait(lambda s:s['count']==9 and s['state']==1 and s['kind']==2)
        while s['index']!=8:
            key('s');s=wait(lambda v:v['ptr']==s['ptr'] and v['index']!=s['index'])
        key('space')
        # Page changes reuse the selector. Wait for the native page update,
        # rather than requiring a new pointer as select() does for scenes.
        frame=b.word(0x8266E184)
        deadline=time.monotonic()+args.timeout
        while b.word(0x8266E184)-frame<15:
            if time.monotonic()>=deadline:raise RuntimeError('Character page did not advance')
            time.sleep(.05)
    select(args.character_group%7+1,9)
    current=state()
    if current and current['count']==7:
        select(args.variant,7)
    elif args.variant:
        raise RuntimeError('This character has no variant selector')
if args.tutorial is not None:
    current=state()
    if current and current['count']==2:select(0,2)
elif args.story_boss:
    current=state()
    if current and current['count']==3:select(2,3)
else:key('space') # offline leaderboard notice
if args.tutorial is None:
    wait(lambda s:s['count']==0 and s['kind']<3)
key('j')
end=time.monotonic()+args.timeout
skip_sent=False
while time.monotonic()<end:
    try:
        s=b.sample()
        if args.skip_intro and not skip_sent and s['mode']==0 and s['players'][0].get('state') in (70,71):
            key('Return');key('space');skip_sent=True
        if ((args.story_boss and s['battle_kind']==1 and s['players'][0].get('state') is not None)
            or (not args.story_boss and s['mode'] in (4,6) and s['players'][0].get('state') in (0,1,20))):
            req({'command':'pause'});print(json.dumps(s),flush=True);break
    except SystemExit:pass
    time.sleep(.2)
else:raise RuntimeError('Battle did not become interactive')
