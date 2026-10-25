"""Execute the HD adapter and compare GPU bytes to authored DDS/RGBA sources.

This verifies bounded native VRAM writes, allocation guards, idempotence,
PowerPC branches and preserved UI frame/LR/r31. It does not prove rendering.
"""
import argparse,hashlib,json,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_PROT_READ,UC_PROT_EXEC,UC_HOOK_MEM_WRITE,UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_LR,UC_PPC_REG_PC
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v8/4E4D084E.gamepad-feedback.patch.toml');source=parser.parse_args().patch
p=tomllib.loads(source.read_text())['patch'][0]
patch_manifest=json.loads((source.parent/'manifest.json').read_text());assets_path=root/patch_manifest['hd_prompt_adapter'].get('assets','assets/controller')
assets=json.loads((assets_path/'manifest.json').read_text())
rgba_faces=any(t.get('gpu_format')==6 for t in assets['textures'])
c=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);c.mem_map(0x82000000,0x700000);c.mem_map(0x100000,0x200000)
c.mem_map(0x300000,0x300000)
c.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for x in p['array']:c.mem_write(x['address'],bytes.fromhex(x['value']))
for x in p['be32']:c.mem_write(x['address'],struct.pack('>I',x['value']))
c.mem_protect(0x82110000,0x4E0000,UC_PROT_READ|UC_PROT_EXEC)
c.mem_protect(0x820FC000,0x14000,UC_PROT_READ)
c.mem_protect(0x82680000,0x40000,UC_PROT_READ)
def put(a,v):c.mem_write(a,struct.pack('>I',v))
def get(a):return int.from_bytes(c.mem_read(a,4),'big')
def reg(n,v):c.reg_write(UC_PPC_REG_0+n,v)
def obj(i):return 0x121000+i*0x100
def meta(i):return 0x125000+i*0x40
def pixels(i):return 0x140000+i*0x4000
owned='face_dimensions' in patch_manifest['hd_prompt_adapter']
face_bytes=patch_manifest['hd_prompt_adapter'].get('face_decoded_bytes',65536)
def allocated(i):return 0x400000+i*0x50000
allocations=[];freed=[]
def allocation(uc,address,size,user):
 if not owned:return
 if rgba_faces and address==int(patch_manifest['hd_prompt_adapter']['allocation_helpers']['commit'],16) and case=='invalid_palette_index':
  if get(get(0x2F0000-0x80+0x60))==target:
   c.mem_write(get(0x2F0000-0x80+0x6C),b'\xff')
 if address==0x823791D8:
  i=get(get(0x2F0000-0x80+0x60));assert get(0x826494A0)==uc.reg_read(UC_PPC_REG_0+3)
  assert [uc.reg_read(UC_PPC_REG_0+r) for r in (4,5,6)]==[face_bytes,4096,1]
  handle=0x129000+i*0x40;data=allocated(i)
  put(handle,0x130000);put(handle+0x10,data);put(data-4,handle)
  allocations.append(i)
  for r in range(3,13):reg(r,0xBAD000+r)
  reg(3,0 if case=='allocation_failed' and i==target else handle)
  reg(0,0xBAD000)
  uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
 elif address==0x823794B8:
  handle=uc.reg_read(UC_PPC_REG_0+4);freed.append(handle)
  assert handle==0x129000+target*0x40
  uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
c.hook_add(UC_HOOK_CODE,allocation)
def run():
 reg(31,0x12345678);reg(1,0x2F0000);c.reg_write(UC_PPC_REG_LR,0x87654321)
 # Stop at the next adapter; the UI postpass has its own scene fixtures.
 end=int(patch_manifest['final_panel_pass']['hd_next_adapter'],16) if 'final_panel_pass' in patch_manifest else (0x825EE100 if 'combat_feedback' in patch_manifest else 0x825ED000)
 c.emu_start(0x825ED900,end,count=6000000)
 assert c.reg_read(UC_PPC_REG_PC)==end
 assert c.reg_read(UC_PPC_REG_0+1)==0x2F0000 and c.reg_read(UC_PPC_REG_0+31)==0x12345678
 assert c.reg_read(UC_PPC_REG_LR)==0x87654321
rows=[];writes=[]
c.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,a,n,v,user:writes.append((a,n)))
for case in ['normal','missing_pad','wrong_count','bad_width','bad_height','bad_size','bad_format','bad_owner','out_of_allocation','bad_fetch_address']+(['allocation_failed','truncated_stream'] if owned else [])+(['invalid_palette_index'] if rgba_faces else []):
 c.mem_write(0x100000,bytes(0x500000));writes.clear();allocations.clear();freed.clear()
 put(0x826494A0,0x130000)
 put(0x82649134,0x120000);put(0x1200D8,34);put(0x1200DC,0x124000);put(0x1200E4,0x140000);put(0x1200BC,0x88000)
 for t in assets['textures']:
  i=t['index'];o=obj(i);m=meta(i);v=pixels(i)
  put(0x124000+i*4,o);put(o+4,0x120000);put(o+0x34,m)
  put(o+0x54,0x800002);put(o+0x58,v|0x86);put(o+0x5C,0x3E01F);put(o+0x60,0xC14)
  put(m,0xA2);put(m+4,v);put(m+0xC,0x4000);put(m+0x10,0x00200020)
 if case=='missing_pad':put(0x82649134,0)
 if case=='wrong_count':put(0x1200D8,33)
 target=5;m=meta(target);o=obj(target)
 if case=='bad_width':put(m+0x10,0x00100020)
 if case=='bad_height':put(m+0x10,0x00200040)
 if case=='bad_size':put(m+0xC,0x2000)
 if case=='bad_format':put(o+0x58,pixels(target)|0x14)
 if case=='bad_owner':put(o+4,0x130000)
 if case=='out_of_allocation':put(m+4,0x300000)
 if case=='bad_fetch_address':put(o+0x58,pixels(target)+0x1000|0x86)
 record=0x825ED840+next(k for k,t in enumerate(assets['textures']) if t['index']==target)*12
 packed=get(record+8)
 if case=='truncated_stream':put(record+8,packed-1)
 before=bytes(c.mem_read(0x100000,0x200000));run();changed=[];allowed=set(range(0x2EFF80,0x2F0000))
 for t in assets['textures']:
  i=t['index'];expected=case not in ('missing_pad','wrong_count') and not (i==target and case!='normal')
  width=t.get('width',128);height=t.get('height',128);size=t['decoded_bytes']
  destination=allocated(i) if owned and width==256 and expected else pixels(i)
  actual=bytes(c.mem_read(destination,size if expected else 16384));dds=(assets_path/(t['label']+'.rgba')).read_bytes() if t.get('gpu_format')==6 else (assets_path/(t['label']+'.dds')).read_bytes()[128:]
  assert actual==(dds if expected else bytes(16384)),(case,t['label'],'pixels differ')
  if owned and 2<=i<=5 and i in allocations:
   allowed.update(range(allocated(i),allocated(i)+face_bytes))
  if expected:
   assert get(meta(i)+0x10)==(width<<16)|height
   assert [get(obj(i)+a) for a in (0x54,0x58,0x5C,0x60)]==[0x02000002 if width==256 else 0x01000002,destination|t.get('gpu_format',20),0x1FE0FF if width==256 else 0xFE07F,t.get('fetch_word3',0xD10)]
   if owned and width==256:
    assert get(meta(i))==0xAA and get(meta(i)+4)==destination and get(meta(i)+0xC)==face_bytes
    allowed.update(range(meta(i),meta(i)+0x10))
   allowed.update(range(destination,destination+size));allowed.update(range(meta(i)+0x10,meta(i)+0x14))
   allowed.update(range(meta(i)+0x20,meta(i)+0x24));allowed.update(range(obj(i)+0x54,obj(i)+0x64));changed.append(i)
 assert all(all(a+k in allowed for k in range(n)) for a,n in writes),(case,'write outside checked storage')
 after=bytes(c.mem_read(0x100000,0x200000));run()
 for t in assets['textures']:
  if owned and t['index'] in changed and t.get('width',128)==256:
   expected=(assets_path/(t['label']+'.rgba')).read_bytes() if t.get('gpu_format')==6 else (assets_path/(t['label']+'.dds')).read_bytes()[128:]
   assert bytes(c.mem_read(allocated(t['index']),len(expected)))==expected,(case,'repeated GPU buffer changed')
 repeated=bytes(c.mem_read(0x100000,0x200000))
 assert repeated[:0x1EFF80]==after[:0x1EFF80] and repeated[0x1F0000:]==after[0x1F0000:],(case,'not idempotent outside private scratch')
 rows.append({'case':case,'textures_replaced':changed,'decoded_bytes':sum(t['decoded_bytes'] for t in assets['textures'] if t['index'] in changed)})
 if case in ('truncated_stream','invalid_palette_index'):assert freed==[0x129000+target*0x40]*2
 if case=='allocation_failed':assert not freed
 if case=='normal' and owned:assert allocations==[2,3,4,5],allocations
 put(record+8,packed)
report={'scope':__doc__,'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':len(rows),'cases':rows}
(source.parent/'hd-prompts-cpu.json').write_text(json.dumps(report,indent=2)+'\n');print('Passed',len(rows),'HD adapter cases;',len(assets['textures']),'decoded textures match their DDS sources')
