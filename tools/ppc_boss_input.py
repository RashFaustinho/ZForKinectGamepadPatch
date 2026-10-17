"""PowerPC bridge for boss consumers that read discrete recognizer states.

The game's runtime action table supplies the recognizer indices and types.
Only battle kind 1 is touched; inputs and normal super windows come from the
same binding table as the public action APIs. No progression flags are set.
"""
import struct

ENTRY=0x825ebe40

def build(target=0x825eb100,entry=ENTRY):
    words=[];labels={};fix=[]
    def emit(w):words.append(w)
    def d(op,rt,ra,imm):emit(op<<26|rt<<21|ra<<16|(imm&65535))
    def cmp(r,n):d(11,0,r,n)
    def jump(name,opcode=0x41820000):fix.append((len(words),name));emit(opcode)
    def branch(a,t):return 0x48000000|((t-a)&0x3fffffc)
    d(15,11,0,0x8265);d(32,11,11,-0x6d68);cmp(11,0);jump('out')
    d(32,11,11,0x54);cmp(11,0);jump('out');d(32,11,11,0xc);cmp(11,1)
    jump('out',0x40820000)
    d(15,11,0,0x8265);d(32,11,11,-0x6e28);cmp(11,0);jump('out')
    d(32,10,11,0x24);cmp(10,0);jump('out');d(14,12,11,0x30)
    # Several public actions share one native recognizer. Clear first, then
    # OR all active bindings; an inactive alias must not erase an active one.
    d(14,6,0,67);emit(0x7cc903a6)
    labels['clear']=len(words)
    d(32,8,12,0x10c);cmp(8,1);jump('clear_next',0x40820000)
    d(32,8,12,0);emit(0x280801a9);jump('clear_next',0x40800000)
    d(14,8,8,0x6bc);emit(0x5508103a);d(14,4,0,0)
    emit(0x7c00012e|(4<<21)|(10<<16)|(8<<11))
    labels['clear_next']=len(words);d(14,12,12,4);jump('clear',0x42000000)
    d(14,12,11,0x30)
    d(15,9,0,0x8265);d(32,9,9,-0x6f24);cmp(9,0);jump('out')
    d(32,9,9,0x98);cmp(9,0);jump('out')
    d(15,7,0,0x825f);d(14,7,7,-0x4500)
    d(14,6,0,67);emit(0x7cc903a6) # mtctr r6
    labels['loop']=len(words)
    d(32,8,12,0x10c);cmp(8,1);jump('next',0x40820000)
    d(32,8,12,0);emit(0x280801a9);jump('next',0x40800000) # unsigned index < 425
    d(14,8,8,0x6bc);emit(0x5508103a) # slwi r8,r8,2
    d(32,5,7,0);d(32,4,7,4)
    cmp(4,0x1000);jump('fire');cmp(4,0x1004);jump('pending')
    emit(0x7c00002e|(4<<21)|(9<<16)|(4<<11));jump('evaluate',0x48000000)
    labels['fire']=len(words);d(15,6,0,0x8267);d(32,4,6,-0x1e54);jump('evaluate',0x48000000)
    labels['pending']=len(words);d(15,6,0,0x8267);d(32,4,6,-0x1e50)
    labels['evaluate']=len(words);emit(0x7c000039|(4<<21)|(4<<16)|(5<<11))
    jump('next');d(14,4,0,3)
    emit(0x7c00012e|(4<<21)|(10<<16)|(8<<11))
    labels['next']=len(words);d(14,7,7,8);d(14,12,12,4)
    jump('loop',0x42000000)
    d(15,11,0,0x8267);d(32,7,11,-0x1e44);d(14,7,7,1);d(36,7,11,-0x1e44)
    labels['out']=len(words);emit(branch(entry+len(words)*4,target))
    for index,name in fix:
        delta=(labels[name]-index)*4
        if not -32768<=delta<=32764:raise ValueError('Mirror branch out of range')
        words[index]|=delta&0xfffc
    result=b''.join(struct.pack('>I',w) for w in words)
    if len(result)>0x2c0:raise ValueError('Mirror exceeds checked padding')
    return result
