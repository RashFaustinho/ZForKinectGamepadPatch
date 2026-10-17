"""Read local native texture-request counters from an owned Xenia session."""
import argparse,json,struct
from pathlib import Path
import battle_state as b
p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');p.add_argument('name');a=p.parse_args();b.connect(a.session)
if not a.name.replace('-','').isalnum():p.error('Invalid report name')
manifest=json.loads((Path(__file__).resolve().parents[1]/'experiments/diagnostic-prompts/manifest.json').read_text())
report={'scope':'Native getter requests and counters; no claim that a widget is visible on screen','classes':{}}
for name,address in manifest['classes'].items():
 values=struct.unpack('>7I',b.read(int(address,16),28))
 report['classes'][name]={'last_slot':values[0],'frame':values[1],'object':hex(values[2]),'caller':hex(values[3]),
                           'slots':[i for i in range(67) if values[4+i//32]&(1<<(i%32))]}
out=b.endpoint.parent/(a.name+'.json')
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report,indent=2))
