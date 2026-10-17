"""Own an X11 connection and release every synthetic key on exit."""
import ctypes
import ctypes.util

from debug_session import runner


class VirtualPad:
    def __init__(self, display_name):
        self.x = runner.x11()
        self.x.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.x.XStringToKeysym.restype = ctypes.c_ulong
        self.x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.x.XKeysymToKeycode.restype = ctypes.c_ubyte
        self.x.XFlush.argtypes = [ctypes.c_void_p]
        self.xtst = ctypes.CDLL(ctypes.util.find_library('Xtst'))
        self.xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                               ctypes.c_int, ctypes.c_ulong]
        self.display = self.x.XOpenDisplay(display_name.encode())
        if not self.display:
            raise RuntimeError('Display is not available: ' + display_name)
        self.held = set()

    def key(self, name, down):
        if not self.display:
            raise RuntimeError('Pad connection is closed')
        if (name in self.held) == bool(down):
            return
        code = self.x.XKeysymToKeycode(self.display,
                                      self.x.XStringToKeysym(name.encode()))
        if not code:
            raise ValueError('Unknown key: ' + name)
        self.xtst.XTestFakeKeyEvent(self.display, code, int(down), 0)
        self.x.XFlush(self.display)
        if down:
            self.held.add(name)
        else:
            self.held.discard(name)

    def close(self):
        if self.display:
            for name in tuple(self.held):
                self.key(name, False)
            self.x.XCloseDisplay(self.display)
            self.display = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
