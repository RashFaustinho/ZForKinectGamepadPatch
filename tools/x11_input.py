"""Drive the task's local virtual display for emulator diagnostics."""
import argparse
import ctypes
import ctypes.util
import time
import importlib.util
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('kind',choices=('click','key','down','up','type'))
parser.add_argument('values',nargs='+')
parser.add_argument('--duration',type=float,default=.6)
parser.add_argument('--display',default=':99')
args=parser.parse_args()
if not args.display.startswith(':') or not args.display[1:].isdigit():parser.error('Invalid X display')
spec=importlib.util.spec_from_file_location('game_runner',Path(__file__).parent / 'run_game.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
runner.DISPLAY=args.display
x=ctypes.CDLL(ctypes.util.find_library('X11'))
t=ctypes.CDLL(ctypes.util.find_library('Xtst'))
x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p
x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong
x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_ubyte
x.XFlush.argtypes=[ctypes.c_void_p];x.XCloseDisplay.argtypes=[ctypes.c_void_p]
t.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
t.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
t.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
display=x.XOpenDisplay(args.display.encode())
if not display:raise SystemExit('Task display '+args.display+' is not running')
def key(name,down):
    code=x.XKeysymToKeycode(display,x.XStringToKeysym(name.encode()))
    if not code:raise ValueError('Unknown key')
    t.XTestFakeKeyEvent(display,code,int(down),0);x.XFlush(display)
try:
    if args.kind=='click':
        a,b=map(int,args.values)
        if not (0<=a<1280 and 0<=b<720):raise ValueError('Outside task display')
        t.XTestFakeMotionEvent(display,-1,a,b,0)
        t.XTestFakeButtonEvent(display,1,1,0);x.XFlush(display);time.sleep(.6)
        t.XTestFakeButtonEvent(display,1,0,0);x.XFlush(display)
    elif args.kind=='type':
        for character in ' '.join(args.values):
            name='space' if character==' ' else character
            runner.keypress(name);time.sleep(.15)
    elif args.kind in ('down','up'):key(args.values[0],args.kind=='down')
    else:
        runner.keypress(args.values[0],args.duration)
finally:x.XCloseDisplay(display)
