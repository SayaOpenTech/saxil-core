"""Length-prefixed transport envelope. Frozen W1 v1 reference copy."""

from __future__ import annotations

import socket
import struct
import threading
import time
from typing import Optional

from .errors import DecodeError, TransportError, VersionError
from .protocol import (
    ENV_VERSION,
    KIND_ACK,
    KIND_SML,
    STATUS_OK,
    Envelope,
)

ENV_HEADER_SIZE = 24
LENGTH_SIZE = 4
MAX_PAYLOAD = 1 << 20


def encode_envelope(env: Envelope) -> bytes:
    if env.env_version != ENV_VERSION:
        raise ValueError("bad env version")
    body = struct.pack(
        "!BBBBQIHHI",
        env.env_version & 0xFF,
        env.kind & 0xFF,
        env.status & 0xFF,
        0,
        int(env.message_id) & 0xFFFFFFFFFFFFFFFF,
        int(env.seq) & 0xFFFFFFFF,
        int(env.src_agent) & 0xFFFF,
        int(env.dst_agent) & 0xFFFF,
        len(env.payload),
    )
    assert len(body) == ENV_HEADER_SIZE
    frame = body + env.payload
    return struct.pack("!I", len(frame)) + frame


def decode_envelope_body(body: bytes) -> Envelope:
    if len(body) < ENV_HEADER_SIZE:
        raise DecodeError("envelope truncate")
    ver, kind, status, _res, msg_id, seq, src, dst, plen = struct.unpack(
        "!BBBBQIHHI", body[:ENV_HEADER_SIZE]
    )
    if ver != ENV_VERSION:
        raise VersionError(f"unsupported envelope version {ver}")
    if plen > MAX_PAYLOAD:
        raise DecodeError("oversized")
    if len(body) != ENV_HEADER_SIZE + plen:
        raise DecodeError("length mismatch")
    return Envelope(
        kind=kind,
        status=status,
        message_id=msg_id,
        seq=seq,
        src_agent=src,
        dst_agent=dst,
        payload=body[ENV_HEADER_SIZE:],
        env_version=ver,
    )


def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise TransportError("connection closed")
        buf.extend(chunk)
    return bytes(buf)


def recv_frame(sock: socket.socket) -> Envelope:
    raw_len = recv_exact(sock, LENGTH_SIZE)
    (n,) = struct.unpack("!I", raw_len)
    if n > MAX_PAYLOAD + ENV_HEADER_SIZE:
        raise DecodeError("oversized frame")
    body = recv_exact(sock, n)
    return decode_envelope_body(body)


def send_frame(sock: socket.socket, env: Envelope) -> None:
    sock.sendall(encode_envelope(env))


def make_ack(message_id: int, seq: int, src: int, dst: int, status: int = STATUS_OK) -> Envelope:
    return Envelope(kind=KIND_ACK, status=status, message_id=message_id, seq=seq, src_agent=src, dst_agent=dst, payload=b"")


class FrameBuffer:
    def __init__(self):
        self._buf = bytearray()

    def feed(self, data: bytes) -> list:
        self._buf.extend(data)
        out = []
        while True:
            if len(self._buf) < LENGTH_SIZE:
                break
            (n,) = struct.unpack("!I", self._buf[:LENGTH_SIZE])
            if n > MAX_PAYLOAD + ENV_HEADER_SIZE:
                raise DecodeError("oversized frame")
            total = LENGTH_SIZE + n
            if len(self._buf) < total:
                break
            body = bytes(self._buf[LENGTH_SIZE:total])
            del self._buf[:total]
            out.append(decode_envelope_body(body))
        return out


class BoundedQueue:
    def __init__(self, maxlen: int = 10_000):
        self.maxlen = maxlen
        self._q = []
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self.rejected = 0

    def put(self, item, block: bool = True, timeout: Optional[float] = None) -> bool:
        with self._not_full:
            if not block and len(self._q) >= self.maxlen:
                self.rejected += 1
                return False
            end = None if timeout is None else time.time() + timeout
            while len(self._q) >= self.maxlen:
                remaining = None if end is None else end - time.time()
                if remaining is not None and remaining <= 0:
                    self.rejected += 1
                    return False
                self._not_full.wait(timeout=remaining)
            self._q.append(item)
            self._not_empty.notify()
            return True

    def get(self, timeout: Optional[float] = None):
        with self._not_empty:
            end = None if timeout is None else time.time() + timeout
            while not self._q:
                remaining = None if end is None else end - time.time()
                if remaining is not None and remaining <= 0:
                    raise TimeoutError("queue empty")
                self._not_empty.wait(timeout=remaining)
            item = self._q.pop(0)
            self._not_full.notify()
            return item

    def qsize(self) -> int:
        with self._lock:
            return len(self._q)


def connect_tcp(host: str, port: int, timeout: float = 5.0) -> socket.socket:
    s = socket.create_connection((host, port), timeout=timeout)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return s


def connect_unix(path: str, timeout: float = 5.0) -> socket.socket:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(path)
    return s


def send_sml(sock, payload: bytes, message_id: int, seq: int, src: int = 1, dst: int = 2, kind: int = KIND_SML) -> None:
    send_frame(
        sock,
        Envelope(kind=kind, status=STATUS_OK, message_id=message_id, seq=seq, src_agent=src, dst_agent=dst, payload=payload),
    )


def receive_sml(sock) -> Envelope:
    return recv_frame(sock)
