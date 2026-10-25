"""Read-only proof that all selected native pad resources contain their GPU data."""
import argparse,hashlib,json,struct
from pathlib import Path
import battle_state as b
p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');p.add_argument('--assets',type=Path,default=Path('assets/controller'));a=p.parse_args();b.connect(a.session)
root=Path(__file__).resolve().parents[1];manifest=json.loads((root/a.assets/'manifest.json').read_text())
loader=b.word(0x82649134);assert loader and b.word(loader+0xD8)==34
base=b.word(loader+0xE4);limit=base+b.word(loader+0xBC);table=b.word(loader+0xDC);rows=[]
for t in manifest['textures']:
 obj=b.word(table+t['index']*4);meta=b.word(obj+0x34);data=b.word(meta+4)
 width=t.get('width',128);height=t.get('height',128);decoded=t['decoded_bytes']
 if width==128:assert base<=data and data+decoded<=limit
 else:
  assert b.word(meta)==0xAA and b.word(meta+0xC)==decoded and data%4096==0
  handle=b.word(data-4);pool=b.word(0x826494A0)
  assert b.word(handle)==pool and b.word(handle+0x10)==data and b.word(handle+0xC)==decoded
 header=struct.unpack('>4I',b.read(obj+0x54,16));size=struct.unpack('>2H',b.read(meta+0x10,4))
 sha=hashlib.sha256(b.read(data,decoded)).hexdigest()
 assert header==(0x2000002 if width==256 else 0x1000002,data|t.get('gpu_format',20),0x1FE0FF if width==256 else 0xFE07F,t.get('fetch_word3',0xD10)),(t['label'],header)
 assert size==(width,height) and sha==t.get('rgba8_sha256',t.get('bc3_sha256')),t['label']
 rows.append({'index':t['index'],'label':t['label'],'resource':hex(obj),'native_size':list(size),'data':hex(data),'sha256':sha})
report={'scope':__doc__+' Rendering still requires a screenshot.','passed':len(rows),'textures':rows}
out=b.endpoint.parent/'hd-textures-runtime.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print('Verified',len(rows),'native texture resources byte for byte')
