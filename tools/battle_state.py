"""Read the two combatants' HP from this game's verified European build."""
import argparse
import json
import socket
import struct
from pathlib import Path

endpoint=None

def display_name():
    metadata=endpoint.parent/'display.json'
    value=json.loads(metadata.read_text())['display'] if metadata.exists() else ':99'
    if not value.startswith(':') or not value[1:].isdigit():raise ValueError('Invalid session display')
    return value

def input_lock_path():
    display=display_name()
    return endpoint.parent.parent/('input-probe.lock' if display==':99' else 'input-probe-'+display[1:]+'.lock')

def connect(session):
    global endpoint
    if not session.replace('-', '').replace('_', '').isalnum():
        raise ValueError('Invalid session name')
    endpoint=Path('/workspace/artifacts/zforkinect/runtime')/session/'control.sock'


def read(address,size):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(10)
        client.connect(str(endpoint))
        client.sendall(json.dumps({'command':'read','address':hex(address),'size':size}).encode()+b'\n')
        data=b''
        while not data.endswith(b'\n'):
            part=client.recv(65536)
            if not part:raise RuntimeError('Supervisor disconnected')
            data+=part
    response=json.loads(data)
    if not response['ok']:raise RuntimeError(response)
    result=bytes.fromhex(response['hex'])
    if len(result)!=size:raise RuntimeError('Short guest read')
    return result


def word(address):return int.from_bytes(read(address,4),'big')


def sample():
    owner=word(0x82649298)
    if not owner:raise SystemExit('Battle manager not allocated')
    context=word(owner+0x54)
    if not context:raise SystemExit('Battle context not allocated')
    kind=word(context+0xc)
    result={'context':hex(context),'battle_kind':kind,'players':[]}
    for index in range(2):
        block=context+index*0x800
        maximum=word(block+0xc0)
        current=struct.unpack('>f',read(block+0x1bc,4))[0]
        energy=struct.unpack('>f',read(block+0x868,4))[0]
        actor=word(context+0x2fc0+index*4)
        item={'index':index,'maximum_hp':maximum,'hp':current,'energy':energy,'actor':hex(actor)}
        if actor and kind==1:
            # The boss uses another actor layout. +2530 is a handler pointer,
            # not last_action; +2580 is not a valid normal-controller pointer.
            if index==0:
                item.update(state=word(actor+0x1130),pending_state=word(actor+0x113c),
                            position=list(struct.unpack('>4f',read(actor+0x40,16))),
                            input_suppressed=0, input_suppression_available=False)
        elif actor:
            control=word(actor+0x2580)
            item['last_action']=word(actor+0x2530)
            item['last_action_side']=word(actor+0x2538)
            item['state']=word(actor+0x1130)
            item['pending_state']=word(actor+0x113c)
            item['last_action_progress']=struct.unpack('>f',read(actor+0x253c,4))[0]
            item['position']=list(struct.unpack('>4f',read(actor+0x40,16)))
            item['control']=hex(control)
            if control:
                item['control_flags']=word(control+0x84)
                item['charge_flags']=word(control+0x88)
                item['input_suppressed']=word(control+0x264)
                item['first_person_enabled']=word(control+0x80)
                item['native_draw_delay']=read(control+0x21A,1)[0]
                item['native_arm_cull_flags']=word(control+0x220)
        result['players'].append(item)
    result['mode']=word(0x826492d8)
    if kind==1:
        phase=word(context+0x2fcc)
        if phase:
            index=word(phase+0xc);count=word(phase+0x14)
            result['boss_phase']={'index':index,'count':count}
            if index<count:
                result['boss_phase']['record']=read(word(phase+4)+index*0x54,0x54).hex()
    diagnostic=read(0x8266e180,48)
    if diagnostic[:4]==b'PAD1':
        values=struct.unpack('>12I',diagnostic)
        result['bridge']={'frame':values[1], 'held':hex(values[3]),
                          'last_query':hex(values[4]), 'last_result':values[5],
                          'last_active_query':hex(values[7]),
                          'lower_release_frames':values[9],
                          'upper_release_frames':values[10],
                          'release_flags':hex(values[11])}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    args=parser.parse_args()
    connect(args.session)
    print(json.dumps(sample()))
