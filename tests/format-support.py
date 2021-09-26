#!/usr/bin/env python3
import os
import sys
import zipfile
from random import randint
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from icnsutil import IcnsFile, PackBytes


def main():
    # generate_raw_rgb()
    generate_icns()
    generate_random_it32_header()
    print('Done.')


INFO = {
    16: ['is32', 'icp4', 'ic04'],
    18: ['icsb'],
    24: ['sb24'],
    32: ['il32', 'icp5', 'ic11', 'ic05'],
    36: ['icsB'],
    48: ['ih32', 'SB24'],
    64: ['icp6', 'ic12'],
    128: ['it32', 'ic07'],
    256: ['ic08', 'ic13'],
    512: ['ic09', 'ic14'],
    1024: ['ic10'],
}


def generate_raw_rgb():
    def testpattern(w, h, *, ch, compress=True):
        ARGB = ch == 4
        sz = w * h
        if compress:
            pattern = [0, 0, 0, 0, 255, 255] * sz
            a = PackBytes.pack([255] * sz) if ARGB else b''
            r = PackBytes.pack(pattern[4:sz + 4])
            g = PackBytes.pack(pattern[2:sz + 2])
            b = PackBytes.pack(pattern[:sz])
        else:
            pattern = b'\x00\x00\x00\x00\xFF\xFF' * sz
            a = b'\xFF' * sz if ARGB else b''
            r = pattern[4:sz + 4]
            g = pattern[2:sz + 2]
            b = pattern[:sz]
        return (b'ARGB' if ARGB else b'') + a + r + g + b

    os.makedirs('format-support-raw', exist_ok=True)
    for s in INFO.keys():
        print(f'generate {s}x{s}.argb')
        argb_data = testpattern(s, s, ch=4)
        with open(f'format-support-raw/{s}x{s}.argb', 'wb') as fp:
            fp.write(argb_data)
        print(f'generate {s}x{s}.rgb')
        rgb_data = testpattern(s, s, ch=3)
        with open(f'format-support-raw/{s}x{s}.rgb', 'wb') as fp:
            fp.write(rgb_data)


def generate_icns():
    os.makedirs('format-support-icns', exist_ok=True)
    with zipfile.ZipFile('format-support-raw.zip') as Zip:
        for s, keys in INFO.items():
            print(f'generate icns for {s}x{s}')
            for key in keys:
                # JPEG 2000, PNG, and ARGB
                for ext in ['jp2', 'png', 'argb']:
                    img = IcnsFile()
                    with Zip.open(f'{s}x{s}.{ext}') as f:
                        img.add_media(key, data=f.read())
                    img.write(f'format-support-icns/{s}-{key}-{ext}.icns',
                              toc=False)
                # RGB + mask
                img = IcnsFile()
                with Zip.open(f'{s}x{s}.rgb') as f:
                    data = f.read()
                    if key == 'it32':
                        data = b'\x00\x00\x00\x00' + data
                img.add_media(key, data=data)
                img.add_media('s8mk', data=b'\xFF' * 256)
                img.add_media('l8mk', data=b'\xFF' * 1024)
                img.add_media('h8mk', data=b'\xFF' * 2304)
                img.add_media('t8mk', data=b'\xFF' * 16384)
                img.write(f'format-support-icns/{s}-{key}-rgb.icns', toc=False)


def generate_random_it32_header():
    print(f'testing random it32 header')
    os.makedirs('format-support-it32', exist_ok=True)
    with zipfile.ZipFile('format-support-raw.zip') as Zip:
        with Zip.open(f'128x128.rgb') as f:
            data = f.read()

    def random_header():
        return bytes([randint(0, 255), randint(0, 255),
                      randint(0, 255), randint(0, 255)])

    for i in range(100):
        img = IcnsFile()
        img.add_media('it32', data=random_header() + data)
        img.add_media('t8mk', data=b'\xFF' * 16384)
        img.write(f'format-support-it32/{i}.icns', toc=False)


if __name__ == '__main__':
    main()
