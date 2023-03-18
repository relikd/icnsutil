#!/usr/bin/env python3
from typing import Tuple, Optional, List, Type, TypeVar

ResizerT = TypeVar('ResizerT', bound='Type[ImageResizer]')


def firstSupportedResizer(choices: List['ResizerT']) -> 'ResizerT':
    for x in choices:
        if x.isSupported():
            return x
    for x in choices:
        print(' NOT SUPPORTED:', (x.__doc__ or '').strip())
    raise RuntimeError('No supported image resizer found.')


# --------------------------------------------------------------------
#  Image resizer (base class)
# --------------------------------------------------------------------

class ImageResizer:
    _exe = None  # type: str # executable to be used for resize()

    @staticmethod
    def isSupported() -> bool:
        assert 0, 'Missing implementation for isSupported() method'

    def __init__(self, fname: str, preferred_size: int):
        self.fname = fname
        self.preferred_size = preferred_size
        self.actual_size = -42  # postpone calculation until needed

    @property
    def exe(self) -> str:
        return self._exe  # guaranteed by isSupported()

    @property
    def size(self) -> int:
        if self.actual_size == -42:
            w, h = self.calculateSize()
            assert w == h, 'Image dimensions must be square'
            self.actual_size = w // 2  # retina half size
        return min(self.preferred_size, self.actual_size)

    def calculateSize(self) -> Tuple[int, int]:
        assert 0, 'Missing implementation for calculateSize() method'

    def resize(self, size: int, fname_out: str) -> None:
        assert 0, 'Missing implementation for resize() method'


class SVGResizer(ImageResizer):
    def calculateSize(self) -> Tuple[int, int]:
        return 999999, 999999


class PixelResizer(ImageResizer):
    pass
