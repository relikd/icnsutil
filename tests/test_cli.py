#!/usr/bin/env python3
import unittest
import shutil  # rmtree, copy
import os  # chdir, listdir, makedirs, path, remove
from subprocess import run, PIPE
if __name__ == '__main__':
    import sys
    sys.path[0] = os.path.dirname(sys.path[0])
from icnsutil import RawData, PIL_ENABLED, __version__


def main():
    # ensure working dir is correct
    os.chdir(os.path.join(os.path.dirname(__file__), 'fixtures'))
    print('Running tests with PIL_ENABLED =', PIL_ENABLED)
    unittest.main()
    exit()


###############
#  CLI tests  #
###############

def run_cli(args):  # relative to fixtures folder
    exec_path = os.path.join(os.pardir, os.pardir, 'icnsutil', 'cli.py')
    return run([sys.executable, exec_path] + args, stdout=PIPE, stderr=PIPE)


class TestCLI(unittest.TestCase):
    def test_help(self):
        val1 = run_cli([]).stdout
        val2 = run_cli(['--help']).stdout
        self.assertEqual(val1, val2)

    def test_version(self):
        val1 = run_cli(['--version']).stdout
        self.assertEqual(val1.split()[1], bytes(__version__, 'utf8'))


class TestCLI_export(unittest.TestCase):
    def setUp(self):
        self.OUTDIR = 'tmp_cli_out_export'
        if os.path.isdir(self.OUTDIR):
            shutil.rmtree(self.OUTDIR)
        os.makedirs(self.OUTDIR, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.OUTDIR)

    def assert_files(self, infile, args, sorted_out_files):
        r = run_cli(['e', infile, '-o', self.OUTDIR] + args)
        files = sorted(os.listdir(self.OUTDIR))
        if r.returncode == 0:
            self.assertListEqual(files, sorted_out_files)
        return r

    def test_extract(self):
        self.assert_files('rgb.icns', [], [
            '128x128-mask8b.bin', '128x128.rgb',
            '16x16-icon1b-mask1b.bin', '16x16-mask8b.bin', '16x16.rgb',
            '32x32-icon1b-mask1b.bin', '32x32-mask8b.bin', '32x32.rgb'])
        for size, fname in [
            (64, '16x16-icon1b-mask1b.bin'),
            (1024, '32x32-mask8b.bin'),
            (14005, '128x128.rgb'),
        ]:
            fsize = os.path.getsize(os.path.join(self.OUTDIR, fname))
            self.assertEqual(size, fsize)

    def test_extract_by_key(self):
        self.assert_files('rgb.icns', ['-k'], [
            'ICN#.bin', 'ics#.bin', 'il32.rgb', 'is32.rgb',
            'it32.rgb', 'l8mk.bin', 's8mk.bin', 't8mk.bin'])

    def test_extract_w_png(self):
        self.assert_files('selected.icns', [], [
            '16x16.argb', '16x16@2x.png', '18x18.argb', '18x18@2x.png',
            '24x24.png', '24x24@2x.png', '32x32.argb', '32x32@2x.png',
            'info.plist', 'selected.icns'])

    def test_extract_png_only(self):
        self.assert_files('selected.icns', ['--png-only'], [
            '16x16@2x.png', '18x18@2x.png', '24x24.png',
            '24x24@2x.png', '32x32@2x.png'])

    def test_extract_nested(self):
        self.assert_files('selected.icns', ['-r', '--png-only'], [
            '16x16@2x.png', '18x18@2x.png', '24x24.png',
            '24x24@2x.png', '32x32@2x.png', 'selected.icns.export'])
        files = sorted(os.listdir(
            os.path.join(self.OUTDIR, 'selected.icns.export')))
        self.assertListEqual(files, [
            '16x16@2x.png', '18x18@2x.png', '24x24.png',
            '24x24@2x.png', '32x32@2x.png'])

    def test_extract_convert_wo_pil(self):
        self.assert_files('icp4rgb.icns', [], [
            '16x16-mask8b.bin', '16x16.rgb', '32x32-mask8b.bin', '32x32.rgb'])

    @unittest.skipUnless(PIL_ENABLED, 'PIL_ENABLED == False')
    def test_extract_convert_w_pil(self):
        self.assert_files('icp4rgb.icns', ['-c'], ['16x16.png', '32x32.png'])


class TestCLI_compose(unittest.TestCase):
    def setUp(self):
        self.OUTFILE = 'tmp_cli_out_compose.icns'
        if os.path.exists(self.OUTFILE):
            os.remove(self.OUTFILE)

    def tearDown(self):
        os.remove(self.OUTFILE)

    def test_ext_completion(self):
        fname = self.OUTFILE[:-5]  # remove '.icns'
        run_cli(['c', fname, 'rgb.icns.png'])
        os.path.exists(self.OUTFILE)  # will append .icns to filename

    def test_force(self):
        args = ['c', self.OUTFILE, 'rgb.icns.png']
        r = run_cli(args)
        self.assertEqual(r.returncode, 0)
        r = run_cli(args)
        self.assertEqual(r.returncode, 1)  # without force overwrite
        self.assertTrue(b'force' in r.stderr.lower())
        self.assertTrue(b'-f' in r.stderr)
        r = run_cli(args + ['-f'])
        self.assertEqual(r.returncode, 0)  # with force overwrite

    def assert_conv_file(self, fname, icns_key, arg=[]):
        run_cli(['c', self.OUTFILE, fname] + arg)
        s_orig = os.path.getsize(fname)
        s_icns = os.path.getsize(self.OUTFILE)
        is_icns = fname.endswith('.icns')
        self.assertEqual(s_orig + (8 if is_icns else 16), s_icns)
        with open(self.OUTFILE, 'rb') as fp:
            key, size = RawData.icns_header_read(fp.read(8))
            self.assertEqual(size, s_icns)
            key, size = RawData.icns_header_read(fp.read(8))
            self.assertEqual(size, s_orig + (0 if is_icns else 8))
            self.assertEqual(key, icns_key)

    def test_png(self):
        self.assert_conv_file('rgb.icns.png', 'icp4')

    def test_jp2(self):
        self.assert_conv_file('256x256.jp2', 'ic08')
        self.assert_conv_file('18x18.j2k', 'icsb', arg=['-f'])

    def test_argb(self):
        self.assert_conv_file('rgb.icns.argb', 'ic04')

    def test_icns(self):
        self.assert_conv_file('selected.icns', 'slct')

    def test_rgb(self):
        self.assert_conv_file('rgb.icns.rgb', 'is32')


class TestCLI_update(unittest.TestCase):
    def setUp(self):
        self.OUTFILE = 'tmp_cli_out_update.icns'
        if os.path.exists(self.OUTFILE):
            os.remove(self.OUTFILE)
        shutil.copy('icp4rgb.icns', self.OUTFILE)

    def tearDown(self):
        os.remove(self.OUTFILE)

    def test_different_outfile(self):
        other_out = 'tmp_cli_out_update_other.icns'
        run_cli(['u', '-o', other_out, self.OUTFILE, '-set', 'TOC=1'])
        s1 = os.path.getsize(self.OUTFILE)
        s2 = os.path.getsize('icp4rgb.icns')
        self.assertEqual(s1, s2)  # outfile should not be modified!
        s3 = os.path.getsize(other_out)
        self.assertNotEqual(s1, s3)
        self.assertEqual(s3, s1 + (8 + 4 * 8))
        os.remove(other_out)

    def assertUpdate(self, args, expected_diff):
        s1 = os.path.getsize(self.OUTFILE)
        run_cli(['u', self.OUTFILE] + args)
        s2 = os.path.getsize(self.OUTFILE)
        self.assertEqual(s2, s1 + expected_diff)

    def test_remove(self):
        self.assertUpdate(['-rm', 's8mk', 'l8mk'], - (256 + 8 + 1024 + 8))

    def test_add(self):
        # dropping icns file header (-8) adding icns entry header (+8)
        self.assertUpdate(['-set', 'selected=selected.icns'], 15587 - 8 + 8)

    def test_rm_add(self):
        self.assertUpdate(['-set', 'Toc', '-rm', 's8mk'], 8 + 3 * 8 - 256 - 8)

    def test_unmodified(self):
        self.assertUpdate(['-rm', 'toc', 'is32', 'it32', 'il32'], 0)


class TestCLI_print(unittest.TestCase):
    def test_single(self):
        ret = run_cli(['p', 'rgb.icns']).stdout
        for x in [b'rgb.icns', b'ICN#', b'il32', b'l8mk', b'ics#', b'is32',
                  b's8mk', b'it32', b't8mk', b'16x16', b'32x32', b'128x128']:
            self.assertTrue(x in ret)
        for x in [b'icp4rgb.icns', b'icp4', b'icp5']:
            self.assertFalse(x in ret)
        self.assertFalse(b'offset' in ret)

    def test_verbose(self):
        ret = run_cli(['p', '-v', 'rgb.icns']).stdout
        self.assertTrue(b'offset' in ret)

    def test_multiple(self):
        ret = run_cli(['p', 'rgb.icns', 'icp4rgb.icns']).stdout
        for x in [b'rgb.icns', b'icp4rgb.icns', b'icp4', b'icp5']:
            self.assertTrue(x in ret)
        self.assertFalse(b'offset' in ret)


class TestCLI_verify(unittest.TestCase):
    def test_ok(self):
        ret = run_cli(['t', 'rgb.icns']).stdout
        self.assertTrue(b'rgb.icns' in ret)
        self.assertTrue(b'OK' in ret)

    def test_multiple(self):
        ret = run_cli(['t', 'rgb.icns', 'icp4rgb.icns']).stdout
        self.assertTrue(b'rgb.icns' in ret)
        self.assertTrue(b'icp4rgb.icns' in ret)
        self.assertTrue(b'OK' in ret)

    def test_fail(self):
        ret = run_cli(['t', '18x18.j2k']).stdout
        self.assertTrue(b'18x18.j2k' in ret)
        self.assertTrue(b'Not an ICNS file' in ret)
        self.assertFalse(b'OK' in ret)

    def test_quiet(self):
        ret = run_cli(['t', '-q', 'rgb.icns', 'icp4rgb.icns']).stdout
        self.assertEqual(ret, b'')
        ret = run_cli(['t', '-q', '18x18.j2k', 'rgb.icns']).stdout
        self.assertTrue(b'18x18.j2k' in ret)
        self.assertFalse(b'rgb.icns' in ret)
        self.assertFalse(b'OK' in ret)


@unittest.skipUnless(PIL_ENABLED, 'PIL_ENABLED == False')
class TestCLI_convert(unittest.TestCase):
    def assertConvert(self, source, ext):
        dest = 'tmp_cli_out_convert.' + ext
        run_cli(['img', dest, source]).stdout
        self.assertTrue(os.path.exists(dest))
        s = os.path.getsize(dest)
        os.remove(dest)
        return s

    def test_to_png(self):
        for expected_size, fname in [
            (103, '18x18.j2k'),
            (4778, '256x256.jp2'),
            (813, 'rgb.icns.png'),
            (813, 'rgb.icns.rgb'),
        ]:
            size = self.assertConvert(fname, 'png')
            self.assertEqual(size, expected_size)

    def test_to_argb(self):
        for expected_size, fname in [
            (822, '18x18.j2k'),
            (14865, '256x256.jp2'),
            (713, 'rgb.icns.png'),
            (713, 'rgb.icns.rgb'),
        ]:
            size = self.assertConvert(fname, 'argb')
            self.assertEqual(size, expected_size)

    def test_to_rgb(self):
        for expected_size, fname, expected_mask_size in [
            (812, '18x18.j2k', 324),
            (13851, '256x256.jp2', 65536),
            (705, 'rgb.icns.png', 256),
            (705, 'rgb.icns.rgb', 256),
        ]:
            size = self.assertConvert(fname, 'rgb')
            self.assertEqual(size, expected_size)
            mask_size = os.path.getsize('tmp_cli_out_convert.rgb.mask')
            self.assertEqual(mask_size, expected_mask_size)
            os.remove('tmp_cli_out_convert.rgb.mask')

    def test_without_dest_name(self):
        src = 'tmp_cli_out_convert.jp2'
        shutil.copy('18x18.j2k', src)
        for ext, size in [('png', 103), ('argb', 822), ('rgb', 812)]:
            run_cli(['img', ext, src]).stdout
            self.assertTrue(os.path.exists(src + '.' + ext))
            self.assertEqual(os.path.getsize(src + '.' + ext), size)
            os.remove(src + '.' + ext)
        os.remove(src)
        # test if mask was created
        self.assertTrue(os.path.exists(src + '.rgb.mask'))
        self.assertEqual(os.path.getsize(src + '.rgb.mask'), 324)
        os.remove(src + '.rgb.mask')


if __name__ == '__main__':
    main()
