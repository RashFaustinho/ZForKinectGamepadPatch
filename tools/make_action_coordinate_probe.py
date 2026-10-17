"""LOCAL ONLY: log queried/accepted action IDs for the coordinate audit."""
import hashlib
import argparse
import json
import struct
import tomllib
from pathlib import Path
from ppc_emit import Assembler
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--boss-regression',action='store_true',help='Exclude global unlock and log the latest non-super-preparation query')
parser.add_argument('--patch',type=Path,default=ROOT/'experiments/gamepad-feedback-v4/4E4D084E.gamepad-feedback.patch.toml')
parser.add_argument('--out',type=Path)
args=parser.parse_args()
source=args.patch
data=tomllib.loads(source.read_text());p=data['patch'][0]
main=next(x for x in p['array'] if x['address']==0x825EB100)
payload=bytearray.fromhex(main['value'])
# Selector telemetry, for pad-only navigation before combat.
hook=next(x for x in p['be32'] if x['address']==0x8211A720)
delta=hook['value']&0x3FFFFFC
if delta&0x2000000:delta-=0x4000000
selector_target=hook['address']+delta
a=Assembler(0x825EB780);a.pointer(11,0x8266E180);a.stw(3,0x38,11)
a.emit(0x7D2802A6);a.stw(9,0x3C,11);a.branch(selector_target)
p['array'].append({'address':a.address,'value':a.finish().hex()})
b=Assembler(hook['address']);b.branch(a.address);hook['value']=b.words[0]
def logger(entry,bitmap,pair,resume,result,caller=False):
    a=Assembler(entry);a.emit(0x28040042);a.jump('out',0x41810000)
    a.emit(0x5489D97E);a.emit(0x5529103A)  # srwi r9,r4,5; slwi r9,r9,2
    a.andi(10,4,31);a.li(8,1);a.emit(0x7D085030)  # slw r8,r8,r10
    a.pointer(11,bitmap);a.emit(0x7D4B482E);a.emit(0x7D4A4378);a.emit(0x7D4B492E)
    a.pointer(11,pair);a.stw(4,0,11);a.pointer(10,0x8266E184)
    a.lwz(8,0,10);a.stw(8,4,11)
    if caller:a.emit(0x7D2802A6);a.stw(9,0x10,11)
    elif args.boss_regression:
        a.cmp(4,0x2D);a.jump('out');a.cmp(4,0x31);a.jump('out')
        a.stw(4,0xC,11)  # latest non-global query at 8266E1FC
    a.label('out');a.li(7,result);a.branch(resume)
    code=a.finish();assert len(code)<=(116 if entry==0x821DB88C else 96)
    p['array'].append({'address':entry,'value':code.hex()})
query=payload.index(bytes.fromhex('38e0000028040042'))
accepted=payload.index(bytes.fromhex('38e000033d608267'))
for off,entry,bitmap,pair,result,caller in ((query,0x821DB88C,0x8266E1D0,0x8266E1F0,0,False),
                                           (accepted,0x825EB7A0,0x8266E1DC,0x8266E1E8,3,True)):
    if entry>=0x825EB100:assert not any(payload[entry-0x825EB100:entry-0x825EB100+96])
    logger(entry,bitmap,pair,main['address']+off+4,result,caller)
    a=Assembler(main['address']+off);a.branch(entry);payload[off:off+4]=a.finish()
main['value']=payload.hex()
p['array'].append({'address':0x8266E1D0,'value':bytes(48).hex()})
if args.boss_regression:
    # The all-content initializer runs at menu construction. Remove that
    # optional feature and its camera replacement, retaining every input hook.
    p['be32']=[x for x in p['be32'] if x['address']!=0x822FC450]
    p['array']=[x for x in p['array'] if x['address'] not in (0x82302220,0x82302508,0x8210EC00,0x8266E1C0)]
p['name']='LOCAL diagnostic: action coverage and coordinate audit'
text='\n'.join(f'{k} = {json.dumps(data[k])}' for k in ('title_name','title_id','hash'))+'\n\n[[patch]]\n'
text+='\n'.join(f'{k} = {json.dumps(p[k])}' for k in ('name','desc','author'))+'\nis_enabled = true\n'
for x in p['be32']:text+=f'\n[[patch.be32]]\naddress = 0x{x["address"]:08X}\nvalue = 0x{x["value"]:08X}\n'
for x in p['array']:text+=f'\n[[patch.array]]\naddress = 0x{x["address"]:08X}\nvalue = "{x["value"]}"\n'
out=args.out or ROOT/('experiments/diagnostic-boss-regression' if args.boss_regression else 'experiments/diagnostic-action-coordinates');out.mkdir(exist_ok=True)
(out/'4E4D084E.local-action-coordinates.patch.toml').write_text(text)
(out/'manifest.json').write_text(json.dumps({'local_only':True,'base_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'global_unlock_removed':args.boss_regression,'queried_bitmap':'8266E1D0','accepted_bitmap':'8266E1DC','last_accepted_pair':'8266E1E8','last_queried_pair':'8266E1F0','last_contextual_query':'8266E1FC' if args.boss_regression else None},indent=2)+'\n')
print(out)
