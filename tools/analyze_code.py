"""Decode a local basic-compressed XEX using Xenia's format, then inspect calls."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

from Cryptodome.Cipher import AES
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--artifacts', type=Path, default=Path('/workspace/artifacts/zforkinect'))
parser.add_argument('--xenia-source', type=Path, default=Path('/workspace/tools/xenia-canary/source/xenia-canary-b735063'))
parser.add_argument('--baseline-log', type=Path, help='Optional original Xenia log for import-thunk call analysis')
args = parser.parse_args()
ROOT = args.artifacts
SOURCE = args.xenia_source
OUT = ROOT / 'analysis'
xex = (OUT / 'default.xex').read_bytes()
if hashlib.sha256(xex).hexdigest() not in {
    'd09d3c36857d930279f2657188f0b135c27d22a39306178743d4e9becd42d438',
    'c4d487f1be66b4484aedee63abd509a20138d283f4f91e074e367521afe24ace',
}:
    raise ValueError('Only the identified European and American original executables are supported')
count = struct.unpack_from('>I', xex, 20)[0]
opts = dict(struct.unpack_from('>II', xex, 24 + i * 8) for i in range(count))
security = struct.unpack_from('>I', xex, 16)[0]
base = struct.unpack_from('>I', xex, security + 0x110)[0]
header_size = struct.unpack_from('>I', xex, 8)[0]
format_offset = opts[0x3FF]
format_size, encryption, compression = struct.unpack_from('>IHH', xex, format_offset)
if compression != 1 or encryption != 1:
    raise ValueError('This inspection helper only supports this encrypted basic-compression format')
source_text = (SOURCE / 'src/xenia/cpu/xex_module.cc').read_text()
public_constant = re.search(r'xe_xex2_retail_key\[16\]\s*=\s*\{([^}]+)', source_text).group(1)
key = bytes(int(h, 16) for h in re.findall(r'0x([0-9A-Fa-f]{2})', public_constant))
session = AES.new(key, AES.MODE_CBC, bytes(16)).decrypt(xex[security + 0x150:security + 0x160])
cipher = AES.new(session, AES.MODE_CBC, bytes(16))
image = bytearray()
position = header_size
for offset in range(format_offset + 8, format_offset + format_size, 8):
    size, zeros = struct.unpack_from('>II', xex, offset)
    if size % 16 or position + size > len(xex):
        raise ValueError('Invalid compressed block')
    image.extend(cipher.decrypt(xex[position:position + size]))
    image.extend(bytes(zeros))
    position += size
if image[:2] != b'MZ':
    raise ValueError('Decoded image has no DOS signature')
pe = struct.unpack_from('<I', image, 60)[0]
if image[pe:pe + 4] != b'PE\0\0':
    raise ValueError('Decoded image has no PE signature')
machine, sections = struct.unpack_from('<HH', image, pe + 4)
optional_size = struct.unpack_from('<H', image, pe + 20)[0]
pe_base = struct.unpack_from('<I', image, pe + 24 + 28)[0]
if pe_base != base:
    raise ValueError('Image base does not match XEX header')
section_list = []
for i in range(sections):
    p = pe + 24 + optional_size + i * 40
    name, virtual_size, va, raw_size, raw_ptr = struct.unpack_from('<8sIIII', image, p)
    flags = struct.unpack_from('<I', image, p + 36)[0]
    section_list.append({'name': name.rstrip(b'\0').decode(), 'rva': va, 'virtual_size': virtual_size,
                         'raw_pointer': raw_ptr, 'raw_size': raw_size, 'executable': bool(flags & 0x20000000)})
(OUT / 'Dbkn.image.bin').write_bytes(image)

# Xenia logs the guest import thunks after loading the unmodified module.
imports = {}
baseline = args.baseline_log or ROOT / 'runtime/game-baseline.log'
for line in baseline.read_text().splitlines() if baseline.is_file() else ():
    match = re.match(r'\s+F\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s+[0-9A-F]+\s+\(\s*\d+\)\s+(?:!!\s*)?(\w+)', line)
    if match:
        imports[int(match[2], 16)] = match[3]
targets = {address: name for address, name in imports.items()
           if any(word in name for word in ('Nui', 'PsCam', 'XamInputGet'))}
calls = []
decoder = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
decoder.skipdata = True
for section in section_list:
    if not section['executable']:
        continue
    start, end = section['rva'], min(len(image), section['rva'] + section['virtual_size'])
    for p in range(start, end - 3, 4):
        word = struct.unpack_from('>I', image, p)[0]
        if word >> 26 != 18:
            continue
        displacement = word & 0x03FFFFFC
        if displacement & 0x02000000:
            displacement -= 0x04000000
        address = base + p
        target = (displacement if word & 2 else address + displacement) & 0xFFFFFFFF
        if target not in targets:
            continue
        context = []
        for instruction in decoder.disasm(bytes(image[max(start, p - 24):p + 36]), base + max(start, p - 24)):
            context.append(f'{instruction.address:08X}  {instruction.mnemonic} {instruction.op_str}')
        calls.append({'address': f'{address:08X}', 'target': f'{target:08X}', 'name': targets[target],
                      'link': bool(word & 1), 'context': context})
strings = []
for match in re.finditer(rb'[\x20-\x7e]{7,}', image):
    text = match[0].decode()
    if re.search(r'kinect|skeleton|gesture|natal|\bnui\b|raise.{0,20}hand', text, re.I):
        strings.append({'address': f'{base + match.start():08X}', 'text': text[:1000]})
report = {'base': f'{base:08X}', 'machine': f'{machine:04X}', 'decoded_bytes': len(image),
          'decoded_sha256': hashlib.sha256(image).hexdigest(), 'sections': section_list,
          'relevant_import_thunks': {f'{k:08X}': v for k, v in targets.items()},
          'calls': calls, 'relevant_strings': strings,
          'caution': 'Static call sites are investigation candidates; they are not validated patches.'}
(OUT / 'code-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
print('Decoded PE:', report['machine'], report['base'], report['decoded_bytes'])
print('Relevant direct branch sites:', len(calls))
for call in calls:
    print(call['address'], call['name'])
print('Relevant strings:', len(strings))
for item in strings[:25]:
    print(item['address'], item['text'])
