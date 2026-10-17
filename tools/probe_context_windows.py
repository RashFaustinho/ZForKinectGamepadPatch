"""LOCAL: reach real contextual windows using ordinary charge/approach inputs.

No guest writes or phase forcing. The native window objects decide when the
requested LB/RB/LT/RT response is sent; accepted queries are recorded separately.
"""
import argparse,ctypes,ctypes.util,fcntl,json,struct,time
import battle_state as b
from coordinate_audit import request
from debug_session import runner
p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');p.add_argument('name')
p.add_argument('--seconds',type=float,default=120)
p.add_argument('--attack-choice',type=int,choices=range(4),default=0)
p.add_argument('--defend-choice',type=int,choices=range(2),default=0)
p.add_argument('--stop-on',choices=('attack','defend','either','none'),default='either')
p.add_argument('--capture',action='store_true')
p.add_argument('--capture-delay-frames',type=int,default=0,help='Let a real prompt settle before answering and capturing it')
p.add_argument('--capture-charge',action='store_true',help='Hold RT for eight extra native frames at full charge and capture before punching X')
p.add_argument('--stop-at-ranged',action='store_true',help='Pause at the first native ranged idle state before sending another approach')
p.add_argument('--initiate',choices=('approach','charged'),default='approach')
a=p.parse_args();b.connect(a.session)
if not a.name.replace('-','').isalnum():p.error('Invalid name')
lock=open(b.input_lock_path(),'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
out=b.endpoint.parent/(a.name+'.json')
if out.exists():raise RuntimeError('Capture exists')
x=runner.x11();d=x.XOpenDisplay(b.display_name().encode())
x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong
x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_ubyte
x.XFlush.argtypes=[ctypes.c_void_p]
t=ctypes.CDLL(ctypes.util.find_library('Xtst'));t.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
def key(n,down):t.XTestFakeKeyEvent(d,x.XKeysymToKeycode(d,x.XStringToKeysym(n.encode())),int(down),0);x.XFlush(d)
def phase(ptr,n):
 raw=b.read(ptr,n)
 return {'state':int.from_bytes(raw[4:8],'big'),'flags':raw[0x18],'raw':raw.hex()}
start=time.monotonic();first=b.word(0x8266E184);held=None;press_frame=first-200;last_approach=first-200
rows=[];screens=[];hits=[];last_capture=None;seen=set();stop_frame=None;charge_punch=False
prompt_start=None;prompt_signature=None
charge_ready_frame=None;charge_captured=False
request({'command':'resume'})
try:
 while time.monotonic()-start<a.seconds:
  s=b.sample();ctx=int(s['context'],16);frame=s['bridge']['frame']
  if s['battle_kind']!=0:raise RuntimeError('Normal battle required')
  if a.stop_at_ranged and s['mode']==6 and s['players'][0]['state']==20 and not s['players'][0].get('input_suppressed',0):break
  attack=phase(ctx+0x307C,0x7C);defend=phase(ctx+0x30F8,0x3C)
  params=b.word(ctx+0x28);native_prompt=b.word(params+0xD8) if params else 0
  native_prompt_flags=b.read(params+0xE8,1)[0] if params else 0
  actor=int(s['players'][0]['actor'],16)
  native_strike_choice=b.word(actor+0x26D4)
  native_counter_choice=b.word(ctx+0x3008)
  owner=b.word(0x82649298);ui=b.word(owner+0x64) if owner else 0
  defense_widget=b.word(ui+0x3C) if ui else 0
  defense_response={'choice':b.word(defense_widget+0x50),'latched':b.word(defense_widget+0x54)} if defense_widget else None
  combo=phase(ctx+0x3134,0x64)
  combo_attacker=int(combo['raw'][0x38*2:0x3C*2],16)
  combo_choice=int(combo['raw'][0x54*2:0x58*2],16)
  combo_active=combo['state']==1 and combo['flags']&1
  attack_window=(attack['state'] in (1,4) and attack['flags']&1 and int(attack['raw'][0x60*2:0x64*2],16)==0 and int(attack['raw'][0x68*2:0x6C*2],16)==0)
  attack_window=attack_window or (s['mode']==5 and native_prompt>27 and native_prompt_flags&1 and b.word(actor+0x26C0)==0)
  defend_window=defend['state']==1 and defend['flags']&1
  action=None;desired=None
  if attack_window:desired=('q','e','1','3')[a.attack_choice];action=0x1E+a.attack_choice
  elif defend_window:desired=('1','e')[a.defend_choice];action=(0x23,0x24)[a.defend_choice]
  elif combo_active and combo_attacker==0:desired='3'
  elif combo_active and combo_attacker==1 and combo_choice<3:desired=('1','a','d')[combo_choice]
  elif frame-first<4:desired='j'
  elif s['mode'] in (4,6) and not s['players'][0].get('input_suppressed',0):
   if a.initiate=='charged':desired='3'
   elif s['players'][0]['energy']<25:desired='c'
   elif (held=='space' and frame-last_approach<3) or frame-last_approach>100:
    desired='space'
    if held!='space':last_approach=frame
  signature=('attack' if attack_window else 'defend' if defend_window else None,action)
  if signature!=prompt_signature:prompt_signature=signature;prompt_start=frame
  if not signature[0]:last_capture=None
  if a.capture and signature[0] and frame-prompt_start<a.capture_delay_frames:desired=None
  if desired=='space' and frame-last_approach>=3:desired=None
  if desired in ('q','e','1','3') and action is not None:
   if frame-press_frame>=6:press_frame=frame
   if frame-press_frame>=3:desired=None
  if desired!=held:
   if held:key(held,False)
   if desired:key(desired,True)
   held=desired
  # The native charged punch is a punch performed while the arm is drawn
  # back. Releasing the charge alone returns to neutral. Use real RT+X here.
  ready=(s['players'][0].get('state')==13 and s['players'][0].get('last_action_progress',0)>=.99)
  if ready and charge_ready_frame is None:charge_ready_frame=frame
  if not ready:charge_ready_frame=None
  if a.capture_charge and ready and not charge_captured and frame-charge_ready_frame>=8:
   request({'command':'pause'});screens.append(request({'command':'screenshot','name':a.name+'-charged-ready-'+str(frame)}));request({'command':'resume'});charge_captured=True
  punch_now=(a.initiate=='charged' and desired=='3' and action is None
             and ready and (not a.capture_charge or frame-charge_ready_frame>=8)
             and (frame-first)%12<3)
  if punch_now!=charge_punch:
   key('j',punch_now);charge_punch=punch_now
  accepted,accepted_frame,query,qframe,caller,context_query=struct.unpack('>6I',b.read(0x8266E1E8,24))
  timestamps=struct.unpack('>67I',b.read(0x8266E2E0,67*4))
  for accepted_action in (*range(0x1E,0x22),0x23,0x24):
   stamp=timestamps[accepted_action];target='attack' if accepted_action<0x22 else 'defend'
   native_choice_call=(accepted==accepted_action and accepted_frame==stamp and caller in (0x8229CF5C,0x8229CFE0,0x8229D03C,0x8229D098))
   if target=='attack' and (accepted_action-0x1D not in (native_strike_choice,native_counter_choice) or (s['players'][0].get('last_action')!=accepted_action and not native_choice_call)):continue
   if target=='defend' and (not defense_response or not defense_response['latched'] or defense_response['choice']!=accepted_action-0x23):continue
   if stamp>first and (accepted_action,stamp) not in seen:
    hits.append({'kind':target,'action':hex(accepted_action),'frame':stamp,
                 'caller':hex(caller) if accepted_action==accepted and stamp==accepted_frame else None,
                 'native_strike_choice':native_strike_choice,'native_counter_choice':native_counter_choice,'defense_response':defense_response})
    seen.add((accepted_action,stamp))
    if a.stop_on in (target,'either') and stop_frame is None:stop_frame=frame
  if a.capture and signature[0] and signature!=last_capture and frame-prompt_start>=a.capture_delay_frames:
   request({'command':'pause'});screens.append(request({'command':'screenshot','name':a.name+'-'+signature[0]+'-'+str(frame)}));request({'command':'resume'});last_capture=signature
  rows.append({'seconds':round(time.monotonic()-start,3),'state':s,'attack_phase':attack,'defend_phase':defend,'combo_phase':combo,
               'key':held,'charge_punch':charge_punch,'native_prompt':native_prompt,'native_prompt_flags':native_prompt_flags,
               'native_strike_choice':native_strike_choice,'native_counter_choice':native_counter_choice,'defense_response':defense_response,
               'accepted':hex(accepted),'accepted_frame':accepted_frame,'caller':hex(caller),'context_query':hex(context_query)})
  if len(rows)%300==0:print(json.dumps({'seconds':rows[-1]['seconds'],'frame':frame,'mode':s['mode'],'ki':s['players'][0]['energy'],'key':held,'attack_window':bool(attack_window),'defend_window':bool(defend_window),'hits':len(hits)}),flush=True)
  if stop_frame is not None and frame-stop_frame>=3:break
  if min(v['hp'] for v in s['players'])<=1 and s['mode']==0:break
  time.sleep(.02)
finally:
 if held:key(held,False)
 if charge_punch:key('j',False)
 x.XCloseDisplay(d);request({'command':'pause'})
 out.write_text(json.dumps({'scope':__doc__.strip(),'hits':hits,'samples':rows,'screenshots':screens},indent=2)+'\n')
print(out)
