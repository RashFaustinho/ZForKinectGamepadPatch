"""Read loaded battle panel textures and native child draw order; never write."""
import argparse,json,struct
import battle_state as b
p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');p.add_argument('name');a=p.parse_args();b.connect(a.session)
if not a.name.replace('-','').isalnum():p.error('Invalid report name')
def pointer(v):return 0x90000000<=v<0xD0000000
def name(addr):return b.read(addr,80).split(b'\0')[0].decode(errors='replace') if pointer(addr) else ''
loader=b.word(0x82649134);table=b.word(loader+0xDC);buttons={b.word(table+i*4):i for i in range(34)}
labels={2:'B',3:'X',4:'Y',5:'A',6:'LB',7:'LT',9:'RB',10:'RT',14:'LS right',15:'LS left',16:'RS up',17:'RS down',21:'D-pad down'}
ui=b.word(b.word(0x82649298)+0x64);rows=[];seen=set()
for off in range(0xC,0xD0,4):
 widget=b.word(ui+off)
 if not pointer(widget) or not 0x82000000<=b.word(widget)<0x82110000:continue
 for slot in range(0x34,0x48,4):
  panel=b.word(widget+slot)
  direct_super=off in (0x5C,0x60,0x64) and slot==0x40
  if not pointer(panel) or panel in seen or (not direct_super and b.word(panel)!=0x820E7A14):continue
  seen.add(panel);layout=b.word(panel+4)
  if not pointer(layout):continue
  pool=b.word(layout+0x14)
  if not pointer(pool):continue
  count=b.word(pool+12);items=b.word(pool+8)
  if not pointer(items) or not 0<count<1024:continue
  root=None;icon=None
  for i in range(count):
   part=b.word(items+i*4)
   if not pointer(part):continue
   n=name(b.word(part+0xD4))
   if n=='i_pl_grp':root=part
   if n=='p_ico_dummy_000':icon=part
  if not root or not icon:continue
  children=b.word(root+0xB8);entries=b.word(children+8);n=int.from_bytes(b.read(children+12,2),'big')
  if n>64:continue
  order=[]
  for i in range(n):
   child=b.word(entries+i*12+4)
   if not pointer(child):continue
   order.append({'index':i,'name':name(b.word(child+0xD4)),'flags':hex(b.word(child+0xD0)),'node':hex(child)})
  tex=b.word(icon+0x24);index=buttons.get(tex)
  rows.append({'widget_offset':hex(off),'panel_slot':hex(slot),'panel':hex(panel),'super_defense':direct_super,'widget_active':b.word(widget+0x58) if direct_super else None,'visibility_state':b.word(widget+0x50) if direct_super else None,'texture_index':index,'label':labels.get(index),'texture':hex(tex),'icon_flags':hex(b.word(icon+0x20)),'children':order})
out=b.endpoint.parent/(a.name+'.json')
with out.open('x') as f:json.dump({'scope':__doc__,'bridge_frame':b.word(0x8266E184),'panels':rows},f,indent=2);f.write('\n')
print(json.dumps({'path':str(out),'panels':len(rows),'buttons':[r['label'] for r in rows]}))
