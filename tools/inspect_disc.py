"""Read an Xbox disc filesystem and XEX metadata without modifying the image."""
import argparse
import hashlib
import json
import mmap
import struct
from pathlib import Path


def inspect(image, output):
    output.mkdir(parents=True, exist_ok=True)
    with image.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        def read(offset, size):
            if offset < 0 or size < 0 or offset + size > len(data):
                raise ValueError('Disc entry outside image')
            return data[offset:offset + size]

        bases = (0, 0xFB20, 0x20600, 0x2080000, 0xFD90000)
        base = next((b for b in bases if read(b + 32 * 2048, 20) == b'MICROSOFT*XBOX*MEDIA'), None)
        if base is None:
            raise ValueError('Xbox filesystem signature not found')
        sector, size = struct.unpack('<II', read(base + 32 * 2048 + 20, 8))
        entries = []
        seen_directories = set()

        def directory(sector, size, parent, depth=0):
            if depth > 64 or (sector, size) in seen_directories:
                raise ValueError('Cyclic or excessively deep directory')
            if size > 32 * 1024 * 1024:
                raise ValueError('Directory too large')
            seen_directories.add((sector, size))
            table = read(base + sector * 2048, size)
            visited = set()

            def node(index):
                if index in visited:
                    raise ValueError('Cyclic directory tree')
                visited.add(index)
                pos = index * 4
                if pos + 14 > len(table):
                    raise ValueError('Truncated directory entry')
                left, right, sec, length, attr, name_length = struct.unpack_from('<HHIIBB', table, pos)
                if pos + 14 + name_length > len(table):
                    raise ValueError('Truncated directory name')
                name = table[pos + 14:pos + 14 + name_length].decode('cp1252')
                path = parent + '/' + name if parent else name
                if left:
                    node(left)
                entry = {'path': path, 'size': length, 'directory': bool(attr & 0x10), 'offset': base + sec * 2048}
                entries.append(entry)
                if entry['directory'] and length:
                    directory(sec, length, path, depth + 1)
                if right:
                    node(right)

            if size:
                node(0)

        directory(sector, size, '')
        (output / 'disc-files.json').write_text(json.dumps(entries, indent=2) + '\n')
        executable = next(e for e in entries if e['path'].lower() == 'default.xex')
        xex = read(executable['offset'], executable['size'])
        if xex[:4] != b'XEX2':
            raise ValueError('Expected XEX2 executable')
        count = struct.unpack_from('>I', xex, 20)[0]
        opts = dict(struct.unpack_from('>II', xex, 24 + i * 8) for i in range(count))
        report = {'image': image.name, 'image_bytes': len(data), 'game_partition_offset': hex(base),
                  'disc_entry_count': len(entries), 'default_xex_bytes': len(xex),
                  'default_xex_sha256': hashlib.sha256(xex).hexdigest(),
                  'entry_point': hex(opts.get(0x10100, 0)), 'optional_headers': [hex(k) for k in opts]}
        if 0x40006 in opts:
            media, version, base_version, title = struct.unpack_from('>IIII', xex, opts[0x40006])
            report.update(media_id=f'{media:08X}', title_id=f'{title:08X}', version=f'{version:08X}', base_version=f'{base_version:08X}')
        if 0x3FF in opts:
            _, encryption, compression = struct.unpack_from('>IHH', xex, opts[0x3FF])
            report.update(encryption_type=encryption, compression_type=compression)
        if 0x183FF in opts:
            p = opts[0x183FF]
            length = struct.unpack_from('>I', xex, p)[0]
            report['original_pe_name'] = xex[p + 4:p + length].rstrip(b'\0').decode(errors='replace')
        if 0x200FF in opts:
            p = opts[0x200FF]
            length = struct.unpack_from('>I', xex, p)[0]
            libraries = []
            for q in range(p + 4, p + length, 16):
                name, major, minor, build, approval, qfe = struct.unpack_from('>8sHHHBB', xex, q)
                libraries.append({'name': name.rstrip(b'\0').decode(errors='replace'), 'version': f'{major}.{minor}.{build}.{qfe}'})
            report['static_libraries'] = libraries
        if 0x103FF in opts:
            p = opts[0x103FF]
            length, strings_size, strings_count = struct.unpack_from('>III', xex, p)
            strings = []
            q = p + 12
            for _ in range(strings_count):
                end = xex.index(b'\0', q, p + 12 + strings_size)
                strings.append(xex[q:end].decode(errors='replace'))
                q = p + 12 + ((end + 1 - (p + 12) + 3) & ~3)
            libraries = []
            q = p + 12 + strings_size
            while q < p + length:
                libsize = struct.unpack_from('>I', xex, q)[0]
                if libsize < 40 or q + libsize > p + length:
                    raise ValueError('Invalid import library size')
                name_index, imports = struct.unpack_from('>HH', xex, q + 36)
                libraries.append({'name': strings[name_index & 0xFF], 'import_records': imports})
                q += libsize
            report['import_libraries'] = libraries
        (output / 'default.xex').write_bytes(xex)
        (output / 'disc-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inspect(args.image, args.output)
