const form = document.getElementById("pullForm");
const urlInput = document.getElementById("url");
const modeButtons = document.querySelectorAll(".mode-btn");
const goBtn = document.getElementById("goBtn");
const dot = document.getElementById("statusDot");
const log = document.getElementById("log");
const result = document.getElementById("result");
const thumb = document.getElementById("thumb");
const resultTitle = document.getElementById("resultTitle");
const resultSub = document.getElementById("resultSub");
const downloadLink = document.getElementById("downloadLink");

let mode = "video";

modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    modeButtons.forEach((b) => {
      b.classList.remove("active");
      b.setAttribute("aria-checked", "false");
    });
    btn.classList.add("active");
    btn.setAttribute("aria-checked", "true");
    mode = btn.dataset.mode;
  });
});

function logLine(text, cls) {
  const p = document.createElement("p");
  p.className = "log-line" + (cls ? " " + cls : "");
  p.textContent = text;
  log.appendChild(p);
  log.scrollTop = log.scrollHeight;
}

function resetLog() {
  log.innerHTML = "";
}

function setStatus(state) {
  dot.classList.remove("busy", "done", "error");
  if (state) dot.classList.add(state);
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

async function handleSubmit(e) {
  e.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;

  result.hidden = true;
  resetLog();
  setStatus("busy");
  goBtn.disabled = true;

  logLine(`$ reading ${url}`);

  let meta = null;
  try {
    const infoRes = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const infoData = await infoRes.json();
    if (!infoRes.ok) throw new Error(infoData.error || "Couldn't read that URL.");
    meta = infoData;
    logLine(`> found: ${meta.title || "untitled"}`, "ok");
  } catch (err) {
    logLine(`! ${err.message}`, "err");
    setStatus("error");
    goBtn.disabled = false;
    return;
  }

  logLine(`$ pulling ${mode === "audio" ? "audio (mp3)" : "video (mp4)"} — this can take a moment…`);

  try {
    const dlRes = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, mode }),
    });

    if (!dlRes.ok) {
      const errData = await dlRes.json().catch(() => ({}));
      throw new Error(errData.error || "Download failed.");
    }

    const blob = await dlRes.blob();
    const disposition = dlRes.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : (mode === "audio" ? "audio.mp3" : "video.mp4");

    const blobUrl = URL.createObjectURL(blob);
    downloadLink.href = blobUrl;
    downloadLink.download = filename;

    thumb.src = meta.thumbnail || "";
    thumb.style.visibility = meta.thumbnail ? "visible" : "hidden";
    resultTitle.textContent = meta.title || filename;
    resultSub.textContent = [meta.uploader, formatDuration(meta.duration)].filter(Boolean).join(" · ");

    result.hidden = false;
    logLine(`> done — ${filename}`, "ok");
    setStatus("done");
  } catch (err) {
    logLine(`! ${err.message}`, "err");
    setStatus("error");
  } finally {
    goBtn.disabled = false;
  }
}

form.addEventListener("submit", handleSubmit);
