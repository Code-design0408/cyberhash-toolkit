"""
utils.py
--------
Shared helper utilities for the CyberHash Toolkit backend.

Responsibilities:
    * Input validation / sanitization helpers
    * A lightweight in-memory rate limiter (no external deps required)
    * Consistent JSON error/response helpers
    * File upload safety checks

Security notes:
    - We never use eval()/exec() anywhere in this project.
    - All user input is validated (length + charset) before being processed.
    - File uploads are capped in size and are never written to disk with
      user-controlled names (they are streamed straight into the hashing
      functions and discarded).
"""

import re
import time
import threading
from functools import wraps
from flask import request, jsonify

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
MAX_TEXT_LENGTH = 200_000          # max characters allowed for text hashing
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB max upload size
MAX_HASH_INPUT_LENGTH = 512        # max length for a hash string to identify

# Simple allow-list regex for the "text" field (printable UTF-8, no control chars)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def sanitize_text_input(value: str) -> str:
    """Strip dangerous control characters and enforce a max length.

    This does NOT attempt to render the string as HTML anywhere, so classic
    stored-XSS is not a concern for the hashing pipeline itself -- but we
    still scrub control characters defensively and cap length to avoid
    memory-exhaustion style abuse.
    """
    if not isinstance(value, str):
        raise ValueError("Input must be a string.")
    value = _CONTROL_CHAR_RE.sub("", value)
    if len(value) > MAX_TEXT_LENGTH:
        raise ValueError(f"Input exceeds maximum length of {MAX_TEXT_LENGTH} characters.")
    return value


def validate_hash_string(value: str) -> str:
    """Validate a hash string submitted to the identifier endpoint."""
    if not isinstance(value, str):
        raise ValueError("Hash must be a string.")
    value = value.strip()
    if not value:
        raise ValueError("Hash value cannot be empty.")
    if len(value) > MAX_HASH_INPUT_LENGTH:
        raise ValueError("Hash value is too long.")
    # Only allow hex / base64-safe characters
    if not re.fullmatch(r"[A-Za-z0-9+/=]+", value):
        raise ValueError("Hash contains invalid characters.")
    return value


def validate_algorithms(selected, available):
    """Ensure the list of requested algorithms is a subset of what we support."""
    if not selected:
        return list(available)
    if not isinstance(selected, list):
        raise ValueError("algorithms must be a list.")
    invalid = [a for a in selected if a not in available]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {', '.join(invalid)}")
    return selected


# ---------------------------------------------------------------------------
# JSON response helpers
# ---------------------------------------------------------------------------
def json_error(message: str, status: int = 400):
    response = jsonify({"success": False, "error": message})
    response.status_code = status
    return response


def json_ok(payload: dict, status: int = 200):
    payload = dict(payload)
    payload["success"] = True
    response = jsonify(payload)
    response.status_code = status
    return response


# ---------------------------------------------------------------------------
# Lightweight in-memory rate limiter
# ---------------------------------------------------------------------------
class RateLimiter:
    """A minimal thread-safe fixed-window rate limiter.

    Not distributed / not persistent -- fine for a single-process demo app.
    For production, swap this for Flask-Limiter backed by Redis.
    """

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            window = self._hits.setdefault(key, [])
            # drop timestamps outside the current window
            window[:] = [t for t in window if now - t < self.window_seconds]
            if len(window) >= self.max_requests:
                return False
            window.append(now)
            return True


rate_limiter = RateLimiter(max_requests=60, window_seconds=60)


def rate_limited(f):
    """Decorator that applies the global rate limiter keyed on client IP."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
        if not rate_limiter.is_allowed(client_ip):
            return json_error("Rate limit exceeded. Please slow down.", status=429)
        return f(*args, **kwargs)

    return wrapper


def allowed_file_size(content_length) -> bool:
    try:
        return int(content_length) <= MAX_FILE_SIZE_BYTES
    except (TypeError, ValueError):
        return False
