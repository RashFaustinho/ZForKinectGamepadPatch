"""LOCAL ONLY: mirror discrete Kinect recognizers during boss battles.

Use the query-logging diagnostic as input. No outcome, HP, phase index or
animation completion is forced. The normal fight code remains unchanged.
"""
import json
import struct
import tomllib
from pathlib import Path
from capstone import Cs,CS_ARCH_PPC,CS_MODE_32,CS_MODE_BIG_ENDIAN

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'experiments/diagnostic-boss-queries/4E4D084E.local-boss-query.patch.toml'
patch=tomllib.loads(source.read_text())['patch'][0]
mapping=json.loads(Path('/workspace/artifacts/zforkinect/analysis/action-mapping.json').read_text())
entry=0x825ebe40
table=entry+0x180
words=[];fix=[];labels={}
def emit(w):words.append(w)
def d(op,rt,ra,imm):emit(op<<26|rt<<21|ra<<16|(imm&65535))
def cmp(r,n):d(11,0,r,n)
def beq(s):fix.append((len(words),s));emit(0x41820000)
def b(s):fix.append((len(words),s));emit(0x48000000)
def branch(a,t):return 0x48000000|((t-a)&0x3fffffc)
d(15,11,0,0x8265);d(32,11,11,-0x6d68);cmp(11,0);beq('out')
d(32,11,11,0x54);cmp(11,0);beq('out');d(32,11,11,0xc);cmp(11,1)
fix.append((len(words),'out'));emit(0x40820000)
d(15,11,0,0x8265);d(32,11,11,-0x6e28);cmp(11,0);beq('out')
d(32,10,11,0x24);cmp(10,0);beq('out')
d(15,9,0,0x8265);d(32,9,9,-0x6f24);cmp(9,0);beq('out')
d(32,9,9,0x98);cmp(9,0);beq('out')
d(15,7,0,0x825f);d(14,7,7,-0x4500)
d(15,11,0,table>>16);d(24,11,11,table&0xffff)
d(14,6,0,67);emit(0x7cc903a6)
labels['loop']=len(words)
d(40,8,11,0);cmp(8,0);beq('next')
d(32,5,7,0);d(32,4,7,4)
cmp(4,0x1000);beq('fire');cmp(4,0x1004);beq('pending')
emit(0x7c00002e|(4<<21)|(9<<16)|(4<<11));b('evaluate')
labels['fire']=len(words);d(15,6,0,0x8267);d(32,4,6,-0x1e54);b('evaluate')
labels['pending']=len(words);d(15,6,0,0x8267);d(32,4,6,-0x1e50)
labels['evaluate']=len(words);emit(0x7c000039|(4<<21)|(4<<16)|(5<<11))
beq('zero');d(14,4,0,3);b('store')
labels['zero']=len(words);d(14,4,0,0)
labels['store']=len(words);emit(0x7c00012e|(4<<21)|(10<<16)|(8<<11))
labels['next']=len(words);d(14,7,7,8);d(14,11,11,2)
fix.append((len(words),'loop'));emit(0x42000000)
d(15,11,0,0x8267);d(32,7,11,-0x1e44);d(14,7,7,1);d(36,7,11,-0x1e44)
labels['out']=len(words)
hook=next(p for p in patch['be32'] if p['address']==0x82195550)
delta=hook['value']&0x3fffffc
if delta&0x2000000:delta-=0x4000000
emit(branch(entry+len(words)*4,hook['address']+delta))
for index,name in fix:words[index]|=((labels[name]-index)*4)&0xfffc
code=b''.join(struct.pack('>I',w) for w in words)
assert len(code)<=0x180
offsets=[]
for item in mapping:
    offset=(item['index']+0x6bc)*4 if item['type']==1 and item['index']<0x10000 else 0
    assert offset<=0xffff
    offsets.append(offset)
payload=code+bytes(0x180-len(code))+struct.pack('>67H',*offsets)
assert len(payload)<=0x2c0
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert not any(image[entry-0x82000000:entry-0x82000000+len(payload)])
for a in patch['array']:
    lo=max(a['address'],entry);hi=min(a['address']+len(bytes.fromhex(a['value'])),entry+len(payload))
    assert hi<=lo or not any(bytes.fromhex(a['value'])[lo-a['address']:hi-a['address']])
instructions=list(Cs(CS_ARCH_PPC,CS_MODE_32|CS_MODE_BIG_ENDIAN).disasm(code,entry))
assert len(instructions)==len(words)
text=source.read_text().replace(f'value = 0x{hook["value"]:08X}',f'value = 0x{branch(hook["address"],entry):08X}',1)
text+=f'\n[[patch.array]]\naddress = 0x{entry:08X}\nvalue = "{payload.hex()}"\n'
out=ROOT/'experiments/diagnostic-boss-watchers';out.mkdir(exist_ok=True)
(out/'4E4D084E.local-boss-watchers.patch.toml').write_text(text)
(out/'generated.asm').write_text('\n'.join(f'{i.address:08x} {i.mnemonic} {i.op_str}' for i in instructions)+'\n')
print(out,len(code),len(payload))
