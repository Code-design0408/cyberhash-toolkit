"""
hash_cracker.py
----------------
"Hash Cracker" module for CyberHash Toolkit.

This builds on the same idea as hash_decoder.py (a dictionary attack)
but generalizes it in two ways that are useful for CTF-style / defensive
education workflows:

    1. Custom wordlist mode - the caller can supply their own candidate
       list (e.g. pasted from a textarea) instead of only the built-in
       common-password list. Still capped in size so a single request
       can't be turned into an unbounded compute job.

    2. Brute-force mode - exhaustively tries every string from a small
       character set up to a short max length. This is intentionally
       bounded very tightly (see MAX_BRUTE_FORCE_LENGTH /
       MAX_BRUTE_FORCE_SPACE below). It exists to *demonstrate* why short
       passwords are unsafe (you can watch the search space explode),
       not to function as a real cracking rig -- there's no GPU
       acceleration, no rule-based mangling, no distributed work, and
       the search space cap keeps worst-case requests fast and bounded
       even on modest hardware.

As with hash_decoder.py: hashing is one-way, so nothing here "reverses"
a hash mathematically. Both modes work by hashing lots of candidate
plaintexts and checking for a match.
"""

import itertools
import string

from hash_generator import SUPPORTED_ALGORITHMS
from hash_decoder import COMMON_WORDLIST

# ---------------------------------------------------------------------------
# Shared bounds (keep every mode fast + bounded on a single request)
# ---------------------------------------------------------------------------
MAX_ALGORITHMS_PER_REQUEST = 4

# Custom wordlist mode
MAX_CUSTOM_WORDLIST_ENTRIES = 5000
MAX_CUSTOM_WORD_LENGTH = 128

# Brute-force mode
MAX_BRUTE_FORCE_LENGTH = 5          # absolute ceiling on candidate length
DEFAULT_BRUTE_FORCE_CHARSET = string.ascii_lowercase + string.digits
MAX_BRUTE_FORCE_CHARSET_LEN = 40    # limits worst-case charset ("everything")
MAX_BRUTE_FORCE_SPACE = 2_000_000   # hard cap on total candidates attempted


def crack_with_wordlist(hash_value: str, algorithms=None, wordlist=None) -> dict:
    """Dictionary attack using either the built-in common-password list
    or a caller-supplied list of candidate plaintexts.

    Args:
        hash_value: target hex digest, case-insensitive.
        algorithms: list of algorithm names to try (defaults to MD5/SHA1/SHA256).
        wordlist: optional list of candidate strings. Falls back to the
            built-in COMMON_WORDLIST from hash_decoder.py when omitted.

    Returns:
        {
            "found": bool,
            "plaintext": str | None,
            "algorithm": str | None,
            "attempts": int,
            "source": "custom" | "built-in",
        }
    """
    target = hash_value.strip().lower()
    algorithms = algorithms or ["MD5", "SHA1", "SHA256"]
    algorithms = [a for a in algorithms if a in SUPPORTED_ALGORITHMS][:MAX_ALGORITHMS_PER_REQUEST]

    if wordlist:
        source = "custom"
        candidates = _clean_custom_wordlist(wordlist)
    else:
        source = "built-in"
        candidates = COMMON_WORDLIST

    attempts = 0
    for word in candidates:
        encoded = word.encode("utf-8")
        for algo in algorithms:
            attempts += 1
            digest = SUPPORTED_ALGORITHMS[algo](encoded).hexdigest()
            if digest == target:
                return {
                    "found": True,
                    "plaintext": word,
                    "algorithm": algo,
                    "attempts": attempts,
                    "source": source,
                }

    return {"found": False, "plaintext": None, "algorithm": None, "attempts": attempts, "source": source}


def crack_with_brute_force(hash_value: str, algorithm: str, charset: str = None, max_length: int = 4) -> dict:
    """Exhaustively try short candidate strings against a single algorithm.

    This is deliberately tiny in scope (see module docstring). It's meant
    to make a point in a UI demo -- "look how fast a 4-character password
    falls" -- not to be a practical cracking tool.

    Args:
        hash_value: target hex digest, case-insensitive.
        algorithm: a single algorithm name (must be in SUPPORTED_ALGORITHMS).
        charset: characters to draw candidates from (defaults to a-z0-9).
        max_length: longest candidate length to try, capped at
            MAX_BRUTE_FORCE_LENGTH regardless of what's requested.

    Returns:
        {
            "found": bool,
            "plaintext": str | None,
            "algorithm": str | None,
            "attempts": int,
            "search_space": int,
            "truncated": bool,   # True if we stopped due to MAX_BRUTE_FORCE_SPACE
        }
    """
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    target = hash_value.strip().lower()
    charset = (charset or DEFAULT_BRUTE_FORCE_CHARSET)[:MAX_BRUTE_FORCE_CHARSET_LEN]
    charset = "".join(dict.fromkeys(charset))  # de-dupe, preserve order
    if not charset:
        raise ValueError("Charset must contain at least one character.")

    max_length = max(1, min(int(max_length), MAX_BRUTE_FORCE_LENGTH))

    ctor = SUPPORTED_ALGORITHMS[algorithm]
    attempts = 0
    truncated = False
    search_space = sum(len(charset) ** n for n in range(1, max_length + 1))

    for length in range(1, max_length + 1):
        for combo in itertools.product(charset, repeat=length):
            if attempts >= MAX_BRUTE_FORCE_SPACE:
                truncated = True
                break
            attempts += 1
            candidate = "".join(combo)
            digest = ctor(candidate.encode("utf-8")).hexdigest()
            if digest == target:
                return {
                    "found": True,
                    "plaintext": candidate,
                    "algorithm": algorithm,
                    "attempts": attempts,
                    "search_space": search_space,
                    "truncated": truncated,
                }
        if truncated:
            break

    return {
        "found": False,
        "plaintext": None,
        "algorithm": None,
        "attempts": attempts,
        "search_space": search_space,
        "truncated": truncated,
    }


def _clean_custom_wordlist(raw_list) -> list:
    """Validate/trim a caller-supplied wordlist to keep requests bounded."""
    if not isinstance(raw_list, list):
        raise ValueError("wordlist must be a list of strings.")
    cleaned = []
    for entry in raw_list[:MAX_CUSTOM_WORDLIST_ENTRIES]:
        if not isinstance(entry, str):
            continue
        entry = entry.strip()
        if not entry or len(entry) > MAX_CUSTOM_WORD_LENGTH:
            continue
        cleaned.append(entry)
    return cleaned
