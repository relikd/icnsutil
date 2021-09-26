#!/usr/bin/env python3
import PackBytes  # pack, unpack, msb_stream
import IcnsType  # match_maxsize
try:
    from PIL import Image
    PIL_ENABLED = True
except ImportError:
    PIL_ENABLED = False


class ArgbImage:
    __slots__ = ['a', 'r', 'g', 'b', 'size', 'channels']

    @classmethod
    def from_mono(cls, data, iType):
        assert(iType.bits == 1)
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

    def __init__(self, *, data=None, file=None, mask=None):
        '''
        Provide either a filename or raw binary data.
        - mask : Optional, may be either binary data or filename
        '''
        if file:
            self.load_file(file)
        elif data:
            self.load_data(data)
        else:
            raise AttributeError('Neither data nor file provided.')
        if mask:
            if type(mask) == bytes:
                self.load_mask(data=mask)
            else:
                self.load_mask(file=mask)

    def load_file(self, fname):
        with open(fname, 'rb') as fp:
            if fp.read(4) == b'\x89PNG':
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

    def load_data(self, data):
        ''' Has support for ARGB and RGB-channels files. '''
        is_argb = data[:4] == b'ARGB'
        if is_argb or data[:4] == b'\x00\x00\x00\x00':
            data = data[4:]  # remove ARGB and it32 header

        data = PackBytes.unpack(data)
        iType = IcnsType.match_maxsize(len(data), 'argb' if is_argb else 'rgb')
        if not iType:
            raise ValueError('No (A)RGB image data. Could not determine size.')

        self.size = iType.size
        self.channels = iType.channels
        self.a, self.r, self.g, self.b = iType.split_channels(data)

    def load_mask(self, *, file=None, data=None):
        ''' Data must be uncompressed and same length as a single channel! '''
        if file:
            with open(file, 'rb') as fp:
                data = fp.read()
        if not data:
            raise AttributeError('Neither data nor file provided.')

        assert(len(data) == len(self.r))
        self.a = data

    def mask_data(self, bits=8, *, compress=False):
        if bits == 8:  # default for rgb and argb
            return PackBytes.pack(self.a) if compress else bytes(self.a)
        return bytes(PackBytes.msb_stream(self.a, bits=bits))

    def rgb_data(self, *, compress=True):
        return b''.join(self._raw_rgb_channels(compress=compress))

    def argb_data(self, *, compress=True):
        return b'ARGB' + self.mask_data(compress=compress) + \
            b''.join(self._raw_rgb_channels(compress=compress))

    def _raw_rgb_channels(self, *, compress=True):
        for x in (self.r, self.g, self.b):
            yield PackBytes.pack(x) if compress else bytes(x)

    def _load_png(self, fname):
        if not PIL_ENABLED:
            raise ImportError('Install Pillow to support PNG conversion.')
        img = Image.open(fname, mode='r')
        self.size = img.size
        self.a = []
        self.r = []
        self.g = []
        self.b = []
        w, h = img.size
        for y in range(h):
            for x in range(w):
                px = img.getpixel((x, y))
                if type(px) == int:
                    px = (px, px, px)  # convert mono to rgb
                if len(px) == 3:
                    px = px + (0xFF,)  # convert rgb to rgba
                r, g, b, a = px
                self.a.append(a)
                self.r.append(r)
                self.g.append(g)
                self.b.append(b)

    def write_png(self, fname):
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

    def __repr__(self):
        typ = ['', 'Mono', 'Mono with Mask', 'RGB', 'RGBA'][self.channels]
        return f'<{type(self).__name__}: {self.size[0]}x{self.size[1]} {typ}>'
