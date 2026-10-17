"""Add guarded 128 px controller textures to revision 7, using existing VRAM.

All original files stay intact. Only the existing, checked 16 KiB allocations
of the eleven pad textures are replaced. Read-only LZ4 source bytes live in
verified zero image padding; the decoder never writes to those source pages.
"""
import hashlib,json,struct,tomllib
from pathlib import Path
from ppc_emit import Assembler
root=Path(__file__).resolve().parents[1]
source=root/'experiments/gamepad-feedback-v7/4E4D084E.gamepad-feedback.patch.toml'
m=json.loads((source.parent/'manifest.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==m['patch_sha256']
d=tomllib.loads(source.read_text());p=d['patch'][0]
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b'
assets=root/'assets/controller';am=json.loads((assets/'manifest.json').read_text());blob=(assets/'buttons.lz4').read_bytes()
assert hashlib.sha256(blob).hexdigest()==am['sha256'] and am['width']==am['height']==128
record=0x825ED840;entry=0x825ED900
regions=[(0x826BB800,0x826C0000),(0x8210F000,0x82110000)]
chunks=[];records=[];cursors=[x for x,y in regions]
for t in sorted(am['textures'],key=lambda x:-x['packed_bytes']):
 n=t['packed_bytes']
 region=next(i for i in range(len(regions)) if cursors[i]+n<=regions[i][1]);cursor=cursors[region]
 raw=blob[t['offset']:t['offset']+n];assert not any(image[cursor-0x82000000:cursor-0x82000000+n])
 chunks.append({'address':cursor,'value':raw.hex()});records.extend((t['index'],cursor,n));cursors[region]+=n
records.extend((0xffffffff,0,0));table=struct.pack('>'+str(len(records))+'I',*records)
assert record+len(table)<=entry

a=Assembler(entry)
def cmpw(x,y):a.emit(0x7C000000|(x<<16)|(y<<11))
def cmplw(x,y):a.emit(0x7C000040|(x<<16)|(y<<11))
def add(x,y,z):a.emit(0x7C000214|(x<<21)|(y<<16)|(z<<11))
def sub(x,y,z):a.emit(0x7C000050|(x<<21)|(z<<16)|(y<<11)) # x=y-z
def lbz(x,off,y):a.d(34,x,y,off)
def next_source():a.d(14,6,6,1)
def b(label):a.jump(label,0x48000000)
def lower_bound(x,y):cmplw(x,y);a.jump('next',0x41800000)
def upper_bound(x,y):cmplw(x,y);a.jump('next',0x41810000)
a.d(37,1,1,-0x80)
a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('out')
a.lwz(3,0xD8,11);a.cmp(3,34);a.jump('out',0x40820000)
a.stw(11,0x78,1);a.pointer(12,record)
a.label('texture');a.stw(12,0x60,1);a.lwz(3,0,12);a.cmp(3,-1);a.jump('out')
a.lwz(11,0x78,1);a.lwz(9,0xDC,11);a.cmp(9,0);a.jump('out')
a.emit(0x5463103A);a.emit(0x7D29182E) # slwi r3,2; lwzx r9,r9,r3
a.cmp(9,0);a.jump('next');a.stw(9,0x64,1)
a.lwz(8,4,9);cmpw(8,11);a.jump('next',0x40820000)
a.lwz(8,0x34,9);a.cmp(8,0);a.jump('next');a.stw(8,0x68,1)
a.lwz(3,0,8);a.cmp(3,0xA2);a.jump('next',0x40820000)
a.lwz(3,0xC,8);a.cmp(3,0x4000);a.jump('next',0x40820000)
a.d(40,3,8,0x12);a.cmp(3,32);a.jump('next',0x40820000)
a.d(40,3,8,0x10);a.cmp(3,32);a.jump('width_ok');a.cmp(3,64);a.jump('next',0x40820000)
a.label('width_ok');a.lwz(7,4,8);a.cmp(7,0);a.jump('next')
a.lwz(3,0xE4,11);lower_bound(7,3);a.lwz(0,0xBC,11);add(3,3,0)
a.d(14,5,7,0x4000);upper_bound(5,3);a.stw(7,0x6C,1)
a.lwz(3,0x58,9);a.andi(0,3,63);a.cmp(0,6);a.jump('next',0x40820000)
a.pointer(0,0xFFFFF000);a.emit(0x7C630038);cmpw(3,7);a.jump('next',0x40820000)
a.lwz(6,4,12);a.lwz(3,8,12);add(11,6,3)
a.label('token');cmplw(6,11);a.jump('next',0x40800000) # source >= end
lbz(4,0,6);next_source();a.emit(0x5483E13E) # srwi r3,r4,4
a.cmp(3,15);a.jump('literal_extra')
b('literal_bounds')
a.label('literal_extra');cmplw(6,11);a.jump('next',0x40800000)
lbz(0,0,6);next_source();add(3,3,0);a.cmp(0,255);a.jump('literal_extra')
a.label('literal_bounds');add(10,6,3);upper_bound(10,11);add(10,7,3);upper_bound(10,5)
a.cmp(3,0);a.jump('after_literal')
a.label('literal');lbz(0,0,6);a.d(38,0,7,0);next_source();a.d(14,7,7,1);a.d(14,3,3,-1);a.cmp(3,0);a.jump('literal',0x40820000)
a.label('after_literal');cmpw(6,11);a.jump('decoded')
a.d(14,10,6,2);upper_bound(10,11)
lbz(8,0,6);lbz(0,1,6);a.emit(0x5400402E);add(8,8,0);a.d(14,6,6,2)
a.cmp(8,0);a.jump('next');sub(8,7,8);a.lwz(10,0x6C,1);lower_bound(8,10)
a.andi(3,4,15);a.cmp(3,15);a.jump('match_extra');b('match_bounds')
a.label('match_extra');cmplw(6,11);a.jump('next',0x40800000)
lbz(0,0,6);next_source();add(3,3,0);a.cmp(0,255);a.jump('match_extra')
a.label('match_bounds');a.d(14,3,3,4);add(10,7,3);upper_bound(10,5)
a.label('match');lbz(0,0,8);a.d(38,0,7,0);a.d(14,8,8,1);a.d(14,7,7,1);a.d(14,3,3,-1);a.cmp(3,0);a.jump('match',0x40820000);b('token')
a.label('decoded');cmpw(7,5);a.jump('next',0x40820000)
a.lwz(9,0x64,1);a.lwz(8,0x68,1)
a.li(3,128);a.d(44,3,8,0x10);a.d(44,3,8,0x12)
a.pointer(3,0x18000000);a.stw(3,0x20,8) # native resource format index 3 = DXT5
a.pointer(3,0x01000002);a.stw(3,0x54,9) # linear pitch 128, fetch texture type 2
a.lwz(3,0x6C,1);a.ori(3,3,20);a.stw(3,0x58,9) # BC3 and no byte swap
a.pointer(3,0x000FE07F);a.stw(3,0x5C,9) # size 128 x 128
a.li(3,0xD10);a.stw(3,0x60,9) # RGBA component swizzle
a.label('next');a.lwz(12,0x60,1);a.d(14,12,12,12);b('texture')
a.label('out');a.d(14,1,1,0x80);a.branch(0x825ED000)
code=a.finish();assert entry+len(code)<0x825F0000
for start,raw in ((entry,code),(record,table)):
 assert not any(image[start-0x82000000:start-0x82000000+len(raw)])
for x in p['be32']:
 if x['address']==0x82114DDC:
  hook=Assembler(x['address']);hook.branch(entry);x['value']=hook.words[0]
# The menu label's style does not run the native button-token parser. A plain
# localized-resource B renders reliably in this style, unlike U+25CB (tofu).
ui=next(x for x in p['array'] if x['address']==0x825ED000)
raw=bytes.fromhex(ui['value']);assert raw.count(bytes.fromhex('3920cb25'))==1
ui['value']=raw.replace(bytes.fromhex('3920cb25'),bytes.fromhex('39204200')).hex()
p['array'] += [{'address':entry,'value':code.hex()},{'address':record,'value':table.hex()},*chunks]
p['name']='Gamepad feedback revision 8: clear 128 px Xbox prompts'
p['desc']='Revision 7 with original vector controller drawings at 128 px, bounded native VRAM replacement, and a readable B menu-return label.'
out=root/'experiments/gamepad-feedback-v8';out.mkdir(exist_ok=True)
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
output=out/'4E4D084E.gamepad-feedback.patch.toml';output.write_text(text)
m.update(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
 status='development: HD UI adapter requires CPU and Vulkan validation',
 hd_prompt_adapter={'hook':'0x82114ddc','entry':hex(entry),'bytes':len(code),'record_table':hex(record),
 'width':128,'height':128,'format':'BC3 linear RGBA, no byte swap','source_sha256':am['sha256'],
 'source_regions':[[hex(x),hex(y)] for x,y in regions],'textures':am['textures'],
 'writes':'Only existing checked 16 KiB native pad VRAM and corresponding texture headers'},
 menu_label='UTF-16LE plain B in the original Left Hand text style')
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(output,'helper bytes',len(code))
