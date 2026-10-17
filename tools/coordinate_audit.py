"""Read typed geometric fields used by this game's virtual-player actions.

No memory writes. A finite value is a data-integrity check, not proof that a
motion or QTE is playable. Unknown structure fields are deliberately excluded.
"""
import argparse
import json
import math
import socket
import struct
from pathlib import Path
import battle_state as b


def request(payload):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(10);s.connect(str(b.endpoint));s.sendall(json.dumps(payload).encode()+b'\n')
        raw=b''
        while not raw.endswith(b'\n'):raw+=s.recv(65536)
    result=json.loads(raw)
    if not result['ok']:raise RuntimeError(result)
    return result


def snapshot():
    regions=[]
    def region(name,address,count,source):
        raw=b.read(address,count*4);values=struct.unpack('>'+str(count)+'f',raw)
        invalid=[{'offset':hex(i*4),'bits':raw[i*4:i*4+4].hex()} for i,x in enumerate(values) if not math.isfinite(x)]
        regions.append({'name':name,'address':hex(address),'source':source,
                        'values':[x if math.isfinite(x) else None for x in values],
                        'invalid':invalid,'finite':not invalid})
    manager=b.word(0x826491D8)
    if not manager:raise RuntimeError('NUI manager not initialized')
    context=b.word(manager+0x1C);processor=b.word(manager+0x20)
    region('raw_root',context+0xC0,4,'virtual raw skeleton')
    for name,offset in (('raw_joints',0xD0),('derived_joints',0xB80),('tracked_joints_getter',0x1600)):
        region(name,context+offset,80,'20 joints; 821B7090 selects the last buffer for tracking ID 1')
    if processor:
        for offset in (0x100,0x140,0x180,0x1C0,0x200,0x240):
            region('body_basis_'+hex(offset),processor+offset,16,'82199D38: shoulder and hip coordinate frames')
        for offset in (0x530,0x550,0x570,0x590,0x5B0,0x5D0,0x5F0,0x610,0x630,0x650):
            region('joint_history_'+hex(offset),processor+offset,8,'82199D38 / 821A1C70: filtered joint pairs')
        for offset in (0x740,0x750,0x760,0x770,0x780,0x790,0x7A0,0x7B0,0x7C0,0x7D0,0x7E0,0x7F0,0x800,0x810):
            region('hand_motion_'+hex(offset),processor+offset,4,'82199D38; 822A3A10 reads hand positions at 740/750')
        for offset in (0xF20,0xF40,0xF60,0xF80,0xFA0):
            region('limb_direction_'+hex(offset),processor+offset,4,'82199D38: normalized limb directions')
        for offset in (0xFD0,0xFD8):
            region('limb_angle_'+hex(offset),processor+offset,1,'82199D38 / 821A2BE8: limb angle')
    bases=[]
    for item in regions:
        if item['name'].startswith('body_basis'):
            v=item['values']
            if item['finite']:
                x,y,z=[v[i:i+3] for i in (0,4,8)]
                det=x[0]*(y[1]*z[2]-y[2]*z[1])-x[1]*(y[0]*z[2]-y[2]*z[0])+x[2]*(y[0]*z[1]-y[1]*z[0])
                norms=[math.sqrt(sum(t*t for t in row)) for row in (x,y,z)]
                bases.append({'name':item['name'],'determinant':det,'axis_norms':norms,'nondegenerate':abs(det)>1e-6 and all(t>1e-6 for t in norms)})
    camera_owner=b.word(0x826493A8)
    camera=b.word(camera_owner+0x234) if camera_owner else 0
    if camera:region('camera_transform',camera+0x50,16,'822D9928: camera transform used by first-person rendering')
    state=None
    try:state=b.sample()
    except SystemExit:pass
    if state:
        for actor in state['players']:
            address=int(actor['actor'],16)
            if not address or (state['battle_kind']==1 and actor['index']!=0):continue
            region('actor_'+str(actor['index'])+'_position',address+0x40,4,'native battle actor')
            if state['battle_kind']==0 and actor.get('control') and int(actor['control'],16):
                control=int(actor['control'],16)
                for offset in (0x90,0xD0):
                    region('first_person_arm_'+hex(offset),control+offset,16,'822D9060 transforms; 822A4CB0 projectile origin')
        if state['battle_kind']==0:
            effect_owner=b.word(0x82649164)
            effect_base=b.word(effect_owner) if effect_owner else 0
            if effect_base:
                for actor in state['players']:
                    address=int(actor['actor'],16)
                    if not address:continue
                    slots=b.read(address+0x11F0,0xEEC)
                    for slot in range(50):
                        ident,kind=struct.unpack_from('>ii',slots,8+slot*0x4C)
                        if 0<=ident<2048 and 0<=kind<=3:
                            effect=effect_base+ident*0xA10
                            prefix='projectile_'+str(actor['index'])+'_'+str(slot)
                            region(prefix+'_spawn_position',effect+0x7B0,4,'native projectile descriptor spawn position at 780+30')
                            region(prefix+'_cached_direction',effect+0x350,4,'native active effect direction vector')
                            region(prefix+'_direction',effect+0x7C0,4,'native projectile descriptor direction at 780+40')
                            region(prefix+'_speed_size',effect+0x7D8,2,'native projectile descriptor speed and size at 780+58')
        ui_owner=b.word(0x82649298)
        ui=b.word(ui_owner+0x64) if ui_owner else 0
        if state['battle_kind']==1:
            qte=b.word(int(state['context'],16)+0x2FD0)
            if qte:region('boss_qte_progress',qte+0x44,1,'8211A430: native type-6 QTE accumulator')
        if ui and state['battle_kind']==0:
            for offset in (0x40,0x44):
                gauge=b.word(ui+offset)
                if gauge:
                    for field in (0x64,0x7C,0x80):
                        region('combo_gauge_'+hex(offset)+'_'+hex(field),gauge+field,1,'native gauge progress and per-frame increments')
    return {'state':state,'regions':regions,'body_bases':bases,'bases_nondegenerate':all(x['nondegenerate'] for x in bases),'all_finite':all(x['finite'] for x in regions),
            'invalid_regions':[x['name'] for x in regions if not x['finite']],
            'joint_buffers_equal':b.read(context+0xB80,320)==b.read(context+0x1600,320)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('session');p.add_argument('name');p.add_argument('--pause',action='store_true')
    a=p.parse_args();b.connect(a.session)
    if not a.name.replace('-','').replace('_','').isalnum():p.error('Invalid capture name')
    out=b.endpoint.parent/(a.name+'.json')
    if out.exists():raise RuntimeError('Capture exists')
    if a.pause:request({'command':'pause'})
    result=snapshot();result['atomic_paused_capture']=a.pause
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'path':str(out),'regions':len(result['regions']),
                      'all_finite':result['all_finite'],'invalid_regions':result['invalid_regions']}))

if __name__=='__main__':main()
