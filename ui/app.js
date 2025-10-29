let API_BASE = localStorage.getItem("API_BASE") || "http://127.0.0.1:8000";
const apiInput = document.getElementById("api-base");
const saveApiBtn = document.getElementById("save-api");
if (apiInput) apiInput.value = API_BASE;
saveApiBtn?.addEventListener("click", () => {
  const v = apiInput.value.trim();
  if (!v) return;
  API_BASE = v.replace(/\/$/, "");
  localStorage.setItem("API_BASE", API_BASE);
  saveApiBtn.textContent = "Saved";
  setTimeout(() => (saveApiBtn.textContent = "Save"), 1200);
});

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
    // Refresh both file lists after upload
    await loadFileList();
    await loadUploadedFilesList();
  } catch (e) {
    setStatus(ingestStatus, `Upload failed: ${e}`, "err");
  }
});

// Uploaded files list (with delete)
const uploadedFilesList = document.getElementById("uploaded-files-list");

async function loadUploadedFilesList() {
  try {
    const res = await fetch(`${API_BASE}/documents/summary`);
    if (!res.ok) throw new Error("Failed to load files");
    const files = await res.json();

    if (files.length === 0) {
      uploadedFilesList.innerHTML =
        '<p class="muted">No files uploaded yet</p>';
      return;
    }

    uploadedFilesList.innerHTML = "";
    files.forEach((file) => {
      const item = document.createElement("div");
      item.className = "uploaded-file-item";

      const info = document.createElement("div");
      info.className = "file-info";

      const name = document.createElement("span");
      name.className = "file-name";
      name.textContent = file.filename || file.id.slice(0, 8) + "…";

      const type = document.createElement("span");
      type.className = "file-type muted";
      type.textContent = file.source_type;

      info.appendChild(name);
      info.appendChild(type);

      const deleteBtn = document.createElement("button");
      deleteBtn.className = "delete-btn";
      deleteBtn.textContent = "✕";
      deleteBtn.title = "Delete file";
      deleteBtn.onclick = async () => {
        if (confirm(`Delete "${file.filename}"?`)) {
          await deleteDocument(file.id);
        }
      };

      item.appendChild(info);
      item.appendChild(deleteBtn);
      uploadedFilesList.appendChild(item);
    });
  } catch (e) {
    uploadedFilesList.innerHTML = `<p class="muted err">Error loading files: ${e.message}</p>`;
  }
}

async function deleteDocument(documentId) {
  try {
    const res = await fetch(`${API_BASE}/documents/${documentId}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete document");
    const json = await res.json();

    if (json.success) {
      // Refresh both lists
      await loadUploadedFilesList();
      await loadFileList();
      setStatus(ingestStatus, "File deleted successfully", "ok");
    } else {
      setStatus(ingestStatus, json.message || "Delete failed", "err");
    }
  } catch (e) {
    setStatus(ingestStatus, `Delete failed: ${e}`, "err");
  }
}

// Load uploaded files on page load
loadUploadedFilesList();

// File filtering functionality
const filterToggle = document.getElementById("filter-files-toggle");
const fileSelector = document.getElementById("file-selector");
const fileList = document.getElementById("file-list");

filterToggle?.addEventListener("change", () => {
  if (filterToggle.checked) {
    fileSelector.style.display = "block";
    loadFileList();
  } else {
    fileSelector.style.display = "none";
  }
});

async function loadFileList() {
  try {
    const res = await fetch(`${API_BASE}/documents/summary`);
    if (!res.ok) throw new Error("Failed to load files");
    const files = await res.json();

    if (files.length === 0) {
      fileList.innerHTML = '<p class="muted">No files uploaded yet</p>';
      return;
    }

    fileList.innerHTML = "";
    files.forEach((file) => {
      const label = document.createElement("label");
      label.className = "file-checkbox";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = file.filename || file.id;
      checkbox.dataset.filename = file.filename;
      checkbox.className = "file-filter-cb";
      label.appendChild(checkbox);
      label.appendChild(
        document.createTextNode(
          ` ${file.filename || file.id.slice(0, 8) + "…"}`
        )
      );
      fileList.appendChild(label);
    });
  } catch (e) {
    fileList.innerHTML = `<p class="muted err">Error loading files: ${e.message}</p>`;
  }
}

// Load file list on page load
loadFileList();

const queryForm = document.getElementById("query-form");
const answerEl = document.getElementById("answer");
const copyBtn = document.getElementById("copy-answer");
const queryStatus = document.getElementById("query-status");
const retrievedDiv = document.getElementById("retrieved");

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
  retrievedDiv.innerHTML = "";
  try {
    const fd = new FormData();
    fd.append("q", q);
    fd.append("k", k);

    // Check if file filtering is enabled
    const useFiltering = filterToggle?.checked;
    let endpoint = `${API_BASE}/query`;

    if (useFiltering) {
      // Get selected files
      const selectedFiles = Array.from(
        document.querySelectorAll(".file-filter-cb:checked")
      )
        .map((cb) => cb.dataset.filename)
        .filter(Boolean);

      if (selectedFiles.length > 0) {
        endpoint = `${API_BASE}/query-filtered`;
        fd.append("filenames", selectedFiles.join(","));
      }
    }

    const res = await fetch(endpoint, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();
    answerEl.textContent = json.answer || "";
    setStatus(queryStatus, "Done", "ok");
    (json.retrieved || []).forEach(({ chunk, score }) => {
      const el = document.createElement("div");
      el.className = "retrieved-item";
      const header = document.createElement("div");
      header.className = "score";
      header.textContent = `score=${Number(score ?? 0).toFixed(3)} · doc=${(
        chunk?.document_id || ""
      ).slice(0, 8)}… · #${chunk?.order}`;
      const body = document.createElement("div");
      body.className = "muted";
      body.textContent =
        (chunk?.text || "").slice(0, 200) +
        (chunk?.text?.length > 200 ? "…" : "");
      el.appendChild(header);
      el.appendChild(body);
      retrievedDiv.appendChild(el);
    });
  } catch (e) {
    setStatus(queryStatus, `Query failed: ${e}`, "err");
  }
});
