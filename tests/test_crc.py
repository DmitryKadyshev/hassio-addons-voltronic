from voltronic import crc


def test_frame_round_trip() -> None:
    command = b"QMOD"
    frame = crc.frame(command)
    assert frame.startswith(command)
    assert frame.endswith(b"\r")
    assert len(frame) == len(command) + 3


def test_known_qmod_frame_crc() -> None:
    command = b"QMOD"
    expected = crc.crc16(command)
    assert crc.frame(command) == command + expected.to_bytes(2, "big") + b"\r"


def test_check_rejects_corrupted_frame() -> None:
    frame = b"(P" + crc.crc16(b"(P").to_bytes(2, "big") + b"\r"
    assert crc.check(frame)
    corrupted = frame[:-3] + bytes([frame[-3] ^ 0x01]) + frame[-2:]
    assert not crc.check(corrupted)
