"""Read-only screenshots of selector menus while a separate pad driver navigates."""
import argparse,json,time
import battle_state as b
from coordinate_audit import request
p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');p.add_argument('--seconds',type=float,default=240);a=p.parse_args();b.connect(a.session)
start=time.monotonic();seen=set();pending={};rows=[]
while time.monotonic()-start<a.seconds:
 ptr=b.word(0x8266E1B8)
 if ptr:
  count=b.word(ptr+4);state=b.word(ptr+0x2C);index=b.word(ptr+0x34);frame=b.word(0x8266E184)
  if count in (3,5,7,9) and state==1 and count not in seen:
   pending.setdefault(count,time.monotonic())
   if time.monotonic()-pending[count]>=1.2:
    result=request({'command':'screenshot','name':'menu-'+str(count)+'-buttons'})
    rows.append({'count':count,'index':index,'frame':frame,'screenshot':result});seen.add(count);print(json.dumps(rows[-1]),flush=True)
 if len(seen)==4:break
 time.sleep(.25)
out=b.endpoint.parent/'menu-button-captures.json'
with out.open('x') as f:json.dump(rows,f,indent=2);f.write('\n')
print(out)
