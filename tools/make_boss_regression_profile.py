"""Create a separate test profile with only the first five story stages open.

This is an offline fixture, not a played save or a released user save. It lets
the game's own progression writes prove the result of the boss fight. The
source profile and original generated all-content save are never overwritten.
"""
import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path
from create_content_save import seal,valid,word,legacy_header

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output',type=Path)
a=p.parse_args()
root=Path('/workspace/artifacts/zforkinect')
source=root/'profile-feedback-test/content/B13EBABEBABEBABE/4E4D084E/00000001/SystemData/DB_SAVE'
data=bytearray(source.read_bytes())
if not valid(data):raise RuntimeError('Invalid source save')
source_hash=hashlib.sha256(data).hexdigest()
# Reset the two mode progression tables, preserving character and bonus data.
data[0x20:0x2EE8]=bytes(0x2EC8)
for mode in range(2):
    for saga in range(5):
        base=0x20+mode*0x1764+saga*0x494
        for stage in range(6):
            record=base+8+stage*0x94
            if saga<4 and (stage<5 or saga!=0):
                for off,value in ((0x14,23),(0x18,391),(0x1c,391)):
                    word(data,record+off,value)
word(data,0x20,1)
for i in range(5):word(data,0x28+i*0x94,1)
seal(data)
assert valid(data) and struct.unpack_from('>I',data,0x4BC)[0]==0
a.output.mkdir(parents=True,exist_ok=False)
shutil.copytree(root/'profile-template/content',a.output/'content')
title=a.output/'content/B13EBABEBABEBABE/4E4D084E'
save=title/'00000001/SystemData/DB_SAVE';save.parent.mkdir(parents=True,exist_ok=True);save.write_bytes(data)
header=title/'Headers/00000001/SystemData.header';header.parent.mkdir(parents=True,exist_ok=True);header.write_bytes(legacy_header(0xB13EBABEBABEBABE))
(a.output/'manifest.json').write_text(json.dumps({'scope':__doc__.strip(),'source_sha256':source_hash,
    'save_sha256':hashlib.sha256(data).hexdigest(),'native_checksum_valid':valid(data),
    'first_five_story_flags':[1]*5,'next_saga_first_stage_flags':0,
    'scores':'reset to zero; no completion flags pre-set'},indent=2)+'\n')
print(a.output)
