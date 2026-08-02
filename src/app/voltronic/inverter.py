"""Blocking, single-connection I/O to a Voltronic inverter.

Opens the device once and keeps the file descriptor open across queries — the
old C++ code re-opened per query (inverter.cpp:76) which is unnecessary when
we're the only consumer. Works for /dev/hidraw* (raw byte stream) and, when the
kernel exposes it as a TTY, /dev/ttyUSB* (configured 2400 8N1).
"""

from __future__ import annotations

import logging
import os
import select
import time
from typing import Optional

from . import crc

log = logging.getLogger(__name__)

READ_TIMEOUT = 2.0  # seconds — matches the old C++ inner read loop


class InverterError(RuntimeError):
    pass


class Inverter:
    def __init__(self, device: str) -> None:
        self.device = device
        self._fd: Optional[int] = None

    def open(self) -> None:
        if self._fd is not None:
            return
        fd = os.open(self.device, os.O_RDWR | os.O_NONBLOCK)
        self._configure_tty(fd)
        self._fd = fd
        log.info("opened device %s (fd=%d)", self.device, fd)

    def close(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    def _configure_tty(self, fd: int) -> None:
        """Best-effort 2400 8N1 setup — silently skips non-TTY devices (hidraw)."""
        try:
            import termios
        except ImportError:
            return
        try:
            attrs = termios.tcgetattr(fd)
        except termios.error:
            return  # not a TTY (hidraw) — no configuration needed
        iflag, oflag, cflag, lflag, ispeed, ospeed, cc = attrs
        cflag &= ~(termios.PARENB | termios.CSTOPB | termios.CSIZE)
        cflag |= termios.CS8 | termios.CLOCAL
        oflag &= ~termios.OPOST
        termios.tcsetattr(
            fd, termios.TCSANOW,
            [iflag, oflag, cflag, lflag, termios.B2400, termios.B2400, cc],
        )
        termios.tcflush(fd, termios.TCOFLUSH)

    def query(self, cmd: str, expected_len: int) -> Optional[bytes]:
        """Send `cmd`, return the raw payload between '(' and CRC, or None on failure."""
        if self._fd is None:
            self.open()
        assert self._fd is not None

        request = crc.frame(cmd.encode("ascii"))
        try:
            os.write(self._fd, request)
        except OSError as e:
            log.warning("write %s failed: %s", cmd, e)
            self.close()
            return None

        buf = bytearray()
        deadline = time.monotonic() + READ_TIMEOUT
        while len(buf) < expected_len:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                log.warning("%s read timeout after %d/%d bytes", cmd, len(buf), expected_len)
                return None
            r, _, _ = select.select([self._fd], [], [], remaining)
            if not r:
                continue
            try:
                chunk = os.read(self._fd, expected_len - len(buf))
            except BlockingIOError:
                continue
            except OSError as e:
                log.warning("read %s failed: %s", cmd, e)
                self.close()
                return None
            if not chunk:
                continue
            buf.extend(chunk)
            # Some inverters return one long frame terminated by 0x0d; if we see
            # the terminator early, stop rather than blocking for the padded length.
            if buf.endswith(b"\r"):
                break

        if not buf or buf[0:1] != b"(" or buf[-1:] != b"\r":
            log.warning("%s bad framing: %r", cmd, bytes(buf))
            return None
        if not crc.check(bytes(buf)):
            log.warning("%s CRC mismatch: %r", cmd, bytes(buf))
            return None
        return bytes(buf[1:-3])  # strip leading '(' and trailing CRC+CR

    def __enter__(self) -> "Inverter":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
