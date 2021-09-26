#!/usr/bin/env python3
def pack(data):
    ret = []
    buf = []
    i = 0

    def flush_buf():
        # write out non-repeating bytes
        if len(buf) > 0:
            ret.append(len(buf) - 1)
            ret.extend(buf)
            buf.clear()

    end = len(data)
    while i < end:
        arr = data[i:i + 3]
        x = arr[0]
        if len(arr) == 3 and x == arr[1] and x == arr[2]:
            flush_buf()
            # repeating
            c = 3
            while (i + c) < len(data) and data[i + c] == x:
                c += 1
            i += c
            while c > 130:  # max number of copies encodable in compression
                ret.append(0xFF)
                ret.append(x)
                c -= 130
            ret.append(c + 0x7D)  # 0x80 - 3
            ret.append(x)
        else:
            buf.append(x)
            if len(buf) > 127:
                flush_buf()
            i += 1
    flush_buf()
    return bytes(ret)


def unpack(data):
    ret = []
    i = 0
    end = len(data)
    while i < end:
        n = data[i]
        if n < 0x80:
            ret += data[i + 1:i + n + 2]
            i += n + 2
        else:
            ret += [data[i + 1]] * (n - 0x7D)
            i += 2
    return ret


def get_size(data):
    count = 0
    i = 0
    end = len(data)
    while i < end:
        n = data[i]
        if n < 0x80:
            count += n + 1
            i += n + 2
        else:
            count += n - 125
            i += 2
    return count


def msb_stream(data, *, bits):
    if bits not in [1, 2, 4]:
        raise NotImplementedError('Unsupported bit-size.')
    c = 0
    byte = 0
    for x in data:  # 8-bits in, most significant n-bits out
        c += bits
        byte <<= bits
        byte |= (x >> (8 - bits))
        if c == 8:
            yield byte
            c = 0
            byte = 0
    if c > 0:  # fill up missing bits
        byte <<= (8 - c)
        yield byte
