"""
    Utilities and functions for dealing with LZSS compression.
    First written for dealing with files for Rusty (PC-98).

    See here for a good resource on LZSS:
    http://wiki.xentax.com/index.php/LZSS
"""

import os
import sys
from bitstring import BitArray

# Methods for dealing with flags.
# 0: pointer
# 1: literal


def interpret_flag(h):
    if isinstance(h, int):
        h = "%x" % h
        h = h.zfill(2)
        h = '0x' + h
    ba = BitArray(hex=h)
    return [x == '1' for x in ba.bin[::-1]]


def flag_length(h):
    flag_interpretation = interpret_flag(h)
    length = 8
    # All literal: 8, all pointers: 16
    # True is equal to 1, so just sum them to get the length above 8.
    return length + (8 - sum(flag_interpretation))


def little_endianize(n):
    # Ex. little_endianize(0x3e1a) -> (0x1a, 0x3e)
    return (n & 0Xff, n >> 8)


def pointer_pack(first, second):
    """Ex. pointer_pack(0xab, 0xcd) == 0xabcd"""
    return (first << 8) + second


def write_little_endian(file, number, bytes=1):
    for i in range(1, bytes + 1):
        shift = 8 * (i - 1)
        value = (number & (0xff << shift)) >> shift
        file.write(chr(value))


def pointer_length(p):
    """The lowest nybble of the pointer is its length, minus 3."""
    return (p & 0xF) + 3


def pointer_offset(p):
    """
    The offset is something like the top three nybbles of the packed bytes.
    """
    # 4 bytes: a b c d
    # offset is 0xcab, which is c << 12
    # Ex. 0x0700 should return 15h.
    return ((p & 0xF0) << 4) + (p >> 8) + 0x12


def decompress(filename):
    output = []
    buf = [0] * 0x1000
    parent_dir = '\\'.join(filename.split('\\')[:-1])
    target_filepath = filename
    with open(target_filepath, 'rb') as f:
        # header = f.read(7) # 4c 5a 1a 3e 46 00 00
        # header stuff
        # Simple header = easier to change lengths of files??? Maybe.
        # Game is 5MB, and has 2.8MB free. (great)
        _ = f.read(3)  # magic number
        _ = f.read(2)  # expected output length
        _ = f.read(2)

        flag = f.read(1)
        cursor = 0
        print(hex(cursor), hex(ord(flag)), ":", end=' ')
        while flag != "":
            things = interpret_flag(ord(flag))
            for literal in things:
                if literal:
                    literal_byte = ord(f.read(1))
                    print(hex(literal_byte), end=' ')
                    buf[cursor % 0x1000] = literal_byte
                    output.append(literal_byte)
                    cursor += 1
                else:
                    try:
                        pointer_bytes = ord(f.read(1)), ord(f.read(1))
                    except TypeError:
                        break
                    print("[%s %s]" % (hex(pointer_bytes[0]), hex(pointer_bytes[1])), end=' ')
                    packed = pointer_pack(pointer_bytes[0], pointer_bytes[1])
                    length = pointer_length(packed)
                    offset = pointer_offset(packed)

                    # Sometimes it does a cool thing where it points to bytes
                    # as it's writing them!!
                    # So you need to access buf one byte at a time to allow that.
                    for b in range(0, length):
                        pointed_byte = buf[(offset + b) % 0x1000]
                        buf[cursor % 0x1000] = pointed_byte
                        output.append(pointed_byte)
                        cursor += 1
            print("")

            flag = f.read(1)
            try:
                print(hex(cursor), hex(ord(flag)), ":", end=' ')
                _ = hex(ord(flag))
            except TypeError:
                # print "end of input"
                break

    output_filepath = os.path.join(parent_dir, 'decompressed_' + filename)
    with open(output_filepath, 'wb') as f:
        for b in output:
            f.write(chr(b))
    return output_filepath


def compress(filepath):
    with open(filepath, 'rb') as f:
        target_bytes = f.read()
    filename = filepath.split('\\')[-1]
    parent_dir = filepath.rstrip(filename)
    compressed_filepath = os.path.join(parent_dir, filename.lstrip('decompressed_'))
    with open(compressed_filepath, 'wb') as f:
        # Write the header first.
        f.write(b'\x4c\x5a\x1a')  # magic number
        write_little_endian(f, len(target_bytes), 2)
        f.write(b'\x00\x00')  # another magic number

        cursor = 0
        while cursor <= len(target_bytes):
            block_counter = 8
            f.write(b'\xff')
            while block_counter:
                try:
                    f.write(chr(ord(target_bytes[cursor])))
                except IndexError:
                    cursor = 999999999
                    break
                cursor += 1
                block_counter -= 1
        # Pad the last flag with 0x00 bytes to fill it up
        while block_counter:
            f.write(b'\x00')
            block_counter -= 1
    return compressed_filepath


# header: 4c5a ("LZ"), almost like 4d5a ("MZ"), but suggesting LZ* compression

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python lzss.py [de]compress file.exe")
        sys.exit()
    if sys.argv[1].lower() == 'decompress':
        decompress(sys.argv[2])
        print("Wrote file to 'decompressed_" + sys.argv[2] + "'")
    elif sys.argv[1].lower() == 'compress':
        compress(sys.argv[2])
        print("Wrote file to '" + sys.argv[2].lstrip('decompressed_') + "'")
