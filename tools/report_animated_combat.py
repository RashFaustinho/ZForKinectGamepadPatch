"""Summarize read-only observations of revision 17; never drive or write a game."""
import argparse,hashlib,json,math,shutil
from pathlib import Path

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--null-session',required=True);p.add_argument('--vulkan-session',required=True)
a=p.parse_args();out=root/'experiments/gamepad-feedback-v17'
patch=out/'4E4D084E.gamepad-feedback.patch.toml';sha=hashlib.sha256(patch.read_bytes()).hexdigest()
diag=root/'experiments/diagnostic-coordinates-v17/4E4D084E.local-action-coordinates.patch.toml'
diag_sha=hashlib.sha256(diag.read_bytes()).hexdigest()
assert json.loads((diag.parent/'manifest.json').read_text())['base_sha256']==sha
checks=json.loads((out/'suite-results.json').read_text());assert all(x['exit_code']==0 for x in checks)
cpu=[]
for f in sorted(set(out.glob('*cpu.json'))|{out/'cpu-checks.json'}):
 d=json.loads(f.read_text());assert d['patch_sha256']==sha,f
 assert d.get('passed'),f
 cpu.append({'file':f.name,'passed':d['passed']})

def summarize(session,names):
 folder=Path('/workspace/artifacts/zforkinect/runtime')/session
 readback=json.loads((folder/'runtime-patch-verification.json').read_text())
 assert readback['passed'] and readback['patch_sha256']==diag_sha
 cases={}
 for name in names:
  path=folder/(name+'.json');d=json.loads(path.read_text());ss=d['samples'];assert ss
  audits=d.get('capture_audits',[])
  assert all(x['all_finite'] and x['joint_buffers_equal'] for x in audits),name
  positions=[next(r['values'][12:15] for r in x['regions'] if r['name']=='first_person_arm_0x90') for x in audits]
  distance=max((math.dist(x,y) for x in positions for y in positions),default=0.)
  held=[s for s in ss if s['bridge']['held']=='0x10']
  hp0=ss[0]['players'][1]['hp'];hp1=ss[-1]['players'][1]['hp']
  if name=='charge-y':
   assert len({s['players'][1]['hp'] for s in held})==1
   assert 13 in {s['players'][0]['state'] for s in ss} and hp1<hp0
   assert any(s['bridge']['held']=='0x0' and s['players'][0]['state']==13 for s in ss)
  if name=='near-x':assert 10 in {s['players'][0]['state'] for s in ss} and hp1<hp0
  if name=='far-x':assert 29 in {s['players'][0]['state'] for s in ss} and hp1<hp0
  if name=='far-y':assert 32 in {s['players'][0]['state'] for s in ss}
  # Far defense uses native state 77/C without the close guard's FP flag 2.
  if name=='guard-b':assert any(s['players'][0]['state']==77 and s['players'][0]['last_action']==0xC and s['bridge']['held']=='0x20' for s in ss)
  if name in ('step-left','step-right'):
   action=0xD if name=='step-left' else 0xE
   assert any(s['players'][0]['last_action']==action and not s['players'][0]['control_flags']&2 for s in ss)
  cases[name]={'source':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
   'native_states':sorted({s['players'][0]['state'] for s in ss}),
   'native_modes':sorted({s['mode'] for s in ss}),
   'native_actions':[hex(x) for x in sorted({s['players'][0]['last_action'] for s in ss}) if x!=0xFFFFFFFF],
   'opponent_hp_before':hp0,'opponent_hp_after':hp1,'capture_count':len(audits),
   'captured_regions':sum(len(x['regions']) for x in audits),'all_captures_finite':all(x['all_finite'] for x in audits),
   'arm_translation_max_distance':distance,'screenshots':d['screenshots']}
 command=json.loads((folder/'command.json').read_text())
 textures=json.loads((folder/'hd-textures-runtime.json').read_text());assert textures['passed']==11
 final=json.loads((folder/'final-audit.json').read_text());assert final['all_finite']
 return {'session':session,'startup_readback_passed':True,
  'native_128px_textures_verified':textures['passed'],'final_geometry_regions':len(final['regions']),
  'final_geometry_all_finite':final['all_finite'],
  'requested_internal_resolution':[x for x in command if x.startswith('--custom_internal_display_resolution')],
  'cases':cases}

native=summarize(a.null_session,['near-x','charge-y','far-x','far-y','guard-b','step-right','step-left'])
visual=summarize(a.vulkan_session,['near-x','charge-y','far-x','far-y'])
previews=out/'previews';previews.mkdir(exist_ok=True)
source=Path('/workspace/artifacts/zforkinect/runtime')/a.vulkan_session
images={'punch-x.png':'near-x-action-7.png','charge-y.png':'charge-y-action-32.png',
        'release-y.png':'charge-y-action-39.png','ki-x.png':'far-x-action-7.png','ki-y.png':'far-y-action-7.png'}
for target,name in images.items():shutil.copyfile(source/name,previews/target)
report={'patch_sha256':sha,'diagnostic_sha256':diag_sha,
 'scope':'Native pad inputs and O_RDONLY guest observations in isolated profiles. No debugger writes to guest memory; native HP/Ki/timing/phase state machines run unforced. Diagnostic counters do not replace game decisions.',
 'animation_source':'Authored first-person trajectories; original character meshes, native hand poses and renderer. No extracted CPU attack clips.',
 'cpu_reports':cpu,'suite_results':checks,'native_null':native,'native_vulkan':visual,
 'previews':images,'limitations':['Goku versus Raditz in Score Attack; not every character or chapter.','No physical USB pad or Windows backend test.','Vulkan screenshots use the internal resolution settings recorded above.']}
(out/'runtime-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(out/'runtime-checks.json')
