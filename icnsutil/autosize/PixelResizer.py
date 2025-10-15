#!/usr/bin/env python3
import re
from shutil import which
from subprocess import run, PIPE, DEVNULL
from typing import Tuple
from .ImageResizer import PixelResizer
try:
    from PIL import Image
    PILLOW_ENABLED = True
except ImportError:
    PILLOW_ENABLED = False


# --------------------------------------------------------------------
#  Raster image resizer
# --------------------------------------------------------------------

class Sips(PixelResizer):
    ''' sips (pre-installed on macOS) '''

    @staticmethod
    def isSupported() -> bool:
        Sips._exe = which('sips')
        return True if Sips._exe else False

    _regex = re.compile(
        rb'.*pixelWidth:([\s0-9]+).*pixelHeight:([\s0-9]+)', re.DOTALL)

    def calculateSize(self) -> Tuple[int, int]:
        res = run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight',
                   self.fname], stdout=PIPE)
        match = Sips._regex.match(res.stdout)
        w, h = map(int, match.groups()) if match else (0, 0)
        return w, h

    def resize(self, size: int, fname_out: str) -> None:
        run(['sips', '-Z', str(size), self.fname, '-o', fname_out],
            stdout=DEVNULL)


class Pillow(PixelResizer):
    ''' PIL (pip3 install Pillow) '''

    @staticmethod
    def isSupported() -> bool:
        return PILLOW_ENABLED

    def calculateSize(self) -> Tuple[int, int]:
        return Image.open(self.fname, mode='r').size  # type: ignore

    def resize(self, size: int, fname_out: str) -> None:
        Image.open(self.fname, mode='r').resize((size, size)).save(fname_out)
