"""Send frame-counted pad events in menus without requiring a battle actor."""
import argparse,fcntl,json,time
import battle_state as b
from coordinate_audit import request
from virtual_pad import VirtualPad
p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');p.add_argument('name');p.add_argument('keys',nargs='+')
p.add_argument('--hold',type=int,default=3);p.add_argument('--gap',type=int,default=6);p.add_argument('--after',type=int,default=60);p.add_argument('--seconds',type=float,default=600);p.add_argument('--capture',action='store_true')
a=p.parse_args()
if not a.name.replace('-','').isalnum() or min(a.hold,a.gap,a.after)<0 or a.seconds<=0:p.error('Invalid report name or limits')
b.connect(a.session);out=b.endpoint.parent/(a.name+'.json')
if out.exists():p.error('Report already exists')
lock=open(b.input_lock_path(),'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
pad=VirtualPad(b.display_name())
held=None;start=time.monotonic();rows=[];shot=None
def key(s,down):pad.key(s,down)
def wait(n):
 f=b.word(0x8266E184)
 while b.word(0x8266E184)-f<n:
  if time.monotonic()-start>a.seconds:raise RuntimeError('Menu pad probe timed out')
  time.sleep(.08)
def sample():
 s={'frame':b.word(0x8266E184)};obj=b.word(0x8266E1B8)
 if obj:s['selector']={'object':hex(obj),'kind':b.word(obj),'count':b.word(obj+4),'state':b.word(obj+0x2C),'index':b.word(obj+0x34)}
 mgr=b.word(0x8264920C)
 if mgr:
  save=b.word(mgr)
  if save:s.update(powerup_flags=b.word(save+0x2EEC),powerup=b.word(save+0x2F00),card_index=b.word(0x8266E1C4))
 return s
request({'command':'resume'})
try:
 for s in a.keys:
  rows.append({'before':sample(),'key':s});key(s,True);held=s;wait(a.hold);key(s,False);held=None;wait(a.gap);rows[-1]['after']=sample()
 wait(a.after);request({'command':'pause'})
 if a.capture:shot=request({'command':'screenshot','name':a.name})
finally:
 if held:key(held,False)
 pad.close();request({'command':'pause'});out.write_text(json.dumps({'keys':a.keys,'samples':rows,'final':sample(),'screenshot':shot},indent=2)+'\n')
print(out)
