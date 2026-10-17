"""Read selected AFS UI resources into private research artifacts, never edit ISO."""
import argparse,hashlib,json,re,struct
from pathlib import Path
root=Path('/workspace/artifacts/zforkinect')
p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',choices=('boot','progress','battle_others'));a=p.parse_args()
entry=next(e for e in json.loads((root/'analysis/disc-files.json').read_text()) if e['path'].endswith('st_pack_'+a.archive+'_pt_x360.afs'))
with (root/'disc/Dragon Ball Z for Kinect (Europe) (En,Fr,De,Es,It).iso').open('rb') as f:f.seek(entry['offset']);archive=f.read(entry['size'])
assert archive[:4]==b'AFS\0'
def decode(data):
 if data[:4]==b'STPZ':data=data[16:]
 if data[:4]!=b'SCD0':return data
 total,size=struct.unpack_from('>II',data,4);assert total<=128*1024*1024 and size<=len(data)
 result=bytearray();pos=16
 while pos<size:
  assert data[pos:pos+4]==b'SCL0'
  expected,chunk_size=struct.unpack_from('>II',data,pos+4);assert chunk_size>=16 and pos+chunk_size<=size
  src=data[pos+16:pos+chunk_size];out=bytearray();i=0
  while i<len(src):
   flag=src[i];i+=1;n=flag>>1
   if flag&1:
    distance=src[i];i+=1;assert 0<distance<=len(out)
    for _ in range(n):out.append(out[-distance])
   else:assert i+n<=len(src);out.extend(src[i:i+n]);i+=n
   assert len(out)<=expected
  assert len(out)==expected;result.extend(out);pos+=chunk_size
 assert pos==size and len(result)==total
 return bytes(result)
outdir=root/'analysis'/('ui-'+a.archive+'-decoded');outdir.mkdir(exist_ok=True);report=[]
for i in range(struct.unpack_from('<I',archive,4)[0]):
 offset,size=struct.unpack_from('<II',archive,8+i*8);assert offset+size<=len(archive)
 src=archive[offset:offset+size];data=decode(src)
 terms=[m.group().decode(errors='replace') for m in re.finditer(rb'[A-Za-z_][A-Za-z0-9_./@ -]{4,}',data)
        if re.search(rb'hand|return|navi|guide|cancel|button|FP_0[123]',m.group(),re.I)]
 if terms:
  path=outdir/(str(i)+'.bin')
  if path.exists():assert path.read_bytes()==data
  else:path.write_bytes(data)
  report.append({'index':i,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'terms':terms})
(outdir/'index.json').write_text(json.dumps(report,indent=2)+'\n')
print('Decoded',len(report),'matching private resources to',outdir)
