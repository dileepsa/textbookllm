const API_BASE = "http://127.0.0.1:8000";

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file");
const uploadBtn = document.getElementById("upload-btn");
const ingestStatus = document.getElementById("ingest-status");

function setStatus(el, msg, cls) {
  el.className = `status ${cls || ""}`.trim();
  el.textContent = msg || "";
}

if (dropzone) {
  dropzone.addEventListener("click", () => fileInput?.click());
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () =>
    dropzone.classList.remove("dragover")
  );
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files?.length) {
      fileInput.files = e.dataTransfer.files;
    }
  });
}

uploadBtn?.addEventListener("click", async () => {
  if (!fileInput?.files?.[0]) {
    setStatus(ingestStatus, "Please choose a file.", "err");
    return;
  }
  try {
    setStatus(ingestStatus, "Uploading...", "loading");
    const fd = new FormData();
    fd.append("file", fileInput.files[0]);
    const res = await fetch(`${API_BASE}/ingest`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();
    setStatus(
      ingestStatus,
      `Ingested: ${json.document_id.slice(0, 8)}… (${json.num_chunks} chunks)`,
      "ok"
    );
  } catch (e) {
    setStatus(ingestStatus, `Upload failed: ${e}`, "err");
  }
});

const queryForm = document.getElementById("query-form");
const answerEl = document.getElementById("answer");
const copyBtn = document.getElementById("copy-answer");
const queryStatus = document.getElementById("query-status");

copyBtn?.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(answerEl?.innerText || "");
    copyBtn.textContent = "Copied";
    setTimeout(() => (copyBtn.textContent = "Copy"), 1200);
  } catch {}
});

queryForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = document.getElementById("q").value;
  const k = document.getElementById("k").value;
  if (!q.trim()) {
    setStatus(queryStatus, "Enter a question.", "err");
    return;
  }
  setStatus(queryStatus, "Searching…", "loading");
  answerEl.textContent = "";
  try {
    const fd = new FormData();
    fd.append("q", q);
    fd.append("k", k);
    const res = await fetch(`${API_BASE}/query`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();
    answerEl.textContent = json.answer || "";
    setStatus(queryStatus, "Done", "ok");
  } catch (e) {
    setStatus(queryStatus, `Query failed: ${e}`, "err");
  }
});
