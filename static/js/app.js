/* ==========================================================================
   CyberHash Toolkit — app.js
   Handles: matrix rain bg, particles, nav, theme toggle, hash generation,
   file hashing (drag & drop + progress), identification, comparison,
   history, copy/toast, ripple buttons.
   ========================================================================== */

(() => {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* Matrix falling code background                                     */
  /* ------------------------------------------------------------------ */
  function initMatrixRain() {
    const canvas = document.getElementById("matrix-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let width, height, columns, drops;
    const glyphs = "01アイウエオカキクケコサシスセソ$#@%&*<>[]{}";

    function resize() {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      columns = Math.floor(width / 16);
      drops = new Array(columns).fill(1);
    }
    window.addEventListener("resize", resize);
    resize();

    function draw() {
      ctx.fillStyle = "rgba(5, 8, 22, 0.08)";
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = "#00ff9d";
      ctx.font = "14px JetBrains Mono, monospace";
      drops.forEach((y, i) => {
        const char = glyphs[Math.floor(Math.random() * glyphs.length)];
        ctx.fillText(char, i * 16, y * 16);
        if (y * 16 > height && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
      });
    }

    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setInterval(draw, 50);
    }
  }

  /* ------------------------------------------------------------------ */
  /* Floating particles                                                  */
  /* ------------------------------------------------------------------ */
  function initParticles() {
    const container = document.body;
    for (let i = 0; i < 25; i++) {
      const p = document.createElement("div");
      p.className = "particle";
      const size = Math.random() * 4 + 2;
      p.style.width = `${size}px`;
      p.style.height = `${size}px`;
      p.style.left = `${Math.random() * 100}vw`;
      p.style.animationDuration = `${Math.random() * 12 + 10}s`;
      p.style.animationDelay = `${Math.random() * 10}s`;
      container.appendChild(p);
    }
  }

  /* ------------------------------------------------------------------ */
  /* Navigation: active link highlight + mobile menu                     */
  /* ------------------------------------------------------------------ */
  function initNav() {
    const links = document.querySelectorAll(".nav-link");
    const sections = document.querySelectorAll("main section[id]");

    const toggle = document.getElementById("mobile-menu-toggle");
    const menu = document.getElementById("mobile-menu");
    toggle?.addEventListener("click", () => menu.classList.toggle("hidden"));
    menu?.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => menu.classList.add("hidden")));

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            links.forEach((l) => l.classList.toggle("active", l.getAttribute("href") === `#${entry.target.id}`));
          }
        });
      },
      { rootMargin: "-40% 0px -55% 0px" }
    );
    sections.forEach((s) => observer.observe(s));
  }

  /* ------------------------------------------------------------------ */
  /* Dark / light mode toggle                                            */
  /* ------------------------------------------------------------------ */
  function initThemeToggle() {
    const btn = document.getElementById("theme-toggle");
    const root = document.documentElement;
    const saved = localStorageSafeGet("chx-theme");
    if (saved === "light") root.classList.add("light-mode");

    btn?.addEventListener("click", () => {
      root.classList.toggle("light-mode");
      const mode = root.classList.contains("light-mode") ? "light" : "dark";
      localStorageSafeSet("chx-theme", mode);
      btn.classList.add("pulse-once");
      setTimeout(() => btn.classList.remove("pulse-once"), 500);
    });
  }

  // localStorage can throw in some sandboxed contexts — guard it.
  function localStorageSafeGet(key) {
    try { return window.localStorage.getItem(key); } catch { return null; }
  }
  function localStorageSafeSet(key, val) {
    try { window.localStorage.setItem(key, val); } catch { /* ignore */ }
  }

  /* ------------------------------------------------------------------ */
  /* Toast notifications                                                  */
  /* ------------------------------------------------------------------ */
  function toast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const el = document.createElement("div");
    const colors = {
      success: "glass glow text-[var(--primary)] border border-[var(--primary)]",
      error: "glass border border-red-500 text-red-400",
      info: "glass glow-cyan border border-[var(--secondary)] text-[var(--secondary)]",
    };
    el.className = `toast ${colors[type] || colors.info}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), 2800);
  }

  /* ------------------------------------------------------------------ */
  /* Ripple button effect                                                */
  /* ------------------------------------------------------------------ */
  function initRipples() {
    document.querySelectorAll(".ripple").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const rect = btn.getBoundingClientRect();
        const circle = document.createElement("span");
        const size = Math.max(rect.width, rect.height);
        circle.className = "ripple-effect";
        circle.style.width = circle.style.height = `${size}px`;
        circle.style.left = `${e.clientX - rect.left - size / 2}px`;
        circle.style.top = `${e.clientY - rect.top - size / 2}px`;
        btn.appendChild(circle);
        setTimeout(() => circle.remove(), 600);
      });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Copy to clipboard helper                                            */
  /* ------------------------------------------------------------------ */
  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied Successfully");
    } catch {
      toast("Copy failed — please copy manually", "error");
    }
  }

  /* ------------------------------------------------------------------ */
  /* API helper                                                           */
  /* ------------------------------------------------------------------ */
  async function apiPost(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || "Request failed");
    return data;
  }

  /* ------------------------------------------------------------------ */
  /* HASH GENERATOR (text)                                               */
  /* ------------------------------------------------------------------ */
  function renderHashCards(results, container) {
    container.innerHTML = "";
    Object.entries(results).forEach(([algo, hash]) => {
      const card = document.createElement("div");
      card.className = "glass hover-glow p-4 rounded-xl slide-up";
      card.innerHTML = `
        <div class="flex items-center justify-between mb-2">
          <span class="font-display text-sm text-[var(--primary)] tracking-wide">${algo}</span>
          <span class="text-xs px-2 py-0.5 rounded-full border border-[var(--primary)] text-[var(--primary)]">
            <i class="fa-solid fa-circle-check mr-1"></i>Generated
          </span>
        </div>
        <p class="hash-value mb-3">${hash}</p>
        <div class="flex gap-2">
          <button type="button" class="copy-btn btn-outline ripple text-xs px-3 py-1.5" aria-label="Copy ${algo} hash">
            <i class="fa-regular fa-copy mr-1"></i>Copy
          </button>
          <button type="button" class="download-btn btn-outline ripple text-xs px-3 py-1.5" aria-label="Download ${algo} hash">
            <i class="fa-solid fa-download mr-1"></i>Download
          </button>
        </div>`;
      card.querySelector(".copy-btn").addEventListener("click", () => copyText(hash));
      card.querySelector(".download-btn").addEventListener("click", () => downloadText(`${algo}.txt`, hash));
      container.appendChild(card);
      initRipples();
    });
  }

  function downloadText(filename, content) {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function getSelectedAlgorithms(scope) {
    return Array.from(scope.querySelectorAll(".algo-checkbox:checked")).map((cb) => cb.value);
  }

  function initTextGenerator() {
    const input = document.getElementById("text-input");
    const resultsEl = document.getElementById("hash-results");
    const scope = document.getElementById("algo-list");
    const generateBtn = document.getElementById("generate-btn");
    const clearBtn = document.getElementById("clear-btn");
    const copyAllBtn = document.getElementById("copy-all-btn");
    const downloadAllBtn = document.getElementById("download-all-btn");
    const liveToggle = document.getElementById("live-toggle");
    if (!input) return;

    let lastResults = {};
    let debounceTimer;

    async function runGenerate() {
      const text = input.value;
      if (!text) {
        resultsEl.innerHTML = "";
        lastResults = {};
        return;
      }
      const algorithms = getSelectedAlgorithms(scope);
      if (algorithms.length === 0) {
        toast("Select at least one algorithm", "error");
        return;
      }
      try {
        resultsEl.setAttribute("aria-busy", "true");
        const data = await apiPost("/api/generate", { text, algorithms });
        lastResults = data.results;
        renderHashCards(data.results, resultsEl);
      } catch (err) {
        toast(err.message, "error");
      } finally {
        resultsEl.removeAttribute("aria-busy");
      }
    }

    generateBtn.addEventListener("click", runGenerate);

    input.addEventListener("input", () => {
      if (!liveToggle.checked) return;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(runGenerate, 400);
    });

    clearBtn.addEventListener("click", () => {
      input.value = "";
      resultsEl.innerHTML = "";
      lastResults = {};
      input.focus();
    });

    copyAllBtn.addEventListener("click", () => {
      const entries = Object.entries(lastResults);
      if (!entries.length) return toast("Nothing to copy yet", "error");
      const text = entries.map(([a, h]) => `${a}: ${h}`).join("\n");
      copyText(text);
    });

    downloadAllBtn.addEventListener("click", () => {
      const entries = Object.entries(lastResults);
      if (!entries.length) return toast("Nothing to download yet", "error");
      const text = entries.map(([a, h]) => `${a}: ${h}`).join("\n");
      downloadText("cyberhash-results.txt", text);
    });
  }

  /* ------------------------------------------------------------------ */
  /* FILE HASH GENERATOR (drag & drop + progress)                        */
  /* ------------------------------------------------------------------ */
  function initFileHasher() {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const progressWrap = document.getElementById("file-progress-wrap");
    const progressFill = document.getElementById("file-progress-fill");
    const fileMeta = document.getElementById("file-meta");
    const fileResults = document.getElementById("file-hash-results");
    if (!dropzone) return;

    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });

    ["dragenter", "dragover"].forEach((evt) =>
      dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); })
    );
    ["dragleave", "drop"].forEach((evt) =>
      dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); })
    );
    dropzone.addEventListener("drop", (e) => {
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    });
    fileInput.addEventListener("change", () => {
      if (fileInput.files[0]) handleFile(fileInput.files[0]);
    });

    function handleFile(file) {
      fileMeta.innerHTML = `<i class="fa-solid fa-file mr-1"></i>${file.name} · ${formatBytes(file.size)}`;
      fileResults.innerHTML = "";
      progressWrap.classList.remove("hidden");
      progressFill.style.width = "0%";

      const formData = new FormData();
      formData.append("file", file);
      ["MD5", "SHA256", "SHA512"].forEach((a) => formData.append("algorithms", a));

      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/file-hash");
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          const pct = Math.round((e.loaded / e.total) * 100);
          progressFill.style.width = `${pct}%`;
        }
      });
      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (!data.success) throw new Error(data.error);
          progressFill.style.width = "100%";
          renderHashCards(data.hashes, fileResults);
          toast("File hashed successfully");
        } catch (err) {
          toast(err.message || "File hashing failed", "error");
        }
      };
      xhr.onerror = () => toast("Upload failed", "error");
      xhr.send(formData);
    }

    function formatBytes(bytes) {
      if (bytes === 0) return "0 B";
      const units = ["B", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(1024));
      return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
    }
  }

  /* ------------------------------------------------------------------ */
  /* HASH IDENTIFIER                                                      */
  /* ------------------------------------------------------------------ */
  function initIdentifier() {
    const input = document.getElementById("identify-input");
    const btn = document.getElementById("identify-btn");
    const out = document.getElementById("identify-results");
    if (!input) return;

    btn.addEventListener("click", async () => {
      const hash = input.value.trim();
      if (!hash) return toast("Paste a hash first", "error");
      try {
        const data = await apiPost("/api/identify", { hash });
        renderIdentifyResult(data, out);
      } catch (err) {
        toast(err.message, "error");
      }
    });

    function renderIdentifyResult(data, container) {
      const alt = data.alternatives
        .map(
          (a) => `<div class="flex items-center justify-between text-sm py-1">
              <span>${a.algorithm}</span>
              <span class="text-[var(--secondary)]">${a.confidence}%</span>
            </div>`
        )
        .join("");

      container.innerHTML = `
        <div class="glass glow p-5 rounded-xl slide-up">
          <p class="text-xs uppercase tracking-widest opacity-60 mb-1">Possible Hash</p>
          <p class="font-display text-2xl text-[var(--primary)] text-glow mb-3">${data.primary_guess.algorithm}</p>
          <p class="text-xs uppercase tracking-widest opacity-60 mb-1">Confidence</p>
          <div class="confidence-track mb-1"><div class="confidence-fill" style="width:${data.primary_guess.confidence}%"></div></div>
          <p class="text-sm text-[var(--secondary)] mb-4">${data.primary_guess.confidence}%</p>
          ${
            data.alternatives.length
              ? `<p class="text-xs uppercase tracking-widest opacity-60 mb-1">Possible Alternatives</p>${alt}`
              : ""
          }
          <p class="text-xs opacity-50 mt-4">Length: ${data.input_length} chars · Hex: ${data.is_hex ? "yes" : "no"} · Base64: ${data.is_base64 ? "yes" : "no"}</p>
        </div>`;
    }
  }

  /* ------------------------------------------------------------------ */
  /* HASH COMPARISON                                                      */
  /* ------------------------------------------------------------------ */
  function initCompare() {
    const a = document.getElementById("compare-a");
    const b = document.getElementById("compare-b");
    const btn = document.getElementById("compare-btn");
    const out = document.getElementById("compare-result");
    if (!a) return;

    btn.addEventListener("click", async () => {
      if (!a.value.trim() || !b.value.trim()) return toast("Enter both hashes", "error");
      try {
        const data = await apiPost("/api/compare", { hash_a: a.value, hash_b: b.value });
        out.innerHTML = data.match
          ? `<div class="glass glow p-4 rounded-xl text-[var(--primary)] font-display text-lg pulse-once"><i class="fa-solid fa-circle-check mr-2"></i>Match</div>`
          : `<div class="glass p-4 rounded-xl border border-red-500 text-red-400 font-display text-lg pulse-once"><i class="fa-solid fa-circle-xmark mr-2"></i>Not Match</div>`;
      } catch (err) {
        toast(err.message, "error");
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* HASH DECODER (common-password wordlist match)                       */
  /* ------------------------------------------------------------------ */
  function initHashDecoder() {
    const input = document.getElementById("decode-input");
    const btn = document.getElementById("decode-btn");
    const out = document.getElementById("decode-result");
    if (!input) return;

    btn.addEventListener("click", async () => {
      const hash = input.value.trim();
      if (!hash) return toast("Paste a hash first", "error");
      btn.disabled = true;
      const original = btn.innerHTML;
      btn.innerHTML = `<span class="spinner inline-block align-middle"></span>`;
      try {
        const data = await apiPost("/api/decode", { hash, algorithms: ["MD5", "SHA1", "SHA256"] });
        out.innerHTML = data.found
          ? `<div class="glass glow p-4 rounded-xl pulse-once">
               <p class="text-xs uppercase tracking-widest opacity-60 mb-1">Match found</p>
               <p class="font-display text-xl text-[var(--primary)] text-glow">${escapeHtml(data.plaintext)}</p>
               <p class="text-xs opacity-60 mt-1">Algorithm: ${data.algorithm} · Checked ${data.attempts} combinations</p>
             </div>`
          : `<div class="glass p-4 rounded-xl border border-[var(--border)] pulse-once">
               <p class="text-sm opacity-80"><i class="fa-solid fa-circle-info mr-2 text-[var(--secondary)]"></i>No match in the built-in common-password list.</p>
               <p class="text-xs opacity-50 mt-1">Checked ${data.attempts} combinations. This does not mean the hash is strong — it only means it's not a top common password.</p>
             </div>`;
      } catch (err) {
        toast(err.message, "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = original;
      }
    });

    function escapeHtml(str) {
      const div = document.createElement("div");
      div.textContent = str;
      return div.innerHTML;
    }
  }

  /* ------------------------------------------------------------------ */
  /* HASH CRACKER (bounded wordlist + brute-force demo)                  */
  /* ------------------------------------------------------------------ */
  function initHashCracker() {
    initWordlistAttack();
    initBruteForceAttack();

    function escapeHtml(str) {
      const div = document.createElement("div");
      div.textContent = str;
      return div.innerHTML;
    }

    function withSpinner(btn, fn) {
      return async (...args) => {
        btn.disabled = true;
        const original = btn.innerHTML;
        btn.innerHTML = `<span class="spinner inline-block align-middle"></span>`;
        try {
          await fn(...args);
        } finally {
          btn.disabled = false;
          btn.innerHTML = original;
        }
      };
    }

    function initWordlistAttack() {
      const hashInput = document.getElementById("crack-wl-hash");
      const listInput = document.getElementById("crack-wl-list");
      const btn = document.getElementById("crack-wl-btn");
      const out = document.getElementById("crack-wl-result");
      if (!hashInput) return;

      btn.addEventListener(
        "click",
        withSpinner(btn, async () => {
          const hash = hashInput.value.trim();
          if (!hash) return toast("Paste a hash first", "error");

          const raw = listInput.value.trim();
          const wordlist = raw
            ? raw.split("\n").map((w) => w.trim()).filter(Boolean)
            : undefined; // omit -> backend falls back to the built-in list

          try {
            const data = await apiPost("/api/crack/wordlist", {
              hash,
              algorithms: ["MD5", "SHA1", "SHA256"],
              wordlist,
            });
            out.innerHTML = data.found
              ? `<div class="glass glow p-4 rounded-xl pulse-once">
                   <p class="text-xs uppercase tracking-widest opacity-60 mb-1">Match found (${data.source} list)</p>
                   <p class="font-display text-xl text-[var(--primary)] text-glow">${escapeHtml(data.plaintext)}</p>
                   <p class="text-xs opacity-60 mt-1">Algorithm: ${data.algorithm} · Checked ${data.attempts} combinations</p>
                 </div>`
              : `<div class="glass p-4 rounded-xl border border-[var(--border)] pulse-once">
                   <p class="text-sm opacity-80"><i class="fa-solid fa-circle-info mr-2 text-[var(--secondary)]"></i>No match in the ${data.source} list.</p>
                   <p class="text-xs opacity-50 mt-1">Checked ${data.attempts} combinations.</p>
                 </div>`;
          } catch (err) {
            toast(err.message, "error");
          }
        })
      );
    }

    function initBruteForceAttack() {
      const hashInput = document.getElementById("crack-bf-hash");
      const algoSelect = document.getElementById("crack-bf-algo");
      const lengthInput = document.getElementById("crack-bf-length");
      const charsetInput = document.getElementById("crack-bf-charset");
      const btn = document.getElementById("crack-bf-btn");
      const out = document.getElementById("crack-bf-result");
      if (!hashInput) return;

      btn.addEventListener(
        "click",
        withSpinner(btn, async () => {
          const hash = hashInput.value.trim();
          if (!hash) return toast("Paste a hash first", "error");

          try {
            const data = await apiPost("/api/crack/brute-force", {
              hash,
              algorithm: algoSelect.value,
              max_length: Number(lengthInput.value) || 3,
              charset: charsetInput.value.trim() || undefined,
            });
            const truncatedNote = data.truncated
              ? `<p class="text-xs text-yellow-400 mt-1"><i class="fa-solid fa-triangle-exclamation mr-1"></i>Search space cap reached before finishing — this is a demo, not an exhaustive search.</p>`
              : "";
            out.innerHTML = data.found
              ? `<div class="glass glow-purple p-4 rounded-xl pulse-once">
                   <p class="text-xs uppercase tracking-widest opacity-60 mb-1">Match found</p>
                   <p class="font-display text-xl text-[var(--accent)]">${escapeHtml(data.plaintext)}</p>
                   <p class="text-xs opacity-60 mt-1">Tried ${data.attempts.toLocaleString()} of ${data.search_space.toLocaleString()} candidates</p>
                   ${truncatedNote}
                 </div>`
              : `<div class="glass p-4 rounded-xl border border-[var(--border)] pulse-once">
                   <p class="text-sm opacity-80"><i class="fa-solid fa-circle-info mr-2 text-[var(--secondary)]"></i>No match within the search space.</p>
                   <p class="text-xs opacity-50 mt-1">Tried ${data.attempts.toLocaleString()} of ${data.search_space.toLocaleString()} candidates.</p>
                   ${truncatedNote}
                 </div>`;
          } catch (err) {
            toast(err.message, "error");
          }
        })
      );
    }
  }

  /* ------------------------------------------------------------------ */
  /* ENCODING DECODER / ENCODER (Base64, Hex, URL, ROT13)                */
  /* ------------------------------------------------------------------ */
  function initEncodingTools() {
    const select = document.getElementById("encoding-select");
    const input = document.getElementById("encoding-input");
    const output = document.getElementById("encoding-output");
    const decodeBtn = document.getElementById("encoding-decode-btn");
    const encodeBtn = document.getElementById("encoding-encode-btn");
    const copyBtn = document.getElementById("encoding-copy-btn");
    if (!select) return;

    async function run(mode) {
      const value = input.value;
      if (!value) return toast("Enter a value first", "error");
      try {
        const data = await apiPost(`/api/encoding/${mode}`, { value, encoding: select.value });
        output.value = data.output;
      } catch (err) {
        output.value = "";
        toast(err.message, "error");
      }
    }

    decodeBtn.addEventListener("click", () => run("decode"));
    encodeBtn.addEventListener("click", () => run("encode"));
    copyBtn.addEventListener("click", () => {
      if (!output.value) return toast("Nothing to copy yet", "error");
      copyText(output.value);
    });
  }

  /* ------------------------------------------------------------------ */
  /* HISTORY                                                              */
  /* ------------------------------------------------------------------ */
  function initHistory() {
    const list = document.getElementById("history-list");
    const search = document.getElementById("history-search");
    const clearBtn = document.getElementById("history-clear-btn");
    const exportBtn = document.getElementById("history-export-btn");
    if (!list) return;

    let cache = [];

    async function load(q = "") {
      try {
        const res = await fetch(`/api/history${q ? `?q=${encodeURIComponent(q)}` : ""}`);
        const data = await res.json();
        if (!data.success) throw new Error(data.error);
        cache = data.entries;
        render(cache);
      } catch (err) {
        toast(err.message, "error");
      }
    }

    function render(entries) {
      if (!entries.length) {
        list.innerHTML = `<p class="opacity-50 text-sm py-4 text-center">No history yet — run a tool above to see it here.</p>`;
        return;
      }
      list.innerHTML = entries
        .map(
          (e) => `
        <div class="glass p-3 rounded-lg flex items-center justify-between gap-3" data-id="${e.id}">
          <div class="min-w-0">
            <p class="text-xs uppercase tracking-widest text-[var(--secondary)]">${e.operation}</p>
            <p class="text-sm truncate">${escapeHtml(e.summary)}</p>
          </div>
          <button type="button" class="delete-entry-btn text-red-400 hover:text-red-300 px-2" aria-label="Delete entry">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>`
        )
        .join("");

      list.querySelectorAll(".delete-entry-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          const row = e.target.closest("[data-id]");
          const id = row.dataset.id;
          try {
            const res = await fetch(`/api/history/${id}`, { method: "DELETE" });
            const data = await res.json();
            if (!data.success) throw new Error(data.error);
            load(search.value.trim());
            toast("Entry deleted");
          } catch (err) {
            toast(err.message, "error");
          }
        });
      });
    }

    function escapeHtml(str) {
      const div = document.createElement("div");
      div.textContent = str;
      return div.innerHTML;
    }

    let debounce;
    search.addEventListener("input", () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => load(search.value.trim()), 300);
    });

    clearBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/history", { method: "DELETE" });
        const data = await res.json();
        if (!data.success) throw new Error(data.error);
        load();
        toast("History cleared");
      } catch (err) {
        toast(err.message, "error");
      }
    });

    exportBtn.addEventListener("click", () => {
      if (!cache.length) return toast("Nothing to export", "error");
      const text = cache.map((e) => `[${e.operation}] ${e.summary}`).join("\n");
      downloadText("cyberhash-history.txt", text);
    });

    load();
    // refresh history after any tool run
    document.addEventListener("chx:history-refresh", () => load(search.value.trim()));
  }

  /* ------------------------------------------------------------------ */
  /* Init on DOM ready                                                    */
  /* ------------------------------------------------------------------ */
  document.addEventListener("DOMContentLoaded", () => {
    initMatrixRain();
    initParticles();
    initNav();
    initThemeToggle();
    initRipples();
    initTextGenerator();
    initFileHasher();
    initIdentifier();
    initCompare();
    initHashDecoder();
    initHashCracker();
    initEncodingTools();
    initHistory();

    if (window.AOS) AOS.init({ duration: 700, once: true });

    // hide the initial page loader once everything is wired up
    const loader = document.getElementById("page-loader");
    if (loader) {
      setTimeout(() => {
        loader.style.opacity = "0";
        setTimeout(() => loader.remove(), 400);
      }, 400);
    }
  });
})();
