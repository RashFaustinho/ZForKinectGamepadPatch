"""LOCAL: confirm boss result screens with A and verify native disk progress.

Only pad input and read-only observations. Requires the separately prepared
fixture whose next chapter was locked and a patch without global unlock.
"""
import argparse
import fcntl
import hashlib
import json
import struct
import time
from pathlib import Path
import battle_state as b
from coordinate_audit import request
from create_content_save import valid

p=argparse.ArgumentParser(description=__doc__);p.add_argument('session')
p.add_argument('--probe',default='native-boss-result.json',help='Completed native boss input report in the session directory')
a=p.parse_args();b.connect(a.session)
lock=open(b.input_lock_path(),'a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
out=b.endpoint.parent/'native-boss-persistence.json'
if out.exists():raise RuntimeError('Capture exists')
save=b.endpoint.parent/'storage/content/B13EBABEBABEBABE/4E4D084E/00000001/SystemData/DB_SAVE'
if Path(a.probe).name!=a.probe:p.error('Probe must be a report filename')
probe=json.loads((b.endpoint.parent/a.probe).read_text())
assert probe['progress_flags_before']['next_saga_first_stage']==0
assert probe['native_next_saga_unlock_observed']
image=Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes()
assert b.read(0x822FC450,4)==image[0x2FC450:0x2FC454], 'Global unlock hook is present'
def disk():
    data=save.read_bytes()
    return {'next_saga_first_stage':struct.unpack_from('>I',data,0x4BC)[0],
            'checksum_valid':valid(data),'sha256':hashlib.sha256(data).hexdigest()}
before=disk();rows=[];request({'command':'resume'})
try:
    for attempt in range(40):
        owner=b.word(0x82649298);ctx=b.word(owner+0x54) if owner else 0
        row={'attempt':attempt,'battle_context':hex(ctx),'disk':disk()};rows.append(row)
        if not ctx and row['disk']['checksum_valid'] and row['disk']['next_saga_first_stage']&1:break
        request({'command':'key','key':'space','duration':.2});time.sleep(.6)
finally:request({'command':'pause'})
result={'scope':__doc__.strip(),'before':before,'samples':rows,'after':disk(),
        'global_unlock_hook_absent':True,'passed':bool(rows and rows[-1]['battle_context']=='0x0'
         and rows[-1]['disk']['checksum_valid'] and rows[-1]['disk']['next_saga_first_stage']&1)}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if not result['passed']:raise SystemExit(1)
