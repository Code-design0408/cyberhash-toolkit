"""
hash_generator.py
------------------
Pure hashing logic for CyberHash Toolkit.

Supports:
    MD5, SHA1, SHA224, SHA256, SHA384, SHA512, SHA3-256, SHA3-512,
    BLAKE2b, BLAKE2s

All functions use Python's standard-library `hashlib`, which wraps
OpenSSL / native implementations -- no custom or unsafe crypto code.
"""

import hashlib

# Map of "display name" -> hashlib constructor
SUPPORTED_ALGORITHMS = {
    "MD5": hashlib.md5,
    "SHA1": hashlib.sha1,
    "SHA224": hashlib.sha224,
    "SHA256": hashlib.sha256,
    "SHA384": hashlib.sha384,
    "SHA512": hashlib.sha512,
    "SHA3-256": hashlib.sha3_256,
    "SHA3-512": hashlib.sha3_512,
    "BLAKE2b": hashlib.blake2b,
    "BLAKE2s": hashlib.blake2s,
}

# Chunk size used when streaming file uploads through the hash functions
CHUNK_SIZE = 1024 * 1024  # 1 MB


def generate_text_hashes(text: str, algorithms=None) -> dict:
    """Generate one or more hashes for a plain-text string.

    Args:
        text: the plaintext to hash (already sanitized by caller).
        algorithms: list of algorithm names to compute; defaults to all.

    Returns:
        dict of {algorithm_name: hex_digest}
    """
    algorithms = algorithms or list(SUPPORTED_ALGORITHMS.keys())
    encoded = text.encode("utf-8")
    results = {}
    for name in algorithms:
        ctor = SUPPORTED_ALGORITHMS.get(name)
        if ctor is None:
            continue
        results[name] = ctor(encoded).hexdigest()
    return results


def generate_file_hashes(file_stream, algorithms=None) -> dict:
    """Stream a file-like object through one or more hash algorithms.

    Reads in fixed-size chunks so large files never need to be fully
    loaded into memory at once.

    Args:
        file_stream: a binary file-like object (has .read(size))
        algorithms: list of algorithm names to compute; defaults to a
            practical default set for file hashing (MD5, SHA256, SHA512).

    Returns:
        dict with 'hashes' (algorithm -> hex digest) and 'size_bytes'.
    """
    algorithms = algorithms or ["MD5", "SHA256", "SHA512"]
    hashers = {name: SUPPORTED_ALGORITHMS[name]() for name in algorithms if name in SUPPORTED_ALGORITHMS}

    total_bytes = 0
    while True:
        chunk = file_stream.read(CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        for hasher in hashers.values():
            hasher.update(chunk)

    return {
        "hashes": {name: h.hexdigest() for name, h in hashers.items()},
        "size_bytes": total_bytes,
    }
