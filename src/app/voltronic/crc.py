"""Voltronic CRC-16 (nibble-lookup XMODEM variant with reserved-byte substitution).

Ported verbatim from src/inverter-cli/inverter.cpp `cal_crc_half`. Reserved bytes
0x28 ('('), 0x0d ('\\r'), and 0x0a ('\\n') are bumped by 1 in either CRC byte to
avoid confusion with framing.
"""

_TABLE = (
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
)


def crc16(data: bytes) -> int:
    crc = 0
    for byte in data:
        da = (crc >> 8) >> 4
        crc = (crc << 4) & 0xFFFF
        crc ^= _TABLE[da ^ (byte >> 4)]
        da = (crc >> 8) >> 4
        crc = (crc << 4) & 0xFFFF
        crc ^= _TABLE[da ^ (byte & 0x0F)]

    lo = crc & 0xFF
    hi = (crc >> 8) & 0xFF
    if lo in (0x28, 0x0D, 0x0A):
        lo += 1
    if hi in (0x28, 0x0D, 0x0A):
        hi += 1
    return (hi << 8) | lo


def check(frame: bytes) -> bool:
    """Verify the trailing 2-byte CRC against everything before it."""
    if len(frame) < 3:
        return False
    expected = crc16(frame[:-3])
    return frame[-3] == (expected >> 8) & 0xFF and frame[-2] == expected & 0xFF


def frame(cmd: bytes) -> bytes:
    """Return `cmd || CRC_hi || CRC_lo || 0x0D` ready to send to the inverter."""
    c = crc16(cmd)
    return cmd + bytes(((c >> 8) & 0xFF, c & 0xFF, 0x0D))
