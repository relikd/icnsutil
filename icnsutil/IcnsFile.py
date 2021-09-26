#!/usr/bin/env python3
import os  # path
import sys  # stderr
import RawData
import IcnsType
import struct  # unpack float in _description()
from ArgbImage import ArgbImage  # in _export_to_png()


class IcnsFile:
    @staticmethod
    def verify(fname):
        '''
        Yields an error message for each issue.
        You can check for validity with `is_invalid = any(obj.verify())`
        '''
        all_keys = set()
        bin_keys = set()
        try:
            for key, data in RawData.parse_icns_file(fname):
                all_keys.add(key)
                # Check if icns type is known
                try:
                    iType = IcnsType.get(key)
                except NotImplementedError:
                    yield f'Unsupported icns type: {key}'
                    continue

                ext = RawData.determine_file_ext(data)
                if ext is None:
                    bin_keys.add(key)

                # Check whether stored type is an expected file format
                if not (iType.is_type(ext) if ext else iType.is_binary()):
                    yield 'Unexpected type for key {}: {} != {}'.format(
                        key, ext or 'binary', iType.types)

                if ext in ['png', 'jp2', 'icns', 'plist']:
                    continue

                # Check whether uncompressed size is equal to expected maxsize
                if key == 'it32' and data[:4] != b'\x00\x00\x00\x00':
                    # TODO: check whether other it32 headers exist
                    yield f'Unexpected it32 data header: {data[:4]}'
                data = iType.decompress(data, ext)  # ignores non-compressable

                # Check expected uncompressed maxsize
                if iType.maxsize and len(data) != iType.maxsize:
                    yield 'Invalid data length for {}: {} != {}'.format(
                        key, len(data), iType.maxsize)
        # if file is not an icns file
        except TypeError as e:
            yield e
            return

        # Check total size after enum. Enum may raise exception and break early
        with open(fname, 'rb') as fp:
            _, header_size = RawData.icns_header_read(fp.read(8))
        actual_size = os.path.getsize(fname)
        if header_size != actual_size:
            yield 'header file-size != actual size: {} != {}'.format(
                header_size, actual_size)

        # Check key pairings
        for img, mask in IcnsType.enum_img_mask_pairs(bin_keys):
            if not img or not mask:
                if not img:
                    img, mask = mask, img
                yield f'Missing key pair: {mask} found, {img} missing.'

        # Check duplicate image dimensions
        for x, y in [('is32', 'icp4'), ('il32', 'icp5'), ('it32', 'ic07'),
                     ('ic04', 'icp4'), ('ic05', 'icp5')]:
            if x in all_keys and y in all_keys:
                yield f'Redundant keys: {x} and {y} have identical size.'

    @staticmethod
    def description(fname, *, verbose=False, indent=0):
        return IcnsFile._description(
            RawData.parse_icns_file(fname), verbose=verbose, indent=indent)

    @staticmethod
    def _description(enumerator, *, verbose=False, indent=0):
        ''' Expects an enumerator with (key, size, data) '''
        txt = ''
        offset = 8  # already with icns header
        for key, data in enumerator:
            # actually, icns length should be -8 (artificially appended header)
            size = len(data)
            txt += ' ' * indent
            txt += f'{key}: {size} bytes'
            if verbose:
                txt += f', offset: {offset}'
                offset += size + 8
            if key == 'name':
                txt += f', value: "{data.decode("utf-8")}"\n'
                continue
            if key == 'icnV':
                txt += f', value: {struct.unpack(">f", data)[0]}\n'
                continue
            ext = RawData.determine_file_ext(data)
            try:
                iType = IcnsType.get(key)
                if not ext:
                    ext = iType.types[-1]
                desc = iType.filename(size_only=True)
                txt += f', {ext or "binary"}: {desc}\n'
            except NotImplementedError:
                txt += f': UNKNOWN TYPE: {ext or data[:6]}\n'
        return txt

    def __init__(self, file=None):
        ''' Read .icns file and load bundled media files into memory. '''
        self.media = {}
        self.infile = file
        if not file:  # create empty image
            return
        for key, data in RawData.parse_icns_file(file):
            self.media[key] = data
            try:
                IcnsType.get(key)
            except NotImplementedError:
                print('Warning: unknown media type: {}, {} bytes, "{}"'.format(
                    key, len(data), file), file=sys.stderr)

    def add_media(self, key=None, *, file=None, data=None, force=False):
        '''
        If you provide both, data and file, data takes precedence.
        However, the filename is still used for type-guessing.
        - Declare retina images with suffix "@2x.png".
        - Declare icns file with suffix "-dark", "-template", or "-selected"
        '''
        assert(not key or len(key) == 4)  # did you miss file= or data=?
        if file and not data:
            with open(file, 'rb') as fp:
                data = fp.read()

        if not key:  # Determine ICNS type
            key = IcnsType.guess(data, file).key
        # Check if type is unique
        if not force and key in self.media.keys():
            raise KeyError(f'Image with identical key "{key}". File: {file}')
        self.media[key] = data

    def write(self, fname, *, toc=True):
        ''' Create a new ICNS file from stored media. '''
        # Rebuild TOC to ensure soundness
        order = self._make_toc(enabled=toc)
        # Total file size has always +8 for media header (after _make_toc)
        total = sum(len(x) + 8 for x in self.media.values())
        with open(fname, 'wb') as fp:
            fp.write(RawData.icns_header_w_len(b'icns', total))
            for key in order:
                RawData.icns_header_write_data(fp, key, self.media[key])

    def export(self, outdir=None, *, allowed_ext=None, key_suffix=False,
               convert_png=False, decompress=False, recursive=False):
        '''
        Write all bundled media files to output directory.

        - outdir : If none provided, use same directory as source file.
        - allowed_ext : Export only data with matching extension(s).
        - key_suffix : If True, use icns type instead of image size filename.
        - convert_png : If True, convert rgb and argb images to png.
        - decompress : Only relevant for ARGB and 24-bit binary images.
        - recursive : Repeat export for all attached icns files.
                      Incompatible with png_only flag.
        '''
        if not outdir:  # aka, determine by input file
            # Determine filename and prepare output directory
            outdir = (self.infile or 'in-memory.icns') + '.export'
            os.makedirs(outdir, exist_ok=True)
        elif not os.path.isdir(outdir):
            raise NotADirectoryError(f'"{outdir}" is not a directory. Abort.')

        exported_files = {'_': self.infile}
        keys = list(self.media.keys())
        # Convert to PNG
        if convert_png:
            # keys = [x for x in keys if x not in []]
            for imgk, maskk in IcnsType.enum_png_convertable(keys):
                fname = self._export_to_png(outdir, imgk, maskk, key_suffix)
                if not fname:
                    continue
                exported_files[imgk] = fname
                if maskk:
                    exported_files[maskk] = fname
                    if maskk in keys:
                        keys.remove(maskk)
                keys.remove(imgk)

        # prepare filter
        if type(allowed_ext) == str:
            allowed_ext = [allowed_ext]
        if recursive:
            cleanup = allowed_ext and 'icns' not in allowed_ext
            if cleanup:
                allowed_ext.append('icns')

        # Export remaining
        for key in keys:
            fname = self._export_single(outdir, key, key_suffix, decompress,
                                        allowed_ext)
            if fname:
                exported_files[key] = fname

        # repeat for all icns
        if recursive:
            for key, fname in exported_files.items():
                if key == '_' or not fname.endswith('.icns'):
                    continue
                prev_fname = exported_files[key]
                exported_files[key] = IcnsFile(fname).export(
                    allowed_ext=allowed_ext, key_suffix=key_suffix,
                    convert_png=convert_png, decompress=decompress,
                    recursive=True)
                if cleanup:
                    os.remove(prev_fname)
        return exported_files

    def _make_toc(self, *, enabled):
        # Rebuild TOC to ensure soundness
        if 'TOC ' in self.media.keys():
            del(self.media['TOC '])
        # We loop two times over the keys; so, make sure order is identical.
        # By default this will be the same order as read/written.
        order = list(self.media.keys())
        if enabled:
            self.media['TOC '] = b''.join(
                RawData.icns_header_w_len(x, len(self.media[x]))
                for x in order)
            # Table of contents, if enabled, is always first entry
            order.insert(0, 'TOC ')

        return order

    def _export_single(self, outdir, key, key_suffix, decompress, allowed_ext):
        ''' You must ensure that keys exist in self.media '''
        data = self.media[key]
        ext = RawData.determine_file_ext(data)
        if ext == 'icns' and data[:4] != b'icns':
            header = RawData.icns_header_w_len(b'icns', len(data))
            data = header + data  # Add missing icns header
        try:
            iType = IcnsType.get(key)
            fname = iType.filename(key_only=key_suffix)
            if decompress:
                data = iType.decompress(data, ext)  # ignores non-compressable
            if not ext:  # overwrite ext after (decompress requires None)
                ext = 'rgb' if iType.compressable else 'bin'
        except NotImplementedError:  # If key unkown, export anyway
            fname = str(key)  # str() because key may be binary-str
            if not ext:
                ext = 'unknown'

        if allowed_ext and ext not in allowed_ext:
            return None
        fname = os.path.join(outdir, f'{fname}.{ext}')
        with open(fname, 'wb') as fp:
            fp.write(data)
        return fname

    def _export_to_png(self, outdir, img_key, mask_key, key_suffix):
        ''' You must ensure key and mask_key exists! '''
        data = self.media[img_key]
        if RawData.determine_file_ext(data) not in ['argb', None]:
            return None  # icp4 and icp5 can have png or jp2 data
        iType = IcnsType.get(img_key)
        fname = iType.filename(key_only=key_suffix, size_only=True)
        fname = os.path.join(outdir, fname + '.png')
        if iType.bits == 1:
            # return None
            ArgbImage.from_mono(data, iType).write_png(fname)
        else:
            mask_data = self.media[mask_key] if mask_key else None
            ArgbImage(data=data, mask=mask_data).write_png(fname)
        return fname

    def __repr__(self):
        lst = ', '.join(str(k) for k in self.media.keys())
        return f'<{type(self).__name__}: file={self.infile}, [{lst}]>'

    def __str__(self):
        return f'File: {self.infile or "-mem-"}\n' \
            + IcnsFile._description(self.media.items(), indent=2)
