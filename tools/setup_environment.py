"""Restore verified tool artifacts retained in this environment snapshot."""
import ctypes.util
import hashlib
import json
import subprocess
import tarfile
import venv
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path('/workspace/artifacts/zforkinect')
TOOLS = Path('/workspace/tools')
artifacts = json.loads((Path(__file__).parent / 'tool-artifacts.json').read_text())
groups = defaultdict(list)
for artifact in artifacts:
    path = Path(artifact['path'])
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
        raise RuntimeError(f'Missing or changed retained tool artifact: {path}')
    if artifact['kind'] == 'deb':
        groups[artifact['extract_to']].append(path)
    if artifact['kind'].startswith('zip'):
        with zipfile.ZipFile(path) as archive:
            destination = Path(artifact['extract_to'])
            members = archive.namelist()
            if any(Path(n).is_absolute() or '..' in Path(n).parts for n in members):
                raise RuntimeError('Unsafe archive member')
            root = destination / members[0].split('/')[0]
            if not root.exists():
                destination.mkdir(parents=True, exist_ok=True)
                archive.extractall(destination)
                for member in archive.infolist():
                    mode = (member.external_attr >> 16) & 0o777
                    if mode & 0o111:
                        (destination/member.filename).chmod(mode)
for destination, packages in groups.items():
    if not Path(destination).exists():
        Path(destination).mkdir(parents=True)
        for package in packages:
            subprocess.run(['dpkg-deb', '-x', str(package), destination], check=True)
image = TOOLS / 'xenia-canary/xenia_canary_linux.AppImage'
binary = TOOLS / 'xenia-canary/squashfs-root/usr/bin/xenia_canary'
if not binary.exists():
    image.chmod(0o755)
    subprocess.run([str(image), '--appimage-extract'], cwd=image.parent, check=True)
source = TOOLS / 'xenia-canary/source'
if not source.exists():
    with tarfile.open(TOOLS / 'xenia-canary/source-b735063.tar.gz') as archive:
        archive.extractall(source, filter='data')
environment = TOOLS / 'archive-check'
if not (environment / 'bin/python').is_file():
    venv.create(environment, with_pip=True)
subprocess.run([str(environment / 'bin/python'), '-m', 'pip', 'install', '--disable-pip-version-check', '--no-cache-dir', '-r', str(Path(__file__).parent / 'analysis-requirements.txt')], check=True)
for path in (binary, TOOLS / 'xvfb/usr/bin/Xvfb', TOOLS / 'mesa-vulkan/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so'):
    result = subprocess.run(['ldd', str(path)], capture_output=True, text=True, check=True)
    if 'not found' in result.stdout:
        raise RuntimeError(f'Missing runtime library for {path}')
for name in ('X11', 'Xtst'):
    if not ctypes.util.find_library(name):
        raise RuntimeError(f'Missing system library: {name}')
runtime = ROOT / 'runtime'
runtime.mkdir(exist_ok=True)
(runtime / 'cache').mkdir(exist_ok=True)
icd = json.loads((TOOLS / 'mesa-vulkan/usr/share/vulkan/icd.d/lvp_icd.json').read_text())
icd['ICD']['library_path'] = str(TOOLS / 'mesa-vulkan/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so')
(runtime / 'lavapipe.json').write_text(json.dumps(icd, indent=2) + '\n')
for name in ('java', 'javac'):
    subprocess.run([str(TOOLS/'jdk21/usr/lib/jvm/java-21-openjdk-amd64/bin'/name), '-version'], check=True)
print('Verified retained artifacts and prepared Xenia, Xvfb, Lavapipe, Ghidra/Xenon, JDK and Python analysis tools.')
