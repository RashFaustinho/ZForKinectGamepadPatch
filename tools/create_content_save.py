"""Create an offline Xenia save with all identified content available.

Generates game progress, not played scores or Xbox achievements. The native
150,000-byte DB_SAVE checksum covers little-endian 16-bit words after byte 8;
its split result is stored in two big-endian words. Never overwrite a profile.
"""
import argparse
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZE = 150000
TITLE = 0x4E4D084E


def word(data, offset, value): struct.pack_into('>I', data, offset, value)


def seal(data):
    if len(data) != SIZE: raise ValueError('Expected 150000 bytes')
    checksum = sum(struct.unpack('<74996H', data[8:])) & 0xffffffff
    word(data, 0, checksum >> 8); word(data, 4, checksum & 255)
    return data


def valid(data):
    return len(data) == SIZE and seal(bytearray(data)) == data


def create_save(catalog, powerup=None):
    if powerup is not None and not 0 <= powerup < 12: raise ValueError('Power-up must be in 0..11, or None')
    data = bytearray(SIZE)
    now = datetime.now(timezone.utc)
    for offset, value in zip(range(8, 0x1c, 4), (now.year, now.month, now.day, now.hour, now.minute)):
        word(data, offset, value)
    # Same availability layout used by 821BEFC0. Bit 2 suppresses "new" badges.
    for mode in range(2):
        for saga in range(5):
            base = 0x20 + mode*0x1764 + saga*0x494
            word(data, base, 3)
            for stage in range(6):
                record = base + 8 + stage*0x94
                word(data, record, 3)
                if saga < 4 and (stage < 5 or saga != 0):
                    # Native fresh-profile default fighter (821BF190).
                    for off, value in ((0x14, 23), (0x18, 391), (0x1c, 391)):
                        word(data, record+off, value)
    for row in catalog['character_variants']:
        group = row['group']; variant = row['row']
        for base, bit in ((0x2fd8, group), (0x2fe0, variant)):
            off = base + (bit//32)*4
            word(data, off, struct.unpack_from('>I', data, off)[0] | (1 << (bit % 32)))
    # Six native selected-item slots default to -1; retain their meaning.
    for off in range(0x2f00, 0x2f18, 4): word(data, off, 0xffffffff)
    word(data, 0x2eec, 1 if powerup is None else 5)
    for off, value in ((0x2ef4, 23), (0x2ef8, 391), (0x2efc, 391)):
        word(data, off, value)
    if powerup is not None: word(data, 0x2f00, powerup)
    data[0x4020:0x4025] = bytes((2, 5, 5, 5, 0))
    word(data, 0x4028, 1)
    return bytes(seal(data))


def legacy_header(xuid):
    # Xenia b735063 accepts XCONTENT_DATA_AGGREGATE (0x148) + license mask.
    header = bytearray(0x14c)
    struct.pack_into('>2I', header, 0, 1, 1)
    label = 'Dragon Ball Z for Kinect - All Content'.encode('utf-16-be')
    header[8:8+len(label)] = label
    header[0x108:0x112] = b'SystemData'
    struct.pack_into('>Q', header, 0x138, xuid)
    word(header, 0x140, TITLE)
    return bytes(header)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path, help='New output directory; must not exist')
    p.add_argument('--xuid', default='B13EBABEBABEBABE')
    p.add_argument('--powerup', type=int, default=None, help='Optional active bonus 0..11; omitted means no active power-up')
    args = p.parse_args()
    if len(args.xuid) != 16: p.error('XUID must have 16 hexadecimal digits')
    xuid = int(args.xuid, 16)
    catalog = json.loads((ROOT/'experiments/content-unlock/catalog.json').read_text())
    data = create_save(catalog, args.powerup)
    args.output.mkdir(parents=True, exist_ok=False)
    title = args.output/'content'/f'{xuid:016X}'/f'{TITLE:08X}'
    save = title/'00000001/SystemData/DB_SAVE'; save.parent.mkdir(parents=True)
    save.write_bytes(data)
    header = title/'Headers/00000001/SystemData.header'; header.parent.mkdir(parents=True)
    header.write_bytes(legacy_header(xuid))
    (args.output/'manifest.json').write_text(json.dumps({
        'status':'generated content-complete candidate; native load validation required',
        'title_id':f'{TITLE:08X}','save_bytes':len(data),'save_sha256':hashlib.sha256(data).hexdigest(),
        'character_groups':catalog['character_groups'],
        'character_variants':len(catalog['character_variants']),
        'powerup':args.powerup,'native_checksum_valid':valid(data),
        'scope':'All identified content available; scores remain zero and Xbox achievements are not written',
        'format':'Xenia extracted content directory; not a signed Xbox 360 STFS container'
    }, indent=2)+'\n')
    print(args.output)


if __name__ == '__main__': main()
