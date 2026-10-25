"""LOCAL rendering fixture: select an existing Super tutorial lesson group.

By default this chooses course 5's defense group 5 instead of group 0;
--group selects another existing group. Native lesson code creates attacks and defense
windows, evaluates pad input and applies results. It does not change combat
phases, HP, Ki, timers or outcomes. Never count this as completing the whole
tutorial. Some groups depend on context from preceding lessons, so selecting
a group alone does not establish that its full exercise is initialized.
"""
import argparse,hashlib,json,tomllib
from pathlib import Path
from ppc_emit import Assembler
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--group',type=int,choices=range(9),default=5,help='Existing native tutorial lesson group; 4 is the Super mash exercise');a=ap.parse_args()
d=tomllib.loads(a.source.read_text());p=d['patch'][0];image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes();hook=0x822F9430;entry=0x825ECE80
assert image[hook-0x82000000:hook-0x82000000+4]==bytes.fromhex('7d8802a6')
x=Assembler(entry);x.lwz(11,0,3);x.cmp(11,5);x.jump('out',0x40820000)
x.lwz(11,0xD0,3);x.cmp(11,0);x.jump('out',0x40820000);x.lwz(11,0xD4,3);x.cmp(11,0);x.jump('out',0x40820000)
x.lwz(11,0x14,3);x.cmp(11,47);x.jump('out',0x40820000);x.lwz(11,0x10,3);x.cmp(11,0);x.jump('out')
x.lwz(9,0xC,11);x.cmp(9,105);x.jump('out',0x40820000)
x.li(11,a.group);x.stw(11,0xD0,3)
x.label('out');x.emit(0x7D8802A6);x.branch(hook+4);code=x.finish();assert len(code)<0x180
assert not any(image[entry-0x82000000:entry-0x82000000+len(code)])
for r in p['array']:assert entry+len(code)<=r['address'] or r['address']+len(bytes.fromhex(r['value']))<=entry
assert not any(r['address']==hook for r in p['be32'])
p['array'].append({'address':entry,'value':code.hex()});x=Assembler(hook);x.branch(entry);p['be32'].append({'address':hook,'value':x.words[0]})
p['name']='LOCAL ONLY: native Super-defense tutorial rendering fixture'
text='\n'.join(f'{k} = {json.dumps(d[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for r in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{r["address"]:08X}\nvalue = 0x{r["value"]:08X}\n'
for r in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{r["address"]:08X}\nvalue = "{r["value"]}"\n'
a.out.mkdir(exist_ok=False);out=a.out/'4E4D084E.local-super-defense.patch.toml';out.write_text(text)
(a.out/'manifest.json').write_text(json.dumps({'scope':__doc__,'group':a.group,'base_patch_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'hook':hex(hook),'entry':hex(entry),'bytes':len(code),'only_changed_data':f'Native tutorial lesson selector D0, initial group 0 -> group {a.group}; no battle fields.'},indent=2)+'\n');print(out)
