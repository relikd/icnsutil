#!/usr/bin/env python3
'''
A fully-featured python library to handle reading and writing icns files.
'''
__version__ = '1.0.1'

from .IcnsFile import IcnsFile
from .ArgbImage import ArgbImage, PIL_ENABLED
from . import IcnsType, PackBytes, RawData
