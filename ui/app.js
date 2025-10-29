let API_BASE = localStorage.getItem('API_BASE') || 'http://127.0.0.1:8000';
const apiInput = document.getElementById('api-base');
const saveApiBtn = document.getElementById('save-api');
if (apiInput) apiInput.value = API_BASE;
saveApiBtn?.addEventListener('click', () => {
  const v = apiInput.value.trim();
  if (!v) return;
  API_BASE = v.replace(/\/$/, '');
  localStorage.setItem('API_BASE', API_BASE);
  saveApiBtn.textContent = 'Saved';
  setTimeout(() => (saveApiBtn.textContent = 'Save'), 1200);
});

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file');
const uploadBtn = document.getElementById('upload-btn');
const ingestStatus = document.getElementById('ingest-status');

function setStatus(el, msg, cls) {
  el.className = `status ${cls || ''}`.trim();
  el.textContent = msg || '';
}

if (dropzone) {
  dropzone.addEventListener('click', () => fileInput?.click());
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () =>
    dropzone.classList.remove('dragover')
  );
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files?.length) {
      fileInput.files = e.dataTransfer.files;
    }
  });
}

uploadBtn?.addEventListener('click', async () => {
  if (!fileInput?.files?.[0]) {
    setStatus(ingestStatus, 'Please choose a file.', 'err');
    return;
  }
  try {
    setStatus(ingestStatus, 'Uploading...', 'loading');
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();
    setStatus(
      ingestStatus,
      `Ingested: ${json.document_id.slice(0, 8)}… (${json.num_chunks} chunks)`,
      'ok'
    );
  } catch (e) {
    setStatus(ingestStatus, `Upload failed: ${e}`, 'err');
  }
});

const queryForm = document.getElementById('query-form');
const answerEl = document.getElementById('answer');
const copyBtn = document.getElementById('copy-answer');
const queryStatus = document.getElementById('query-status');
const retrievedDiv = document.getElementById('retrieved');

copyBtn?.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(answerEl?.innerText || '');
    copyBtn.textContent = 'Copied';
    setTimeout(() => (copyBtn.textContent = 'Copy'), 1200);
  } catch {}
});

queryForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = document.getElementById('q').value;
  const k = document.getElementById('k').value;
  if (!q.trim()) {
    setStatus(queryStatus, 'Enter a question.', 'err');
    return;
  }
  setStatus(queryStatus, 'Searching…', 'loading');
  answerEl.textContent = '';
  retrievedDiv.innerHTML = '';
  try {
    const fd = new FormData();
    fd.append('q', q);
    fd.append('k', k);
    const res = await fetch(`${API_BASE}/query`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();
    answerEl.textContent = json.answer || '';
    setStatus(queryStatus, 'Done', 'ok');
    (json.retrieved || []).forEach(({ chunk, score }) => {
      const el = document.createElement('div');
      el.className = 'retrieved-item';
      const header = document.createElement('div');
      header.className = 'score';
      header.textContent = `score=${Number(score ?? 0).toFixed(3)} · doc=${(
        chunk?.document_id || ''
      ).slice(0, 8)}… · #${chunk?.order}`;
      const body = document.createElement('div');
      body.className = 'muted';
      body.textContent =
        (chunk?.text || '').slice(0, 200) +
        (chunk?.text?.length > 200 ? '…' : '');
      el.appendChild(header);
      el.appendChild(body);
      retrievedDiv.appendChild(el);
    });
  } catch (e) {
    setStatus(queryStatus, `Query failed: ${e}`, 'err');
  }
});
