"""Create an offline-only Xenia test profile using its documented source format.

No Xbox Live account, password or online authentication is created or used.
"""
from pathlib import Path
import hashlib
import hmac
import re
from Cryptodome.Cipher import ARC4

root=Path('/workspace/artifacts/zforkinect/profile-template/content')
xuid='B13EBABEBABEBABE'
gamertag='PadTest'
directory=root/xuid/'FFFE07D1/00010000'/xuid
path=directory/'Account'
if path.exists():
    raise SystemExit('Local test account already exists; refusing to overwrite')
source=Path('/workspace/tools/xenia-canary/source/xenia-canary-b735063/src/xenia/kernel/util/crypto_utils.cc').read_text()
constant=re.search(r'xekey_0x19\[\]\s*=\s*\{([^}]+)',source).group(1)
key=bytes(int(v,16) for v in re.findall(r'0x([A-Fa-f0-9]{2})',constant))
account=bytearray(0x17c)
name=gamertag.encode('utf-16-be')
account[8:8+len(name)]=name
clear=bytes([0xfd])*8+account
digest=hmac.new(key,clear,hashlib.sha1).digest()[:16]
rc4_key=hmac.new(key,digest,hashlib.sha1).digest()[:16]
encrypted=digest+ARC4.new(rc4_key).encrypt(clear)
roundtrip=ARC4.new(rc4_key).decrypt(encrypted[16:])
assert hmac.compare_digest(hmac.new(key,roundtrip,hashlib.sha1).digest()[:16],digest)
assert roundtrip[8:]==account and len(encrypted)==0x194
directory.mkdir(parents=True,exist_ok=False)
path.write_bytes(encrypted)
print('Created offline-only local test profile:',gamertag,'at',directory)
