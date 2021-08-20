#!/usr/bin/env python3
import os
import sys
import struct


class IcnsType(object):
    '''
    Namespace for the ICNS format.
    '''
    # https://en.wikipedia.org/wiki/Apple_Icon_Image_format
    TYPES = {
        'ICON': (32, '32×32 1-bit mono icon'),
        'ICN#': (32, '32×32 1-bit mono icon with 1-bit mask'),
        'icm#': (16, '16×12 1 bit mono icon with 1-bit mask'),
        'icm4': (16, '16×12 4 bit icon'),
        'icm8': (16, '16×12 8 bit icon'),
        'ics#': (16, '16×16 1-bit mask'),
        'ics4': (16, '16×16 4-bit icon'),
        'ics8': (16, '16x16 8 bit icon'),
        'is32': (16, '16×16 24-bit icon'),
        's8mk': (16, '16x16 8-bit mask'),
        'icl4': (32, '32×32 4-bit icon'),
        'icl8': (32, '32×32 8-bit icon'),
        'il32': (32, '32x32 24-bit icon'),
        'l8mk': (32, '32×32 8-bit mask'),
        'ich#': (48, '48×48 1-bit mask'),
        'ich4': (48, '48×48 4-bit icon'),
        'ich8': (48, '48×48 8-bit icon'),
        'ih32': (48, '48×48 24-bit icon'),
        'h8mk': (48, '48×48 8-bit mask'),
        'it32': (128, '128×128 24-bit icon'),
        't8mk': (128, '128×128 8-bit mask'),
        'icp4': (16, '16x16 icon in JPEG 2000 or PNG format'),
        'icp5': (32, '32x32 icon in JPEG 2000 or PNG format'),
        'icp6': (64, '64x64 icon in JPEG 2000 or PNG format'),
        'ic07': (128, '128x128 icon in JPEG 2000 or PNG format'),
        'ic08': (256, '256×256 icon in JPEG 2000 or PNG format'),
        'ic09': (512, '512×512 icon in JPEG 2000 or PNG format'),
        'ic10': (1024, '1024×1024 in 10.7 (or 512x512@2x "retina" in 10.8) icon in JPEG 2000 or PNG format'),
        'ic11': (32, '16x16@2x "retina" icon in JPEG 2000 or PNG format'),
        'ic12': (64, '32x32@2x "retina" icon in JPEG 2000 or PNG format'),
        'ic13': (256, '128x128@2x "retina" icon in JPEG 2000 or PNG format'),
        'ic14': (512, '256x256@2x "retina" icon in JPEG 2000 or PNG format'),
        'ic04': (16, '16x16 ARGB'),
        'ic05': (32, '32x32 ARGB'),
        'icsB': (36, '36x36'),
        'icsb': (18, '18x18 '),

        'TOC ': (0, '"Table of Contents" a list of all image types in the file, and their sizes (added in Mac OS X 10.7)'),
        'icnV': (0, '4-byte big endian float - equal to the bundle version number of Icon Composer.app that created to icon'),
        'name': (0, 'Unknown'),
        'info': (0, 'Info binary plist. Usage unknown'),
    }

    @staticmethod
    def size_of(x):
        return IcnsType.TYPES[x][0]

    @staticmethod
    def is_bitmap(x):
        return x in ['ICON', 'ICN#', 'icm#', 'icm4', 'icm8', 'ics#', 'ics4',
                     'ics8', 'is32', 's8mk', 'icl4', 'icl8', 'il32', 'l8mk',
                     'ich#', 'ich4', 'ich8', 'ih32', 'h8mk', 'it32', 't8mk']

    @staticmethod
    def is_retina(x):  # all of these are macOS 10.8+
        return x in ['ic10', 'ic11', 'ic12', 'ic13', 'ic14']

    @staticmethod
    def is_argb(x):
        return x in ['ic04', 'ic05']

    @staticmethod
    def is_meta(x):
        return x in ['TOC ', 'icnV', 'name', 'info']

    @staticmethod
    def is_compressable(x):
        return x in ['is32', 'il32', 'ih32', 'it32', 'ic04', 'ic05']

    @staticmethod
    def is_mask(x):
        return x.endswith('mk') or x.endswith('#')

    @staticmethod
    def description(x):
        size = IcnsType.size_of(x)
        if size == 0:
            return f'{x}'
        if IcnsType.is_mask(x):
            return f'{size}-mask'
        if IcnsType.is_retina(x):
            return f'{size // 2}@2x'
        return f'{size}'

    @staticmethod
    def guess_type(size, retina):
        tmp = [(k, v[-1]) for k, v in IcnsType.TYPES.items() if v[0] == size]
        # Support only PNG/JP2k types
        tmp = [k for k, desc in tmp if desc.endswith('PNG format')]
        for x in tmp:
            if retina == IcnsType.is_retina(x):
                return x
        return tmp[0]


def extract(fname, *, png_only=False):
    '''
    Read an ICNS file and export all media entries to the same directory.
    '''
    with open(fname, 'rb') as fpr:
        def read_img():
            # Read ICNS type
            kind = fpr.read(4).decode('utf8')
            if kind == '':
                return None, None, None

            # Read media byte size (incl. +8 for header)
            size = struct.unpack('>I', fpr.read(4))[0]
            # Determine file format
            data = fpr.read(size - 8)
            if data[1:4] == b'PNG':
                ext = 'png'
            elif data[:6] == b'bplist':
                ext = 'plist'
            elif IcnsType.is_argb(kind):
                ext = 'argb'
            else:
                ext = 'bin'
                if not (IcnsType.is_bitmap(kind) or IcnsType.is_meta(kind)):
                    print('Unsupported image format', data[:6], 'for', kind)

            # Optional args
            if png_only and ext != 'png':
                data = None

            # Write data out to a file
            if data:
                suffix = IcnsType.description(kind)
                with open(f'{fname}-{suffix}.{ext}', 'wb') as fpw:
                    fpw.write(data)
            return kind, size, data

        # Check whether it is an actual ICNS file
        ext = fpr.read(4)
        if ext != b'icns':
            raise ValueError('Not an ICNS file.')

        # Ignore total size
        _ = struct.unpack('>I', fpr.read(4))[0]
        # Read media entries as long as there is something to read
        while True:
            kind, size, data = read_img()
            if not kind:
                break
            print(f'{kind}: {size} bytes, {IcnsType.description(kind)}')


def compose(fname, images, *, toc=True):
    '''
    Create a new ICNS file from multiple PNG source files.
    Retina images should be ending in "@2x".
    '''
    def image_dimensions(fname):
        with open(fname, 'rb') as fp:
            head = fp.read(8)
            if head == b'\x89PNG\x0d\x0a\x1a\x0a':  # PNG
                _ = fp.read(8)
                return struct.unpack('>ii', fp.read(8))
            elif head == b'\x00\x00\x00\x0CjP  ':  # JPEG 2000
                raise ValueError('JPEG 2000 is not supported!')
            else:  # ICNS does not support other types (except binary and argb)
                raise ValueError('Unsupported image format.')

    book = []
    for x in images:
        # Determine ICNS type
        w, h = image_dimensions(x)
        if w != h:
            raise ValueError(f'Image must be square! {x} is {w}x{h} instead.')
        is_retina = x.endswith('@2x.png')
        kind = IcnsType.guess_type(w, is_retina)
        # Check if type is unique
        if any(True for x, _, _ in book if x == kind):
            raise ValueError(f'Image with same size ({kind}). File: {x}')
        # Read image data
        with open(x, 'rb') as fp:
            data = fp.read()
            book.append((kind, len(data) + 8, data))  # + data header

    total = sum(x for _, x, _ in book) + 8  # + file header
    with open(fname, 'wb') as fp:
        # Magic number
        fp.write(b'icns')
        # Total file size
        if toc:
            toc_size = len(book) * 8 + 8
            total += toc_size
        fp.write(struct.pack('>I', total))
        # Table of contents (if enabled)
        if toc:
            fp.write(b'TOC ')
            fp.write(struct.pack('>I', toc_size))
            for kind, size, _ in book:
                fp.write(kind.encode('utf8'))
                fp.write(struct.pack('>I', size))
        # Media files
        for kind, size, data in book:
            fp.write(kind.encode('utf8'))
            fp.write(struct.pack('>I', size))
            fp.write(data)


# Main entry

def show_help():
    print('''Usage:
  extract: {0} input.icns [--png-only]
           --png-only: Do not extract ARGB, binary, and meta files.

  compose: {0} output.icns [-f] [--no-toc] 16.png 16@2x.png ...
           -f: Force overwrite output file.
           --no-toc: Do not write TOC to file.

Note: Icon dimensions are read directly from file.
However, the suffix "@2x" will set the retina flag accordingly.
'''.format(os.path.basename(sys.argv[0])))
    exit(0)


def main():
    args = sys.argv[1:]

    # Parse optional args
    def has_arg(x):
        if x in args:
            args.remove(x)
            return True
    force = has_arg('-f')
    png_only = has_arg('--png-only')
    no_toc = has_arg('--no-toc')

    # Check for valid syntax
    if not args:
        return show_help()

    target, *media = args
    try:
        # Compose new icon
        if media:
            if not os.path.splitext(target)[1]:
                target += '.icns'  # for the lazy people
            if not force and os.path.exists(target):
                raise IOError(f'File "{target}" already exists. Force overwrite with -f.')
            compose(target, media, toc=not no_toc)
        # Extract from existing icon
        else:
            if not os.path.isfile(target):
                raise IOError(f'File "{target}" does not exist.')
            extract(target, png_only=png_only)

    except Exception as x:
        print(x)
        exit(1)


main()
