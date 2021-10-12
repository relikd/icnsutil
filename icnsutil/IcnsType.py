#!/usr/bin/env python3
'''
Namespace for the ICNS format.
@see https://en.wikipedia.org/wiki/Apple_Icon_Image_format
'''
import os  # path
from typing import Union, Optional, Tuple, Iterator, List, Iterable, Dict
from . import PackBytes, RawData


class CanNotDetermine(Exception):
    pass


class Media:
    KeyT = Union[str, bytes]
    __slots__ = ['key', 'types', 'size', 'channels', 'bits', 'availability',
                 'desc', 'compressable', 'retina', 'maxsize', 'ext_certain']

    def __init__(self, key: KeyT, types: list,
                 size: Optional[Union[int, Tuple[int, int]]] = None,
                 *, ch: Optional[int] = None, bits: Optional[int] = None,
                 os: Optional[float] = None, desc: str = '') -> None:
        self.key = key
        self.types = types
        self.size = (size, size) if isinstance(size, int) else size
        self.availability = os
        self.desc = desc
        # computed properties
        self.compressable = self.is_type('argb') or self.is_type('rgb')
        self.retina = '@2x' in self.desc
        if self.is_type('rgb'):
            ch = 3
            bits = 8
        if self.is_type('argb'):
            ch = 4
            bits = 8
        self.channels = ch
        self.bits = bits
        self.maxsize = None  # type: Optional[int]
        if self.size and ch and bits:
            self.maxsize = self.size[0] * self.size[1] * ch * bits // 8
        self.ext_certain = all(x in ['png', 'argb', 'plist', 'jp2', 'icns']
                               for x in self.types)

    def is_type(self, typ: str) -> bool:
        return typ in self.types

    def is_binary(self) -> bool:
        return any(x in self.types for x in ['rgb', 'bin'])

    def fallback_ext(self) -> str:
        if self.channels in [1, 2]:
            return self.desc  # guaranteed to be icon, mask, or iconmask
        return self.types[-1]

    def decompress(self, data: bytes, ext: Optional[str] = '-?-') -> Optional[
            List[int]]:
        ''' Returns None if media is not decompressable. '''
        if self.compressable:
            if ext == '-?-':
                ext = RawData.determine_file_ext(data)
            if ext == 'argb':
                return PackBytes.unpack(data[4:])  # remove ARGB header
            if ext is None or ext == 'rgb':  # RGB files dont have magic number
                if self.key == 'it32':
                    data = data[4:]
                return PackBytes.unpack(data)
        return None

    def filename(self, *, key_only: bool = False, size_only: bool = False) \
            -> str:
        if key_only:
            if os.path.exists(__file__.upper()):  # check case senstive
                if self.key in ['sb24', 'icsb']:
                    return self.key + '-a'  # type: ignore
                elif self.key in ['SB24', 'icsB']:
                    return self.key + '-b'  # type: ignore
            return str(self.key)  # dont return directy, may be b''-str
        else:
            if self.is_type('icns'):
                return self.desc
            if not self.size:
                return str(self.key)  # dont return directy, may be b''-str
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
                    suffix += '-icon{}b'.format(self.bits)
                if self.desc in ['mask', 'iconmask']:
                    suffix += '-mask{}b'.format(self.bits)
            return '{}x{}{}'.format(w, h, suffix)

    def __repr__(self) -> str:
        return '<{}: {}, {}.{}>'.format(
            type(self).__name__, str(self.key), self.filename(), self.types[0])

    def __str__(self) -> str:
        T = ''
        if self.size:
            T += '{}x{}, '.format(*self.size)
            if self.maxsize:
                T += '{}ch@{}-bit={}, '.format(
                    self.channels, self.bits, self.maxsize)
        if self.desc:
            T += self.desc + ', '
        return '{}: {}macOS {}+'.format(
            str(self.key), T, self.availability or '?')


_TYPES = {x.key: x for x in (
    # Read support for these:
    Media('ICON', ['bin'], 32, ch=1, bits=1, os=1.0, desc='icon'),
    Media('ICN#', ['bin'], 32, ch=2, bits=1, os=6.0, desc='iconmask'),
    Media('icm#', ['bin'], (16, 12), ch=2, bits=1, os=6.0, desc='iconmask'),
    Media('icm4', ['bin'], (16, 12), ch=1, bits=4, os=7.0, desc='icon'),
    Media('icm8', ['bin'], (16, 12), ch=1, bits=8, os=7.0, desc='icon'),
    Media('ics#', ['bin'], 16, ch=2, bits=1, os=6.0, desc='iconmask'),
    Media('ics4', ['bin'], 16, ch=1, bits=4, os=7.0, desc='icon'),
    Media('ics8', ['bin'], 16, ch=1, bits=8, os=7.0, desc='icon'),
    Media('is32', ['rgb'], 16, os=8.5),
    Media('s8mk', ['bin'], 16, ch=1, bits=8, os=8.5, desc='mask'),
    Media('icl4', ['bin'], 32, ch=1, bits=4, os=7.0, desc='icon'),
    Media('icl8', ['bin'], 32, ch=1, bits=8, os=7.0, desc='icon'),
    Media('il32', ['rgb'], 32, os=8.5),
    Media('l8mk', ['bin'], 32, ch=1, bits=8, os=8.5, desc='mask'),
    Media('ich#', ['bin'], 48, ch=2, bits=1, os=8.5, desc='iconmask'),
    Media('ich4', ['bin'], 48, ch=1, bits=4, os=8.5, desc='icon'),
    Media('ich8', ['bin'], 48, ch=1, bits=8, os=8.5, desc='icon'),
    Media('ih32', ['rgb'], 48, os=8.5),
    Media('h8mk', ['bin'], 48, ch=1, bits=8, os=8.5, desc='mask'),
    Media('it32', ['rgb'], 128, os=10.0),
    Media('t8mk', ['bin'], 128, ch=1, bits=8, os=10.0, desc='mask'),
    # Write support for these:
    Media('icp4', ['png', 'jp2', 'rgb'], 16, os=10.7),
    Media('icp5', ['png', 'jp2', 'rgb'], 32, os=10.7),
    Media('icp6', ['png'], 64, os=10.7),
    Media('ic07', ['png', 'jp2'], 128, os=10.7),
    Media('ic08', ['png', 'jp2'], 256, os=10.5),
    Media('ic09', ['png', 'jp2'], 512, os=10.5),
    Media('ic10', ['png', 'jp2'], 1024, os=10.7, desc='or 512x512@2x (10.8)'),
    Media('ic11', ['png', 'jp2'], 32, os=10.8, desc='16x16@2x'),
    Media('ic12', ['png', 'jp2'], 64, os=10.8, desc='32x32@2x'),
    Media('ic13', ['png', 'jp2'], 256, os=10.8, desc='128x128@2x'),
    Media('ic14', ['png', 'jp2'], 512, os=10.8, desc='256x256@2x'),
    Media('ic04', ['argb', 'png', 'jp2'], 16, os=11.0),  # ARGB is macOS 11+
    Media('ic05', ['argb', 'png', 'jp2'], 32, os=11.0),
    Media('icsb', ['argb', 'png', 'jp2'], 18, os=11.0),
    Media('icsB', ['png', 'jp2'], 36, desc='18x18@2x'),
    Media('sb24', ['png', 'jp2'], 24),
    Media('SB24', ['png', 'jp2'], 48, desc='24x24@2x'),
    # ICNS media files
    Media('sbtp', ['icns'], desc='template'),
    Media('slct', ['icns'], desc='selected'),
    Media(b'\xFD\xD9\x2F\xA8', ['icns'], os=10.14, desc='dark'),
    # Meta types:
    Media('TOC ', ['bin'], os=10.7, desc='Table of Contents'),
    Media('icnV', ['bin'], desc='4-byte Icon Composer.app bundle version'),
    Media('name', ['bin'], desc='Unknown'),
    Media('info', ['plist'], desc='Info binary plist'),
)}  # type: Dict[Media.KeyT, Media]


def enum_img_mask_pairs(available_keys: Iterable[Media.KeyT]) -> Iterator[
        Tuple[Optional[str], Optional[str]]]:
    for mask_k, *imgs in [  # list probably never changes, ARGB FTW
        ('s8mk', 'is32', 'ics8', 'ics4', 'icp4'),
        ('l8mk', 'il32', 'icl8', 'icl4', 'icp5'),
        ('h8mk', 'ih32', 'ich8', 'ich4'),
        ('t8mk', 'it32'),
    ]:
        mk = mask_k if mask_k in available_keys else None
        any_img = False
        for img_k in imgs:
            if img_k in available_keys:
                any_img = True
                yield img_k, mk
        if mk and not any_img:
            yield None, mk


def enum_png_convertable(available_keys: Iterable[Media.KeyT]) -> Iterator[
        Tuple[Media.KeyT, Optional[Media.KeyT]]]:
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


def get(key: Media.KeyT) -> Media:
    try:
        return _TYPES[key]
    except KeyError:
        pass
    raise NotImplementedError('Unsupported icns type "' + str(key) + '"')


def key_from_readable(key: str) -> Media.KeyT:
    key_mapping = {
        'dark': b'\xFD\xD9\x2F\xA8',
        'selected': 'slct',
        'template': 'sbtp',
        'toc': 'TOC ',
    }  # type: Dict[str, Media.KeyT]
    return key_mapping.get(key.lower(), key)


def match_maxsize(total: int, typ: str) -> Media:
    assert(typ == 'argb' or typ == 'rgb')
    ret = [x for x in _TYPES.values() if x.is_type(typ) and x.maxsize == total]
    return _best_option(ret, typ)


def guess(data: bytes, filename: Optional[str] = None) -> Media:
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

    # Filter attributes
    desc = None
    size = None
    maxsize = None
    retina = False

    # Guess extension
    ext = RawData.determine_file_ext(data)
    if not ext and filename:
        if filename.endswith('.rgb'):
            ext = 'rgb'
        elif filename.endswith('.mask'):
            maxsize = len(data)
            desc = 'mask'

    # Guess image size
    if ext:
        size = RawData.determine_image_size(data, ext)

    # if filename is set, then bname is also set (see above)
    if filename:
        # Guess retina flag
        retina = bname.lower().endswith('@2x')
        # Guess icns-specific type
        if ext == 'icns':
            for candidate in ['template', 'selected', 'dark']:
                if bname.endswith(candidate):
                    desc = candidate
                    break

    # stupid double usage of ic10, enforce retina flag
    if size == (1024, 1024):
        retina = True

    choices = []
    for x in _TYPES.values():
        if retina != x.retina:  # png + jp2
            continue
        if desc and desc != x.desc:  # icns or rgb-mask
            continue
        if ext:
            if size != x.size or not x.is_type(ext):
                continue
        else:  # not ext
            if x.ext_certain:
                continue
            if maxsize and x.maxsize and maxsize != x.maxsize:  # mask only
                continue
        choices.append(x)

    return _best_option(choices, ext)


def _best_option(choices: List[Media], ext: Optional[str] = None) -> Media:
    '''
    Get most favorable media type.
    If more than one option exists, choose based on order index of ext.
    '''
    if len(choices) == 1:
        return choices[0]
    # Try get most favorable type (sort order of types)
    if ext:
        best_i = 99
        best_choice = []
        for x in choices:
            i = x.types.index(ext)
            if i < best_i:
                best_i = i
                best_choice = [x]
            elif i == best_i:
                best_choice.append(x)
        if len(best_choice) == 1:
            return best_choice[0]
        choices = best_choice

    raise CanNotDetermine('Could not determine type – one of {}.'.format(
        [x.key for x in choices]))
