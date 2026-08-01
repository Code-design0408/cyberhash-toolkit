"""
app.py
------
CyberHash Toolkit - Flask backend entry point.

Routes:
    GET  /                     -> main single-page app (all sections)
    POST /api/generate         -> generate hashes for text input
    POST /api/file-hash        -> generate hashes for an uploaded file
    POST /api/identify         -> identify a pasted hash
    POST /api/decode           -> check a hash against a small common-password wordlist
    POST /api/crack/wordlist   -> dictionary attack (built-in list or a caller-supplied wordlist)
    POST /api/crack/brute-force -> tightly bounded brute-force search over a short charset/length
    POST /api/encoding/decode  -> decode a reversible encoding (Base64/Hex/URL/ROT13)
    POST /api/encoding/encode  -> encode a value into Base64/Hex/URL/ROT13
    POST /api/compare          -> compare two hashes
    GET  /api/history          -> list recent history entries
    DELETE /api/history/<id>   -> delete one history entry
    DELETE /api/history        -> clear all history

Security:
    * Rate limiting on every API route (see utils.rate_limited)
    * Strict input validation (see utils.py)
    * Security response headers (CSP, X-Content-Type-Options, etc.)
    * No eval(), no raw SQL string interpolation (parameterized queries only)
    * Uploaded files are streamed directly into the hasher, never saved to disk
"""

import sqlite3
import time
from pathlib import Path

from flask import Flask, render_template, request, g

from hash_generator import generate_text_hashes, generate_file_hashes, SUPPORTED_ALGORITHMS
from hash_identifier import identify_hash, compare_hashes
from hash_decoder import attempt_decode
from hash_cracker import crack_with_wordlist, crack_with_brute_force, MAX_BRUTE_FORCE_LENGTH
from encoding_tools import decode_value, encode_value, SUPPORTED_ENCODINGS
from utils import (
    sanitize_text_input,
    validate_hash_string,
    validate_algorithms,
    json_ok,
    json_error,
    rate_limited,
    allowed_file_size,
    MAX_FILE_SIZE_BYTES,
)

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "history.db"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE_BYTES  # hard cap enforced by Flask itself


# ---------------------------------------------------------------------------
# Database helpers (SQLite - used only for optional scan history)
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,        -- 'generate' | 'identify' | 'file-hash' | 'compare'
            summary TEXT NOT NULL,          -- short human-readable summary
            detail TEXT NOT NULL,           -- JSON blob with full result
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_history(operation: str, summary: str, detail_json: str):
    db = get_db()
    db.execute(
        "INSERT INTO history (operation, summary, detail, created_at) VALUES (?, ?, ?, ?)",
        (operation, summary, detail_json, time.time()),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Security headers on every response
# ---------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://unpkg.com 'unsafe-inline'; "
        "style-src 'self' https://cdnjs.cloudflare.com https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return response


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template(
        "index.html",
        algorithms=list(SUPPORTED_ALGORITHMS.keys()),
        max_brute_force_length=MAX_BRUTE_FORCE_LENGTH,
    )


# ---------------------------------------------------------------------------
# API: Generate hash(es) from text
# ---------------------------------------------------------------------------
@app.route("/api/generate", methods=["POST"])
@rate_limited
def api_generate():
    data = request.get_json(silent=True) or {}
    try:
        text = sanitize_text_input(data.get("text", ""))
        algorithms = validate_algorithms(data.get("algorithms"), SUPPORTED_ALGORITHMS.keys())
    except ValueError as e:
        return json_error(str(e))

    if not text:
        return json_error("Please provide text to hash.")

    results = generate_text_hashes(text, algorithms)

    try:
        save_history(
            "generate",
            f"Text hash ({len(algorithms)} algorithm(s), {len(text)} chars)",
            _to_json_safe({"algorithms": algorithms, "length": len(text)}),
        )
    except Exception:
        pass  # history is best-effort; never break the main feature

    return json_ok({"results": results})


# ---------------------------------------------------------------------------
# API: Generate hash(es) from an uploaded file
# ---------------------------------------------------------------------------
@app.route("/api/file-hash", methods=["POST"])
@rate_limited
def api_file_hash():
    if not allowed_file_size(request.content_length):
        return json_error("File too large. Maximum size is 50 MB.", status=413)

    if "file" not in request.files:
        return json_error("No file was uploaded.")

    uploaded = request.files["file"]
    if uploaded.filename == "":
        return json_error("No file was selected.")

    algorithms = request.form.getlist("algorithms") or ["MD5", "SHA256", "SHA512"]
    try:
        algorithms = validate_algorithms(algorithms, SUPPORTED_ALGORITHMS.keys())
    except ValueError as e:
        return json_error(str(e))

    result = generate_file_hashes(uploaded.stream, algorithms)

    safe_name = Path(uploaded.filename).name  # strip any path components

    try:
        save_history(
            "file-hash",
            f"File hash: {safe_name} ({result['size_bytes']} bytes)",
            _to_json_safe({"filename": safe_name, **result}),
        )
    except Exception:
        pass

    return json_ok({"filename": safe_name, **result})


# ---------------------------------------------------------------------------
# API: Identify a pasted hash
# ---------------------------------------------------------------------------
@app.route("/api/identify", methods=["POST"])
@rate_limited
def api_identify():
    data = request.get_json(silent=True) or {}
    try:
        hash_value = validate_hash_string(data.get("hash", ""))
    except ValueError as e:
        return json_error(str(e))

    result = identify_hash(hash_value)

    try:
        save_history("identify", f"Identify: {hash_value[:24]}...", _to_json_safe(result))
    except Exception:
        pass

    return json_ok(result)


# ---------------------------------------------------------------------------
# API: Hash decoder (dictionary attack against a built-in common wordlist)
# ---------------------------------------------------------------------------
@app.route("/api/decode", methods=["POST"])
@rate_limited
def api_decode():
    data = request.get_json(silent=True) or {}
    try:
        hash_value = validate_hash_string(data.get("hash", ""))
        algorithms = validate_algorithms(data.get("algorithms"), SUPPORTED_ALGORITHMS.keys())
    except ValueError as e:
        return json_error(str(e))

    result = attempt_decode(hash_value, algorithms)

    try:
        save_history(
            "decode",
            f"Decode: {'found' if result['found'] else 'not found'} ({hash_value[:16]}...)",
            _to_json_safe(result),
        )
    except Exception:
        pass

    return json_ok(result)


# ---------------------------------------------------------------------------
# API: Hash cracker (dictionary attack w/ optional custom wordlist, and a
# tightly bounded brute-force mode). See hash_cracker.py for the bounds
# that keep this a fast, single-request-safe educational demo.
# ---------------------------------------------------------------------------
@app.route("/api/crack/wordlist", methods=["POST"])
@rate_limited
def api_crack_wordlist():
    data = request.get_json(silent=True) or {}
    try:
        hash_value = validate_hash_string(data.get("hash", ""))
        algorithms = validate_algorithms(data.get("algorithms"), SUPPORTED_ALGORITHMS.keys())
    except ValueError as e:
        return json_error(str(e))

    wordlist = data.get("wordlist")  # optional list[str]; falls back to built-in list
    try:
        result = crack_with_wordlist(hash_value, algorithms, wordlist)
    except ValueError as e:
        return json_error(str(e))

    try:
        save_history(
            "crack-wordlist",
            f"Crack (wordlist/{result['source']}): {'found' if result['found'] else 'not found'} "
            f"({hash_value[:16]}...)",
            _to_json_safe(result),
        )
    except Exception:
        pass

    return json_ok(result)


@app.route("/api/crack/brute-force", methods=["POST"])
@rate_limited
def api_crack_brute_force():
    data = request.get_json(silent=True) or {}
    try:
        hash_value = validate_hash_string(data.get("hash", ""))
    except ValueError as e:
        return json_error(str(e))

    algorithm = data.get("algorithm", "MD5")
    if algorithm not in SUPPORTED_ALGORITHMS:
        return json_error(f"Unsupported algorithm: {algorithm}")

    charset = data.get("charset")
    if charset is not None and not isinstance(charset, str):
        return json_error("charset must be a string.")

    try:
        max_length = int(data.get("max_length", 4))
    except (TypeError, ValueError):
        return json_error("max_length must be an integer.")
    if max_length < 1:
        return json_error("max_length must be at least 1.")

    try:
        result = crack_with_brute_force(hash_value, algorithm, charset, max_length)
    except ValueError as e:
        return json_error(str(e))

    try:
        save_history(
            "crack-brute-force",
            f"Crack (brute-force, max_length={min(max_length, MAX_BRUTE_FORCE_LENGTH)}): "
            f"{'found' if result['found'] else 'not found'} ({hash_value[:16]}...)",
            _to_json_safe(result),
        )
    except Exception:
        pass

    return json_ok(result)


# ---------------------------------------------------------------------------
# API: Encoding decoder / encoder (Base64, Hex, URL, ROT13 - NOT hashing)
# ---------------------------------------------------------------------------
@app.route("/api/encoding/decode", methods=["POST"])
@rate_limited
def api_encoding_decode():
    data = request.get_json(silent=True) or {}
    try:
        value = sanitize_text_input(data.get("value", ""))
    except ValueError as e:
        return json_error(str(e))
    encoding = data.get("encoding")
    if encoding not in SUPPORTED_ENCODINGS:
        return json_error(f"Unsupported encoding. Choose one of: {', '.join(SUPPORTED_ENCODINGS)}")
    if not value:
        return json_error("Please provide a value to decode.")

    result = decode_value(value, encoding)
    if not result["ok"]:
        return json_error(result["error"])

    try:
        save_history("encoding-decode", f"Decode ({encoding}): {value[:24]}...", _to_json_safe(result))
    except Exception:
        pass

    return json_ok(result)


@app.route("/api/encoding/encode", methods=["POST"])
@rate_limited
def api_encoding_encode():
    data = request.get_json(silent=True) or {}
    try:
        value = sanitize_text_input(data.get("value", ""))
    except ValueError as e:
        return json_error(str(e))
    encoding = data.get("encoding")
    if encoding not in SUPPORTED_ENCODINGS:
        return json_error(f"Unsupported encoding. Choose one of: {', '.join(SUPPORTED_ENCODINGS)}")
    if not value:
        return json_error("Please provide a value to encode.")

    result = encode_value(value, encoding)
    if not result["ok"]:
        return json_error(result["error"])
    return json_ok(result)


# ---------------------------------------------------------------------------
# API: Compare two hashes
# ---------------------------------------------------------------------------
@app.route("/api/compare", methods=["POST"])
@rate_limited
def api_compare():
    data = request.get_json(silent=True) or {}
    try:
        a = validate_hash_string(data.get("hash_a", ""))
        b = validate_hash_string(data.get("hash_b", ""))
    except ValueError as e:
        return json_error(str(e))

    result = compare_hashes(a, b)

    try:
        save_history("compare", f"Compare: match={result['match']}", _to_json_safe(result))
    except Exception:
        pass

    return json_ok(result)


# ---------------------------------------------------------------------------
# API: History
# ---------------------------------------------------------------------------
@app.route("/api/history", methods=["GET"])
@rate_limited
def api_history_list():
    search = request.args.get("q", "").strip()
    db = get_db()
    if search:
        rows = db.execute(
            "SELECT id, operation, summary, created_at FROM history "
            "WHERE summary LIKE ? ORDER BY created_at DESC LIMIT 100",
            (f"%{search}%",),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT id, operation, summary, created_at FROM history ORDER BY created_at DESC LIMIT 100"
        ).fetchall()

    entries = [
        {"id": r["id"], "operation": r["operation"], "summary": r["summary"], "created_at": r["created_at"]}
        for r in rows
    ]
    return json_ok({"entries": entries})


@app.route("/api/history/<int:entry_id>", methods=["DELETE"])
@rate_limited
def api_history_delete_one(entry_id):
    db = get_db()
    db.execute("DELETE FROM history WHERE id = ?", (entry_id,))
    db.commit()
    return json_ok({"deleted": entry_id})


@app.route("/api/history", methods=["DELETE"])
@rate_limited
def api_history_clear():
    db = get_db()
    db.execute("DELETE FROM history")
    db.commit()
    return json_ok({"cleared": True})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(413)
def too_large(e):
    return json_error("Uploaded file is too large.", status=413)


@app.errorhandler(404)
def not_found(e):
    return json_error("Resource not found.", status=404)


@app.errorhandler(500)
def server_error(e):
    return json_error("An internal error occurred.", status=500)


def _to_json_safe(obj):
    import json
    return json.dumps(obj)


if __name__ == "__main__":
    init_db()
    # debug=False in any environment resembling production
    app.run(host="127.0.0.1", port=5000, debug=False)
