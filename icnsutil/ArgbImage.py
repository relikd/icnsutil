#!/usr/bin/env python3
from typing import Union, Optional
from math import sqrt
from . import IcnsType, PackBytes, RawData
try:
    from PIL import Image
    PIL_ENABLED = True
except ImportError:
    PIL_ENABLED = False


class ArgbImage:
    __slots__ = ['a', 'r', 'g', 'b', 'size', 'channels']

    @classmethod
    def from_mono(cls, data: bytes, iType: IcnsType.Media) -> 'ArgbImage':
        ''' Load monochrome 1-bit image with or without mask. '''
        assert(iType.bits == 1)
        assert(iType.size)
        assert(iType.channels)
        img = []
        for byte in data:
            for i in range(7, -1, -1):
                img.append(255 if byte & (1 << i) else 0)
        self = object.__new__(cls)
        self.size = iType.size
        self.channels = iType.channels
        if iType.channels == 2:
            self.a = img[len(img) // 2:]
            img = img[:len(img) // 2]
        else:
            self.a = [255] * len(img)
        self.r, self.g, self.b = img, img, img
        return self

    def __init__(
        self,
        *,
        data: Optional[bytes] = None,
        file: Optional[str] = None,
        image: Optional['Image.Image'] = None,
        mask: Union[bytes, str, None] = None,
    ) -> None:
        '''
        Provide either a filename or raw binary data.
        - mask : Optional, may be either binary data or filename
        '''
        self.size = (0, 0)
        self.channels = 0
        if file:
            self.load_file(file)
        elif data:
            self.load_data(data)
        elif image:
            self._load_pillow_image(image)
        else:
            raise AttributeError('Neither data nor file provided.')
        if mask:
            if isinstance(mask, bytes):
                self.load_mask(data=mask)
            else:
                self.load_mask(file=mask)

    def load_file(self, fname: str) -> None:
        with open(fname, 'rb') as fp:
            if RawData.determine_file_ext(fp.read(8)) in ['png', 'jp2']:
                self._load_png(fname)
                return
            # else
            fp.seek(0)
            data = fp.read()
        try:
            self.load_data(data)
            return
        except Exception as e:
            tmp = e  # ignore previous exception to create a new one
        raise type(tmp)('{} File: "{}"'.format(str(tmp), fname))

    def load_data(self, data: bytes) -> None:
        ''' Has support for ARGB and RGB-channels files. '''
        is_argb = data[:4] == b'ARGB'
        if is_argb or data[:4] == b'\x00\x00\x00\x00':
            data = data[4:]  # remove ARGB and it32 header

        uncompressed_data = PackBytes.unpack(data)

        self.channels = 4 if is_argb else 3
        per_channel = len(uncompressed_data) // self.channels
        w = sqrt(per_channel)
        if w != int(w):
            raise NotImplementedError(
                'Could not determine square image size. Or unknown type.')
        self.size = (int(w), int(w))
        if self.channels == 3:
            self.a = [255] * per_channel  # opaque alpha channel for rgb
        else:
            self.a = uncompressed_data[:per_channel]
        i = 1 if is_argb else 0
        self.r = uncompressed_data[(i + 0) * per_channel:(i + 1) * per_channel]
        self.g = uncompressed_data[(i + 1) * per_channel:(i + 2) * per_channel]
        self.b = uncompressed_data[(i + 2) * per_channel:(i + 3) * per_channel]

    def load_mask(
        self, *, file: Optional[str] = None, data: Optional[bytes] = None,
    ) -> None:
        ''' Data must be uncompressed and same length as a single channel! '''
        if file:
            with open(file, 'rb') as fp:
                data = fp.read()
        else:
            assert(isinstance(data, bytes))
        if not data:
            raise AttributeError('Neither data nor file provided.')

        assert(len(data) == len(self.r))
        self.a = list(data)

    def mask_data(self, bits: int = 8, *, compress: bool = False) -> bytes:
        if bits == 8:  # default for rgb and argb
            return PackBytes.pack(self.a) if compress else bytes(self.a)
        return bytes(PackBytes.msb_stream(self.a, bits=bits))

    def rgb_data(self, *, compress: bool = True) -> bytes:
        return b''.join(PackBytes.pack(x) if compress else bytes(x)
                        for x in (self.r, self.g, self.b))

    def argb_data(self, *, compress: bool = True) -> bytes:
        return b'ARGB' + self.mask_data(compress=compress) \
                       + self.rgb_data(compress=compress)

    def _load_png(self, fname: str) -> None:
        if not PIL_ENABLED:
            raise ImportError('Install Pillow to support PNG conversion.')
        self._load_pillow_image(Image.open(fname, mode='r'))

    def _load_pillow_image(self, image: 'Image.Image') -> None:
        img = image.convert('RGBA')
        self.size = img.size
        self.channels = 4
        self.a = []
        self.r = []
        self.g = []
        self.b = []
        for r, g, b, a in img.getdata():
            self.a.append(a)
            self.r.append(r)
            self.g.append(g)
            self.b.append(b)

    def write_png(self, fname: str) -> None:
        if not PIL_ENABLED:
            raise ImportError('Install Pillow to support PNG conversion.')
        img = Image.new(mode='RGBA', size=self.size)
        w, h = self.size
        for y in range(h):
            for x in range(w):
                i = y * w + x
                img.putpixel(
                    (x, y), (self.r[i], self.g[i], self.b[i], self.a[i]))
        img.save(fname)

    def __repr__(self) -> str:
        typ = ['', 'Mono', 'Mono with Mask', 'RGB', 'RGBA'][self.channels]
        return '<{}: {}x{} {}>'.format(
            type(self).__name__, self.size[0], self.size[1], typ)
