"""Render vector controller labels at the requested size and pack BC3 blocks.

These are new UI drawings, not enlarged copies of the game's 32 px artwork.
The game uses 16 KiB of linear physical storage per existing pad texture;
128x128 BC3 occupies exactly that amount. The LZ4 stream is decoded by the
startup patch into those existing allocations, without editing disc assets.
"""
import argparse,io,json,hashlib
import lz4.block
from pathlib import Path
import cairosvg
from PIL import Image
from collections import deque


def bleed_transparent_rgb(image, radius=4):
 """Extend edge RGB under zero alpha, avoiding black BC3/filtering fringes."""
 width,height=image.size;pixels=list(image.get_flattened_data());distance=[-1]*len(pixels)
 queue=deque()
 for i,pixel in enumerate(pixels):
  if pixel[3]:distance[i]=0;queue.append(i)
 while queue:
  i=queue.popleft()
  if distance[i]>=radius:continue
  x,y=i%width,i//width
  for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
   if not (0<=xx<width and 0<=yy<height):continue
   j=yy*width+xx
   if distance[j]>=0:continue
   pixels[j]=(*pixels[i][:3],pixels[j][3]);distance[j]=distance[i]+1;queue.append(j)
 result=Image.new('RGBA',image.size);result.putdata(pixels);return result

root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--size',type=int,choices=(128,256),default=128);ap.add_argument('--out',type=Path)
ap.add_argument('--content-scale',type=float,default=1.0,help='Centered drawing size within the transparent canvas')
ap.add_argument('--include-super-defense',action='store_true',help='Include native right-stick up/down slots for Super counters')
ap.add_argument('--face-supersample',type=int,choices=(1,2,4,8),default=1,help='Render A/B/X/Y larger before premultiplied-alpha downsampling')
ap.add_argument('--face-alpha-bleed',action='store_true',help='Extend A/B/X/Y edge RGB under transparent pixels before BC3 encoding')
ap.add_argument('--face-size',type=int,choices=(128,256),help='Override only the four face-button canvas sizes')
args=ap.parse_args();out=args.out or root/'assets/controller';out.mkdir(parents=True,exist_ok=True)
if not .25<=args.content_scale<=1:ap.error('Content scale must be between .25 and 1')
buttons={2:('B','#bc2429'),3:('X','#2458b6'),4:('Y','#d49c13'),5:('A','#287d32'),
         6:('LB',None),7:('LT',None),9:('RB',None),10:('RT',None),
         14:('LS_RIGHT',None),15:('LS_LEFT',None),21:('DPAD_DOWN',None)}
if args.include_super_defense:buttons.update({16:('RS_UP',None),17:('RS_DOWN',None)})

records=[];blob=bytearray()
for index,(label,color) in buttons.items():
 body='<g stroke="#111820" stroke-width="3">'
 if color:
  body+=f'<circle cx="64" cy="64" r="57" fill="{color}"/>'
  body+='<circle cx="64" cy="64" r="52" fill="none" stroke="#ffffff" stroke-opacity=".55" stroke-width="2"/>'
  body+=f'<text x="64" y="87" fill="white" stroke="none" font-size="66">{label}</text>'
 elif label.startswith(('LS_','RS_')):
  body+='<circle cx="64" cy="64" r="57" fill="#26313d"/>'
  body+=f'<text x="64" y="53" fill="white" stroke="none" font-size="32">{label[:2]}</text>'
  path='M 98,83 H 36 M 54,65 L 35,83 L 54,101' if label=='LS_LEFT' else 'M 30,83 H 92 M 74,65 L 93,83 L 74,101'
  if label=='RS_UP':path='M 64,107 V 69 M 48,85 L 64,68 L 80,85'
  if label=='RS_DOWN':path='M 64,66 V 104 M 48,88 L 64,105 L 80,88'
  body+=f'<path d="{path}" fill="none" stroke="white" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
 elif label=='DPAD_DOWN':
  body+='<path d="M 45,7 H 83 V 44 H 120 V 82 H 83 V 120 H 45 V 82 H 8 V 44 H 45 Z" fill="#26313d"/>'
  body+='<path d="M 64,72 V 105 M 52,93 L 64,106 L 76,93" fill="none" stroke="white" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
 else:
  body+='<rect x="7" y="25" width="114" height="78" rx="19" fill="#26313d"/>'
  body+='<rect x="12" y="30" width="104" height="68" rx="15" fill="none" stroke="#8593a1" stroke-width="2"/>'
  body+=f'<text x="64" y="80" fill="white" stroke="none" font-size="43">{label}</text>'
 inset=64*(1-args.content_scale)
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"><g transform="translate('+str(inset)+' '+str(inset)+') scale('+str(args.content_scale)+')" font-family="DejaVu Sans" font-weight="bold" text-anchor="middle">'+body+'</g></g></svg>'
 (out/(label+'.svg')).write_text(svg+'\n')
 factor=args.face_supersample if color else 1
 size=(args.face_size or args.size) if color else args.size
 png=cairosvg.svg2png(bytestring=svg.encode(),output_width=size*factor,output_height=size*factor)
 image=Image.open(io.BytesIO(png)).convert('RGBA')
 if factor>1:image=image.convert('RGBa').resize((size,size),Image.Resampling.LANCZOS).convert('RGBA')
 if color and args.face_alpha_bleed:image=bleed_transparent_rgb(image)
 image.save(out/(label+'.png'))
 dds=io.BytesIO();image.save(dds,format='DDS',pixel_format='DXT5');data=dds.getvalue()[128:]
 assert len(data)==size*size
 # A block-preserving stream keeps native BC3 byte order and is trivial to
 # decode with volatile PowerPC integer registers.
 packed=lz4.block.compress(data,store_size=False,mode='high_compression',compression=12)
 records.append({'index':index,'label':label,'offset':len(blob),'packed_bytes':len(packed),
                 'decoded_bytes':len(data),'bc3_sha256':hashlib.sha256(data).hexdigest()})
 if args.face_size:records[-1].update(width=size,height=size)
 if color and (args.face_supersample>1 or args.face_alpha_bleed):records[-1]['fetch_word3']=0x01280D10
 blob.extend(packed)
 (out/(label+'.dds')).write_bytes(dds.getvalue())
(out/'buttons.lz4').write_bytes(blob)
(out/'manifest.json').write_text(json.dumps({'width':args.size,'height':args.size,'content_scale':args.content_scale,'face_supersample':args.face_supersample,'face_alpha_bleed':args.face_alpha_bleed,'format':'BC3/DXT5, linear RGBA, no byte swap',
 'packing':'independent raw LZ4 blocks','packed_bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'textures':records},indent=2)+'\n')
print('Packed',len(records),'HD buttons into',len(blob),'bytes')
