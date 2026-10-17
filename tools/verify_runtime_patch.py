"""Read back an owned Xenia session's startup patch; never write guest memory."""
import argparse
import hashlib
import json
import struct
import tomllib
from pathlib import Path
import battle_state as b

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('session');p.add_argument('patch',type=Path)
p.add_argument('--report-name',default='runtime-patch-verification.json')
args=p.parse_args();b.connect(args.session)
source=args.patch.read_bytes();patch=tomllib.loads(source.decode())
result={'patch_sha256':hashlib.sha256(source).hexdigest(),'title_id':patch['title_id'],
        'module_hash':patch['hash'],'hooks':[],'arrays':[]}
for group in patch['patch']:
    if not group.get('is_enabled'):continue
    for item in group.get('be32',[]):
        actual=b.read(item['address'],4);expected=struct.pack('>I',item['value'])
        result['hooks'].append({'address':hex(item['address']),'match':actual==expected,
                                'expected':expected.hex(),'actual':actual.hex()})
    arrays=group.get('array',[])
    for index,item in enumerate(arrays):
        expected=bytearray.fromhex(item['value'])
        # Diagnostic variants may fill a previously zero part of a larger
        # payload with a later array. Compare the resulting startup image.
        for later in arrays[index+1:]:
            start=max(item['address'],later['address'])
            value=bytes.fromhex(later['value'])
            end=min(item['address']+len(expected),later['address']+len(value))
            if start<end:
                expected[start-item['address']:end-item['address']]=value[start-later['address']:end-later['address']]
        if item['address']==0x8266E1D0 and bytes(expected)==bytes(48):
            result['arrays'].append({'address':hex(item['address']),
                'scope':'mutable diagnostic coverage; excluded from immutable comparison',
                'bytes_checked':0,'match':True})
            continue
        if item['address']==0x8266E220 and bytes(expected)==bytes(0xC0):
            result['arrays'].append({'address':hex(item['address']),
                'scope':'mutable local prompt counters; excluded from immutable comparison',
                'bytes_checked':0,'match':True})
            continue
        if item['address']==0x8266E2E0 and bytes(expected)==bytes(67*4):
            result['arrays'].append({'address':hex(item['address']),
                'scope':'mutable local per-action timestamps; excluded from immutable comparison',
                'bytes_checked':0,'match':True})
            continue
        mutable=item['address'] in (0x8266e180,0x8266e1c0)
        actual=b.read(item['address'],4 if mutable else len(expected))
        result['arrays'].append({'address':hex(item['address']),
            'scope':'signature only; input counters/selections are mutable' if mutable else 'entire immutable payload',
            'bytes_checked':len(actual),'match':actual==(expected[:4] if mutable else expected)})
result['passed']=all(i['match'] for i in result['hooks']+result['arrays'])
if Path(args.report_name).name!=args.report_name:p.error('Report name must be a filename')
out=b.endpoint.parent/args.report_name
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
if not result['passed']:raise SystemExit(1)
