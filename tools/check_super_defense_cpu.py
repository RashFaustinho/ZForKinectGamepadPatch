"""Execute native Super-defense selectors and consumers with revision 18.

Texture/part resolution and 64-bit register spill helpers are ABI fixtures.
The original selector, named-group traversal and defense query code execute
on the PowerPC CPU; this does not stand in for a rendered gameplay test.
"""
import argparse,hashlib,json,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_PC,UC_PPC_REG_LR
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v18/4E4D084E.gamepad-feedback.patch.toml');source=ap.parse_args().patch
m=json.loads((source.parent/'manifest.json').read_text());p=tomllib.loads(source.read_text())['patch'][0]
assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
c=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);c.mem_map(0x82000000,0x700000);c.mem_map(0x100000,0x200000)
c.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for x in p['array']:c.mem_write(x['address'],bytes.fromhex(x['value']))
for x in p['be32']:c.mem_write(x['address'],struct.pack('>I',x['value']))
def put(a,v):c.mem_write(a,struct.pack('>I',v&0xffffffff))
def get(a):return int.from_bytes(c.mem_read(a,4),'big')
def reg(n,v):c.reg_write(UC_PPC_REG_0+n,v)
def g(n):return c.reg_read(UC_PPC_REG_0+n)
def ret():c.reg_write(UC_PPC_REG_PC,c.reg_read(UC_PPC_REG_LR))
names=['i_pl_seal_anm_grp','a_pl_attack_anm_grp','i_pl_attack','a_pl_guard_anm_grp','i_pl_guard','i_ico_dummy_grp']
lookup={};calls=[];writes=[];case='normal'
def fixture(uc,a,n,user):
 # Xenon uses 64-bit std/ld for its ABI, outside Unicorn PPC32. Preserve
 # their low GPR words and the native saved LR at their actual stack slots.
 if 0x8251D780<=a<=0x8251D7C4 and (a-0x8251D780)%4==0:
  first=14+(a-0x8251D780)//4
  for r in range(first,32):put(g(1)-0x98+(r-14)*8+4,g(r))
  put(g(1)-8,g(12));ret();return
 if 0x8251D7D0<=a<=0x8251D814 and (a-0x8251D7D0)%4==0:
  first=14+(a-0x8251D7D0)//4
  for r in range(first,32):reg(r,get(g(1)-0x98+(r-14)*8+4))
  reg(12,get(g(1)-8));uc.reg_write(UC_PPC_REG_LR,g(12));ret();return
 if a==0x82115458:
  name=bytes(uc.mem_read(g(4),80)).split(b'\0')[0].decode();reg(3,lookup.get(name,0));ret()
 if a==0x823498A8:
  loader,index,kind=g(3),g(4),g(5);calls.append([loader,index,kind])
  reg(3,0 if case=='missing_texture' and loader==0x180000 else (0x190000+index*0x100 if loader==0x180000 else 0x195000));ret()
c.hook_add(UC_HOOK_CODE,fixture);c.hook_add(UC_HOOK_MEM_WRITE,lambda uc,a,addr,n,v,_:writes.append((addr,n)))
def setup(kind,subtype,variant=0,scenario='normal'):
 global case
 case=scenario;c.mem_write(0x100000,bytes(0x200000));calls.clear();writes.clear();lookup.clear()
 lookup.update({'p_ico_dummy_000':0x121000,'i_pl_grp':0x120000})
 if case=='missing_dummy':lookup['p_ico_dummy_000']=0
 if case=='missing_root':lookup['i_pl_grp']=0
 put(0x110034,kind);put(0x110038,subtype);put(0x11003C,subtype);put(0x11004C,variant);put(0x110040,0x111000);put(0x111004,0x112000)
 put(0x1200B8,0x122000);put(0x122008,0x123000);c.mem_write(0x12200C,struct.pack('>H',len(names)))
 put(0x121020,5);put(0x121024,0x195000)
 for i,name in enumerate(names):
  obj=0x124000+i*0x100;s=0x130000+i*0x80;c.mem_write(s,name.encode()+b'\0');put(obj+0xD4,s);put(obj+0xD0,1)
  for off,v in ((0,77+i),(4,obj),(8,0xAA000000+i)):put(0x123000+i*12+off,v)
 put(0x8264910C,0x160000);put(0x160314,4)
 for off in (0x290,0x2B4,0x2CC,0x2D8,0x2E4,0x2F0,0x2FC,0x308):put(0x160000+off,0x170000);put(0x170088,1)
 put(0x82649134,0 if case=='missing_pad' else 0x180000);put(0x1800D8,33 if case=='wrong_count' else 34);put(0x1800DC,0 if case=='missing_table' else 0x181000)
 for i in range(34):put(0x181000+i*4,0x190000+i*0x100)
 reg(1,0x2EF000);reg(3,0x110000)
 for r in range(14,32):reg(r,0x55550000+r)
def run(a,end=0x2F0000):
 c.reg_write(UC_PPC_REG_LR,end);c.emu_start(a,end,count=10000);assert c.reg_read(UC_PPC_REG_PC)==end
variants=[('guard',2,0,0,2),*[(f'evade_{t}',1,t,0,15) for t in range(1,5)],
 *[(f'counter_1_{v}',0,1,v,17 if v==0 else 16) for v in range(3)],
 *[(f'counter_{t}',0,t,0,16) for t in range(2,5)]]
ui=[]
for label,kind,subtype,variant,texture in variants:
 setup(kind,subtype,variant);run(0x822EF2B0)
 assert calls[-1]==[0x180000,texture,0x54583244],(label,calls)
 assert get(0x121024)==0x190000+texture*0x100 and get(0x121020)==1
 assert all(g(r)==0x55550000+r for r in range(14,32)),label
 assert g(1)==0x2EF000 and c.reg_read(UC_PPC_REG_LR)==0x2F0000
 for i,name in enumerate(names):assert get(0x1240D0+i*0x100)==(0 if name in names[1:5] else 1),(label,name)
 order=[get(0x123000+i*12+4) for i in range(len(names))];assert order.index(0x124000)>order.index(0x124500)
 # The original setup turns the pose groups on again. Its emitted wrapper
 # must hide them after that native code, keeping the prohibition seal last.
 reg(3,0x110000);run(0x822EF728)
 for i,name in enumerate(names):assert get(0x1240D0+i*0x100)==(0 if name in names[1:5] else 1)
 allowed=set(range(0x2EEE00,0x2EF000))|set(range(0x121020,0x121028))|set(range(0x123000,0x123000+12*len(names)))
 for i in range(len(names)):allowed.update(range(0x1240D0+i*0x100,0x1240D4+i*0x100))
 assert all(all(addr+k in allowed for k in range(n)) for addr,n in writes),(label,'unbounded UI write')
 ui.append({'case':label,'texture':texture,'native_visibility_setup_checked':True})
fallback=[]
for scenario in ('missing_pad','wrong_count','missing_table','missing_texture','missing_dummy','missing_root'):
 setup(0,1,0,scenario);run(0x822EF2B0)
 assert get(0x121024)==(0x191100 if scenario=='missing_root' else 0x195000),(scenario,hex(get(0x121024)))
 assert all(get(0x1240D0+i*0x100)==1 for i in range(len(names)))
 fallback.append(scenario)
for kind,t,v in ((3,0,0),(0,0,0),(0,5,0),(0,1,3),(1,0,0),(1,5,0)):
 setup(kind,t,v);run(0x822EF2B0);assert not any(x[0]==0x180000 for x in calls)

# Execute every ORIGINAL counter consumer branch against the actual patched
# gesture-query code. Distinct lower/upper follow-up windows must agree with
# the icon selected by the widget; a window for the other stick is rejected.
put(0x826491D8,0x150000);put(0x826490DC,0x105000);put(0x105098,0x106000);put(0x826492D8,10)
consumer=[]
for label,kind,t,v,texture in variants:
 if kind==2:continue
 put(0x110370,1);put(0x110D10,0);put(0x110D10+4,0);put(0x110D14, v);put(0x110384,0x140000);put(0x140014,0x100)
 # D10 doubles as the second record's owner ID; defender field D10 is 0.
 put(0x110D10,0);put(0x110D14,v);put(0x111CF4,t)
 if kind==1:
  for held,expected in ((0x4000,1),(0,0),(0x8000,0)):
   put(0x106020,held);put(0x106028,0);reg(1,0x2EF000);reg(3,0x110000);run(0x82253A80);assert g(3)==expected,(label,held,g(3))
 else:
  mask=0x20000 if texture==17 else 0x10000
  for window,expected in ((mask,1),(0,0),(mask^0x30000,0)):
   put(0x8266E1AC,window);reg(1,0x2EF000);reg(3,0x110000);run(0x82253B68);assert g(3)==expected,(label,hex(window),g(3))
 consumer.append(label)
# Exact original Super guard call block, now querying the B recognizer.
for site in m['super_defense'].get('guard_queries',[m['super_defense']['guard_query']]):
 site=int(site,16)
 for held,expected in ((0x20,3),(0x8000,0),(0,0)):
  put(0x106020,held);put(0x106028,0);reg(1,0x2EF000)
  c.emu_start(site-4,site+12,count=300);assert g(3)==expected,(hex(site),held,g(3))
report={'scope':__doc__,'patch_sha256':m['patch_sha256'],'passed':True,'selector_variants':ui,'fallback_cases':fallback,'invalid_selectors':6,'native_consumer_variants':consumer,'super_guard':'B accepted; LS-right and neutral rejected','player_super_art':'Original special action map and dedicated player Super pose loader unchanged'}
(source.parent/'super-defense-cpu.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
