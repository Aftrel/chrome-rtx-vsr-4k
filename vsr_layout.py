"""Locate the verified VSR function in a Windows x64 NVIDIA driver."""

import hashlib
import mmap
import struct


FUNCTION_SIZE = 0x14d9
FUNCTION_HASH = 'd22011d13e658973b0f3bff16757544c95abdbc9fcaa2292b795dd85ad2060d0'
ANCHOR = bytes.fromhex('4648412b46400fafc881e900a3020081f9009d3500774a')
ANCHOR_OFFSET = 0xb25
HOOK_OFFSETS = (0xab2, 0xb34, 0xc5e)
# Four-byte RIP-relative displacements and calls leaving the function.
RELOCATIONS = (
    0x20, 0x27, 0x31, 0x45, 0x6e, 0x28f, 0x2a8, 0x2bc, 0x2d0, 0x38a,
    0x3e8, 0x41c, 0x427, 0x46b, 0x476, 0x673, 0xd1d, 0xe29, 0xf22,
    0x118e, 0x11be, 0x1235, 0x125a, 0x127f, 0x12f8, 0x1379, 0x1452, 0x1457, 0x1462,
)


def pe_sections(data):
    if data[:2] != b'MZ':
        raise ValueError('Missing DOS header')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if data[pe:pe + 6] != b'PE\0\0\x64\x86':
        raise ValueError('Expected a Windows x64 driver')
    section_count = struct.unpack_from('<H', data, pe + 6)[0]
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    first = pe + 24 + optional_size
    sections = {}
    for index in range(section_count):
        name, size, rva, raw_size, file_offset = struct.unpack_from('<8sIIII', data, first + index * 40)
        sections[name.rstrip(b'\0')] = (rva, file_offset, min(size, raw_size))
    return sections


def matches_function(code):
    if len(code) != FUNCTION_SIZE:
        return False
    normalized = bytearray(code)
    for offset in RELOCATIONS:
        normalized[offset:offset + 4] = b'\0' * 4
    return hashlib.sha256(normalized).hexdigest() == FUNCTION_HASH


def find_layout(path):
    with path.open('rb') as driver, mmap.mmap(driver.fileno(), 0, access=mmap.ACCESS_READ) as data:
        sections = pe_sections(data)
        code_rva, code_start, size = sections[b'.text']
        _, unwind_start, unwind_size = sections[b'.pdata']
        unwind_end = unwind_start + unwind_size - unwind_size % 12
        functions = {start for start, end, _ in struct.iter_unpack('<III', data[unwind_start:unwind_end])
                     if end - start == FUNCTION_SIZE}
        code_end = code_start + size
        match = data.find(ANCHOR, code_start, code_end)
        matches = []
        while match != -1:
            start = match - ANCHOR_OFFSET
            rva = code_rva + start - code_start
            if rva in functions and code_start <= start <= code_end - FUNCTION_SIZE:
                if matches_function(data[start:start + FUNCTION_SIZE]):
                    matches.append(rva)
            match = data.find(ANCHOR, match + 1, code_end)
    if len(matches) != 1:
        raise RuntimeError('Could not uniquely identify the verified VSR function in the NVIDIA driver.')
    return tuple(matches[0] + offset for offset in HOOK_OFFSETS)
