"""
hash_identifier.py
-------------------
Heuristic hash-type identification.

Hashes carry no metadata about which algorithm produced them, so this
module can only make an educated guess based on:
    * String length
    * Character set (hex vs base64)
    * Common "fingerprints" (e.g. bcrypt/argon2 prefixes)

This is intentionally heuristic / best-effort -- it is a learning &
CTF-style utility, not a forensic tool. Confidence scores communicate
that clearly to the user.
"""

import re
import base64

_HEX_RE = re.compile(r"^[a-fA-F0-9]+$")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")

# length (hex chars) -> list of (algorithm, base_confidence)
_LENGTH_MAP = {
    16: [("MD4/Half-MD5 fragment", 30)],
    32: [("MD5", 55), ("NTLM", 30), ("LM", 15)],
    40: [("SHA1", 70), ("RIPEMD160", 20), ("MySQL5", 10)],
    56: [("SHA224", 75), ("SHA3-224", 25)],
    64: [("SHA256", 65), ("SHA3-256", 25), ("BLAKE2s", 10)],
    96: [("SHA384", 75), ("SHA3-384", 25)],
    128: [("SHA512", 65), ("SHA3-512", 25), ("Whirlpool", 10)],
}

# Known textual prefixes for salted / KDF-based hashes
_PREFIX_SIGNATURES = [
    (r"^\$2[aby]?\$", "bcrypt"),
    (r"^\$argon2(id|i|d)\$", "Argon2"),
    (r"^\$6\$", "SHA-512 crypt (Unix)"),
    (r"^\$5\$", "SHA-256 crypt (Unix)"),
    (r"^\$1\$", "MD5 crypt (Unix)"),
    (r"^\{SSHA\}", "Salted SHA (SSHA)"),
]


def identify_hash(value: str) -> dict:
    """Return a best-guess identification for the given hash string.

    Returns:
        {
            "input_length": int,
            "primary_guess": {"algorithm": str, "confidence": int} | None,
            "alternatives": [{"algorithm": str, "confidence": int}, ...],
            "is_hex": bool,
            "is_base64": bool,
        }
    """
    value = value.strip()
    length = len(value)
    is_hex = bool(_HEX_RE.fullmatch(value))
    is_base64 = _is_valid_base64(value) if not is_hex else False

    candidates = []

    # 1. Check well-known salted-hash prefixes first (highest confidence)
    for pattern, name in _PREFIX_SIGNATURES:
        if re.match(pattern, value):
            candidates.append((name, 95))

    # 2. Hex-length based guesses
    if is_hex and length in _LENGTH_MAP:
        candidates.extend(_LENGTH_MAP[length])

    # 3. Base64-encoded hash guess (common for SHA1/SHA256 stored as base64)
    if is_base64 and not is_hex:
        decoded_len = _decoded_byte_length(value)
        base64_len_map = {16: "MD5 (base64)", 20: "SHA1 (base64)", 32: "SHA256 (base64)", 64: "SHA512 (base64)"}
        guess = base64_len_map.get(decoded_len)
        if guess:
            candidates.append((guess, 50))
        else:
            candidates.append(("Base64-encoded data", 40))

    # 4. Fallback: unknown
    if not candidates:
        candidates.append(("Unknown", 20))

    # Deduplicate + sort by confidence desc
    seen = {}
    for name, conf in candidates:
        if name not in seen or conf > seen[name]:
            seen[name] = conf
    sorted_candidates = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)

    primary = sorted_candidates[0]
    alternatives = sorted_candidates[1:6]  # cap list length

    return {
        "input_length": length,
        "primary_guess": {"algorithm": primary[0], "confidence": primary[1]},
        "alternatives": [{"algorithm": a, "confidence": c} for a, c in alternatives],
        "is_hex": is_hex,
        "is_base64": is_base64,
    }


def _is_valid_base64(value: str) -> bool:
    if not _BASE64_RE.fullmatch(value) or len(value) % 4 != 0:
        return False
    try:
        base64.b64decode(value, validate=True)
        return True
    except Exception:
        return False


def _decoded_byte_length(value: str) -> int:
    try:
        return len(base64.b64decode(value, validate=True))
    except Exception:
        return -1


def compare_hashes(hash_a: str, hash_b: str) -> dict:
    """Case-insensitive comparison of two hash strings."""
    a, b = hash_a.strip().lower(), hash_b.strip().lower()
    return {"match": a == b and a != "", "hash_a": hash_a.strip(), "hash_b": hash_b.strip()}
