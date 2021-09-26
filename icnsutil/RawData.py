#!/usr/bin/env python3
import struct  # pack, unpack
import PackBytes  # get_size
import IcnsType  # get, match_maxsize


def determine_file_ext(data):
    '''
    Data should be at least 8 bytes long.
    Returns one of: png, argb, plist, jp2, icns, None
    '''
    if data[:8] == b'\x89PNG\x0d\x0a\x1a\x0a':
        return 'png'
    if data[:4] == b'ARGB':
        return 'argb'
    if data[:6] == b'bplist':
        return 'plist'
    if data[:8] in [b'\x00\x00\x00\x0CjP  ',
                    b'\xFF\x4F\xFF\x51\x00\x2F\x00\x00']:  # JPEG 2000
        return 'jp2'
    # if data[:3] == b'\xFF\xD8\xFF':  # JPEG (not supported in icns files)
    #     return 'jpg'
    if data[:4] == b'icns' or is_icns_without_header(data):
        return 'icns'  # a rather heavy calculation, postpone till end
    return None


def determine_image_size(data, ext=None):
    ''' Supports PNG, ARGB, and Jpeg 2000 image data. '''
    if not ext:
        ext = determine_file_ext(data)
    if ext == 'png':
        return struct.unpack('>II', data[16:24])
    elif ext == 'argb':
        total = PackBytes.get_size(data[4:])  # without ARGB header
        return IcnsType.match_maxsize(total, 'argb').size
    elif ext == 'jp2':
        if data[:4] == b'\xFF\x4F\xFF\x51':
            return struct.unpack('>II', data[8:16])
        len_ftype = struct.unpack('>I', data[12:16])[0]
        # file header + type box + header box (super box) + image header box
        offset = 12 + len_ftype + 8 + 8
        h, w = struct.unpack('>II', data[offset:offset + 8])
        return w, h
    return None  # icns does not support other image types except binary


def is_icns_without_header(data):
    ''' Returns True even if icns header is missing. '''
    offset = 0
    for i in range(2):  # test n keys if they exist
        key, size = icns_header_read(data[offset:offset + 8])
        try:
            IcnsType.get(key)
        except NotImplementedError:
            return False
        offset += size
        if offset > len(data) or size == 0:
            return False
        if offset == len(data):
            return True
    return True


def icns_header_read(data):
    ''' Returns icns type name and data length (incl. +8 for header) '''
    assert(type(data) == bytes)
    if len(data) != 8:
        return None, 0
    try:
        name = data[:4].decode('utf8')
    except UnicodeDecodeError:
        name = data[:4]  # Fallback to bytes-string key
    return name, struct.unpack('>I', data[4:])[0]


def icns_header_write_data(fp, key, data):
    ''' Calculates length from data. '''
    fp.write(key.encode('utf8') if type(key) == str else key)
    fp.write(struct.pack('>I', len(data) + 8))
    fp.write(data)


def icns_header_w_len(key, length):
    ''' Adds +8 to length. '''
    name = key.encode('utf8') if type(key) == str else key
    return name + struct.pack('>I', length + 8)


def parse_icns_file(fname):
    '''
    Parse file and yield media entries: (key, data)
    :raises:
        TypeError: if file is not an icns file ("icns" header missing)
    '''
    with open(fname, 'rb') as fp:
        # Check whether it is an actual ICNS file
        magic_num, _ = icns_header_read(fp.read(8))  # ignore total size
        if magic_num != 'icns':
            raise TypeError('Not an ICNS file, missing "icns" header.')
        # Read media entries as long as there is something to read
        while True:
            key, size = icns_header_read(fp.read(8))
            if not key:
                break  # EOF
            # TODO: remove test case
            if key in ['ICON', 'icm#', 'icm4', 'icm8']:
                print('YAAAY', key, fname)
            yield key, fp.read(size - 8)  # -8 header
