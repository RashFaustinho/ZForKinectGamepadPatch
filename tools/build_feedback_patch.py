"""Build the Score Attack revision on top of a verified existing patch.

Original game assets are untouched. The disabled Kinect Tuner update body hosts
small texture adapters, which reuse the game's loaded Xbox button textures.
"""
import hashlib
import json
import struct
import tomllib
from pathlib import Path
from ppc_emit import Assembler

ROOT = Path(__file__).resolve().parents[1]
IMAGE = Path('/workspace/artifacts/zforkinect/analysis/Dbkn.image.bin')
TUNER = 0x821DB5D0
ACTION_ICON = TUNER + 4
COMMON_ICON = TUNER + 0x90
ACTION_MAP = TUNER + 0x250
COMMON_MAP = TUNER + 0x2A0
OUT = ROOT/'experiments/gamepad-feedback-v4'


def texture_adapter(entry, hook, table, maximum):
    a = Assembler(entry)
    a.emit(0x28040000 | maximum)  # cmplwi r4, maximum
    a.jump('original', 0x41810000)
    a.pointer(11, table)
    a.emit(0x7d2b20ae)  # lbzx r9,r11,r4
    a.cmp(9, 255); a.jump('original')
    a.pointer(11, 0x82649134); a.lwz(11, 0, 11)
    a.cmp(11, 0); a.jump('original')
    a.emit(0x7d635b78)  # mr r3,r11: pad SPR loader
    a.emit(0x7d244b78)  # mr r4,r9: button index
    a.pointer(5, 0x54583244)
    a.branch(0x823498A8)
    a.label('original')
    a.emit(0x8163007c if hook == 0x822DAE40 else 0x7d8802a6)
    a.branch(hook+4)
    return a.finish()


def build():
    source = ROOT/'experiments/gamepad-unlocked/4E4D084E.gamepad-unlocked.patch.toml'
    expected = 'd144e215d0883acf7355b4ff1e0609e1c9c7da44b641857ca19e900969cd6258'
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise RuntimeError('The input patch differs from the verified revision')
    data = tomllib.loads(source.read_text()); patch = data['patch'][0]
    image = IMAGE.read_bytes()
    if hashlib.sha256(image).hexdigest() != '72a42f55ed4bf98f7f81d0037144b49997bfe9cb916ddac4fc610a2594296b6b':
        raise RuntimeError('Unsupported flat executable image')
    def original(address, size): return image[address-0x82000000:address-0x82000000+size]
    for address in (TUNER, 0x821DB888, 0x822DE720, 0x822DAE40):
        expected_word = '8163007c' if address == 0x822DAE40 else '7d8802a6'
        if original(address, 4) != bytes.fromhex(expected_word):
            raise RuntimeError(f'Unexpected prologue at {address:08X}')

    main = next(x for x in patch['array'] if x['address'] == 0x825EB100)
    payload = bytearray.fromhex(main['value'])
    previous_payload=bytes(payload)
    # A maintained lateral input must remain active while a native gauge polls
    # it. Normal left/right are 42/C; D/E are used by contextual hip responses.
    for action, mask in ((0x42, 0x4000), (0xC, 0x8000),
                         (0xD, 0x4000), (0xE, 0x8000), (0x26, 0x4400), (0x28, 0x4400)):
        struct.pack_into('>II', payload, 0xA00+action*8, mask, 0x20)
    # The native close-range front-sway gate polls 28 before preparing D;
    # preserve LT as an alternative and let LS-left reach that gate too.
    # The first-person hand processor obtains the tracked body's joints from
    # ctx+1600 (821B7090), whereas the earlier bridge filled only ctx+B80.
    # Keep both buffers in sync before native hand processing. A tail branch
    # preserves LR and the copy loop's CTR.
    copy_pattern=bytes.fromhex('38ea0b80396a00d0')
    copy_offset=payload.index(copy_pattern)+20
    assert payload[copy_offset:copy_offset+4] == bytes.fromhex('91070000')
    copy_hook=0x825EB100+copy_offset
    copy_entry=0x825EBD20
    assert not any(original(copy_entry,16))
    a=Assembler(copy_entry);a.stw(8,0,7);a.stw(8,0xA80,7);a.branch(copy_hook+4)
    patch['array'].append({'address':copy_entry,'value':a.finish().hex()})
    a=Assembler(copy_hook);a.branch(copy_entry)
    payload[copy_offset:copy_offset+4]=a.finish()
    allowed_changes=set(range(copy_offset,copy_offset+4))
    for action in (0x42,0xC,0xD,0xE,0x26,0x28):
        allowed_changes.update(range(0xA00+action*8,0xA00+action*8+8))
    assert all(a==b or i in allowed_changes
               for i,(a,b) in enumerate(zip(previous_payload,payload)))
    main['value'] = payload.hex()

    button_for_mask = {0x80:3, 0x10:4, 0x40:5, 0x20:2,
                       0x100:6, 0x200:9, 0x400:7, 0x800:10,
                       2:21, 0x4000:15, 0x8000:14, 0x4400:7}
    action_map = bytearray([255]*67)
    for action in list(range(0x2D))+[0x42]:
        mask, _ = struct.unpack_from('>II', payload, 0xA00+action*8)
        action_map[action] = button_for_mask.get(mask, 255)
    # Common gesture icons 0..16, derived from native 822DE7B8.
    common_map = bytes([3,6,4,10,3,3,10,2,2,14,15,14,10,4,21,9,5])

    tuner = bytearray(692)
    tuner[:4] = bytes.fromhex('4e800020')
    adapters = [(ACTION_ICON, 0x822DE720, ACTION_MAP, 66),
                (COMMON_ICON, 0x822DAE40, COMMON_MAP, 16)]
    for entry, hook, table, maximum in adapters:
        code = texture_adapter(entry, hook, table, maximum)
        off = entry-TUNER
        if any(tuner[off:off+len(code)]): raise RuntimeError('Adapter overlap')
        tuner[off:off+len(code)] = code
        a = Assembler(hook); a.branch(entry)
        patch['be32'].append({'address':hook, 'value':a.words[0]})
    tuner[ACTION_MAP-TUNER:ACTION_MAP-TUNER+67] = action_map
    tuner[COMMON_MAP-TUNER:COMMON_MAP-TUNER+17] = common_map
    patch['array'].append({'address':TUNER, 'value':tuner.hex()})
    patch['be32'].append({'address':0x821DB888, 'value':0x4E800020})

    # Contextual panels use separate texture paths. Native 8211CB48 maps
    # their slots to 1E/1F/20/21 and 2A/2B/28/29 respectively.
    # Tail calls preserve the call site's LR and all nonvolatile loop registers.
    hard_map = bytes([6,9,7,10,2,4,15,14,7,15,14])
    hard_table = 0x821DB7D0
    shared = 0x821DB740
    for entry, hook, kind in ((0x821DB700,0x822E4218,0),
                               (0x821DB710,0x822E3AF8,1),
                               (0x821DB720,0x822E0EEC,2)):
        a = Assembler(entry)
        if kind == 0: a.emit(0x7FC4F378)  # mr r4,r30: slot 0..3
        elif kind == 1: a.d(8,4,28,8)  # subfic r4,r28,8: slot 4..7
        else: a.lwz(4,0x78,31);a.d(14,4,4,8)  # defender gauge 8..10
        a.branch(shared)
        off=entry-TUNER;code=a.finish()
        assert not any(tuner[off:off+len(code)])
        tuner[off:off+len(code)]=code
        b=Assembler(hook);b.branch(entry,link=True)
        patch['be32'].append({'address':hook,'value':b.words[0]})
    a=Assembler(shared)
    a.pointer(11,0x82649134);a.lwz(11,0,11);a.cmp(11,0);a.jump('original')
    a.emit(0x7D635B78);a.pointer(11,hard_table)
    a.emit(0x7C8B20AE)  # lbzx r4,r11,r4
    a.branch(0x823498A8)
    a.label('original');a.li(4,0);a.branch(0x823498A8)
    code=a.finish();off=shared-TUNER
    assert not any(tuner[off:off+len(code)])
    tuner[off:off+len(code)]=code
    # Button lettering must not inherit a mirrored body gesture.
    entry=0x821DB790;a=Assembler(entry)
    a.lwz(11,0,8);a.li(10,-5);a.emit(0x7D6B5038)
    a.stw(11,0,8);a.li(3,0);a.emit(0x4E800020)
    code=a.finish();off=entry-TUNER
    assert not any(tuner[off:off+len(code)])
    tuner[off:off+len(code)]=code
    b=Assembler(0x822E4240);b.branch(entry,link=True)
    patch['be32'].append({'address':0x822E4240,'value':b.words[0]})
    tuner[hard_table-TUNER:hard_table-TUNER+len(hard_map)]=hard_map
    # Update the already registered array after filling the additional adapters.
    next(x for x in patch['array'] if x['address']==TUNER)['value']=tuner.hex()

    context_map = bytes([6,9,7,10,2,4,15,14,14,7,9,255,255,255,255,7,5,255,255,255,255])
    context_table = 0x821DB7E0
    tuner[context_table-TUNER:context_table-TUNER+len(context_map)] = context_map
    next(x for x in patch['array'] if x['address']==TUNER)['value']=tuner.hex()
    context_entry=0x825EB600
    assert not any(payload[0x500:0x580])
    a=Assembler(context_entry)
    a.lwz(11,0x24,3);a.lwz(9,0x10,3);a.emit(0x7C8B4A14)  # add r4,r11,r9
    context_code=a.finish()+texture_adapter(context_entry+12,0x822EBBB8,context_table,20)
    assert len(context_code)<=128
    patch['array'].append({'address':context_entry,'value':context_code.hex()})
    b=Assembler(0x822EBBB8);b.branch(context_entry)
    patch['be32'].append({'address':0x822EBBB8,'value':b.words[0]})

    OUT.mkdir(exist_ok=True)
    patch['name'] = 'Gamepad feedback revision 4, with optional all-content unlock'
    patch['desc'] = 'Experimental: finite first-person hand joints, sustained combo responses, hidden Kinect Tuner, native Xbox prompt textures.'
    text = '\n'.join(f'{k} = {json.dumps(data[k])}' for k in ('title_name','title_id','hash'))
    text += '\n\n[[patch]]\n'
    text += '\n'.join(f'{k} = {json.dumps(patch[k])}' for k in ('name','desc','author'))
    text += '\nis_enabled = true\n'
    for item in patch['be32']:
        text += f'\n[[patch.be32]]\naddress = 0x{item["address"]:08X}\nvalue = 0x{item["value"]:08X}\n'
    for item in patch['array']:
        text += f'\n[[patch.array]]\naddress = 0x{item["address"]:08X}\nvalue = "{item["value"]}"\n'
    output = OUT/'4E4D084E.gamepad-feedback.patch.toml'
    output.write_text(text)
    manifest = {'status':'development; requires separate CPU and gameplay evidence',
                'input_sha256':expected, 'patch_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                'original_regions':{hex(a):{'bytes':n,'sha256':hashlib.sha256(original(a,n)).hexdigest()}
                                    for a,n in ((TUNER,692),(0x821DB888,164),(0x822DE720,148),(0x822DAE40,48),(0x822EBBB8,132),(0x822E4218,4),(0x822E3AF8,4),(0x822E0EEC,4),(0x822E4240,4))},
                'button_texture_by_action':list(action_map),
                'first_person_joint_copy':{'source':'ctx+D0','destinations':['ctx+B80','ctx+1600']},'special_pose_icons_preserved':True,'contextual_texture_indices':list(hard_map),'extra_pose_texture_indices':list(context_map)}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(output)


if __name__ == '__main__': build()
