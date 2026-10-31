const el = (id) => document.getElementById(id);
const select = el("bucketSelect");
const startBtn = el("startBtn");
const stopBtn = el("stopBtn");
const videoFeed = el("videoFeed");
const placeholder = el("videoPlaceholder");
const errorBox = el("errorBox");

let pollTimer = null;
let running = false;

const VERDICT_TEXT = {
  idle: "—", loading: "LOADING…", scanning: "SCANNING…", unclear: "UNCLEAR",
  pass: "PASS", reject: "REJECT", error: "ERROR",
};

async function api(url, options) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function showError(msg) {
  errorBox.textContent = msg || "";
  errorBox.hidden = !msg;
}

async function loadBuckets(keepSelection = true) {
  const previous = select.value;
  try {
    const buckets = await api("/api/buckets");
    select.innerHTML = "";
    if (buckets.length === 0) {
      select.add(new Option("No images found in Images folder", ""));
    } else {
      select.add(new Option("— Select a paint bucket —", ""));
      buckets.forEach((b) => {
        const opt = new Option(b.name, b.name);
        opt.dataset.filename = b.filename;
        select.add(opt);
      });
      if (keepSelection && buckets.some((b) => b.name === previous)) select.value = previous;
    }
  } catch (err) {
    showError(err.message);
  }
  updateSelection();
}

function updateSelection() {
  const opt = select.selectedOptions[0];
  const img = el("bucketPreview");
  if (opt && opt.value) {
    img.src = `/bucket_image/${encodeURIComponent(opt.dataset.filename)}`;
    img.hidden = false;
    el("previewHint").hidden = true;
    el("selectedProduct").textContent = opt.value;
  } else {
    img.hidden = true;
    el("previewHint").hidden = false;
    el("selectedProduct").textContent = "—";
  }
  startBtn.disabled = running || !select.value;
}

function setRunning(state) {
  running = state;
  stopBtn.disabled = !state;
  startBtn.disabled = state || !select.value;
  if (state) {
    videoFeed.src = `/video_feed?t=${Date.now()}`;
    videoFeed.hidden = false;
    placeholder.hidden = true;
    pollTimer = setInterval(pollStatus, 500);
  } else {
    clearInterval(pollTimer);
    videoFeed.removeAttribute("src");
    videoFeed.hidden = true;
    placeholder.hidden = false;
  }
}

function renderStatus(s) {
  const verdict = el("verdict");
  verdict.className = `verdict ${s.status}`;
  verdict.textContent = VERDICT_TEXT[s.status] || "—";
  el("detectedProduct").textContent = s.detected_product || "—";
  el("confidence").textContent = s.confidence ? `${Math.round(s.confidence * 100)}%` : "—";
  el("message").textContent = s.message || "";

  const texts = el("detectedTexts");
  texts.innerHTML = "";
  if (s.detected_texts && s.detected_texts.length) {
    s.detected_texts.forEach((t) => {
      const chip = document.createElement("span");
      chip.textContent = t;      // textContent: safe against HTML injection
      texts.appendChild(chip);
    });
  } else {
    texts.textContent = "—";
  }
}

async function pollStatus() {
  try {
    const s = await api("/api/status");
    renderStatus(s);
    if (running && !s.camera_running) setRunning(false);
  } catch (err) { /* transient error, try again next tick */ }
}

startBtn.addEventListener("click", async () => {
  showError("");
  startBtn.disabled = true;
  try {
    await api("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: select.value }),
    });
    setRunning(true);
  } catch (err) {
    showError(err.message);
    startBtn.disabled = !select.value;
  }
});

stopBtn.addEventListener("click", async () => {
  try { await api("/api/stop", { method: "POST" }); } catch (err) { showError(err.message); }
  setRunning(false);
  renderStatus({ status: "idle", detected_texts: [], message: "Webcam stopped." });
});

select.addEventListener("change", async () => {
  updateSelection();
  if (running && select.value) {
    try {
      await api("/api/target", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: select.value }),
      });
    } catch (err) { showError(err.message); }
  }
});

el("refreshBtn").addEventListener("click", () => loadBuckets(true));

loadBuckets();