#!/usr/bin/env python3
import unittest
import shutil  # rmtree
import os  # chdir, listdir, makedirs, path, remove
from typing import Optional, Dict, Any
if __name__ == '__main__':
    import sys
    sys.path[0] = os.path.dirname(sys.path[0])
from icnsutil import *


def main():
    # ensure working dir is correct
    os.chdir(os.path.join(os.path.dirname(__file__), 'fixtures'))
    print('Running tests with PIL_ENABLED =', PIL_ENABLED)
    unittest.main()
    exit()


################
#  Unit tests  #
################

class TestArgbImage(unittest.TestCase):
    def test_init_data(self):
        w = 16  # size
        ch_255 = b'\xFF\xFF\xFB\xFF'
        ch_128 = b'\xFF\x80\xFB\x80'
        ch_000 = b'\xFF\x00\xFB\x00'
        # Test ARGB init
        img = ArgbImage(data=b'ARGB' + ch_000 + ch_128 + ch_000 + ch_255)
        self.assertEqual(img.size, (w, w))
        self.assertEqual(img.a, [0] * w * w)
        self.assertEqual(img.r, [128] * w * w)
        self.assertEqual(img.g, [0] * w * w)
        self.assertEqual(img.b, [255] * w * w)
        # Test RGB init
        img = ArgbImage(data=ch_128 + ch_000 + ch_255)
        self.assertEqual(img.size, (w, w))
        self.assertEqual(img.a, [255] * w * w)
        self.assertEqual(img.r, [128] * w * w)
        self.assertEqual(img.g, [0] * w * w)
        self.assertEqual(img.b, [255] * w * w)
        # Test setting mask manually
        img.load_mask(data=b'\x75' * w * w)
        self.assertEqual(img.size, (w, w))
        self.assertEqual(img.a, [117] * w * w)
        self.assertEqual(img.r, [128] * w * w)
        self.assertEqual(img.g, [0] * w * w)
        self.assertEqual(img.b, [255] * w * w)
        with self.assertRaises(AssertionError):
            img.load_mask(data=[117] * 42)

    def test_init_file(self):
        # Test ARGB init
        img = ArgbImage(file='rgb.icns.argb')
        self.assertEqual(img.size, (16, 16))
        self.assertEqual(img.a, [255] * 16 * 16)
        # Test RGB init
        img = ArgbImage(file='rgb.icns.rgb')
        self.assertEqual(img.size, (16, 16))
        self.assertEqual(img.a, [255] * 16 * 16)
        # Test PNG init
        if not PIL_ENABLED:
            with self.assertRaises(ImportError):
                ArgbImage(file='rgb.icns.png')
        else:
            img = ArgbImage(file='rgb.icns.png')
            self.assertEqual(img.size, (16, 16))
            self.assertEqual(img.a, [255] * 16 * 16)

    @unittest.skipUnless(PIL_ENABLED, 'PIL_ENABLED == False')
    def test_attributes(self):
        img = ArgbImage(file='rgb.icns.png')
        self.assertTrue(img.channels != 0)
        # will raise AttributeError if _load_png didnt init all attrributes
        str(img)

    def test_data_getter(self):
        img = ArgbImage(file='rgb.icns.argb')
        argb = img.argb_data(compress=True)
        self.assertEqual(argb[:4], b'ARGB')
        self.assertEqual(argb[4:8], b'\xFF\xFF\xFB\xFF')
        self.assertEqual(len(argb), 4 + 709)
        self.assertEqual(len(img.argb_data(compress=False)), 4 + 16 * 16 * 4)
        self.assertEqual(len(img.rgb_data(compress=True)), 705)
        self.assertEqual(len(img.rgb_data(compress=False)), 16 * 16 * 3)
        self.assertEqual(len(img.mask_data(compress=True)), 4)
        self.assertEqual(len(img.mask_data(compress=False)), 16 * 16)
        self.assertEqual(img.mask_data(), b'\xFF' * 16 * 16)
        if PIL_ENABLED:
            img = ArgbImage(file='rgb.icns.png')
            self.assertEqual(img.argb_data(), argb)
            self.assertEqual(img.mask_data(), b'\xFF' * 16 * 16)

    def test_export(self):
        img = ArgbImage(file='rgb.icns.argb')
        if not PIL_ENABLED:
            with self.assertRaises(ImportError):
                img.write_png('any')
        else:
            img.write_png('tmp_argb_to_png.png')
            with open('tmp_argb_to_png.png', 'rb') as fA:
                with open('rgb.icns.png', 'rb') as fB:
                    self.assertEqual(fA.read(1), fB.read(1))
            os.remove('tmp_argb_to_png.png')


class TestIcnsFile(unittest.TestCase):
    def test_init(self):
        img = IcnsFile()
        self.assertEqual(img.media, {})
        self.assertEqual(img.infile, None)
        img = IcnsFile(file='rgb.icns')
        self.assertEqual(img.infile, 'rgb.icns')
        self.assertEqual(len(img.media), 8)
        self.assertListEqual(list(img.media.keys()),
                             ['ICN#', 'il32', 'l8mk', 'ics#',
                              'is32', 's8mk', 'it32', 't8mk'])
        img = IcnsFile(file='selected.icns')
        self.assertEqual(len(img.media), 10)
        self.assertListEqual(list(img.media.keys()),
                             ['info', 'ic12', 'icsb', 'sb24', 'ic04',
                              'SB24', 'ic05', 'icsB', 'ic11', 'slct'])
        # Not an ICNS file
        with self.assertRaises(RawData.ParserError):
            IcnsFile(file='rgb.icns.argb')
        with self.assertRaises(RawData.ParserError):
            IcnsFile(file='rgb.icns.png')

    def test_load_file(self):
        img = IcnsFile()
        fname = 'rgb.icns.argb'
        with open(fname, 'rb') as fp:
            img.add_media(data=fp.read(), file='lol.argb')
            self.assertListEqual(list(img.media.keys()), ['ic04'])
        # test overwrite
        with self.assertRaises(KeyError):
            img.add_media(file=fname)
        img.add_media(file=fname, force=True)
        self.assertListEqual(list(img.media.keys()), ['ic04'])
        # test manual key assignment
        img.add_media('ic05', file=fname)
        self.assertListEqual(list(img.media.keys()), ['ic04', 'ic05'])

    def test_add_named_media(self):
        img = IcnsFile('selected.icns')
        data = img.media['ic11']
        newimg = IcnsFile()
        newimg.add_media(data=data)
        self.assertEqual(list(newimg.media.keys()), ['icp5'])
        newimg.add_media(data=data, file='@2x.png')
        self.assertEqual(list(newimg.media.keys()), ['icp5', 'ic11'])
        # Test duplicate key exception
        try:
            newimg.add_media(data=data, file='dd.png')
        except KeyError as e:
            self.assertTrue('icp5' in str(e))
            self.assertTrue('ic11' not in str(e))
        try:
            newimg.add_media(data=data, file='dd@2x.png')
        except KeyError as e:
            self.assertTrue('icp5' not in str(e))
            self.assertTrue('ic11' in str(e))
        # Test Jpeg 2000
        newimg.add_media(file='256x256.jp2')
        self.assertEqual(list(newimg.media.keys()), ['icp5', 'ic11', 'ic08'])
        # Test jp2 with retina flag
        with open('256x256.jp2', 'rb') as fp:
            newimg.add_media(data=fp.read(), file='256x256@2x.jp2')
        self.assertEqual(
            list(newimg.media.keys()), ['icp5', 'ic11', 'ic08', 'ic13'])

    def test_add_nested_icns(self):
        img = IcnsFile()
        img.add_media(file='selected.icns')
        self.assertTrue('slct' in img.media.keys())
        self.assertNotEqual(img.media['slct'][:4], b'icns')
        with self.assertRaises(KeyError):
            img.add_media('slct', file='rgb.icns')
        with self.assertRaises(IcnsType.CanNotDetermine):
            img.add_media(file='icp4rgb.icns')
        with self.assertRaises(IcnsType.CanNotDetermine):
            img.add_media(file='rgb.icns')
        img.add_media('no_key', file='rgb.icns')
        self.assertTrue('no_key' in img.media.keys())
        self.assertNotEqual(img.media['no_key'][:4], b'icns')

    def test_remove_media(self):
        img = IcnsFile()
        img.add_media(file='selected.icns')
        img.add_media(file='rgb.icns.rgb')
        img.add_media(file='rgb.icns.argb')
        self.assertListEqual(list(img.media.keys()), ['slct', 'is32', 'ic04'])
        img.remove_media('is32')
        self.assertListEqual(list(img.media.keys()), ['slct', 'ic04'])
        img.remove_media(b'ic04')
        self.assertListEqual(list(img.media.keys()), ['slct', 'ic04'])
        img.remove_media('')
        self.assertListEqual(list(img.media.keys()), ['slct', 'ic04'])
        img.remove_media('slct')
        self.assertListEqual(list(img.media.keys()), ['ic04'])

    def test_toc(self):
        img = IcnsFile()
        fname_out = 'tmp-out.icns'
        img.add_media('ic04', file='rgb.icns.argb')
        # without TOC
        img.write(fname_out, toc=False)
        with open(fname_out, 'rb') as fp:
            self.assertEqual(fp.read(4), b'icns')
            self.assertEqual(fp.read(4), b'\x00\x00\x02\xD9')
            self.assertEqual(fp.read(4), b'ic04')
            self.assertEqual(fp.read(4), b'\x00\x00\x02\xD1')
            self.assertEqual(fp.read(4), b'ARGB')
        self.assertFalse(IcnsFile(fname_out).has_toc())
        # with TOC
        img.write(fname_out, toc=True)
        with open(fname_out, 'rb') as fp:
            self.assertEqual(fp.read(4), b'icns')
            self.assertEqual(fp.read(4), b'\x00\x00\x02\xE9')
            self.assertEqual(fp.read(4), b'TOC ')
            self.assertEqual(fp.read(4), b'\x00\x00\x00\x10')
            self.assertEqual(fp.read(4), b'ic04')
            self.assertEqual(fp.read(4), b'\x00\x00\x02\xD1')
            self.assertEqual(fp.read(4), b'ic04')
            self.assertEqual(fp.read(4), b'\x00\x00\x02\xD1')
            self.assertEqual(fp.read(4), b'ARGB')
        self.assertTrue(IcnsFile(fname_out).has_toc())
        os.remove(fname_out)

    def test_verify(self):
        is_invalid = any(IcnsFile.verify('rgb.icns'))
        self.assertEqual(is_invalid, False)
        is_invalid = any(IcnsFile.verify('selected.icns'))
        self.assertEqual(is_invalid, False)

    def test_description(self):
        str = IcnsFile.description('rgb.icns', indent=0)
        self.assertEqual(str, '''
ICN#: 256 bytes, iconmask: 32x32-mono
il32: 2224 bytes, rgb: 32x32
l8mk: 1024 bytes, mask: 32x32
ics#: 64 bytes, iconmask: 16x16-mono
is32: 705 bytes, rgb: 16x16
s8mk: 256 bytes, mask: 16x16
it32: 14005 bytes, rgb: 128x128
t8mk: 16384 bytes, mask: 128x128
'''.strip().replace('\n', os.linesep))
        str = IcnsFile.description('selected.icns', verbose=True, indent=0)
        self.assertEqual(str, '''
info: 314 bytes, offset: 8, plist: info
ic12: 1863 bytes, offset: 330, png: 32x32@2x
icsb: 271 bytes, offset: 2201, argb: 18x18
sb24: 748 bytes, offset: 2480, png: 24x24
ic04: 215 bytes, offset: 3236, argb: 16x16
SB24: 1681 bytes, offset: 3459, png: 24x24@2x
ic05: 690 bytes, offset: 5148, argb: 32x32
icsB: 1001 bytes, offset: 5846, png: 18x18@2x
ic11: 1056 bytes, offset: 6855, png: 16x16@2x
slct: 7660 bytes, offset: 7919, icns: selected
'''.strip().replace('\n', os.linesep))


class TestIcnsType(unittest.TestCase):
    def test_sizes(self):
        for key, ext, desc, size, total in [
            ('ics4', 'bin', 'icon', (16, 16), 128),  # 4-bit icon
            ('ich#', 'bin', 'iconmask', (48, 48), 576),  # 2x1-bit
            ('it32', 'rgb', '', (128, 128), 49152),  # 3x8-bit
            ('t8mk', 'bin', 'mask', (128, 128), 16384),  # 8-bit mask
            ('ic05', 'argb', '', (32, 32), 4096),  # 4x8-bit
            ('icp6', 'png', '', (48, 48), None),
            ('ic14', 'png', '@2x', (512, 512), None),
            ('info', 'plist', '', None, None),
            ('sbtp', 'icns', 'template', None, None),
            ('slct', 'icns', 'selected', None, None),
            (b'\xFD\xD9\x2F\xA8', 'icns', 'dark', None, None),
        ]:
            m = IcnsType.get(key)
            self.assertEqual(m.size, size)
            self.assertTrue(m.is_type(ext))
            self.assertTrue(desc in m.desc)
            self.assertEqual(m.maxsize, total)

    def test_guess(self):
        with open('rgb.icns.png', 'rb') as fp:
            x = IcnsType.guess(fp.read(32), 'rgb.icns.png')
            self.assertTrue(x.is_type('png'))
            self.assertEqual(x.size, (16, 16))
            self.assertEqual(x.retina, False)
            self.assertEqual(x.channels, 3)  # because icp4 supports RGB
            self.assertEqual(x.compressable, True)
        with open('rgb.icns.argb', 'rb') as fp:
            x = IcnsType.guess(fp.read(), 'rgb.icns.argb')
            self.assertTrue(x.is_type('argb'))
            self.assertEqual(x.size, (16, 16))
            self.assertEqual(x.retina, False)
            self.assertEqual(x.channels, 4)
            self.assertEqual(x.compressable, True)
        with open('256x256.jp2', 'rb') as fp:
            x = IcnsType.guess(fp.read(), '256x256.jp2')
            self.assertTrue(x.is_type('jp2'))
            self.assertEqual(x.size, (256, 256))
            self.assertEqual(x.compressable, False)
            self.assertEqual(x.availability, 10.5)
        # Test rgb is detected by filename extension
        with open('rgb.icns.rgb', 'rb') as fp:
            x = IcnsType.guess(fp.read(), 'rgb.icns.rgb')
            self.assertTrue(x.is_type('rgb'))
            self.assertEqual(x.size, (16, 16))
            self.assertEqual(x.retina, False)
            self.assertEqual(x.channels, 3)
            self.assertEqual(x.compressable, True)
            fp.seek(0)
            with self.assertRaises(IcnsType.CanNotDetermine):
                x = IcnsType.guess(fp.read(), 'rgb.icns.bin')

    def test_img_mask_pairs(self):
        for x, y in IcnsType.enum_img_mask_pairs(['t8mk']):
            self.assertEqual(x, None)
            self.assertEqual(y, 't8mk')
        for x, y in IcnsType.enum_img_mask_pairs(['it32']):
            self.assertEqual(x, 'it32')
            self.assertEqual(y, None)
        for x, y in IcnsType.enum_img_mask_pairs(['it32', 't8mk', 'ic04']):
            self.assertEqual(x, 'it32')
            self.assertEqual(y, 't8mk')
        with self.assertRaises(StopIteration):
            next(IcnsType.enum_img_mask_pairs(['info', 'icm#', 'ICN#']))

    def test_enum_png_convertable(self):
        gen = IcnsType.enum_png_convertable([
            'ICON', 'ICN#', 'icm#',  # test 1-bit mono icons
            'icm4', 'icl4', 'ic07',  # test keys that should not be exported
            'ic04', 'ic05',  # test if argb are exported without mask
            'icp5', 'l8mk',  # test if png+mask is exported (YES if icp4 icp5)
            'ih32', 'h8mk',  # test if 24-bit + mask is exported (YES)
            'is32',  # test if image only is exported (YES)
            't8mk',  # test if mask only is exported (NO)
            'icp4',  # test if png is exported (user must validate file type!)
        ])
        self.assertEqual(next(gen), ('ICON', None))
        self.assertEqual(next(gen), ('ICN#', None))
        self.assertEqual(next(gen), ('icm#', None))
        self.assertEqual(next(gen), ('is32', None))
        self.assertEqual(next(gen), ('ih32', 'h8mk'))
        self.assertEqual(next(gen), ('icp4', None))  # icp4 & icp5 can be RGB
        self.assertEqual(next(gen), ('icp5', 'l8mk'))
        self.assertEqual(next(gen), ('ic04', None))
        self.assertEqual(next(gen), ('ic05', None))
        with self.assertRaises(StopIteration):
            print(next(gen))

    def test_match_maxsize(self):
        for typ, size, key in [
            ('rgb', 768, 'is32'),
            ('rgb', 3072, 'il32'),
            ('rgb', 6912, 'ih32'),
            ('rgb', 49152, 'it32'),
            ('argb', 1024, 'ic04'),
            ('argb', 4096, 'ic05'),
            ('argb', 1296, 'icsb'),
        ]:
            iType = IcnsType.match_maxsize(size, typ)
            self.assertEqual(iType.key, key, msg=f'{typ} ({size}) != {key}')
        for typ, size, key in [
            ('bin', 512, 'icl4'),
            ('bin', 192, 'icm8'),
            ('png', 768, 'icp4'),
        ]:
            with self.assertRaises(AssertionError):
                IcnsType.match_maxsize(size, typ)

    def test_decompress(self):
        # Test ARGB deflate
        with open('rgb.icns.argb', 'rb') as fp:
            data = fp.read()
        data = IcnsType.get('ic04').decompress(data)
        self.assertEqual(len(data), 16 * 16 * 4)
        # Test RGB deflate
        with open('rgb.icns.rgb', 'rb') as fp:
            data = fp.read()
        d = IcnsType.get('is32').decompress(data)
        self.assertEqual(len(d), 16 * 16 * 3)
        d = IcnsType.get('it32').decompress(data)
        self.assertEqual(len(d), 1966)  # decompress removes 4-byte it32-header
        d = IcnsType.get('ic04').decompress(data, ext='png')
        self.assertEqual(d, None)  # if png, dont decompress

    def test_exceptions(self):
        with self.assertRaises(NotImplementedError):
            IcnsType.get('wrong key')
        with self.assertRaises(IcnsType.CanNotDetermine):
            IcnsType.guess(b'\x00')
        with self.assertRaises(IcnsType.CanNotDetermine):  # could be any icns
            with open('rgb.icns', 'rb') as fp:
                IcnsType.guess(fp.read(6))


class TestPackBytes(unittest.TestCase):
    def test_pack(self):
        d = PackBytes.pack(b'\x00' * 514)
        self.assertEqual(d, b'\xff\x00\xff\x00\xff\x00\xf9\x00')
        d = PackBytes.pack(b'\x01\x02' * 5)
        self.assertEqual(d, b'\t\x01\x02\x01\x02\x01\x02\x01\x02\x01\x02')
        d = PackBytes.pack(b'\x01\x02' + b'\x03' * 134 + b'\x04\x05')
        self.assertEqual(d, b'\x01\x01\x02\xff\x03\x81\x03\x01\x04\x05')
        d = PackBytes.pack(b'\x00' * 223 + b'\x01' * 153)
        self.assertEqual(d, b'\xff\x00\xda\x00\xff\x01\x94\x01')
        d = PackBytes.pack(b'\x13' * 131)
        self.assertEqual(d, b'\xff\x13\x00\x13')
        d = PackBytes.pack(b'\x13' * 132)
        self.assertEqual(d, b'\xff\x13\x01\x13\x13')

    def test_unpack(self):
        d = PackBytes.unpack(b'\xff\x00\xff\x00\xff\x00\xf9\x00')
        self.assertListEqual(d, [0] * 514)
        d = PackBytes.unpack(b'\t\x01\x02\x01\x02\x01\x02\x01\x02\x01\x02')
        self.assertListEqual(d, [1, 2] * 5)
        d = PackBytes.unpack(b'\x01\x01\x02\xff\x03\x81\x03\x01\x04\x05')
        self.assertListEqual(d, [1, 2] + [3] * 134 + [4, 5])
        d = PackBytes.unpack(b'\xff\x00\xda\x00\xff\x01\x94\x01')
        self.assertListEqual(d, [0] * 223 + [1] * 153)
        d = PackBytes.unpack(b'\xff\x13\x00\x13')
        self.assertListEqual(d, [19] * 131)

    def test_get_size(self):
        for d in [b'\xff\x00\xff\x00\xff\x00\xf9\x00',
                  b'\t\x01\x02\x01\x02\x01\x02\x01\x02\x01\x02',
                  b'\x01\x01\x02\xff\x03\x81\x03\x01\x04\x05',
                  b'\xff\x00\xda\x00\xff\x01\x94\x01']:
            self.assertEqual(PackBytes.get_size(d), len(PackBytes.unpack(d)))


class TestRawData(unittest.TestCase):
    def test_img_size(self):
        def fn(fname):
            with open(fname, 'rb') as fp:
                return RawData.determine_image_size(fp.read())

        self.assertEqual(fn('rgb.icns'), None)
        self.assertEqual(fn('rgb.icns.png'), (16, 16))
        self.assertEqual(fn('rgb.icns.argb'), (16, 16))
        self.assertEqual(fn('256x256.jp2'), (256, 256))
        self.assertEqual(fn('18x18.j2k'), (18, 18))

    def test_ext(self):
        for data, ext in (
            (b'\x89PNG\x0d\x0a\x1a\x0a#', 'png'),
            (b'ARGB\x00\x00', 'argb'),
            (b'icns\x00\x00', 'icns'),
            (b'bplist\x00\x00', 'plist'),
            (b'\xff\xd8\xff\x00\x00', None),  # JPEG
            (b'\x00\x00\x00\x0CjP  \x00\x00', 'jp2'),  # JPEG2000
        ):
            self.assertEqual(RawData.determine_file_ext(data), ext)


#######################
#  Integration tests  #
#######################

class TestExport(unittest.TestCase):
    INFILE = None  # type: Optional[str]
    OUTDIR = None  # type: Optional[str] # set in setUpClass
    CLEANUP = True  # for debugging purposes
    ARGS = {}  # type: Dict[str, Any]

    @classmethod
    def setUpClass(cls):
        cls.OUTDIR = 'tmp_' + cls.__name__
        if os.path.isdir(cls.OUTDIR):
            shutil.rmtree(cls.OUTDIR)
        os.makedirs(cls.OUTDIR, exist_ok=True)
        cls.img = IcnsFile(file=cls.INFILE)
        cls.outfiles = cls.img.export(cls.OUTDIR, **cls.ARGS)

    @classmethod
    def tearDownClass(cls):
        if cls.CLEANUP:
            shutil.rmtree(cls.OUTDIR)

    def assertEqualFiles(self, fname_a, fname_b):
        with open(fname_a, 'rb') as fA:
            with open(fname_b, 'rb') as fB:
                self.assertEqual(fA.read(1), fB.read(1))

    def assertExportCount(self, filecount, subpath=None):
        self.assertEqual(len(os.listdir(subpath or self.OUTDIR)), filecount)


class TestRGB(TestExport):
    INFILE = 'rgb.icns'

    def test_export_count(self):
        self.assertExportCount(8)

    def test_file_extension(self):
        for x in ['ICN#', 'ics#', 'l8mk', 's8mk', 't8mk']:
            self.assertTrue(self.outfiles[x].endswith('.bin'))
        for x in ['il32', 'is32', 'it32']:
            self.assertTrue(self.outfiles[x].endswith('.rgb'))

    def test_rgb_size(self):
        for key, s in [('is32', 705), ('il32', 2224), ('it32', 14005)]:
            self.assertEqual(os.path.getsize(self.outfiles[key]), s)
            img = ArgbImage(file=self.outfiles[key])
            media = IcnsType.get(key)
            self.assertEqual(img.size, media.size)
            self.assertEqual(len(img.a), len(img.r))
            self.assertEqual(len(img.r), len(img.g))
            self.assertEqual(len(img.g), len(img.b))
            self.assertEqual(media.maxsize, len(img.rgb_data(compress=False)))

    def test_rgb_to_png(self):
        fname = self.outfiles['is32']
        img = ArgbImage(file=fname)
        fname = fname + '.png'
        if not PIL_ENABLED:
            with self.assertRaises(ImportError):
                img.write_png(fname)
        else:
            img.write_png(fname)
            self.assertEqualFiles(fname, self.INFILE + '.png')
            os.remove(fname)


class TestARGB(TestExport):
    INFILE = 'selected.icns'

    def test_export_count(self):
        self.assertExportCount(10)

    def test_file_extension(self):
        for x in ['ic11', 'ic12', 'icsB', 'sb24', 'SB24']:
            self.assertTrue(self.outfiles[x].endswith('.png'))
        for x in ['ic04', 'ic05', 'icsb']:
            self.assertTrue(self.outfiles[x].endswith('.argb'))
        self.assertTrue(self.outfiles['info'].endswith('.plist'))
        self.assertTrue(self.outfiles['slct'].endswith('.icns'))

    def test_argb_size(self):
        f_argb = self.outfiles['ic05']
        self.assertEqual(os.path.getsize(f_argb), 690)  # compressed
        img = ArgbImage(file=f_argb)
        self.assertEqual(img.size, (32, 32))
        self.assertEqual(len(img.a), len(img.r))
        self.assertEqual(len(img.r), len(img.g))
        self.assertEqual(len(img.g), len(img.b))

        len_argb = len(img.argb_data(compress=False)) - 4  # -header
        self.assertEqual(len_argb, IcnsType.get('ic05').maxsize)
        len_rgb = len(img.rgb_data(compress=False))
        self.assertEqual(len_rgb, len_argb // 4 * 3)
        len_mask = len(img.mask_data(compress=False))
        self.assertEqual(len_mask, len_argb // 4)

    def test_argb_to_png(self):
        f_argb = self.outfiles['ic05']
        img = ArgbImage(file=f_argb)
        fname = f_argb + '.png'
        if not PIL_ENABLED:
            with self.assertRaises(ImportError):
                img.write_png(fname)
        else:
            img.write_png(fname)
            self.assertEqualFiles(fname, self.outfiles['ic11'])
            os.remove(fname)

    def test_png_to_argb(self):
        f_png = self.outfiles['ic11']
        if not PIL_ENABLED:
            with self.assertRaises(ImportError):
                ArgbImage(file=f_png)
        else:
            img = ArgbImage(file=f_png)
            fname = f_png + '.argb'
            with open(fname, 'wb') as fp:
                fp.write(img.argb_data())
            self.assertEqualFiles(fname, self.outfiles['ic05'])
            os.remove(fname)

    def test_argb_compression(self):
        fname = self.outfiles['ic05']
        img = ArgbImage(file=fname)
        # test decompress
        self.assertEqual(img.rgb_data(compress=False), b'\x00' * 32 * 32 * 3)
        with open(fname + '.tmp', 'wb') as fp:
            fp.write(img.argb_data(compress=True))
        # test compress
        self.assertEqualFiles(fname, fname + '.tmp')
        os.remove(fname + '.tmp')


class TestNested(TestExport):
    INFILE = 'selected.icns'
    ARGS = {'recursive': True}

    def test_export_count(self):
        self.assertExportCount(10 + 1)
        self.assertExportCount(9, self.outfiles['slct']['_'] + '.export')

    def test_icns_readable(self):
        img = IcnsFile(file=self.outfiles['slct']['_'])
        self.assertEqual(len(img.media), 9)
        argb = ArgbImage(data=img.media['ic04'])
        self.assertEqual(argb.rgb_data(compress=False), b'\x00' * 16 * 16 * 3)


class TestPngOnly(TestExport):
    INFILE = 'selected.icns'
    ARGS = {'allowed_ext': 'png'}

    def test_export_count(self):
        self.assertExportCount(5)


class TestPngOnlyNested(TestExport):
    INFILE = 'selected.icns'
    ARGS = {'allowed_ext': 'png', 'recursive': True}

    def test_export_count(self):
        self.assertExportCount(5 + 1)
        self.assertExportCount(5, self.outfiles['slct']['_'] + '.export')


class TestIcp4RGB(TestExport):
    INFILE = 'icp4rgb.icns'
    ARGS = {'key_suffix': True}

    def test_export_count(self):
        self.assertExportCount(4)
        self.assertListEqual(list(self.outfiles.keys()),
                             ['_', 'icp4', 's8mk', 'icp5', 'l8mk'])

    def test_filenames(self):
        for fname in ['s8mk.bin', 'icp4.rgb', 'icp5.rgb', 'l8mk.bin']:
            self.assertTrue(os.path.exists(os.path.join(
                self.OUTDIR, fname)), msg='File does not exist: ' + fname)


@unittest.skipUnless(PIL_ENABLED, 'PIL_ENABLED == False')
class TestRGB_toPNG(TestExport):
    INFILE = 'rgb.icns'
    ARGS = {'convert_png': True}

    def test_export_count(self):
        self.assertExportCount(5)

    def test_conversion(self):
        img = ArgbImage(file=self.outfiles['il32'])
        self.assertEqual(self.img.media['il32'], img.rgb_data())
        self.assertEqual(self.img.media['l8mk'], img.mask_data())
        self.assertTrue(self.outfiles['il32'].endswith('.png'))


@unittest.skipUnless(PIL_ENABLED, 'PIL_ENABLED == False')
class TestARGB_toPNG(TestExport):
    INFILE = 'selected.icns'
    ARGS = {'convert_png': True}

    def test_export_count(self):
        self.assertExportCount(10)

    def test_conversion(self):
        img = ArgbImage(file=self.outfiles['ic05'])
        self.assertEqual(self.img.media['ic05'], img.argb_data())
        self.assertTrue(self.outfiles['ic05'].endswith('.png'))
        img = ArgbImage(file=self.outfiles['ic04'])  # is a PNG
        self.assertEqual(self.img.media['ic04'], img.argb_data())
        self.assertTrue(self.outfiles['ic04'].endswith('.png'))


@unittest.skipUnless(PIL_ENABLED, 'PIL_ENABLED == False')
class TestNested_toPNG(TestExport):
    INFILE = 'selected.icns'
    ARGS = {'convert_png': True, 'recursive': True}

    def test_export_count(self):
        self.assertExportCount(10 + 1)

    def test_conversion(self):
        fname = self.outfiles['slct']['ic05']
        self.assertTrue(fname.endswith('.png'))


@unittest.skipUnless(PIL_ENABLED, 'PIL_ENABLED == False')
class TestPngOnlyNested_toPNG(TestExport):
    INFILE = 'selected.icns'
    ARGS = {'allowed_ext': 'png', 'convert_png': True, 'recursive': True}

    def test_export_count(self):
        self.assertExportCount(8 + 1)
        self.assertExportCount(8, self.outfiles['slct']['_'] + '.export')


@unittest.skipUnless(PIL_ENABLED, 'PIL_ENABLED == False')
class TestIcp4RGB_toPNG(TestExport):
    INFILE = 'icp4rgb.icns'
    ARGS = {'convert_png': True}

    def test_export_count(self):
        self.assertExportCount(2)


if __name__ == '__main__':
    main()
