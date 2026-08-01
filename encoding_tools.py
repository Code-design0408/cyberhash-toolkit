"""
encoding_tools.py
------------------
Reversible *encoding* decode/encode helpers — Base64, Hex, URL-encoding,
and ROT13.

Important distinction from hashing: encodings like these are NOT
cryptographic hashes. They carry no security property at all; they are
just alternate representations of the same data, and are always fully
reversible with no key or secret required. This module exists to cover
that use case explicitly, since users often confuse "hash" and
"encoding" (see the Documentation section on the site for more).
"""

import base64
import binascii
import codecs
import urllib.parse

SUPPORTED_ENCODINGS = ["Base64", "Hex", "URL", "ROT13"]


def decode_value(value: str, encoding: str) -> dict:
    """Decode `value` assuming it was encoded with `encoding`.

    Returns {"ok": bool, "output": str | None, "error": str | None}

    Note: the key is deliberately "ok" rather than "success" -- the API
    layer's json_ok() helper always sets a top-level "success": true on
    any 2xx response, so reusing that name here would get silently
    overwritten and hide real decode failures from the client.
    """
    try:
        if encoding == "Base64":
            # Add missing padding defensively before decoding
            padded = value + "=" * (-len(value) % 4)
            output = base64.b64decode(padded, validate=False).decode("utf-8", errors="replace")
        elif encoding == "Hex":
            output = bytes.fromhex(value.strip()).decode("utf-8", errors="replace")
        elif encoding == "URL":
            output = urllib.parse.unquote(value)
        elif encoding == "ROT13":
            output = codecs.decode(value, "rot_13")
        else:
            return {"ok": False, "output": None, "error": f"Unsupported encoding: {encoding}"}
        return {"ok": True, "output": output, "error": None}
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return {"ok": False, "output": None, "error": f"Could not decode as {encoding}: invalid input."}


def encode_value(value: str, encoding: str) -> dict:
    """Encode `value` using `encoding` (the inverse of decode_value)."""
    try:
        if encoding == "Base64":
            output = base64.b64encode(value.encode("utf-8")).decode("ascii")
        elif encoding == "Hex":
            output = value.encode("utf-8").hex()
        elif encoding == "URL":
            output = urllib.parse.quote(value)
        elif encoding == "ROT13":
            output = codecs.encode(value, "rot_13")
        else:
            return {"ok": False, "output": None, "error": f"Unsupported encoding: {encoding}"}
        return {"ok": True, "output": output, "error": None}
    except Exception:
        return {"ok": False, "output": None, "error": f"Could not encode as {encoding}."}


def auto_detect_encoding(value: str) -> str:
    """Best-effort guess at which encoding a string is in, for UI convenience."""
    stripped = value.strip()
    if all(c in "0123456789abcdefABCDEF" for c in stripped) and len(stripped) % 2 == 0 and stripped:
        return "Hex"
    if "%" in stripped:
        return "URL"
    try:
        padded = stripped + "=" * (-len(stripped) % 4)
        base64.b64decode(padded, validate=True)
        return "Base64"
    except Exception:
        pass
    return "ROT13"
