"""Validate and serialize the single-title Xenia patch format used here."""
import copy
import json
import re
import tomllib


def validate(document):
    if (document.get('title_id') != '4E4D084E'
            or document.get('hash') != 'C9561ED1F9AFFED4'):
        raise ValueError('Unsupported title or executable module')
    groups = document.get('patch', [])
    if len(groups) != 1 or groups[0].get('is_enabled') is not True:
        raise ValueError('Expected exactly one enabled patch')
    p = groups[0]
    for field in ('name', 'desc', 'author'):
        if not isinstance(p.get(field), str):
            raise ValueError('Missing patch metadata: ' + field)
    for kind in ('be32', 'array'):
        seen = set()
        for item in p.get(kind, []):
            address = item['address']
            if type(address) is not int or address % 4 or address in seen:
                raise ValueError('Unaligned or duplicate patch address')
            seen.add(address)
            value = item['value']
            if kind == 'be32':
                if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
                    raise ValueError('Invalid PowerPC word')
                size = 4
            else:
                if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9a-fA-F]{2})+', value):
                    raise ValueError('Invalid byte array')
                size = len(value) // 2
            if not 0x82000000 <= address < address + size <= 0x82700000:
                raise ValueError('Patch exceeds the verified image range')
    return document


def read(path):
    return validate(tomllib.loads(path.read_text()))


def effective_bytes(document):
    """Resolve writes in the same be32/array order as the startup patch."""
    memory = {}
    p = validate(document)['patch'][0]
    for kind in ('be32', 'array'):
        for item in p.get(kind, []):
            raw = (item['value'].to_bytes(4, 'big') if kind == 'be32'
                   else bytes.fromhex(item['value']))
            memory.update((item['address'] + i, value) for i, value in enumerate(raw))
    return memory


def consolidate_arrays(document):
    """Fold overlapping arrays; preserve every final byte and every address."""
    result = copy.deepcopy(validate(document))
    arrays = result['patch'][0].get('array', [])
    # Preserve source order when resolving overlaps before sorting intervals.
    memory = {}
    intervals = []
    for item in arrays:
        raw = bytes.fromhex(item['value'])
        start = item['address']
        memory.update((start + i, v) for i, v in enumerate(raw))
        intervals.append((start, start + len(raw)))
    merged = []
    for start, end in sorted(intervals):
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    result['patch'][0]['array'] = [
        {'address': start, 'value': bytes(memory[a] for a in range(start, end)).hex()}
        for start, end in merged
    ]
    if effective_bytes(document) != effective_bytes(result):
        raise ValueError('Consolidation changed startup memory')
    return result


def serialize(document):
    validate(document)
    p = document['patch'][0]
    lines = [f'{key} = {json.dumps(document[key], ensure_ascii=False)}'
             for key in ('title_name', 'title_id', 'hash')]
    lines += ['', '[[patch]]']
    lines += [f'{key} = {json.dumps(p[key], ensure_ascii=False)}'
              for key in ('name', 'desc', 'author')]
    lines += ['is_enabled = true']
    for kind in ('be32', 'array'):
        for item in sorted(p.get(kind, []), key=lambda x: x['address']):
            value = f'0x{item["value"]:08X}' if kind == 'be32' else json.dumps(item['value'])
            lines += ['', f'[[patch.{kind}]]',
                      f'address = 0x{item["address"]:08X}', f'value = {value}']
    text = '\n'.join(lines) + '\n'
    if effective_bytes(tomllib.loads(text)) != effective_bytes(document):
        raise ValueError('Serialization changed startup memory')
    return text
