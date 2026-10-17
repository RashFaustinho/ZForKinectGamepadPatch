"""Exercise contextual inputs and bounded UI changes; no gameplay claim."""
import argparse,hashlib,json,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_PC,UC_PPC_REG_LR,UC_PPC_REG_MSR
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v15/4E4D084E.gamepad-feedback.patch.toml');source=ap.parse_args().patch
manifest=json.loads((source.parent/'manifest.json').read_text())
p=tomllib.loads(source.read_text())['patch'][0]
c=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);c.mem_map(0x82000000,0x700000);c.mem_map(0x100000,0x100000)
c.reg_write(UC_PPC_REG_MSR,0x2000)
c.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for x in p['array']:c.mem_write(x['address'],bytes.fromhex(x['value']))
for x in p['be32']:c.mem_write(x['address'],struct.pack('>I',x['value']))
def put(a,v):c.mem_write(a,struct.pack('>I',v))
def get(a):return int.from_bytes(c.mem_read(a,4),'big')
def reg(n,v):c.reg_write(UC_PPC_REG_0+n,v)
def run(a,end=0x1F0000):
 c.reg_write(UC_PPC_REG_LR,end);c.emu_start(a,end,count=100000)
 assert c.reg_read(UC_PPC_REG_PC)==end
put(0x826490DC,0x105000);put(0x105098,0x106000);rows=[]
for mode in (0,4,5,6,7,8,9,10):
 put(0x826492D8,mode)
 for action in (0,2,3,5,6,7,8,10,11,0x23,0x24,0x2a):
  for button,mask in [('B',0x20),('X',0x80),('Y',0x10),('RT',0x800)]:
   put(0x106020,mask);put(0x106028,mask);reg(4,action);reg(5,3);run(0x82197118);v=c.reg_read(UC_PPC_REG_0+3)
   if mode==6 and action in (3,6,7,8,10):assert v==(3 if button=='Y' else 0),(mode,action,button,v)
   if mode==6 and action==2:assert v==0
   if mode in (4,6) and action==0x2a:assert v==0
   if mode==4 and action==3:assert v==(0 if 'step_guard' in manifest else (3 if button=='RT' else 0))
   if mode==4 and action in (5,6,7,8,10):
    expected='Y' if 'animated_combat' in manifest and action in (5,6) else 'RT'
    assert v==(3 if button==expected else 0)
   if mode in (5,8) and action==0x2a:assert v==(3 if button=='B' else 0)
   if action==11:assert v==(3 if button=='B' else 0)
   rows.append({'mode':mode,'action':action,'button':button,'result':v})
# Execute the actual new scene pass. Part lookup is fixture-bound; the native
# named-child lookup executes original PowerPC over the real child-list layout.
writes=[];textures=[];lookup={};render_visits=[];c.hook_add(UC_HOOK_MEM_WRITE,lambda u,a,addr,n,v,_:writes.append((addr,n)))
def fixture(uc,a,n,user):
 if a==0x8251D7A8:uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
 if a==0x8251D7F8:uc.reg_write(UC_PPC_REG_PC,0x1F0000)
 if a==0x1D0000:
  render_visits.append(uc.reg_read(UC_PPC_REG_0+3));uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
 if a==0x82115458:
  address=uc.reg_read(UC_PPC_REG_0+4);name=bytes(uc.mem_read(address,80)).split(b'\0')[0].decode()
  reg(3,lookup.get(name,0));uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
 if a==0x823498A8:
  textures.append(uc.reg_read(UC_PPC_REG_0+4));reg(3,0x150000);uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
 if a in (0x822EC8FC,0x822E4194,0x822E3A8C,0x822EE18C):
  # Native body fixture reenables its art after a UI update, as observed in
  # the original callers. The final wrapper must run after this write.
  for i,name in enumerate(names):put(0x1240D0+i*0x100,1)
  uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_0+12))
c.hook_add(UC_HOOK_CODE,fixture)
ui=[]
names=['i_pl_seal_anm_grp','a_pl_attack_anm_grp','i_pl_attack','a_pl_guard_anm_grp','i_pl_guard','i_ico_dummy_grp']
for case in ('normal','already_ordered','missing_pad','unmapped_texture','missing_root','missing_dummy'):
 c.mem_write(0x110000,bytes(0x60000));lookup.update({'i_pl_grp':0x120000,'p_ico_dummy_000':0x121000})
 if case=='missing_root':lookup['i_pl_grp']=0
 if case=='missing_dummy':lookup['p_ico_dummy_000']=0
 put(0x110004,0x111000);put(0x1200B8,0x122000);put(0x121024,0x150000);put(0x121020,5)
 put(0x82649134,0 if case=='missing_pad' else 0x140000);put(0x1400D8,34);put(0x1400DC,0x141000);put(0x14101C,0x150000)
 if case=='unmapped_texture':put(0x121024,0x150100)
 put(0x122008,0x123000);c.mem_write(0x12200C,struct.pack('>H',len(names)))
 order=list(reversed(names)) if case=='already_ordered' else names
 for i,name in enumerate(order):
  obj=0x124000+i*0x100;string=0x130000+i*0x80
  c.mem_write(string,name.encode()+b'\0');put(obj+0xD4,string);put(obj+0xD0,1)
  for off,value in ((0,i+77),(4,obj),(8,0xAA000000+i)):put(0x123000+i*12+off,value)
 before=bytes(c.mem_read(0x110000,0x60000));writes.clear();reg(1,0x1EF000);reg(31,0x110000);run(0x825EE100,0x825ED000)
 assert c.reg_read(UC_PPC_REG_0+1)==0x1EF000 and c.reg_read(UC_PPC_REG_0+31)==0x110000
 changed=case in ('normal','already_ordered')
 assert get(0x121020)==(1 if changed else 5),(case,hex(get(0x121020)))
 after_order=[get(0x123000+i*12+4) for i in range(len(names))]
 if changed:
  seal=0x124000+order.index('i_pl_seal_anm_grp')*0x100;dummy=0x124000+order.index('i_ico_dummy_grp')*0x100
  assert after_order.index(seal)>after_order.index(dummy)
  for i,name in enumerate(order):assert get(0x124000+i*0x100+0xD0)==(0 if name in names[1:5] else 1)
 allowed=set(range(0x1EEF70,0x1EF000))
 if changed:
  allowed.update(range(0x121020,0x121024));allowed.update(range(0x123000,0x123000+12*len(names)))
  for i in range(len(names)):allowed.update(range(0x1240D0+i*0x100,0x1240D4+i*0x100))
 assert all(all(addr+k in allowed for k in range(n)) for addr,n in writes),(case,'unbounded write')
 stable=bytes(c.mem_read(0x110000,0x60000));run(0x825EE100,0x825ED000);assert bytes(c.mem_read(0x110000,0x60000))==stable
 ui.append({'case':case,'changed':changed,'idempotent':True})
for entry,choice in [(0x825EE000,0),(0x825EE000,1),(0x825EE040,0),(0x825EE080,1)]:
 put(0x82649134,0x140000);reg(30,choice);textures.clear();run(entry);assert textures==[(7,9)[choice]]
wrappers=[]
if 'final_panel_pass' in manifest:
 for info in manifest['final_panel_pass']['wrappers']:
  lookup.update({'i_pl_grp':0x120000,'p_ico_dummy_000':0x121000})
  for i,name in enumerate(names):
   obj=0x124000+i*0x100;string=0x130000+i*0x80;c.mem_write(string,name.encode()+b'\0');put(obj+0xD4,string)
   for off,value in ((0,i+77),(4,obj),(8,0xAA000000+i)):put(0x123000+i*12+off,value)
  for i in range(info['panels']):put(0x170034+i*4,0x110000)
  put(0x121024,0x150000);put(0x121020,5);reg(31,0x11223344);reg(3,0x170000);reg(1,0x1EF000)
  run(int(info['wrapper'],16));assert c.reg_read(UC_PPC_REG_0+31)==0x11223344 and c.reg_read(UC_PPC_REG_0+1)==0x1EF000
  for i,name in enumerate(names):assert get(0x1240D0+i*0x100)==(0 if name in names[1:5] else 1)
  assert get(0x123000+(len(names)-1)*12+4)==0x124000
  wrappers.append(info)
 textures.clear();run(0x825EE0C0);assert textures==[3]
 # Run the original native child renderer after the final postpass. Its leaf
 # draw callbacks and ABI helpers are fixtures; the traversal/order is native.
 for i in range(len(names)):
  put(0x123000+i*12,0);put(0x123000+i*12+8,0);put(0x124000+i*0x100,0x190000)
 put(0x19000C,0x1D0000);reg(1,0x1EF000);reg(3,0x122000);reg(4,0x1C0000);reg(5,0);reg(6,0)
 run(0x8211E590);assert render_visits.index(0x124500)<render_visits.index(0x124000)
report={'scope':__doc__,'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'input_cases':len(rows),'ui_cases':ui,'clash_texture_cases':4,'post_native_wrappers':wrappers,'native_renderer_draw_order':[names[(v-0x124000)//0x100] for v in render_visits],'passed':True}
(source.parent/'combat-feedback-cpu.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
