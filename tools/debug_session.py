"""Local Xenia session for screenshots, gamepad events and guest-data inspection.

Only the Xenia child created by this process is inspected. Original game files
are never changed. Code changes should use a version-checked Xenia patch file.
"""
import argparse
import ctypes
import fcntl
import importlib.util
import json
import os
import socket
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/workspace/artifacts/zforkinect')
spec = importlib.util.spec_from_file_location('game_runner', Path(__file__).parent / 'run_game.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def serve(name, seconds, patch_directory=None, profile_source=None, render_size=None, gpu='vulkan', hid='keyboard', apu='nop', log_level=2, display_name=':99'):
    display_guard=(ROOT/'runtime'/('display-'+display_name[1:]+'.lock')).open('a')
    try:fcntl.flock(display_guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('Another supervised Xenia session owns display '+display_name)
    directory = ROOT / 'runtime' / name
    directory.mkdir(parents=True, exist_ok=False)
    (directory/'display.json').write_text(json.dumps({'display':display_name})+'\n')
    runner.DISPLAY=display_name
    endpoint = directory / 'control.sock'
    lib = runner.x11()
    display = lib.XOpenDisplay(display_name.encode())
    server = None
    if display:
        lib.XCloseDisplay(display)
    else:
        display_log = (directory / 'xvfb.log').open('w')
        server = subprocess.Popen(['/workspace/tools/xvfb/usr/bin/Xvfb', display_name, '-screen', '0', '1280x720x24', '-nolisten', 'tcp'], stdout=display_log, stderr=subprocess.STDOUT)
        for _ in range(100):
            display = lib.XOpenDisplay(display_name.encode())
            if display:
                lib.XCloseDisplay(display)
                break
            if server.poll() is not None:
                raise RuntimeError('Virtual display failed')
            time.sleep(0.05)
        else:
            raise RuntimeError('Virtual display not ready')
    storage = directory / 'storage'
    storage.mkdir()
    if patch_directory:
        import shutil
        patches=storage/'patches';patches.mkdir()
        for patch in patch_directory.glob('*.patch.toml'):shutil.copy2(patch,patches/patch.name)
    if profile_source:
        import shutil
        shutil.copytree(profile_source,storage/'content')
    env = os.environ.copy()
    env.update(DISPLAY=display_name, VK_DRIVER_FILES=str(ROOT / 'runtime/lavapipe.json'), XDG_CACHE_HOME=str(ROOT / 'runtime/cache'))
    if apu=='sdl':env['SDL_AUDIODRIVER']='dummy'
    command = ['/workspace/tools/xenia-canary/squashfs-root/usr/bin/xenia_canary', '--gpu=vulkan', '--apu=nop', '--hid=keyboard', '--keyboard_mode=1', '--headless=true', '--discord=false', '--keybind_a=0x20', '--keybind_b=B', '--keybind_x=J', '--keybind_y=K', '--keybind_start=0x0D', '--storage_root=' + str(storage), '--log_file=' + str(directory / 'xenia.log'), str(ROOT / 'disc/Dragon Ball Z for Kinect (Europe) (En,Fr,De,Es,It).iso')]
    if profile_source:command.insert(-1,'--logged_profile_slot_0_xuid=B13EBABEBABEBABE')
    command[1]='--gpu='+gpu
    command[2]='--apu='+apu
    command[3]='--hid='+hid
    command[-1:-1]=[f'--log_level={log_level}', '--log_to_stdout=false']
    # Explicit bindings avoid K being consumed by the default right-stick click.
    command[-1:-1]=['--keybind_right_thumb=M','--keybind_dpad_down=C',
                    '--keybind_dpad_up=I',
                    '--keybind_left_trigger=1','--keybind_right_trigger=3',
                    '--keybind_left_shoulder=Q','--keybind_right_shoulder=E']
    if render_size:
        width,height=render_size
        command[-1:-1]=[f'--custom_internal_display_resolution_x={width}',f'--custom_internal_display_resolution_y={height}']
    output = (directory / 'console.log').open('w')
    process = subprocess.Popen(command, cwd=directory, env=env, stdout=output, stderr=subprocess.STDOUT)
    (directory / 'command.json').write_text(json.dumps(command, indent=2))
    memory = None
    base = None
    stop = False
    paused = False
    history = (directory / 'events.jsonl').open('w')
    started = time.monotonic()

    def guest_base():
        nonlocal memory, base
        if base is not None:
            return base
        if memory is None:
            memory = os.open(f'/proc/{process.pid}/mem', os.O_RDONLY)
        image = (ROOT / 'analysis/Dbkn.image.bin').read_bytes()
        address = 0x8237ED60
        expected = image[address - 0x82000000:address - 0x82000000 + 16]
        for bit in range(32, 48):
            try:
                if os.pread(memory, 16, (1 << bit) + address) == expected:
                    base = 1 << bit
                    return base
            except OSError:
                pass
        raise RuntimeError('Guest image is not loaded at a verified memory base')

    def dispatch(request):
        nonlocal stop, paused
        kind = request['command']
        if kind == 'status':
            return {'pid': process.pid, 'exit': process.poll(), 'paused':paused, 'elapsed': round(time.monotonic() - started, 1), 'guest_base': hex(guest_base())}
        if kind in ('pause','resume'):
            os.kill(process.pid,signal.SIGSTOP if kind=='pause' else signal.SIGCONT)
            paused=kind=='pause'
            return {'paused':paused}
        if kind == 'screenshot':
            name = request.get('name', f'screen-{int(time.monotonic() - started)}')
            if not name.replace('-', '').replace('_', '').isalnum():
                raise ValueError('Invalid screenshot name')
            path = directory / (name + '.png')
            if path.exists():
                raise FileExistsError('Screenshot already exists')
            runner.ImageGrab.grab(xdisplay=display_name).save(path)
            return {'path': str(path)}
        if kind == 'key':
            key = request['key']
            if key not in ('Return', 'space', 'b', 'j', 'k', 'c', 'i', 'w', 'a', 's', 'd', 'Up', 'Down', 'Left', 'Right', 'q', 'e', '1', '3'):
                raise ValueError('Key not in diagnostic gamepad mapping')
            duration = float(request.get('duration', .6))
            if not .05 <= duration <= 5:raise ValueError('Invalid key duration')
            runner.keypress(key, duration)
            return {'key': key}
        if kind in ('read', 'write'):
            if kind == 'write':
                raise RuntimeError('Live memory writes are unavailable in this environment; use a checked startup patch')
            address = int(str(request['address']), 16)
            if not 0 <= address < 0x100000000:
                raise ValueError('Invalid guest address')
            host = guest_base() + address
            if kind == 'read':
                length = int(request.get('size', 64))
                if not 0 < length <= 1024 * 1024 or address + length > 0x100000000:
                    raise ValueError('Invalid read size')
                data = os.pread(memory, length, host)
                return {'address': hex(address), 'hex': data.hex(), 'u32be': [f'{v[0]:08X}' for v in struct.iter_unpack('>I', data[:len(data) // 4 * 4])]}
        if kind == 'stop':
            stop = True
            return {'stopping': True}
        raise ValueError('Unknown command')

    try:
        with socket.socket(socket.AF_UNIX) as control:
            control.bind(str(endpoint))
            os.chmod(endpoint, 0o600)
            control.listen(4)
            control.settimeout(0.5)
            print('Control socket:', endpoint, flush=True)
            while not stop and process.poll() is None and time.monotonic() - started < seconds:
                try:
                    client, _ = control.accept()
                except socket.timeout:
                    continue
                with client:
                    client.settimeout(5)
                    data = b''
                    while not data.endswith(b'\n') and len(data) < 131072:
                        chunk = client.recv(65536)
                        if not chunk:
                            break
                        data += chunk
                    request = None
                    try:
                        request = json.loads(data)
                        result = {'ok': True, **dispatch(request)}
                    except Exception as error:
                        result = {'ok': False, 'error': str(error)}
                    history.write(json.dumps({'seconds': round(time.monotonic() - started, 2), 'request': request, 'result': result}) + '\n')
                    history.flush()
                    try:
                        client.sendall(json.dumps(result).encode() + b'\n')
                    except (BrokenPipeError, ConnectionResetError):
                        pass # A disconnected diagnostic client must not kill Xenia.
    finally:
        if process.poll() is None:
            if paused:os.kill(process.pid,signal.SIGCONT)
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if memory is not None:
            os.close(memory)
        output.close()
        history.close()
        endpoint.unlink(missing_ok=True)
        if server is not None:
            server.terminate()
            server.wait(timeout=5)
            display_log.close()
        (directory / 'result.json').write_text(json.dumps({'returncode': process.returncode, 'elapsed': round(time.monotonic() - started, 1), 'intentional_stop': stop or time.monotonic() - started >= seconds}, indent=2))
        display_guard.close()


def request(name, payload):
    if isinstance(payload,dict):payload=json.dumps(payload)
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(10)
        client.connect(str(ROOT / 'runtime' / name / 'control.sock'))
        client.sendall(payload.encode() + b'\n')
        data = b''
        while not data.endswith(b'\n'):
            chunk = client.recv(65536)
            if not chunk:
                break
            data += chunk
    print(data.decode().strip())
    if json.loads(payload).get('command')=='stop':
        # The server owns Xvfb too. Wait for cleanup before a replacement
        # session can attach to the same display during teardown.
        result=ROOT/'runtime'/name/'result.json'
        deadline=time.monotonic()+15
        while not result.exists():
            if time.monotonic()>=deadline:raise RuntimeError('Session cleanup did not finish')
            time.sleep(.05)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('serve', 'request'))
    parser.add_argument('name')
    parser.add_argument('payload', nargs='?')
    parser.add_argument('--seconds', type=int, default=1800)
    parser.add_argument('--patches', type=Path)
    parser.add_argument('--profile-source',type=Path)
    parser.add_argument('--render-size',type=int,nargs=2,metavar=('WIDTH','HEIGHT'))
    parser.add_argument('--gpu',choices=('vulkan','null'),default='vulkan',help='null is for logic-only tests; it renders no game frames')
    parser.add_argument('--hid',choices=('keyboard','sdl','any'),default='keyboard',help='keyboard is the diagnostic pad; sdl uses connected gamepads')
    parser.add_argument('--apu',choices=('nop','sdl'),default='nop',help='sdl uses a silent dummy output but retains SDL buffer consumption')
    parser.add_argument('--log-level',type=int,choices=(0,1,2,3),default=2)
    parser.add_argument('--display',default=':99',help='Dedicated X display; one Xenia child per display')
    args = parser.parse_args()
    if not args.name.replace('-', '').replace('_', '').isalnum():
        parser.error('Invalid session name')
    if not args.display.startswith(':') or not args.display[1:].isdigit():parser.error('Invalid X display')
    if args.render_size and not (1<=args.render_size[0]<=1920 and 1<=args.render_size[1]<=1080):
        parser.error('Unsupported render dimensions')
    if args.mode == 'serve':
        serve(args.name, args.seconds, args.patches,args.profile_source,args.render_size,args.gpu,args.hid,args.apu,args.log_level,args.display)
    else:
        request(args.name, args.payload)
