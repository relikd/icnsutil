#!/usr/bin/env python3
import os
from .ImageResizer import firstSupportedResizer
from .PixelResizer import Sips, Pillow
from .SVGResizer import ReSVG, ChromeSVG
from typing import TYPE_CHECKING, List, Optional, Type
if TYPE_CHECKING:
    from .ImageResizer import ImageResizer, SVGResizer, PixelResizer

# order matters! First supported resizer is returned. Prefer faster ones.

SVG_RESIZERS = [
    ReSVG,
    ChromeSVG,
]  # type: List[Type[SVGResizer]]
PX_RESIZERS = [
    Sips,
    Pillow,
]  # type: List[Type[PixelResizer]]

BEST_SVG = None  # type: Optional[Type[SVGResizer]]
BEST_PX = None  # type: Optional[Type[PixelResizer]]


def bestImageResizer(fname: str, preferred_size: int) -> 'ImageResizer':
    global BEST_SVG, BEST_PX
    ext = os.path.splitext(fname)[1].lower()
    if ext == '.svg':
        BEST_SVG = BEST_SVG or firstSupportedResizer(SVG_RESIZERS)
        assert BEST_SVG, 'No supported image resizer found for ' + ext
        return BEST_SVG(fname, preferred_size)
    else:
        BEST_PX = BEST_PX or firstSupportedResizer(PX_RESIZERS)
        assert BEST_PX, 'No supported image resizer found for ' + ext
        return BEST_PX(fname, preferred_size)
