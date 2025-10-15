#!/usr/bin/env python3
import os
import platform
from shutil import which
from subprocess import run, PIPE, DEVNULL
from .ImageResizer import SVGResizer


# --------------------------------------------------------------------
#  Vector based image resizer
# --------------------------------------------------------------------

class ReSVG(SVGResizer):
    ''' resvg (https://github.com/RazrFalcon/resvg/) '''

    @staticmethod
    def isSupported() -> bool:
        ReSVG._exe = which('resvg')
        return True if ReSVG._exe else False

    def resize(self, size: int, fname_out: str) -> None:
        run([self.exe, '-w', str(size), self.fname, fname_out])


class ChromeSVG(SVGResizer):
    ''' Google Chrome (macOS only) '''

    @staticmethod
    def isSupported() -> bool:
        if platform.system() == 'Darwin':
            ret = run(['defaults', 'read', 'com.google.Chrome',
                       'LastRunAppBundlePath'], stdout=PIPE).stdout.strip()
            app_path = ret.decode('utf8') or '/Applications/Google Chrome.app'
            app_path += '/Contents/MacOS/Google Chrome'
            if os.path.isfile(app_path):
                ChromeSVG._exe = app_path
                return True
        return False

    def resize(self, size: int, fname_out: str) -> None:
        run([self.exe, '--headless', '--disable-gpu', '--hide-scrollbars',
             '--force-device-scale-factor=1', '--default-background-color=000000',
             '--window-size={0},{0}'.format(size),
             '--screenshot={}'.format(fname_out), self.fname],
            stderr=DEVNULL)
