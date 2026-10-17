import argparse
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument('name')
parser.add_argument('addresses',nargs='+')
parser.add_argument('--fix',action='store_true')
parser.add_argument('--only',action='store_true',help='Export only the requested functions, without their callers')
args=parser.parse_args()
root=Path('/workspace/artifacts/zforkinect')
out=root/'analysis'/args.name
out.mkdir(exist_ok=False)
env=os.environ.copy()
env['JAVA_HOME']='/workspace/tools/jdk21/usr/lib/jvm/java-21-openjdk-amd64'
env['JAVA_TOOL_OPTIONS']='-Duser.home=/workspace/tools/reverse/user-settings'
command=['/workspace/tools/reverse/ghidra/ghidra_12.1.3_PUBLIC/support/analyzeHeadless',str(root/'ghidra-project'),'DBZKinect','-process','dbz-xenon.xex','-noanalysis','-scriptPath',str(Path(__file__).parent / 'ghidra')]
if args.fix:command+=['-preScript','ResearchFixPdata.java',*args.addresses]
command+=['-postScript','ResearchDumpFocus.java',str(out),*(['ONLY'] if args.only else []),*args.addresses]
with (out/'query.log').open('w') as log:
    result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,cwd=root)
text=(out/'query.log').read_text(errors='replace')
print(text[-7000:])
if result.returncode or 'SCRIPT ERROR' in text or not (out/'focus-references.txt').exists():
    raise SystemExit(1)
