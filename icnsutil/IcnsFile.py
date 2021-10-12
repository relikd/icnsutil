#!/usr/bin/env python3
import os  # path, makedirs, remove
import struct  # unpack float in _description()
from sys import stderr
from typing import Iterator, Iterable, Tuple, Optional, List, Dict, Union
from . import RawData, IcnsType
from .ArgbImage import ArgbImage


class IcnsFile:
    __slots__ = ['media', 'infile']

    @staticmethod
    def verify(fname: str) -> Iterator[str]:
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
                    yield 'Unsupported icns type: ' + str(key)
                    continue

                ext = RawData.determine_file_ext(data)
                if ext is None:
                    bin_keys.add(key)

                # Check whether stored type is an expected file format
                if not (iType.is_type(ext) if ext else iType.is_binary()):
                    yield 'Unexpected type for key {}: {} != {}'.format(
                        str(key), ext or 'binary', iType.types)

                if ext in ['png', 'jp2', 'icns', 'plist']:
                    continue

                # Check whether uncompressed size is equal to expected maxsize
                if key == 'it32' and data[:4] != b'\x00\x00\x00\x00':
                    # TODO: check whether other it32 headers exist
                    yield 'Unexpected it32 data header: ' + str(data[:4])
                udata = iType.decompress(data, ext) or data

                # Check expected uncompressed maxsize
                if iType.maxsize and len(udata) != iType.maxsize:
                    yield 'Invalid data length for {}: {} != {}'.format(
                        str(key), len(udata), iType.maxsize)
        # if file is not an icns file
        except RawData.ParserError as e:
            yield str(e)
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
                yield 'Missing key pair: {} found, {} missing.'.format(
                    mask, img)

        # Check duplicate image dimensions
        for x, y in [('is32', 'icp4'), ('il32', 'icp5'), ('it32', 'ic07'),
                     ('ic04', 'icp4'), ('ic05', 'icp5')]:
            if x in all_keys and y in all_keys:
                yield 'Redundant keys: {} and {} have identical size.'.format(
                    x, y)

    @staticmethod
    def description(fname: str, *, verbose: bool = False, indent: int = 0) -> \
            str:
        return IcnsFile._description(
            RawData.parse_icns_file(fname), verbose=verbose, indent=indent)

    @staticmethod
    def _description(enumerator: Iterable[Tuple[IcnsType.Media.KeyT, bytes]],
                     *, verbose: bool = False, indent: int = 0) -> str:
        ''' Expects an enumerator with (key, size, data) '''
        txt = ''
        offset = 8  # already with icns header
        try:
            for key, data in enumerator:
                size = len(data)
                txt += os.linesep + ' ' * indent
                txt += '{}: {} bytes'.format(str(key), size)
                if verbose:
                    txt += ', offset: {}'.format(offset)
                    offset += size + 8
                if key == 'name':
                    txt += ', value: "{}"'.format(data.decode('utf-8'))
                    continue
                if key == 'icnV':
                    txt += ', value: {}'.format(struct.unpack('>f', data)[0])
                    continue
                ext = RawData.determine_file_ext(data)
                try:
                    iType = IcnsType.get(key)
                    if not ext:
                        ext = iType.fallback_ext()
                    txt += ', ' + ext + ': ' + iType.filename(size_only=True)
                except NotImplementedError:
                    txt += ': UNKNOWN TYPE: ' + str(ext or data[:6])
            return txt[len(os.linesep):] + os.linesep
        # if file is not an icns file
        except RawData.ParserError as e:
            return ' ' * indent + str(e) + os.linesep

    def __init__(self, file: str = None) -> None:
        ''' Read .icns file and load bundled media files into memory. '''
        self.media = {}  # type: Dict[IcnsType.Media.KeyT, bytes]
        self.infile = file
        if not file:  # create empty image
            return
        for key, data in RawData.parse_icns_file(file):
            self.media[key] = data
            try:
                IcnsType.get(key)
            except NotImplementedError:
                print('Warning: unknown media type: {}, {} bytes, "{}"'.format(
                    str(key), len(data), file), file=stderr)

    def has_toc(self) -> bool:
        return 'TOC ' in self.media.keys()

    def add_media(self, key: Optional[IcnsType.Media.KeyT] = None, *,
                  file: Optional[str] = None, data: Optional[bytes] = None,
                  force: bool = False) -> None:
        '''
        If you provide both, data and file, data takes precedence.
        However, the filename is still used for type-guessing.
        - Declare retina images with suffix "@2x.png".
        - Declare icns file with suffix "-dark", "-template", or "-selected"
        '''
        if file and not data:
            with open(file, 'rb') as fp:
                data = fp.read()
        if not data:
            raise AttributeError('Did you miss file= or data= attribute?')

        if not key:  # Determine ICNS type
            iType = IcnsType.guess(data, file)
            key = iType.key
            is_icns = iType.is_type('icns')
        else:
            is_icns = True  # we dont know, so we assume it is

        # Check if type is unique
        if not force and key in self.media.keys():
            raise KeyError('Image with identical key "{}". File: {}'.format(
                str(key), file))
        # Nested icns files must omit the icns header
        if is_icns and data[:4] == b'icns':
            data = data[8:]
        self.media[key] = data

    def remove_media(self, key: IcnsType.Media.KeyT) -> bool:
        if key not in self.media.keys():
            return False
        del self.media[key]
        return True

    def write(self, fname: str, *, toc: bool = False) -> None:
        ''' Create a new ICNS file from stored media. '''
        # Rebuild TOC to ensure soundness
        order = self._make_toc(enabled=toc)
        # Total file size has always +8 for media header (after _make_toc)
        total = sum(len(x) + 8 for x in self.media.values())
        with open(fname, 'wb') as fp:
            fp.write(RawData.icns_header_w_len(b'icns', total))
            for key in order:
                RawData.icns_header_write_data(fp, key, self.media[key])

    def export(self, outdir: Optional[str] = None, *,
               allowed_ext: str = '*', key_suffix: bool = False,
               convert_png: bool = False, decompress: bool = False,
               recursive: bool = False) -> Dict[IcnsType.Media.KeyT,
                                                Union[str, Dict]]:
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
            raise OSError('"{}" is not a directory. Abort.'.format(outdir))

        export_files = {}  # type: Dict[IcnsType.Media.KeyT, Union[str, Dict]]
        if self.infile:
            export_files['_'] = self.infile
        keys = list(self.media.keys())
        # Convert to PNG
        if convert_png:
            for imgk, maskk in IcnsType.enum_png_convertable(keys):
                fname = self._export_to_png(outdir, imgk, maskk, key_suffix)
                if not fname:
                    continue
                export_files[imgk] = fname
                if maskk:
                    export_files[maskk] = fname
                    if maskk in keys:
                        keys.remove(maskk)
                keys.remove(imgk)

        # prepare filter
        allowed = [] if allowed_ext == '*' else allowed_ext.split(',')
        if recursive:
            cleanup = allowed and 'icns' not in allowed
            if cleanup:
                allowed.append('icns')

        # Export remaining
        for key in keys:
            fname = self._export_single(outdir, key, key_suffix,
                                        decompress, allowed)
            if fname:
                export_files[key] = fname

        # repeat for all icns
        if recursive:
            for old_key, old_name in export_files.items():
                assert(isinstance(old_name, str))
                if not old_name.endswith('.icns') or old_key == '_':
                    continue
                export_files[old_key] = IcnsFile(old_name).export(
                    allowed_ext=allowed_ext, key_suffix=key_suffix,
                    convert_png=convert_png, decompress=decompress,
                    recursive=True)
                if cleanup:
                    os.remove(old_name)
        return export_files

    def _make_toc(self, *, enabled: bool) -> List[IcnsType.Media.KeyT]:
        # Rebuild TOC to ensure soundness
        if self.has_toc():
            del self.media['TOC ']
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

    def _export_single(self, outdir: str, key: IcnsType.Media.KeyT,
                       key_suffix: bool, decompress: bool,
                       allowed: List[str]) -> Optional[str]:
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
                data = iType.decompress(data, ext) or data  # type: ignore
            if not ext:  # overwrite ext after (decompress requires None)
                ext = 'rgb' if iType.compressable else 'bin'
        except NotImplementedError:  # If key unkown, export anyway
            fname = str(key)  # str() because key may be binary-str
            if not ext:
                ext = 'unknown'

        if allowed and ext not in allowed:
            return None
        fname = os.path.join(outdir, fname + '.' + ext)
        with open(fname, 'wb') as fp:
            fp.write(data)
        return fname

    def _export_to_png(self, outdir: str, img_key: IcnsType.Media.KeyT,
                       mask_key: Optional[IcnsType.Media.KeyT],
                       key_suffix: bool) -> Optional[str]:
        ''' You must ensure key and mask_key exists! '''
        data = self.media[img_key]
        if RawData.determine_file_ext(data) not in ['argb', None]:
            return None  # icp4 and icp5 can have png or jp2 data
        iType = IcnsType.get(img_key)
        fname = iType.filename(key_only=key_suffix, size_only=True)
        fname = os.path.join(outdir, fname + '.png')
        if iType.bits == 1:
            ArgbImage.from_mono(data, iType).write_png(fname)
        else:
            mask_data = self.media[mask_key] if mask_key else None
            ArgbImage(data=data, mask=mask_data).write_png(fname)
        return fname

    def __repr__(self) -> str:
        lst = ', '.join(str(k) for k in self.media.keys())
        return '<{}: file={}, [{}]>'.format(
            type(self).__name__, self.infile, lst)

    def __str__(self) -> str:
        return 'File: ' + (self.infile or '-mem-') + os.linesep \
            + IcnsFile._description(self.media.items(), indent=2)
