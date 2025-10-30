let API_BASE = localStorage.getItem('API_BASE') || 'http://127.0.0.1:8000';

// DOM elements
const apiInput = document.getElementById('api-base');
const saveApiBtn = document.getElementById('save-api');
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file');
const uploadBtn = document.getElementById('upload-btn');
const ingestStatus = document.getElementById('ingest-status');
const queryForm = document.getElementById('query-form');
const answerEl = document.getElementById('answer');
const copyBtn = document.getElementById('copy-answer');
const queryStatus = document.getElementById('query-status');
const retrievedDiv = document.getElementById('retrieved');
const selectedFileDiv = document.getElementById('selected-file');
const selectedFileName = document.getElementById('selected-file-name');
const selectedFileSize = document.getElementById('selected-file-size');
const removeFileBtn = document.getElementById('remove-file');

// API configuration
if (apiInput) apiInput.value = API_BASE;
saveApiBtn?.addEventListener('click', () => {
  const v = apiInput.value.trim();
  if (!v) return;
  API_BASE = v.replace(/\/$/, '');
  localStorage.setItem('API_BASE', API_BASE);
  saveApiBtn.textContent = 'Saved';
  setTimeout(() => (saveApiBtn.textContent = 'Save'), 1200);
});

// Utility functions
function setStatus(el, msg, cls) {
  el.className = `status ${cls || ''}`.trim();
  el.textContent = msg;
}

function getFileType(fileName) {
  const ext = fileName.split('.').pop().toLowerCase();
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'svg'];
  const audioExts = ['mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a', 'wma'];
  const videoExts = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', 'm4v'];

  if (imageExts.includes(ext)) return 'image';
  if (audioExts.includes(ext)) return 'audio';
  if (videoExts.includes(ext)) return 'video';
  return 'text';
}

function getTypeMessage(fileType) {
  switch (fileType) {
    case 'image':
      return 'Image';
    case 'audio':
      return 'Audio file';
    case 'video':
      return 'Video file';
    default:
      return 'File';
  }
}

// File selection display functions
function showSelectedFile(file) {
  if (!selectedFileDiv || !selectedFileName || !selectedFileSize) return;

  const fileSize = (file.size / 1024 / 1024).toFixed(2); // MB
  const fileName = file.name;

  // Get appropriate icon based on file type
  const fileType = getFileType(fileName);
  const fileIcon = selectedFileDiv.querySelector('.file-icon');
  if (fileIcon) {
    switch (fileType) {
      case 'image':
        fileIcon.textContent = '🖼️';
        break;
      case 'audio':
        fileIcon.textContent = '🎵';
        break;
      case 'video':
        fileIcon.textContent = '🎬';
        break;
      default:
        fileIcon.textContent = '📄';
    }
  }

  selectedFileName.textContent = fileName;
  selectedFileSize.textContent = `${fileSize} MB`;
  selectedFileDiv.style.display = 'block';
}

function hideSelectedFile() {
  if (!selectedFileDiv) return;
  selectedFileDiv.style.display = 'none';
  if (selectedFileName) selectedFileName.textContent = '';
  if (selectedFileSize) selectedFileSize.textContent = '';
}

function clearFileInput() {
  if (fileInput) {
    fileInput.value = '';
    hideSelectedFile();
  }
}

// Load uploaded files list
async function loadUploadedFilesList() {
  const uploadedFilesList = document.getElementById('uploaded-files-list');
  if (!uploadedFilesList) return;

  try {
    const res = await fetch(`${API_BASE}/documents/summary`);
    if (!res.ok) throw new Error('Failed to load files');
    const files = await res.json();

    if (files.length === 0) {
      uploadedFilesList.innerHTML =
        '<p class="muted">No files uploaded yet</p>';
      return;
    }

    uploadedFilesList.innerHTML = '';
    for (const file of files) {
      const item = document.createElement('div');
      item.className = 'uploaded-file-item';

      const info = document.createElement('div');
      info.className = 'file-info';

      const name = document.createElement('span');
      name.className = 'file-name';
      name.textContent = file.filename || file.id.slice(0, 8) + '…';

      const type = document.createElement('span');
      type.className = 'file-type muted';
      type.textContent = file.source_type;

      info.appendChild(name);
      info.appendChild(type);

      item.appendChild(info);
      uploadedFilesList.appendChild(item);
    }
  } catch (e) {
    uploadedFilesList.innerHTML = `<p class="muted err">Error loading files: ${e.message}</p>`;
  }
}

// Load file filter list
async function loadFileFilterList() {
  const fileList = document.getElementById('file-list');
  if (!fileList) return;

  try {
    const res = await fetch(`${API_BASE}/documents/summary`);
    if (!res.ok) throw new Error('Failed to load files');
    const files = await res.json();

    if (files.length === 0) {
      fileList.innerHTML = '<p class="muted">No files uploaded yet</p>';
      return;
    }

    fileList.innerHTML = '';
    for (const file of files) {
      const label = document.createElement('label');
      label.className = 'file-checkbox';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.value = file.filename || file.id;
      checkbox.dataset.filename = file.filename;
      checkbox.className = 'file-filter-cb';

      label.appendChild(checkbox);
      label.appendChild(
        document.createTextNode(
          ` ${file.filename || file.id.slice(0, 8) + '…'}`
        )
      );
      fileList.appendChild(label);
    }
  } catch (e) {
    fileList.innerHTML = `<p class="muted err">Error loading files: ${e.message}</p>`;
  }
}

// File filtering functionality
const filterToggle = document.getElementById('filter-files-toggle');
const fileSelector = document.getElementById('file-selector');

filterToggle?.addEventListener('change', () => {
  if (filterToggle.checked) {
    fileSelector.style.display = 'block';
    loadFileFilterList();
  } else {
    fileSelector.style.display = 'none';
  }
});

// Drag and drop functionality
if (dropzone) {
  dropzone.addEventListener('click', (e) => {
    // Only trigger file input if not clicking on the label
    if (e.target.tagName !== 'LABEL') {
      fileInput?.click();
    }
  });
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
      // Show the selected file
      if (fileInput.files[0]) {
        showSelectedFile(fileInput.files[0]);
      }
    }
  });
}

// File input change handler
fileInput?.addEventListener('change', (e) => {
  if (e.target.files?.length) {
    showSelectedFile(e.target.files[0]);
  } else {
    hideSelectedFile();
  }
});

// Remove file button handler
removeFileBtn?.addEventListener('click', () => {
  clearFileInput();
});

// File upload functionality
uploadBtn?.addEventListener('click', async () => {
  if (!fileInput?.files?.[0]) {
    setStatus(ingestStatus, 'Please choose a file.', 'err');
    return;
  }

  const file = fileInput.files[0];
  const fileName = file.name;
  const fileSize = (file.size / 1024 / 1024).toFixed(2); // MB

  try {
    setStatus(
      ingestStatus,
      `Uploading ${fileName} (${fileSize}MB)...`,
      'loading'
    );
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();

    // Show file type specific success message
    const fileType = getFileType(fileName);
    const typeMsg = getTypeMessage(fileType);

    setStatus(
      ingestStatus,
      `${typeMsg} processed: ${json.document_id.slice(0, 8)}… (${
        json.num_chunks
      } chunks)`,
      'ok'
    );

    // Refresh the uploaded files list and file filter list
    await loadUploadedFilesList();
    if (filterToggle?.checked) {
      await loadFileFilterList();
    }

    // Clear the selected file display
    clearFileInput();
  } catch (e) {
    setStatus(ingestStatus, `Upload failed: ${e.message}`, 'err');
  }
});

// Query functionality
queryForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(queryForm);
  const q = formData.get('q');
  const k = formData.get('k');

  if (!q) {
    setStatus(queryStatus, 'Please enter a question.', 'err');
    return;
  }

  try {
    setStatus(queryStatus, 'Searching...', 'loading');
    const fd = new FormData();
    fd.append('q', q);
    fd.append('k', k);

    // Check if file filtering is enabled
    const useFiltering = filterToggle?.checked;
    let endpoint = `${API_BASE}/query`;

    if (useFiltering) {
      // Get selected files
      const selectedFiles = Array.from(
        document.querySelectorAll('.file-filter-cb:checked')
      )
        .map((cb) => cb.dataset.filename)
        .filter(Boolean);

      if (selectedFiles.length > 0) {
        endpoint = `${API_BASE}/query-filtered`;
        fd.append('filenames', selectedFiles.join(','));
      }
    }

    const res = await fetch(endpoint, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();

    answerEl.textContent = json.answer || 'No answer received.';
    setStatus(queryStatus, 'Complete', 'ok');

    // Show retrieved chunks
    if (retrievedDiv && json.retrieved?.length) {
      retrievedDiv.innerHTML = '<h3>Retrieved Chunks</h3>';
      for (const item of json.retrieved) {
        const div = document.createElement('div');
        div.className = 'retrieved-chunk';
        div.innerHTML = `
          <div class="chunk-meta">Score: ${item.score.toFixed(3)}</div>
          <div class="chunk-text">${item.chunk.text}</div>
        `;
        retrievedDiv.appendChild(div);
      }
    }
  } catch (e) {
    setStatus(queryStatus, `Query failed: ${e.message}`, 'err');
    answerEl.textContent = '';
  }
});

// Copy answer functionality
copyBtn?.addEventListener('click', async () => {
  if (!answerEl?.textContent) {
    setStatus(queryStatus, 'No answer to copy.', 'err');
    return;
  }

  try {
    await navigator.clipboard.writeText(answerEl.textContent);
    copyBtn.textContent = 'Copied!';
    setTimeout(() => (copyBtn.textContent = 'Copy'), 1200);
  } catch (clipboardError) {
    console.warn('Clipboard API failed:', clipboardError);
    setStatus(queryStatus, 'Failed to copy to clipboard.', 'err');
  }
});

// Load uploaded files list on page load
document.addEventListener('DOMContentLoaded', () => {
  loadUploadedFilesList();
});
