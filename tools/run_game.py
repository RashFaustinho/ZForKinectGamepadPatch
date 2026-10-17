"""Run a bounded Xenia diagnostic, retaining logs and screenshots outside Git."""
import argparse
import ctypes
import ctypes.util
import json
import os
import subprocess
import time
from pathlib import Path

from PIL import ImageGrab

ROOT = Path(__file__).parent
RUNTIME = ROOT / 'runtime'
DISPLAY = ':99'


def x11():
    lib = ctypes.CDLL(ctypes.util.find_library('X11'))
    lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    lib.XOpenDisplay.restype = ctypes.c_void_p
    lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
    return lib


def keypress(key, duration=0.25):
    lib = x11()
    display = lib.XOpenDisplay(DISPLAY.encode())
    if not display:
        raise RuntimeError('Virtual display unavailable')
    try:
        lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        lib.XDefaultRootWindow.restype = ctypes.c_ulong
        lib.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)), ctypes.POINTER(ctypes.c_uint)]
        lib.XFetchName.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_char_p)]
        lib.XSetInputFocus.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        class WindowAttributes(ctypes.Structure):
            _fields_ = [('x', ctypes.c_int), ('y', ctypes.c_int), ('width', ctypes.c_int), ('height', ctypes.c_int), ('border_width', ctypes.c_int), ('depth', ctypes.c_int), ('visual', ctypes.c_void_p), ('root', ctypes.c_ulong), ('window_class', ctypes.c_int), ('bit_gravity', ctypes.c_int), ('win_gravity', ctypes.c_int), ('backing_store', ctypes.c_int), ('backing_planes', ctypes.c_ulong), ('backing_pixel', ctypes.c_ulong), ('save_under', ctypes.c_int), ('colormap', ctypes.c_ulong), ('map_installed', ctypes.c_int), ('map_state', ctypes.c_int), ('all_event_masks', ctypes.c_long), ('your_event_mask', ctypes.c_long), ('do_not_propagate_mask', ctypes.c_long), ('override_redirect', ctypes.c_int), ('screen', ctypes.c_void_p)]
        lib.XGetWindowAttributes.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(WindowAttributes)]
        lib.XFree.argtypes = [ctypes.c_void_p]
        lib.XFlush.argtypes = [ctypes.c_void_p]
        root = lib.XDefaultRootWindow(display)
        returned_root, parent = ctypes.c_ulong(), ctypes.c_ulong()
        children, count = ctypes.POINTER(ctypes.c_ulong)(), ctypes.c_uint()
        if not lib.XQueryTree(display, root, ctypes.byref(returned_root), ctypes.byref(parent), ctypes.byref(children), ctypes.byref(count)):
            raise RuntimeError('Cannot inspect virtual windows')
        target = None
        try:
            for i in range(count.value):
                name = ctypes.c_char_p()
                if lib.XFetchName(display, children[i], ctypes.byref(name)) and name.value:
                    attributes = WindowAttributes()
                    if b'xenia' in name.value.lower() and lib.XGetWindowAttributes(display, children[i], ctypes.byref(attributes)) and attributes.map_state == 2 and attributes.width >= 320 and attributes.height >= 200:
                        target = children[i]
                    lib.XFree(name)
        finally:
            if children:
                lib.XFree(children)
        if target is None:
            raise RuntimeError('Xenia window not found')
        lib.XSetInputFocus(display, target, 1, 0)
        lib.XStringToKeysym.argtypes = [ctypes.c_char_p]
        lib.XStringToKeysym.restype = ctypes.c_ulong
        lib.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        lib.XKeysymToKeycode.restype = ctypes.c_ubyte
        code = lib.XKeysymToKeycode(display, lib.XStringToKeysym(key.encode()))
        if not code:
            raise RuntimeError('Key has no X11 mapping')
        test = ctypes.CDLL(ctypes.util.find_library('Xtst'))
        test.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        test.XTestFakeKeyEvent(display, code, 1, 0)
        lib.XFlush(display)
        time.sleep(duration)
        test.XTestFakeKeyEvent(display, code, 0, 0)
        lib.XFlush(display)
    finally:
        lib.XCloseDisplay(display)


def run(name, controller):
    RUNTIME.mkdir(exist_ok=True)
    if (RUNTIME / f'{name}-result.json').exists():
        raise RuntimeError('Run name already exists; choose a new name to preserve previous evidence')
    lib = x11()
    display = lib.XOpenDisplay(DISPLAY.encode())
    server = None
    server_log = None
    if display:
        lib.XCloseDisplay(display)
    else:
        server_log = (RUNTIME / f'{name}-xvfb.log').open('w')
        server = subprocess.Popen(['/workspace/tools/xvfb/usr/bin/Xvfb', DISPLAY, '-screen', '0', '1280x720x24', '-nolisten', 'tcp'], stdout=server_log, stderr=subprocess.STDOUT)
        for _ in range(50):
            if server.poll() is not None:
                raise RuntimeError('Xvfb exited; inspect its log')
            display = lib.XOpenDisplay(DISPLAY.encode())
            if display:
                lib.XCloseDisplay(display)
                break
            time.sleep(0.1)
        else:
            server.terminate()
            server.wait()
            raise RuntimeError('Xvfb did not become available')
    env = os.environ.copy()
    env.update(DISPLAY=DISPLAY, VK_DRIVER_FILES=str(RUNTIME / 'lavapipe.json'), XDG_CACHE_HOME=str(RUNTIME / 'cache'))
    iso = ROOT / 'disc/Dragon Ball Z for Kinect (Europe) (En,Fr,De,Es,It).iso'
    command = ['/workspace/tools/xenia-canary/squashfs-root/usr/bin/xenia_canary', '--gpu=vulkan', '--apu=nop', '--hid=keyboard', '--headless=true', '--discord=false', '--keyboard_mode=1', '--keybind_a=0x20', '--keybind_start=0x0D', '--storage_root=' + str(RUNTIME / 'storage-game'), '--log_file=' + str(RUNTIME / f'{name}.log'), str(iso)]
    actions = []
    shots = []
    process = None
    began = time.monotonic()
    result = {'command': command}
    try:
        with (RUNTIME / f'{name}-console.txt').open('w') as output:
            process = subprocess.Popen(command, cwd=RUNTIME, env=env, stdout=output, stderr=subprocess.STDOUT)
            print('Xenia PID:', process.pid, flush=True)
            for seconds in (30, 60, 70, 80, 90):
                try:
                    process.wait(timeout=max(0.1, seconds - (time.monotonic() - began)))
                except subprocess.TimeoutExpired:
                    pass
                if process.poll() is not None:
                    break
                if controller and seconds in (60, 80):
                    key = 'space' if seconds == 60 else 'Return'
                    keypress(key)
                    actions.append({'seconds': seconds, 'button': 'A' if key == 'space' else 'Start'})
                    print('Sent controller button:', actions[-1], flush=True)
                shot = f'{name}-{seconds}s.png'
                ImageGrab.grab(xdisplay=DISPLAY).save(RUNTIME / shot)
                shots.append(shot)
                print('Screenshot:', shot, 'log bytes:', (RUNTIME / f'{name}.log').stat().st_size, flush=True)
            result['still_running_at_limit'] = process.poll() is None
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            result['returncode'] = process.returncode
        if server is not None:
            server.terminate()
            server.wait(timeout=5)
            server_log.close()
        result.update(elapsed_seconds=round(time.monotonic() - began, 1), actions=actions, screenshots=shots)
        (RUNTIME / f'{name}-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--controller', action='store_true', help='Test A and Start at the title screen')
    args = parser.parse_args()
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.name):
        parser.error('Use a simple alphanumeric run name')
    run(args.name, args.controller)
