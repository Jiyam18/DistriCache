"""
Protocol parser for DistriCache's TCP layer.

Supports two input styles, matching how real Redis clients work:
  1. Inline commands (simple, human-typeable): "SET foo bar\\r\\n"
  2. RESP arrays (what real client libraries send):
       *3\\r\\n$3\\r\\nSET\\r\\n$3\\r\\nfoo\\r\\n$3\\r\\nbar\\r\\n
     which means: array of 3 bulk strings: "SET", "foo", "bar"

Why support both? Inline mode makes manual testing with `telnet` or
`nc` trivial (good for demos/debugging). RESP mode is what makes this
protocol "real" rather than a toy -- it's the same wire format Redis
uses, parsed byte-accurately, which is the part worth explaining in an
interview.

This module is intentionally synchronous and pure (no I/O) so it can
be unit tested without a running server: feed it bytes, get back
either a parsed command or "need more data."
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


class ProtocolError(Exception):
    """Raised when the input bytes are malformed per the protocol."""


@dataclass
class ParseResult:
    command: Optional[list[str]]  # None if more data is needed
    bytes_consumed: int


def parse_inline(buffer: bytes) -> ParseResult:
    """Parse a single inline command terminated by \\r\\n or \\n."""
    newline_idx = buffer.find(b"\n")
    if newline_idx == -1:
        return ParseResult(command=None, bytes_consumed=0)

    line = buffer[:newline_idx]
    if line.endswith(b"\r"):
        line = line[:-1]

    consumed = newline_idx + 1
    text = line.decode("utf-8", errors="replace").strip()
    if not text:
        return ParseResult(command=[], bytes_consumed=consumed)

    # Simple whitespace split -- no quoting support by design (inline
    # mode is for quick manual testing, not binary-safe values).
    parts = text.split()
    return ParseResult(command=parts, bytes_consumed=consumed)


def parse_resp(buffer: bytes) -> ParseResult:
    """
    Parse one RESP array-of-bulk-strings command from the start of buffer.
    Returns command=None (bytes_consumed=0) if the buffer doesn't yet
    contain a complete command -- caller should read more bytes and retry.
    Raises ProtocolError on malformed input (wrong type markers, bad
    lengths) so the server can close the misbehaving connection.
    """
    if not buffer:
        return ParseResult(command=None, bytes_consumed=0)

    if buffer[0:1] != b"*":
        raise ProtocolError(f"expected '*' to start a RESP array, got {buffer[0:1]!r}")

    pos = _find_crlf(buffer, 0)
    if pos is None:
        return ParseResult(command=None, bytes_consumed=0)

    try:
        num_args = int(buffer[1:pos])
    except ValueError:
        raise ProtocolError(f"invalid array length: {buffer[1:pos]!r}")
    if num_args < 0:
        raise ProtocolError("negative array length")

    cursor = pos + 2  # skip past \r\n
    args: list[str] = []

    for _ in range(num_args):
        if cursor >= len(buffer):
            return ParseResult(command=None, bytes_consumed=0)
        if buffer[cursor:cursor + 1] != b"$":
            raise ProtocolError(f"expected '$' bulk string marker, got {buffer[cursor:cursor+1]!r}")

        len_end = _find_crlf(buffer, cursor)
        if len_end is None:
            return ParseResult(command=None, bytes_consumed=0)

        try:
            arg_len = int(buffer[cursor + 1:len_end])
        except ValueError:
            raise ProtocolError(f"invalid bulk string length: {buffer[cursor+1:len_end]!r}")
        if arg_len < 0:
            raise ProtocolError("negative bulk string length")

        data_start = len_end + 2
        data_end = data_start + arg_len
        trailing_crlf_end = data_end + 2

        if trailing_crlf_end > len(buffer):
            return ParseResult(command=None, bytes_consumed=0)
        if buffer[data_end:trailing_crlf_end] != b"\r\n":
            raise ProtocolError("bulk string not terminated with CRLF")

        args.append(buffer[data_start:data_end].decode("utf-8", errors="replace"))
        cursor = trailing_crlf_end

    return ParseResult(command=args, bytes_consumed=cursor)


def _find_crlf(buffer: bytes, start: int) -> Optional[int]:
    idx = buffer.find(b"\r\n", start)
    return idx if idx != -1 else None


def parse_command(buffer: bytes) -> ParseResult:
    """
    Auto-detect protocol style from the first byte and dispatch.
    '*' => RESP array. Anything else => inline command.
    """
    if not buffer:
        return ParseResult(command=None, bytes_consumed=0)
    if buffer[0:1] == b"*":
        return parse_resp(buffer)
    return parse_inline(buffer)


def encode_simple_string(s: str) -> bytes:
    return f"+{s}\r\n".encode("utf-8")


def encode_error(msg: str) -> bytes:
    return f"-ERR {msg}\r\n".encode("utf-8")


def encode_integer(n: int) -> bytes:
    return f":{n}\r\n".encode("utf-8")


def encode_bulk_string(s: Optional[str]) -> bytes:
    if s is None:
        return b"$-1\r\n"  # RESP null bulk string
    encoded = s.encode("utf-8")
    return f"${len(encoded)}\r\n".encode("utf-8") + encoded + b"\r\n"


def encode_array(items: list[str]) -> bytes:
    out = f"*{len(items)}\r\n".encode("utf-8")
    for item in items:
        out += encode_bulk_string(item)
    return out
