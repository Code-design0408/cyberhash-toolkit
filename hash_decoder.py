"""
hash_decoder.py
----------------
Best-effort "hash decoder" (dictionary attack) for CyberHash Toolkit.

Hashing is one-way by design, so there is no way to mathematically
reverse a hash back into its input. What tools like this actually do
is a *dictionary attack*: hash a list of common candidate strings with
the requested algorithm(s) and see if any of them match.

This module intentionally uses a small, built-in list of extremely
common passwords/words (the kind that show up at the top of every
"most common passwords" list) rather than pulling in a leaked
credential database. The point is defensive: quickly flag "this hash
corresponds to a trivially weak/common value," not to crack arbitrary
real-world passwords.

If nothing in the wordlist matches, we report that plainly instead of
guessing.
"""

from hash_generator import SUPPORTED_ALGORITHMS

# A small, well-known list of extremely common passwords / test values.
# Deliberately NOT a large breach-derived wordlist -- this is meant to
# catch trivially weak hashes for educational/defensive checks, not to
# function as a general-purpose password cracker.
COMMON_WORDLIST = [
    "123456", "password", "123456789", "12345678", "12345", "qwerty",
    "abc123", "111111", "123123", "letmein", "iloveyou", "admin",
    "welcome", "monkey", "login", "starwars", "dragon", "sunshine",
    "master", "hello", "freedom", "whatever", "trustno1", "654321",
    "1234567", "12345678910", "password1", "qwerty123", "1q2w3e4r",
    "000000", "football", "baseball", "superman", "michael", "shadow",
    "test", "test123", "guest", "root", "changeme", "default",
    "administrator", "hunter2", "passw0rd", "p@ssw0rd", "letmein123",
    "1234", "123", "abcd1234", "asdfgh", "zxcvbn", "google", "facebook",
]

MAX_ALGORITHMS_PER_REQUEST = 4  # keep the dictionary sweep bounded


def attempt_decode(hash_value: str, algorithms=None) -> dict:
    """Attempt to match a hash against the built-in common-value wordlist.

    Args:
        hash_value: the target hash (hex digest), case-insensitive.
        algorithms: list of algorithm names to try; defaults to the most
            commonly seen ones (MD5, SHA1, SHA256).

    Returns:
        {
            "found": bool,
            "plaintext": str | None,
            "algorithm": str | None,
            "attempts": int,
        }
    """
    target = hash_value.strip().lower()
    algorithms = algorithms or ["MD5", "SHA1", "SHA256"]
    algorithms = [a for a in algorithms if a in SUPPORTED_ALGORITHMS][:MAX_ALGORITHMS_PER_REQUEST]

    attempts = 0
    for word in COMMON_WORDLIST:
        encoded = word.encode("utf-8")
        for algo in algorithms:
            attempts += 1
            digest = SUPPORTED_ALGORITHMS[algo](encoded).hexdigest()
            if digest == target:
                return {"found": True, "plaintext": word, "algorithm": algo, "attempts": attempts}

    return {"found": False, "plaintext": None, "algorithm": None, "attempts": attempts}
