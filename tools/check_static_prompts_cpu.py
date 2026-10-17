"""Verify the UI epilogue adapter with the original native part-name lookup."""
import argparse,hashlib,json,struct,tomllib
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_LR,UC_PPC_REG_PC
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--patch',type=Path,default=root/'experiments/gamepad-feedback-v7/4E4D084E.gamepad-feedback.patch.toml')
source=parser.parse_args().patch
manifest=json.loads((source.parent/'manifest.json').read_text());label=bytes.fromhex('42000000' if 'menu_label' in manifest else 'cb250000')
p=tomllib.loads(source.read_text())['patch'][0]
c=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);c.mem_map(0x82000000,0x700000);c.mem_map(0x100000,0x60000)
c.mem_write(0x82000000,Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin').read_bytes())
for x in p['array']:c.mem_write(x['address'],bytes.fromhex(x['value']))
for x in p['be32']:c.mem_write(x['address'],struct.pack('>I',x['value']))
def put(a,v):c.mem_write(a,struct.pack('>I',v))
def get(a):return int.from_bytes(c.mem_read(a,4),'big')
def reg(n,v):c.reg_write(UC_PPC_REG_0+n,v)
calls=[]
def tex(uc,a,size,user):
 if a==0x823498A8:
  calls.append([uc.reg_read(UC_PPC_REG_0+n) for n in (3,4,5)])
  reg(3,0x130100);uc.reg_write(UC_PPC_REG_PC,uc.reg_read(UC_PPC_REG_LR))
c.hook_add(UC_HOOK_CODE,tex)
rows=[]
for case in ['normal','already_labelled','no_manager','no_text_base','wrong_header','wrong_name','wrong_count','short_text','wrong_BOM','not_ready','no_scene','no_pad','no_part']:
 c.mem_write(0x100000,bytes(0x60000));calls.clear()
 put(0x826490E0,0x102000);put(0x102020,0x105000)
 put(0x105000,0x5354504B);put(0x105008,99);put(0x105C70,0x2000);put(0x105C74,22)
 c.mem_write(0x105C80,b'PBC_KN_066_UK.txt\0');old=b'\xff\xfe'+('Left Hand\0').encode('utf-16le');c.mem_write(0x107000,old)
 put(0x82649134,0x130000);put(0x120014,1);put(0x120004,0x122000)
 put(0x122014,0x123000);put(0x123008,0x124000);put(0x12300C,1);put(0x124000,0x126000)
 put(0x1260D4,0x127000);c.mem_write(0x127000,b'p_jump_ico_000\0');put(0x126020,4);put(0x126024,0x12345678)
 if case=='already_labelled':c.mem_write(0x107002,label)
 if case=='no_manager':put(0x826490E0,0)
 if case=='no_text_base':put(0x102020,0)
 if case=='wrong_header':put(0x105000,0)
 if case=='wrong_name':c.mem_write(0x105C80,b'OTHER_RESOURCE\0')
 if case=='wrong_count':put(0x105008,98)
 if case=='short_text':put(0x105C74,4)
 if case=='wrong_BOM':c.mem_write(0x107000,b'XX')
 if case=='not_ready':put(0x120014,0)
 if case=='no_scene':put(0x120004,0)
 if case=='no_pad':put(0x82649134,0)
 if case=='no_part':c.mem_write(0x127000,b'p_other_ico_00\0')
 before=bytes(c.mem_read(0x100000,0x60000));reg(31,0x120000);reg(1,0x14F000)
 c.reg_write(UC_PPC_REG_LR,0x87654321);c.emu_start(0x82114DDC,0x82114DE0,count=1500)
 assert c.reg_read(UC_PPC_REG_PC)==0x82114DE0 and c.reg_read(UC_PPC_REG_0+1)==0x14F060
 assert c.reg_read(UC_PPC_REG_0+31)==0x120000
 valid_label=case not in ('no_manager','no_text_base','wrong_header','wrong_name','wrong_count','short_text','wrong_BOM')
 assert bytes(c.mem_read(0x107002,4))==(label if valid_label else before[0x7002:0x7006])
 valid_icon=case not in ('not_ready','no_scene','no_pad','no_part')
 assert calls==([[0x130000,5,0x54583244]] if valid_icon else [])
 assert get(0x126024)==(0x130100 if valid_icon else 0x12345678)
 assert get(0x126020)==(1 if valid_icon else 4)
 after=bytes(c.mem_read(0x100000,0x60000));allowed={*range(0x7002,0x7006),*range(0x26020,0x26028),*range(0x4EF80,0x4EF84),*range(0x4EFE0,0x4EFE4)}
 if 'combat_feedback' in manifest:allowed.update(range(0x4EF70,0x4F000)) # Private UI postpass frame.
 if 'final_panel_pass' in manifest:allowed.update(range(0x4EEF0,0x4F000)) # HD caller plus shared postpass.
 assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(before,after)))
 rows.append({'case':case,'label_replaced':valid_label,'approach_icon_replaced':valid_icon})
report={'scope':__doc__+' Native texture creation stubbed; screen rendering requires Vulkan.',
        'patch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':len(rows),'cases':rows}
(source.parent/'static-prompts-cpu.json').write_text(json.dumps(report,indent=2)+'\n');print('Passed',len(rows),'UI adapter cases')
