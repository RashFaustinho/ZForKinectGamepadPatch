"""Reach Super-defense windows using ordinary pad events and read-only data.

The optional tutorial driver charges Ki and requests the Super direction
actually allowed by the current lesson. It never changes phases, energy,
health, outcomes or animation state. Each session has an exclusive pad lock.
"""
import argparse,fcntl,json,time
import battle_state as b
from coordinate_audit import request
from virtual_pad import VirtualPad
p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');p.add_argument('name')
p.add_argument('--tutorial',action='store_true');p.add_argument('--action',choices=('observe','guard','evade','counter'),default='observe')
p.add_argument('--seconds',type=float,default=900);p.add_argument('--frames',type=int,default=4000)
p.add_argument('--capture',action='store_true');p.add_argument('--settle',type=int,default=3)
a=p.parse_args();b.connect(a.session);lock=open(b.input_lock_path(),'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
out=b.endpoint.parent/(a.name+'.json');assert not out.exists()
pad=VirtualPad(b.display_name());held=None
def key(k):
 global held
 if k==held:return
 if held:pad.key(held,False)
 if k:pad.key(k,True)
 held=k
def sample():
 s=b.sample();q=int(s['context'],16)+0x1150
 s['super']={k:b.word(q+o) for k,o in [('attacker',0x370),('defender',0xD10),('phase',0x1CBC),('scripted_phase',0x1D04),('counter_type',0x1CF4),('result',0x16D4)]}
 u=b.word(b.word(0x82649298)+0x64);s['panels']=[]
 for off in (0x5C,0x60,0x64):
  obj=b.word(u+off)
  if obj:s['panels'].append({'slot':hex(off),'object':hex(obj),'state':b.word(obj+0x28),'kind':b.word(obj+0x34),'evade_type':b.word(obj+0x38),'counter_type':b.word(obj+0x3C),'variant':b.word(obj+0x4C),'visibility_state':b.word(obj+0x50),'active':b.word(obj+0x58),'ui':hex(b.word(obj+0x40))})
 if a.tutorial:
  tptr=b.word(0x8264933C);s['lesson']=b.word(tptr+0x2C);s['allowed']=list(b.read(tptr+0xB0,21))
 return s
rows=[];last=None;window=None;success=False;start=time.monotonic();initial=b.word(0x8266E184);last_launch=-1000;screens=[]
request({'command':'resume'})
try:
 while time.monotonic()-start<a.seconds:
  s=sample();f=s['bridge']['frame'];q=s['super'];state=(s['mode'],s.get('lesson'),q['attacker'],q['phase'],q['result'],int(s['players'][0]['energy']))
  if state!=last:rows.append(s);last=state;print(json.dumps({'frame':f,'mode':s['mode'],'lesson':s.get('lesson'),'super':q,'energy':s['players'][0]['energy']}),flush=True)
  active_panels=[p for p in s['panels'] if p['active'] and p['visibility_state'] in (1,2)]
  desired=None;defense=s['mode']==10 and q['attacker']==1 and q['defender']==0 and (q['phase']==13 or active_panels)
  if window is not None and a.action!='observe' and q['result']=={'guard':7,'evade':6,'counter':5}[a.action] and (q['phase']==14 or q['scripted_phase'] in (2,4)):
   success=True;break
  if a.tutorial and s.get('lesson') in (118,131):
   desired='j' if f%12<3 else 'k' if 6<=f%12<9 else None
  elif defense:
   if window is None:window=f
   if a.action=='observe' and f-window>=a.settle:
    request({'command':'pause'})
    if a.capture:screens.append(request({'command':'screenshot','name':a.name+'-window'}))
    break
   if a.action=='guard':desired='b'
   elif a.action=='evade':desired='a'
   elif a.action=='counter':
    panel=s['panels'][0];desired='Down' if panel['counter_type']==1 and panel['variant']==0 else 'Up'
  elif window is not None and q['phase']==14:
   success=q['result'] in (5,6,7);break
  elif a.tutorial and s['mode']==10 and q['attacker']==0 and int(s['bridge']['release_flags'],16)==0 and f-last_launch>90:
   desired='Up';last_launch=f
  elif a.tutorial and s['mode'] in (4,6):
   allowed=s['allowed'];energy=s['players'][0]['energy']
   if energy<100:desired='c'
   elif f-last_launch>90:
    if 0x31 in allowed:desired='Up'
    elif 0x2D in allowed:desired='Down'
    if desired:last_launch=f
  key(desired)
  if f-initial>=a.frames:break
  time.sleep(.12)
finally:
 key(None);pad.close();request({'command':'pause'});final=sample()
 out.write_text(json.dumps({'scope':__doc__,'action':a.action,'window_frame':window,'success':success,'samples':rows,'screenshots':screens,'final':final},indent=2)+'\n')
print(out)
