const API_BASE = 'http://127.0.0.1:8000';

const ingestForm = document.getElementById('ingest-form');
ingestForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('file');
  if (!fileInput.files[0]) return;
  const fd = new FormData();
  fd.append('file', fileInput.files[0]);
  const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: fd });
  const json = await res.json();
  document.getElementById(
    'ingest-result'
  ).innerText = `Document ${json.document_id} ingested with ${json.num_chunks} chunks.`;
});

const queryForm = document.getElementById('query-form');
queryForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = document.getElementById('q').value;
  const k = document.getElementById('k').value;
  const fd = new FormData();
  fd.append('q', q);
  fd.append('k', k);
  const res = await fetch(`${API_BASE}/query`, { method: 'POST', body: fd });
  const json = await res.json();
  document.getElementById('answer').innerText = json.answer;
  const retrievedDiv = document.getElementById('retrieved');
  retrievedDiv.innerHTML = '';
  (json.retrieved || []).forEach(({ chunk, score }) => {
    const el = document.createElement('div');
    el.className = 'muted';
    el.textContent = `score=${score.toFixed(3)}: ${chunk.text.slice(
      0,
      120
    )}...`;
    retrievedDiv.appendChild(el);
  });
});
