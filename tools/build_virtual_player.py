"""Build a hash-checked experimental Xenia patch, without changing game files.

Experiments progress from player/identity fields to a controller action bridge.
The combat option is a development prototype, not a fully validated conversion.
"""
import hashlib
import argparse
import json
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN

ROOT=Path('/workspace/artifacts/zforkinect')
parser=argparse.ArgumentParser()
parser.add_argument('--pose',action='store_true',help='Supply a neutral tracked skeleton to investigate presence checks')
parser.add_argument('--postupdate',action='store_true',help='Inject after the Kinect update instead of before the input update')
parser.add_argument('--postlogic',action='store_true',help='Inject after the per-frame Kinect logic, including presence and edge events')
parser.add_argument('--selector',action='store_true',help='Replace the hand slide selector with pad edges (experimental)')
parser.add_argument('--combat',action='store_true',help='Experimentally translate action queries to pad buttons; requires --selector --postlogic')
parser.add_argument('--requested-layout',action='store_true',help='Use the user-requested Xbox layout, with stick-release super attacks')
parser.add_argument('--revised-layout',action='store_true',help='Preview 2: single-impulse supers, contextual X, extra gestures and hidden menu hands')
args=parser.parse_args()
if args.revised_layout:args.requested_layout=True
if args.selector and not args.postlogic:parser.error('--selector requires --postlogic')
if args.combat and not (args.selector and args.pose):parser.error('--combat requires --selector and --pose')
if args.requested_layout and not args.combat:parser.error('--requested-layout requires --combat')
if args.postlogic and args.postupdate:parser.error('Choose one injection phase')
REPO=Path(__file__).resolve().parents[1]
image=(ROOT/'analysis/Dbkn.image.bin').read_bytes()
xex=(ROOT/'analysis/default.xex').read_bytes()
if hashlib.sha256(xex).hexdigest()!='d09d3c36857d930279f2657188f0b135c27d22a39306178743d4e9becd42d438':
    raise SystemExit('Unsupported executable')
HOOK=0x82195550 if args.postlogic else (0x821B678C if args.postupdate else 0x82192D20)
CAVE=0x825EB100
SCRATCH=0x8266E180
expected_hook=struct.pack('>I',0x48000000|((0x8251D7D0-HOOK)&0x3fffffc)) if args.postupdate else bytes.fromhex('7d8802a6')
if args.postlogic:expected_hook=bytes.fromhex('817f0008')
if image[HOOK-0x82000000:HOOK-0x82000000+4]!=expected_hook:
    raise SystemExit('Hook instruction mismatch')
if any(image[CAVE-0x82000000:CAVE-0x82000000+4096]) or any(image[SCRATCH-0x82000000:SCRATCH-0x82000000+64]):
    raise SystemExit('Expected unused alignment padding is not empty')

words=[];labels={};fixups=[]
def emit(word):words.append(word)
def d(op,rt,ra,imm):emit((op<<26)|(rt<<21)|(ra<<16)|(imm&0xffff))
def li(rt,n):d(14,rt,0,n)
def lis(rt,n):d(15,rt,0,n)
def lwz(rt,n,ra):d(32,rt,ra,n)
def stw(rt,n,ra):d(36,rt,ra,n)
def ori(rt,rs,n):d(24,rs,rt,n)
def andi(rt,rs,n):d(28,rs,rt,n)
def andis(rt,rs,n):d(29,rs,rt,n)
def compare(rt,n):d(11,0,rt,n)
def beq(label):fixups.append((len(words),label));emit(0x41820000)
def label(name):labels[name]=len(words)
def branch(source,target):
    delta=target-source
    if delta%4 or not -0x2000000<=delta<0x2000000:raise ValueError('Branch out of range')
    return 0x48000000|(delta&0x03fffffc)

# All temporary GPRs and CR0 are volatile in the guest ABI. r3 and LR are kept.
lis(11,0x8267);lwz(9,-0x1e7c,11);d(14,9,9,1);stw(9,-0x1e7c,11)
lis(11,0x8265);lwz(11,-0x6e28,11);compare(11,0);beq('out')
lwz(10,0x1c,11);compare(10,0);beq('out')
lis(11,0x8267);stw(10,-0x1e78,11)
if args.pose:
    lwz(9,-0x1e7c,11);stw(9,0x88,10);stw(9,0x84,10)
    lis(9,0x3f80);stw(9,0x94,10);stw(9,0xa4,10)
    d(14,7,10,0xb0)
    lis(11,0x825f);d(14,11,11,-0x4700 if args.combat else -0x4b00)
    li(9,0x1c0//4);emit(0x7d2903a6)
    label('copy_skeleton')
    lwz(8,0,11);stw(8,0,7);d(14,11,11,4);d(14,7,7,4)
    fixups.append((len(words),'copy_skeleton'));emit(0x42000000)
    if args.combat:
        # The absent camera poll normally also fills this derived joint buffer.
        d(14,7,10,0xb80);d(14,11,10,0xd0)
        li(9,20*4);emit(0x7d2903a6)
        label('copy_derived_joints')
        lwz(8,0,11);stw(8,0,7);d(14,11,11,4);d(14,7,7,4)
        fixups.append((len(words),'copy_derived_joints'));emit(0x42000000)
li(9,2);stw(9,0xb0,10)
li(9,1);stw(9,0xb4,10);stw(9,0x2444,10)
if args.postupdate:stw(9,0x24e8,10)
li(9,0);stw(9,0xb8,10);stw(9,0x24e4,10)
li(9,8);stw(9,0x2440,10)
li(9,4);stw(9,0x2568,10)
lis(9,0x3f80);stw(9,0x2574,10)
if args.postlogic:
    # Active tracking ID (not controller index), and the presence grace counter.
    li(9,1);stw(9,0x2430,10)
    li(9,0);stw(9,0x27ac,10)
    if args.combat:
        # Camera-derived depth, lateral position, and body validity flags.
        # 27a4=4 means "back up" and prevents the start-punch gate from polling.
        stw(9,0x27a4,10);stw(9,0x27a8,10);stw(9,0x278c,10)
        lis(9,0x4020);stw(9,0x2788,10);stw(9,0x2790,10)
lis(11,0x8265);lwz(11,-0x6f24,11);compare(11,0);beq('out')
lwz(11,0x98,11);compare(11,0);beq('out');lwz(8,0x20,11)
lis(11,0x8267);stw(8,-0x1e74,11)
if args.requested_layout:
    # Keep a fire window for the multi-frame super-attack sequence.
    # Down/up timers at scratch+24/+28; synthesized fire flags at scratch+2c.
    if args.revised_layout:
        # Keep the follow-up gesture throughout the native super sequence,
        # including animations longer than the initial acceptance window.
        lis(9,0x8265);lwz(5,-0x6d28,9)
        lwz(4,-0x1e4c,11);stw(5,-0x1e4c,11)
        compare(5,10);beq('super_timers_ready')
        compare(4,10)
        fixups.append((len(words),'super_decrement'));emit(0x40820000)
        li(9,0);stw(9,-0x1e5c,11);stw(9,-0x1e58,11)
        label('super_decrement')
    for offset,name in ((-0x1e5c,'low'),(-0x1e58,'high')):
        lwz(9,offset,11);compare(9,0);beq('timer_zero_'+name)
        d(14,9,9,-1);stw(9,offset,11);label('timer_zero_'+name)
    if args.revised_layout:label('super_timers_ready')
    if args.revised_layout:
        # Admit a request only on the stick's rising edge, with enough Ki NOW.
        # There is no queued request on insufficient energy and no stick charge.
        # Ki is a native nonnegative float (0..100), so its bits sort as uints.
        lwz(6,-0x1e50,11) # Pending initiation bits, separate from follow-up bits.
        lis(9,0x8265);lwz(9,-0x6d28,9)
        compare(9,4);beq('super_interactive')
        compare(9,6);beq('super_interactive')
        li(6,0);compare(9,10)
        fixups.append((len(words),'super_impulses_done'));emit(0x40820000)
        # Scripted techniques/QTEs can request a gesture after Ki consumption.
        # In this mode an impulse supplies continuation only, never initiation.
        lis(9,0x8265);lwz(9,-0x6f24,9);lwz(9,0x98,9);lwz(8,0x28,9)
        for mask,offset,name in ((2,-0x1e5c,'low'),(1,-0x1e58,'high')):
            andis(9,8,mask);beq('no_continuation_'+name)
            li(9,300);stw(9,offset,11);label('no_continuation_'+name)
        fixups.append((len(words),'super_impulses_done'));emit(0x48000000)
        label('super_interactive')
        li(7,0);lis(9,0x8265);lwz(9,-0x6d68,9)
        compare(9,0);beq('super_energy_ready')
        lwz(9,0x54,9);compare(9,0);beq('super_energy_ready');lwz(7,0x868,9)
        label('super_energy_ready')
        lis(9,0x8265);lwz(9,-0x6f24,9);lwz(9,0x98,9);lwz(8,0x28,9)
        for mask,offset,name,threshold in ((2,-0x1e5c,'low',0x4248),(1,-0x1e58,'high',0x42c8)):
            andis(9,8,mask);beq('no_impulse_'+name)
            li(9,0);stw(9,offset,11)
            lis(9,threshold);emit(0x7c000040|(7<<16)|(9<<11)) # cmplw r7,r9
            fixups.append((len(words),'no_impulse_'+name));emit(0x41800000) # blt
            li(9,300);stw(9,offset,11);d(25,6,6,mask);label('no_impulse_'+name)
        label('super_impulses_done')
    else:
        lis(9,0x8265);lwz(9,-0x6f24,9);lwz(9,0x98,9);lwz(8,0x2c,9)
        for mask,offset,name in ((2,-0x1e5c,'low'),(1,-0x1e58,'high')):
            andis(9,8,mask);beq('no_release_'+name);li(9,300);stw(9,offset,11);label('no_release_'+name)
        # A new hold cancels any previous release window for that direction.
        lis(9,0x8265);lwz(9,-0x6f24,9);lwz(9,0x98,9);lwz(8,0x20,9)
        for mask,offset,name in ((2,-0x1e5c,'low'),(1,-0x1e58,'high')):
            andis(9,8,mask);beq('not_held_'+name);li(9,0);stw(9,offset,11);label('not_held_'+name)
    li(7,0)
    for mask,offset,name in ((2,-0x1e5c,'low'),(1,-0x1e58,'high')):
        lwz(9,offset,11);compare(9,0);beq('no_fire_'+name)
        d(25,7,7,mask);label('no_fire_'+name)
    stw(7,-0x1e54,11)
    if args.revised_layout:
        emit(0x7cc63838) # and r6,r6,r7: expire initiation with the window.
        stw(6,-0x1e50,11)
if args.postlogic:
    # Menu actions are edges, so holding A cannot confirm multiple screens.
    lis(11,0x8265);lwz(11,-0x6f24,11);lwz(11,0x98,11);lwz(8,0x28,11)
li(9,0)
for mask,flag,name in ((0x40,4,'a'),(0x1000,1,'up'),(0x2000,2,'down')):
    andi(11,8,mask);beq('skip_'+name);ori(9,9,flag);label('skip_'+name)
stw(9,0x2780,10);li(9,0)
if args.selector:
    andi(11,8,0x20);beq('not_back');li(9,4);label('not_back')
stw(9,0x2784,10)
label('out')
if args.postlogic:lwz(11,8,31);emit(branch(CAVE+len(words)*4,HOOK+4))
elif args.postupdate:emit(branch(CAVE+len(words)*4,0x8251D7D0))
else:emit(0x7d8802a6);emit(branch(CAVE+len(words)*4,HOOK+4))
selector_address=None
combat_entries={}
if args.selector:
    selector_address=CAVE+len(words)*4
    if image[0x11a720:0x11a724]!=bytes.fromhex('7d8802a6'):raise SystemExit('Selector hook mismatch')
    # r3 points to the selector payload: count+4, current index+34,
    # state+2c, slide progress+40. This replacement has no stack or calls.
    if args.revised_layout:
        # A back-only selector has count=0, so B must precede that early exit.
        # Types 0/1 have no native left-hand return area; type 2 supports it.
        lis(11,0x8265);lwz(11,-0x6f24,11);compare(11,0);beq('selector_return')
        lwz(11,0x98,11);compare(11,0);beq('selector_return');lwz(8,0x28,11)
        andi(11,8,0x20);beq('selector_not_back')
        lwz(9,0,3);compare(9,2)
        fixups.append((len(words),'selector_not_back'));emit(0x41800000)
        li(9,4);stw(9,0x2c,3);lis(9,0x3f80);stw(9,0x40,3);emit(0x4e800020)
        label('selector_not_back')
    lwz(7,4,3);compare(7,0);beq('selector_return')
    lwz(9,0x34,3)
    emit(0x7c000040|(9<<16)|(7<<11)) # cmplw r9,r7
    fixups.append((len(words),'selector_valid'));emit(0x41800000) # blt
    li(9,0)
    label('selector_valid')
    lis(11,0x8265);lwz(11,-0x6f24,11);compare(11,0);beq('selector_return')
    lwz(11,0x98,11);compare(11,0);beq('selector_return');lwz(8,0x28,11)
    andi(11,8,0x1000);beq('selector_not_up')
    compare(9,0)
    fixups.append((len(words),'selector_up_nonzero'));emit(0x40820000)
    emit(0x7ce93b78) # mr r9,r7
    label('selector_up_nonzero');d(14,9,9,-1)
    label('selector_not_up')
    andi(11,8,0x2000);beq('selector_not_down');d(14,9,9,1)
    emit(0x7c000040|(9<<16)|(7<<11))
    fixups.append((len(words),'selector_not_down'));emit(0x41800000)
    li(9,0)
    label('selector_not_down');stw(9,0x34,3)
    li(9,1);stw(9,0x2c,3);li(9,0);stw(9,0x40,3)
    andi(11,8,0x40);beq('selector_return')
    li(9,2);stw(9,0x2c,3);lis(9,0x3f80);stw(9,0x40,3)
    label('selector_return');emit(0x4e800020)
if args.combat:
    for address in (0x82197118,0x82197250):
        if image[address-0x82000000:address-0x82000000+4]!=bytes.fromhex('7d8802a6'):raise SystemExit('Action API hook mismatch')
    combat_entries[0x82197118]=CAVE+len(words)*4
    li(6,0);fixups.append((len(words),'action_common'));emit(0x48000000)
    combat_entries[0x82197250]=CAVE+len(words)*4
    li(6,1)
    label('action_common')
    # Two public action-query entry points, sharing one input table.
    # A table entry stores the internal pad mask and held/edge field offset.
    li(7,0);emit(0x28040042)
    fixups.append((len(words),'action_result'));emit(0x41810000) # bgt
    lis(11,0x8267);stw(4,-0x1e70,11)
    lwz(9,-0x1e68,11);d(14,9,9,1);stw(9,-0x1e68,11)
    lis(11,0x8265);lwz(11,-0x6f24,11);compare(11,0);beq('action_result')
    lwz(11,0x98,11);compare(11,0);beq('action_result')
    emit(0x54881838) # slwi r8,r4,3
    lis(9,0x825f);d(14,9,9,-0x4500)
    emit(0x7d294214) # add r9,r9,r8
    lwz(8,0,9);lwz(9,4,9)
    if args.requested_layout:
        # At ranged distance, the native normal-shot dispatcher polls action 0.
        # Keep menu A and close-range X separate, and allow A for this context.
        if not args.revised_layout:
            compare(4,0)
            fixups.append((len(words),'action_context_done'));emit(0x40820000)
            lis(7,0x8265);lwz(7,-0x6d28,7);compare(7,6)
            fixups.append((len(words),'action_context_done'));emit(0x40820000)
            ori(8,8,0x40)
            label('action_context_done');li(7,0)
        compare(9,0x1000)
        fixups.append((len(words),'action_normal_source'));emit(0x40820000)
        lis(11,0x8267);lwz(9,-0x1e54,11)
        fixups.append((len(words),'action_apply_mask'));emit(0x48000000)
        label('action_normal_source')
        if args.revised_layout:
            compare(9,0x1004)
            fixups.append((len(words),'action_pad_source'));emit(0x40820000)
            lis(11,0x8267);lwz(9,-0x1e50,11)
            fixups.append((len(words),'action_apply_mask'));emit(0x48000000)
            label('action_pad_source')
    emit(0x7d2b482e) # lwzx r9,r11,r9
    if args.requested_layout:label('action_apply_mask')
    emit(0x7d294039) # and. r9,r9,r8
    beq('action_result');li(7,3)
    lis(11,0x8267);stw(4,-0x1e64,11)
    lwz(9,-0x1e60,11);d(14,9,9,1);stw(9,-0x1e60,11)
    label('action_result')
    lis(11,0x8267);stw(7,-0x1e6c,11)
    compare(6,0);beq('action_integer')
    lis(11,0x820e);d(48,1,11,0x6c1c)
    emit(0x7ce72839) # and. r7,r7,r5
    beq('action_return');d(48,1,11,0x6c70)
    label('action_return');emit(0x4e800020)
    label('action_integer');emit(0x7ce33b78);emit(0x4e800020) # mr r3,r7; blr
hand_entry=None
if args.revised_layout:
    # Only the menu hand position getter is replaced. Its caller copies these
    # coordinates into the two hand widgets; pad selection uses another hook.
    if image[0x1dc5b0:0x1dc5b4]!=bytes.fromhex('3d608265'):
        raise SystemExit('Menu hand coordinate hook mismatch')
    hand_entry=CAVE+len(words)*4
    lis(9,0xc580) # -4096.0f, outside the 1280x720 menu canvas
    for offset in (0,4,8,12):stw(9,offset,4)
    emit(0x4e800020)
for index,target in fixups:
    delta=(labels[target]-index)*4
    if not -32768<=delta<=32764:raise ValueError('Conditional branch out of range')
    words[index]|=delta&0xfffc
code=b''.join(struct.pack('>I',word) for word in words)
decoder=Cs(CS_ARCH_PPC,CS_MODE_32|CS_MODE_BIG_ENDIAN)
instructions=list(decoder.disasm(code,CAVE))
if len(instructions)!=len(words):raise SystemExit('Generated instruction stream did not disassemble completely')
payload=code
if args.pose:
    skeleton=bytearray(0x1c0)
    struct.pack_into('>IIII',skeleton,0,2,1,0,0)
    struct.pack_into('>4f',skeleton,16,0.,0.,2.5,1.)
    joints=[(0,0,2.5),(0,.3,2.5),(0,.6,2.5),(0,.9,2.5),(-.2,.6,2.5),(-.35,.3,2.5),(-.35,.05,2.5),(-.35,0,2.5),(.2,.6,2.5),(.35,.3,2.5),(.35,.05,2.5),(.35,0,2.5),(-.13,0,2.5),(-.13,-.45,2.5),(-.13,-.85,2.5),(-.13,-.9,2.4),(.13,0,2.5),(.13,-.45,2.5),(.13,-.85,2.5),(.13,-.9,2.4)]
    for index,position in enumerate(joints):
        struct.pack_into('>4f',skeleton,32+index*16,*position,1.)
        struct.pack_into('>I',skeleton,0x160+index*4,2)
    pose_offset=0x800 if args.combat else 0x400
    if len(code)>pose_offset:raise SystemExit('Generated code overlaps the neutral pose')
    payload=code+bytes(pose_offset-len(code))+skeleton
bindings=[]
if args.combat:
    EDGE=0x28;HELD=0x20
    bindings=[(0,EDGE)]*67
    def bind(indices,mask,source=EDGE):
        for index in indices:bindings[index]=(mask,source)
    bind([0,0x13],0x80);bind([1,4],0x200000);bind([2,0x10,0x11,0x12,0x2f],0x40)
    bind([3,6],0x200,HELD);bind([5,7,0x17,0x29],0x800)
    bind([8,0xa],0x100,HELD);bind([9],0x20)
    bind([0xb,0x14,0x24,0x2a,0x2b,0x2c],0x20,HELD)
    bind([0xc,0x19],0x8000);bind([0x42,0x18],0x4000)
    bind([0xd,0x26],0x1000);bind([0xe,0x25,0x28],0x2000)
    bind([0xf],0x400,HELD);bind([0x15,0x1e,0x1f,0x20,0x21,0x22,0x23],0x200000)
    bind([0x1a],0x1000,HELD);bind([0x27],0x40)
    bind([0x16,0x1b,0x1d,0x2d,0x30,0x31,0x34,0x35,0x38,0x39,0x3c,0x3f],0x100,HELD)
    bind([0x1c,0x2e,0x32,0x37,0x3a,0x3b,0x3d,0x40,0x41],0x200)
    bind([0x33,0x36,0x3e],0x100)
    if args.requested_layout:
        RELEASE_WINDOW=0x1000
        bindings=[(0,EDGE)]*67
        bind([0,0x13],0x80) # X: jab / hook, according to combat phase.
        bind([2,0x10,0x12],0x10) # Y: kick.
        bind([5,7],0x40) # Normal shot; action 0 also accepts A at ranged distance.
        bind([0xb,0xc,0x14,0x24,0x2a,0x2c],0x20,HELD)
        bind([9],0x20)
        bind([0x19],0x8000);bind([0x42,0x18],0x4000)
        bind([0xd,0x26,0x28],0x4000);bind([0xe,0x25,0x29],0x8000)
        # Consumer 822241A0 enters native energy charging via action 11.
        # Super directions charge here too, but launch only on release below.
        bind([0x11],0x30002,HELD)
        bind([0x2b],0x10) # Contextual side kick.
        bind([0x2d,0x2e,0x2f,0x30],0x20000,RELEASE_WINDOW)
        bind([0x1b,0x1c,0x1d,0x31,0x32,0x33,0x34],0x10000,RELEASE_WINDOW)
        if args.revised_layout:
            bind([0,5,7,0x13,0x17],0x80) # Native close/ranged dispatcher chooses X's action.
            bind([2,0x10,0x2b],0x10) # Y retains the user's observed uppercut.
            bind([0x12,0x27],0x40) # Native rush/approach request; A is free in battle.
            bind([1,0x15,0x1e],0x100) # Additional basic strike / contextual choice.
            bind([4,0x1f],0x200) # Additional basic strike / contextual choice.
            bind([3,6,8,0xa],0x800,HELD) # Native charged attacks, by distance.
            bind([0xf,0x16,0x22],0x800,HELD)
            bind([0x1a],0x40,HELD) # Boss running gesture.
            bind([0x18],0x4000,HELD)
            # Boss consumers 8223C428/8223CFE0: 19 charges Ki; 1B/1C
            # choose the two lateral moves (-1.6/+1.6), independently of supers.
            bind([0x19],2,HELD)
            bind([0x1b],0x4000);bind([0x1c],0x8000)
            bind([0x1d],0x800,HELD) # Boss scripted preparation/charge gesture, independent of normal supers.
            bind([0x20,0x23,0x28],0x400) # Contextual avoidance / third strike choice.
            bind([0x26],0x4400) # Preserve left and add LT for contextual prompt.
            bind([0x21],0x800) # Fourth contextual strike choice.
            bind([0x24],0x200,HELD) # Second approach-clash response.
            bind([0x11],2,HELD) # Preserve the proven D-pad aura charge only.
            bind(list(range(0x35,0x42)),0x10000,RELEASE_WINDOW)
            # Once the native sequence enters a cinematic, initiation clears;
            # follow-ups remain available without repeating the original cast.
            bind([0x2d],0x20000,0x1004)
            bind([0x31,0x35],0x10000,0x1004)
    table=b''.join(struct.pack('>II',*binding) for binding in bindings)
    payload+=bytes(0xa00-len(payload))+table
out=REPO/('experiments/gamepad-layout-v2' if args.revised_layout else ('experiments/gamepad-layout' if args.requested_layout else ('experiments/virtual-player-combat' if args.combat else ('experiments/virtual-player-selector' if args.selector else ('experiments/virtual-player-postlogic' if args.postlogic else ('experiments/virtual-player-post' if args.postupdate else ('experiments/virtual-player-pose' if args.pose else 'experiments/virtual-player')))))))
out.mkdir(parents=True,exist_ok=True)
boss_payload=b''
if args.revised_layout:
    from ppc_boss_input import ENTRY as BOSS_ENTRY,build as build_boss_input
    from ppc_boss_qte import ENTRY as QTE_ENTRY, HOOK as QTE_HOOK, build as build_boss_qte
    from ppc_storage import ENTRY as STORAGE_ENTRY, build as build_storage
    boss_payload=build_boss_input(CAVE)
    boss_instructions=list(decoder.disasm(boss_payload,BOSS_ENTRY))
    if len(boss_instructions)*4!=len(boss_payload):raise SystemExit('Boss bridge did not disassemble completely')
    if BOSS_ENTRY<CAVE+len(payload):raise SystemExit('Boss bridge overlaps the main payload')
    (out/'boss-recognizers.asm').write_text('\n'.join(f'{i.address:08X} {i.mnemonic} {i.op_str}' for i in boss_instructions)+'\n')
    qte_payload=build_boss_qte()
    if image[QTE_HOOK-0x82000000:QTE_HOOK-0x82000000+4]!=bytes.fromhex('3d608265'):
        raise SystemExit('Boss QTE input hook mismatch')
    qte_offset=QTE_ENTRY-CAVE
    if any(payload[qte_offset:qte_offset+len(qte_payload)]) or qte_offset+len(qte_payload)>0x680:
        raise SystemExit('Boss QTE adapter overlaps an existing payload or diagnostic selector')
    qte_instructions=list(decoder.disasm(qte_payload,QTE_ENTRY))
    if len(qte_instructions)*4!=len(qte_payload):raise SystemExit('Invalid boss QTE adapter')
    (out/'boss-qte.asm').write_text('\n'.join(f'{i.address:08X} {i.mnemonic} {i.op_str}' for i in qte_instructions)+'\n')
    payload=payload[:qte_offset]+qte_payload+payload[qte_offset+len(qte_payload):]
    storage_payload=build_storage()
    if image[STORAGE_ENTRY-0x82000000:STORAGE_ENTRY-0x82000000+4]!=bytes.fromhex('7d8802a6'):
        raise SystemExit('Storage-selector hook mismatch')
    if len(storage_payload)>0xa0:raise SystemExit('Storage adapter exceeds original function')
patch='''title_name = "Dragon Ball Z for Kinect - experimental virtual player"
title_id = "4E4D084E"
hash = "C9561ED1F9AFFED4"

[[patch]]
name = "EXPERIMENT: virtual player and title A confirmation"
desc = "Unvalidated development experiment; not a finished combat/gamepad patch."
author = "ZForKinectGamepadPatch"
is_enabled = true

[[patch.be32]]
address = 0x%08X
value = 0x%08X

[[patch.array]]
address = 0x%08X
value = "%s"

[[patch.array]]
address = 0x%08X
value = "%s"
'''%(HOOK,branch(HOOK,BOSS_ENTRY if args.revised_layout else CAVE),CAVE,payload.hex(),SCRATCH,(b'PAD1'+bytes(60)).hex())
if boss_payload:
    patch+='\n[[patch.array]]\naddress = 0x%08X\nvalue = "%s"\n'%(BOSS_ENTRY,boss_payload.hex())
    patch+='\n[[patch.be32]]\naddress = 0x%08X\nvalue = 0x%08X\n'%(QTE_HOOK,branch(QTE_HOOK,QTE_ENTRY))
    patch+='\n[[patch.array]]\naddress = 0x%08X\nvalue = "%s"\n'%(STORAGE_ENTRY,storage_payload.hex())
if selector_address:
    patch+='\n[[patch.be32]]\naddress = 0x8211A720\nvalue = 0x%08X\n'%branch(0x8211A720,selector_address)
for address,target in combat_entries.items():
    patch+='\n[[patch.be32]]\naddress = 0x%08X\nvalue = 0x%08X\n'%(address,branch(address,target))
if hand_entry:
    patch+='\n[[patch.be32]]\naddress = 0x821DC5B0\nvalue = 0x%08X\n'%branch(0x821DC5B0,hand_entry)
if args.combat:patch=patch.replace('EXPERIMENT: virtual player and title A confirmation','EXPERIMENT: controller action bridge')
(out/'4E4D084E.virtual-player.patch.toml').write_text(patch)
(out/'generated.asm').write_text('\n'.join(f'{i.address:08X} {i.mnemonic} {i.op_str}' for i in instructions)+'\n')
if bindings:(out/'bindings.json').write_text(json.dumps([{'action':i,'pad_mask':hex(mask),'source':({HELD:'held',EDGE:'pressed',0x1000:'super impulse window' if args.revised_layout else 'super release window',0x1004:'pending super initiation'}[source])} for i,(mask,source) in enumerate(bindings)],indent=2)+'\n')
manifest={'status':'experimental, unvalidated','hook':hex(HOOK),'code_cave':hex(CAVE),'diagnostic_data':hex(SCRATCH),'code_bytes':len(code),'original_xex_sha256':hashlib.sha256(xex).hexdigest(),'purpose':('Experimental action API mapping; individual combat actions require gameplay verification' if args.combat else 'Test logical player fields and menu confirmation; combat not implemented')}
if args.revised_layout:
    manifest['status']='experimental; see separate CPU, runtime and gameplay validation files'
    manifest.update(main_code_bytes=len(code),code_bytes=len(code)+len(boss_payload),
                    boss_recognizers={'entry':hex(BOSS_ENTRY),'bytes':len(boss_payload),
                                      'scope':'battle kind 1 only','runtime_registration':True})
    manifest['boss_qte']={'entry':hex(QTE_ENTRY),'hook':hex(QTE_HOOK),'bytes':len(qte_payload),
                          'input':'RT held for native type-6 accumulation; no outcome override'}
    manifest['code_bytes']+=len(qte_payload)
    manifest['storage']={'entry':hex(STORAGE_ENTRY),'bytes':len(storage_payload),
                         'scope':'Xenia simulated HDD device 1; requires a signed-in game user'}
    manifest['code_bytes']+=len(storage_payload)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Generated experimental patch:',out,'instructions:',len(words),'bytes:',len(code))
