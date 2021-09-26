#!/usr/bin/env python3
'''
Namespace for the ICNS format.
@see https://en.wikipedia.org/wiki/Apple_Icon_Image_format
'''
import os  # path
from enum import Enum  # IcnsType.Role
import RawData
import PackBytes


class Role(Enum):
    DARK = b'\xFD\xD9\x2F\xA8'
    TEMPLATE = 'sbtp'
    SELECTED = 'slct'


class Media:
    __slots__ = ['key', 'types', 'size', 'channels', 'bits', 'availability',
                 'desc', 'compressable', 'retina', 'maxsize']

    def __init__(self, key, types, size=None, *,
                 ch=None, bits=None, os=None, desc=''):
        self.key = key
        self.types = types if type(types) == list else [types]
        self.size = (size, size) if type(size) == int else size
        self.availability = os
        self.desc = desc
        # computed properties
        self.compressable = self.is_type('argb') or self.is_type('rgb')
        self.retina = ('@2x' in self.desc) if self.is_type('png') else None
        if self.is_type('rgb'):
            ch = 3
            bits = 8
        if self.is_type('argb'):
            ch = 4
            bits = 8
        self.channels = ch
        self.bits = bits
        self.maxsize = None
        if size and ch and bits:
            self.maxsize = self.size[0] * self.size[1] * ch * bits // 8

    def is_type(self, typ):
        return typ in self.types

    def is_binary(self) -> bool:
        return any(x in self.types for x in ['rgb', 'bin'])

    def split_channels(self, uncompressed_data):
        if self.channels not in [3, 4]:
            raise NotImplementedError('Only RGB and ARGB data supported.')
        if len(uncompressed_data) != self.maxsize:
            raise ValueError(
                'Data does not match expected uncompressed length. '
                '{} != {}'.format(len(uncompressed_data), self.maxsize))
        per_channel = self.maxsize // self.channels
        if self.channels == 3:
            yield [255] * per_channel  # opaque alpha channel for rgb
        for i in range(self.channels):
            yield uncompressed_data[per_channel * i:per_channel * (i + 1)]

    def decompress(self, data, ext='-?-'):
        if not self.compressable:
            return data
        if ext == '-?-':
            ext = RawData.determine_file_ext(data)
        if ext == 'argb':
            return PackBytes.unpack(data[4:])  # remove ARGB header
        if ext is None or ext == 'rgb':  # RGB files dont have a magic number
            if self.key == 'it32':
                data = data[4:]  # TODO: dirty fix for it32 \x00\x00\x00\x00
            return PackBytes.unpack(data)
        return data

    def filename(self, *, key_only=False, size_only=False):
        if key_only:
            if os.path.exists(__file__.upper()):  # check case senstive
                if self.key in ['sb24', 'icsb']:
                    return self.key + '-a'
                elif self.key in ['SB24', 'icsB']:
                    return self.key + '-b'
            return f'{self.key}'  # dont return directy, may be b''-str
        else:
            if self.is_type('icns'):
                return Role(self.key).name.lower()
            if not self.size:
                return f'{self.key}'  # dont return directy, may be b''-str
            w, h = self.size
            suffix = ''
            if self.retina:
                w //= 2
                h //= 2
                suffix = '@2x'
            if size_only:
                if self.bits == 1:
                    suffix += '-mono'
            else:
                if self.desc in ['icon', 'iconmask']:
                    suffix += f'-icon{self.bits}b'
                if self.desc in ['mask', 'iconmask']:
                    suffix += f'-mask{self.bits}b'
            return f'{w}x{h}{suffix}'

    def __repr__(self):
        return '<{}: {}, {}.{}>'.format(type(self).__name__, self.key,
                                        self.filename(), self.types[0])

    def __str__(self):
        T = ''
        if self.size:
            T += '{}x{}, '.format(*self.size)
            if self.maxsize:
                T += f'{self.channels}ch@{self.bits}-bit={self.maxsize}, '
        if self.desc:
            T += f'{self.desc}, '
        return f'{self.key}: {T}macOS {self.availability or "?"}+'


_TYPES = {x.key: x for x in (
    # Read support for these:
    Media('ICON', 'bin', 32, ch=1, bits=1, os=1.0, desc='icon'),
    Media('ICN#', 'bin', 32, ch=2, bits=1, os=6.0, desc='iconmask'),
    Media('icm#', 'bin', (16, 12), ch=2, bits=1, os=6.0, desc='iconmask'),
    Media('icm4', 'bin', (16, 12), ch=1, bits=4, os=7.0, desc='icon'),
    Media('icm8', 'bin', (16, 12), ch=1, bits=8, os=7.0, desc='icon'),
    Media('ics#', 'bin', 16, ch=2, bits=1, os=6.0, desc='iconmask'),
    Media('ics4', 'bin', 16, ch=1, bits=4, os=7.0, desc='icon'),
    Media('ics8', 'bin', 16, ch=1, bits=8, os=7.0, desc='icon'),
    Media('is32', 'rgb', 16, os=8.5),
    Media('s8mk', 'bin', 16, ch=1, bits=8, os=8.5, desc='mask'),
    Media('icl4', 'bin', 32, ch=1, bits=4, os=7.0, desc='icon'),
    Media('icl8', 'bin', 32, ch=1, bits=8, os=7.0, desc='icon'),
    Media('il32', 'rgb', 32, os=8.5),
    Media('l8mk', 'bin', 32, ch=1, bits=8, os=8.5, desc='mask'),
    Media('ich#', 'bin', 48, ch=2, bits=1, os=8.5, desc='iconmask'),
    Media('ich4', 'bin', 48, ch=1, bits=4, os=8.5, desc='icon'),
    Media('ich8', 'bin', 48, ch=1, bits=8, os=8.5, desc='icon'),
    Media('ih32', 'rgb', 48, os=8.5),
    Media('h8mk', 'bin', 48, ch=1, bits=8, os=8.5, desc='mask'),
    Media('it32', 'rgb', 128, os=10.0),
    Media('t8mk', 'bin', 128, ch=1, bits=8, os=10.0, desc='mask'),
    # Write support for these:
    Media('icp4', ['png', 'jp2', 'rgb'], 16, os=10.7),
    Media('icp5', ['png', 'jp2', 'rgb'], 32, os=10.7),
    Media('icp6', 'png', 64, os=10.7),
    Media('ic07', ['png', 'jp2'], 128, os=10.7),
    Media('ic08', ['png', 'jp2'], 256, os=10.5),
    Media('ic09', ['png', 'jp2'], 512, os=10.5),
    Media('ic10', ['png', 'jp2'], 1024, os=10.7, desc='or 512x512@2x (10.8)'),
    Media('ic11', ['png', 'jp2'], 32, os=10.8, desc='16x16@2x'),
    Media('ic12', ['png', 'jp2'], 64, os=10.8, desc='32x32@2x'),
    Media('ic13', ['png', 'jp2'], 256, os=10.8, desc='128x128@2x'),
    Media('ic14', ['png', 'jp2'], 512, os=10.8, desc='256x256@2x'),
    Media('ic04', 'argb', 16, os=11.0),
    Media('ic05', 'argb', 32, os=11.0),
    Media('icsb', 'argb', 18, os=11.0),
    Media('icsB', ['png', 'jp2'], 36, desc='18x18@2x'),
    Media('sb24', ['png', 'jp2'], 24),
    Media('SB24', ['png', 'jp2'], 48, desc='24x24@2x'),
    # ICNS media files
    Media(Role.TEMPLATE.value, 'icns', desc='"template" icns'),
    Media(Role.SELECTED.value, 'icns', desc='"selected" icns'),
    Media(Role.DARK.value, 'icns', os=10.14, desc='"dark" icns'),
    # Meta types:
    Media('TOC ', 'bin', os=10.7, desc='Table of Contents'),
    Media('icnV', 'bin', desc='4-byte Icon Composer.app bundle version'),
    Media('name', 'bin', desc='Unknown'),
    Media('info', 'plist', desc='Info binary plist'),
)}


def enum_img_mask_pairs(available_keys):
    for mask_k, *imgs in [  # list probably never changes, ARGB FTW
        ('s8mk', 'is32', 'ics8', 'ics4', 'icp4'),
        ('l8mk', 'il32', 'icl8', 'icl4', 'icp5'),
        ('h8mk', 'ih32', 'ich8', 'ich4'),
        ('t8mk', 'it32'),
    ]:
        if mask_k not in available_keys:
            mask_k = None
        any_img = False
        for img_k in imgs:
            if img_k in available_keys:
                any_img = True
                yield img_k, mask_k
        if mask_k and not any_img:
            yield None, mask_k


def enum_png_convertable(available_keys):
    ''' Yield (image-key, mask-key or None) '''
    for img in _TYPES.values():
        if img.key not in available_keys:
            continue
        if img.is_type('argb') or img.bits == 1:  # allow mono icons
            yield img.key, None
        elif img.is_type('rgb'):
            mask_key = None
            for mask in _TYPES.values():
                if mask.key not in available_keys:
                    continue
                if mask.desc == 'mask' and mask.size == img.size:
                    mask_key = mask.key
                    break
            yield img.key, mask_key


def get(key):  # support for IcnsType[key]
    try:
        return _TYPES[key]
    except KeyError:
        pass
    raise NotImplementedError(f'Unsupported icns type "{key}"')


def match_maxsize(maxsize, typ):
    for x in _TYPES.values():
        if x.is_type(typ) and x.maxsize == maxsize:
            return x  # TODO: handle cases with multiple options? eg: is32 icp4
    return None


def guess(data, filename=None):
    '''
    Guess icns media type by analyzing the raw data + file naming convention.
    Use:
    - @2x.png or @2x.jp2 for retina images
    - directly name the file with the corresponding icns-key
    - or {selected|template|dark}.icns to select the proper icns key.
    '''
    # Set type directly via filename
    if filename:
        bname = os.path.splitext(os.path.basename(filename))[0]
        if bname in _TYPES:
            return _TYPES[bname]

    ext = RawData.determine_file_ext(data)
    # Icns specific names
    if ext == 'icns' and filename:
        for candidate in Role:
            if filename.endswith(f'{candidate.name.lower()}.icns'):
                return _TYPES[candidate.value]
        # if not found, fallback and output all options

    # Guess by image size and retina flag
    size = RawData.determine_image_size(data, ext)  # None for non-image types
    retina = None
    if ext in ['png', 'jp2']:
        retina = bname.lower().endswith('@2x') if filename else False

    choices = []
    for x in _TYPES.values():
        if size != x.size:  # currently no support for RGB and binary data
            continue
        if ext and not x.is_type(ext):
            continue
        if retina is not None and retina != x.retina:
            continue
        choices.append(x)

    if len(choices) == 1:
        return choices[0]
    raise ValueError('Could not determine type – one of {} -- {}'.format(
        [x.key for x in choices],
        {'type': ext, 'size': size, 'retina': retina}))
