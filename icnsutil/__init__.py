#!/usr/bin/env python3
__version__ = '1.0'

import sys
if __name__ != '__main__':
    sys.path.insert(0, __path__[0])

# static modules
import IcnsType
import PackBytes
import RawData
# class modules
from ArgbImage import ArgbImage, PIL_ENABLED
from IcnsFile import IcnsFile
