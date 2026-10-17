"""Read-only proof that all eleven native pad resources contain the HD data."""
import argparse,hashlib,json,struct
from pathlib import Path
import battle_state as b
p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');p.add_argument('--assets',type=Path,default=Path('assets/controller'));a=p.parse_args();b.connect(a.session)
root=Path(__file__).resolve().parents[1];manifest=json.loads((root/a.assets/'manifest.json').read_text())
loader=b.word(0x82649134);assert loader and b.word(loader+0xD8)==34
base=b.word(loader+0xE4);limit=base+b.word(loader+0xBC);table=b.word(loader+0xDC);rows=[]
for t in manifest['textures']:
 obj=b.word(table+t['index']*4);meta=b.word(obj+0x34);data=b.word(meta+4)
 assert base<=data and data+16384<=limit
 header=struct.unpack('>4I',b.read(obj+0x54,16));size=struct.unpack('>2H',b.read(meta+0x10,4))
 sha=hashlib.sha256(b.read(data,16384)).hexdigest()
 assert header==(0x1000002,data|20,0xFE07F,0xD10),(t['label'],header)
 assert size==(128,128) and sha==t['bc3_sha256'],t['label']
 rows.append({'index':t['index'],'label':t['label'],'resource':hex(obj),'native_size':list(size),'data':hex(data),'sha256':sha})
report={'scope':__doc__+' Rendering still requires a screenshot.','passed':len(rows),'textures':rows}
out=b.endpoint.parent/'hd-textures-runtime.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print('Verified',len(rows),'native 128x128 texture resources byte for byte')
