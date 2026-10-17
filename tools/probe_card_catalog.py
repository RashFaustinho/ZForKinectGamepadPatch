"""Read all twelve power-up cards through the real pad-operated Card Reader.

This uses an isolated profile, genuine pad events, read-only guest inspection
and the game's own save path. No menu, selection or save fields are forced.
Start at the root menu with the catalog on Shield (67), or on a character.
"""
import fcntl,json,time,argparse,struct,hashlib
from pathlib import Path
import battle_state as b
from coordinate_audit import request
from virtual_pad import VirtualPad
from create_content_save import valid
p=argparse.ArgumentParser(description=__doc__);p.add_argument('session');a=p.parse_args();b.connect(a.session)
out=b.endpoint.parent/'card-catalog-native.json'
if out.exists():p.error('Catalog report already exists')
lock=open(b.input_lock_path(),'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
pad=VirtualPad(b.display_name())
def wait_frames(n):
 f=b.word(0x8266E184);end=time.monotonic()+30
 while b.word(0x8266E184)-f<n:
  if time.monotonic()>end:raise RuntimeError('Native menu frames stalled')
  time.sleep(.04)
def press(s):
 pad.key(s,True);wait_frames(4);pad.key(s,False);wait_frames(6)
def menu():
 o=b.word(0x8266E1B8);return {'kind':b.word(o),'count':b.word(o+4),'state':b.word(o+0x2C),'index':b.word(o+0x34)}
def root():
 end=time.monotonic()+30
 while time.monotonic()<end:
  m=menu()
  if m['kind']==2 and m['count']==6 and m['state']==1:return m
  time.sleep(.1)
 raise RuntimeError('Root menu did not return: '+str(menu()))
rows=[];request({'command':'resume'})
try:
 for i in range(12):
  m=root()
  while m['index']!=2:press('s');m=menu()
  press('space');wait_frames(180)
  before=b.word(0x8266E1C4);press('3');wait_frames(60);selected=b.word(0x8266E1C4)
  expected=67 if not 67<=before<79 or before==78 else before+1
  assert selected==expected,(before,selected)
  sv=b.word(b.word(0x8264920C));arg=b.word(sv+0x2F00);assert arg==selected-67 and b.word(sv+0x2EEC)&4
  bank=b.word(b.word(0x826490E0)+0x20);off,n=struct.unpack('>II',b.read(bank+0x10+(29+arg)*48,8));label=b.read(bank+off,n).decode('utf-16-le').strip('\ufeff\0')
  press('b');root()
  f=next(b.endpoint.parent.glob('storage/content/*/4E4D084E/00000001/SystemData/DB_SAVE'));raw=f.read_bytes()
  assert valid(raw) and int.from_bytes(raw[0x2F00:0x2F04],'big')==arg
  row={'catalog_index':selected,'powerup':arg,'native_label':label,'saved_flags':int.from_bytes(raw[0x2EEC:0x2EF0],'big'),'save_checksum_valid':True,'save_sha256':hashlib.sha256(raw).hexdigest()};rows.append(row);print(json.dumps(row),flush=True)
finally:
 pad.close();request({'command':'pause'})
 with out.open('x') as f:f.write(json.dumps({'scope':__doc__,'rows':rows,'complete':len(rows)==12},indent=2)+'\n')
