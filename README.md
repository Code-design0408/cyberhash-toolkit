# CyberHash Toolkit

A modern, cyberpunk-themed **Hash Generator** and **Hash Identifier** web app, built for cybersecurity education and defensive security workflows (integrity verification, hash recognition, CTF-style triage).

![CyberHash Toolkit](static/img/screenshot-placeholder.png)

## Features

- **Hash Generator** — MD5, SHA1, SHA224, SHA256, SHA384, SHA512, SHA3-256, SHA3-512, BLAKE2b, BLAKE2s, with live generation as you type
- **File Hash Generator** — drag-and-drop upload with a progress bar, streamed hashing (no memory blowups on large files)
- **Hash Identifier** — heuristic algorithm detection by length/format with a confidence score and alternative guesses
- **Hash Decoder** — checks a hash against a small, built-in list of common/weak passwords (educational demo of why weak passwords are risky — cryptographic hashes are one-way and cannot be truly "decoded")
- **Hash Cracker** — dictionary attack against either the built-in common-password list or a caller-supplied wordlist (capped at 5,000 entries), plus a tightly bounded brute-force mode (max length 5, capped search space) that demonstrates how quickly short passwords fall
- **Encoding Decoder/Encoder** — Base64, Hex, URL-encoding, and ROT13 — these are reversible *encodings*, not hashes, so full round-trip decode/encode is supported
- **Hash Comparison** — quick match / not-match check between two hashes
- **History** — recent operations stored in SQLite, with search, delete, and export
- **Copy / Download** — one-click copy with toast feedback, downloadable `.txt` results
- **Dark / Light mode**, animated cyberpunk UI (matrix rain, animated grid, glassmorphism, neon glow)
- **Accessible** — keyboard navigable, ARIA labels, visible focus rings, respects `prefers-reduced-motion`

## Tech Stack

- **Backend:** Python 3, Flask, SQLite (stdlib `sqlite3`)
- **Frontend:** HTML5, Tailwind CSS (CDN), vanilla JS (ES6), Font Awesome, AOS
- **Fonts:** Orbitron (display), JetBrains Mono (body/code)

## Project Structure

```
cyberhash-toolkit/
├── app.py                 # Flask app & API routes
├── hash_generator.py      # Text/file hashing logic
├── hash_identifier.py     # Hash-type identification heuristics
├── hash_decoder.py        # Common-password wordlist check ("decoder")
├── hash_cracker.py        # Wordlist + bounded brute-force cracking ("cracker")
├── encoding_tools.py      # Base64 / Hex / URL / ROT13 encode & decode
├── utils.py                # Validation, rate limiting, response helpers
├── requirements.txt
├── templates/
│   └── index.html          # Single-page app (all sections)
└── static/
    ├── css/style.css       # Cyberpunk theme
    ├── js/app.js            # Frontend logic
    └── img/                 # Screenshots / assets
```

## Setup

1. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app:**
   ```bash
   python app.py
   ```

4. Open your browser at **http://127.0.0.1:5000**

The SQLite database (`history.db`) is created automatically on first run.

## API Reference

| Method | Endpoint              | Description                          |
|--------|------------------------|---------------------------------------|
| POST   | `/api/generate`        | Hash plain text (`{text, algorithms}`) |
| POST   | `/api/file-hash`       | Hash an uploaded file (multipart form) |
| POST   | `/api/identify`        | Identify a hash string (`{hash}`)     |
| POST   | `/api/decode`          | Check a hash against the built-in common-password wordlist (`{hash, algorithms}`) |
| POST   | `/api/crack/wordlist`  | Dictionary attack — built-in list or a caller-supplied one (`{hash, algorithms, wordlist?}`) |
| POST   | `/api/crack/brute-force` | Bounded brute-force search (`{hash, algorithm, charset?, max_length?}`, length capped at 5) |
| POST   | `/api/encoding/decode` | Decode a Base64/Hex/URL/ROT13 value (`{value, encoding}`) |
| POST   | `/api/encoding/encode` | Encode a value as Base64/Hex/URL/ROT13 (`{value, encoding}`) |
| POST   | `/api/compare`         | Compare two hashes (`{hash_a, hash_b}`) |
| GET    | `/api/history?q=`      | List/search recent history            |
| DELETE | `/api/history/<id>`    | Delete one history entry              |
| DELETE | `/api/history`         | Clear all history                     |

All API routes are rate-limited (60 requests/minute per IP by default) and validate their inputs before processing.

## Security Notes

- No `eval()` / dynamic code execution anywhere in the codebase
- All SQL uses parameterized queries — no string-built SQL
- File uploads are size-capped (50 MB) and streamed directly into the hash functions — never written to disk with a user-controlled name
- Security response headers set on every response (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- Text/hash inputs are length-capped and charset-validated

## Disclaimer

This tool is built **for educational and defensive security purposes** — understanding hashing, verifying file integrity, and recognizing hash formats. Hash identification is heuristic (based on length/format only) and is not a guarantee of the true algorithm used. This project is not intended to facilitate credential attacks.

## License

MIT
