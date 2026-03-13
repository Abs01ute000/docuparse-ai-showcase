const uploadForm = document.getElementById('uploadForm');
const pdfFile = document.getElementById('pdfFile');
const samplesList = document.getElementById('samplesList');
const jsonOutput = document.getElementById('jsonOutput');
const reportView = document.getElementById('reportView');
const fieldStatus = document.getElementById('fieldStatus');
const previewOutput = document.getElementById('previewOutput');
const statusBox = document.getElementById('statusBox');
const metaChips = document.getElementById('metaChips');
const loadSamplesBtn = document.getElementById('loadSamplesBtn');
const refreshSamplesBtn = document.getElementById('refreshSamplesBtn');

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function setStatus(message, type = 'idle') {
  statusBox.className = `status-box ${type}`;
  statusBox.textContent = message;
}

function setChips(data) {
  metaChips.innerHTML = '';
  const entries = [
    ['Type', data.document_type],
    ['Source', data.source_type],
    ['OCR', data.ocr_used ? 'yes' : 'no'],
    ['Lang', data.detected_language],
    ['Confidence', data.confidence_score],
    ['Method', data.extraction_method],
  ];
  for (const [label, value] of entries) {
    const chip = document.createElement('div');
    chip.className = 'chip';
    chip.textContent = `${label}: ${value ?? 'n/a'}`;
    metaChips.appendChild(chip);
  }
}

function renderFieldStatus(data) {
  const status = data.extracted_fields_status || {};
  const rows = [
    ['Title', status.title],
    ['Document number', status.document_number],
    ['Date', status.date],
    ['Parties', status.parties],
    ['Valid until', status.valid_until],
    ['Key points', status.key_points],
  ];
  fieldStatus.innerHTML = rows.map(([label, value]) => `
    <div class="status-row">
      <span>${label}</span>
      <strong class="${value ? 'ok' : 'bad'}">${value ? 'found' : 'missing'}</strong>
    </div>
  `).join('');
}

function renderReport(data) {
  const parties = (data.parties || []).map(p => `<li>${escapeHtml(p.raw_value)}</li>`).join('') || '<li>None</li>';
  const keyPoints = (data.key_points || []).map(p => `<li>${escapeHtml(p)}</li>`).join('') || '<li>None</li>';
  const warnings = (data.warnings || []).length
    ? `<ul>${data.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul>`
    : '<p class="muted">No warnings.</p>';

  reportView.innerHTML = `
    <section class="report-block">
      <h3>${escapeHtml(data.title || 'Untitled document')}</h3>
      <p class="report-summary">${escapeHtml(data.summary || 'No summary available.')}</p>
    </section>

    <section class="report-grid">
      <div class="report-card">
        <span>Filename</span>
        <strong>${escapeHtml(data.filename || '-')}</strong>
      </div>
      <div class="report-card">
        <span>Document type</span>
        <strong>${escapeHtml(data.document_type || '-')}</strong>
      </div>
      <div class="report-card">
        <span>Document number</span>
        <strong>${escapeHtml(data.document_number || '-')}</strong>
      </div>
      <div class="report-card">
        <span>Date</span>
        <strong>${escapeHtml(data.date || '-')}</strong>
      </div>
      <div class="report-card">
        <span>Valid until</span>
        <strong>${escapeHtml(data.valid_until || '-')}</strong>
      </div>
      <div class="report-card">
        <span>Pages</span>
        <strong>${escapeHtml(data.pages || '-')}</strong>
      </div>
    </section>

    <section class="report-block">
      <h3>Parties</h3>
      <ul>${parties}</ul>
    </section>

    <section class="report-block">
      <h3>Key points</h3>
      <ul>${keyPoints}</ul>
    </section>

    <section class="report-block">
      <h3>Warnings</h3>
      ${warnings}
    </section>
  `;
}

async function loadSamples() {
  samplesList.innerHTML = '<div class="muted">Loading sample files...</div>';
  try {
    const response = await fetch('/samples');
    const data = await response.json();
    if (!data.items?.length) {
      samplesList.innerHTML = '<div class="empty">No sample files found.</div>';
      return;
    }
    samplesList.innerHTML = '';
    for (const item of data.items) {
      const div = document.createElement('div');
      div.className = 'sample-item';
      div.innerHTML = `
        <h4>${escapeHtml(item.name)}</h4>
        <p>${escapeHtml(item.description || 'Sample PDF file for parser testing.')}</p>
        <a href="${item.url}" target="_blank" rel="noreferrer">Open / download sample</a>
      `;
      samplesList.appendChild(div);
    }
  } catch (error) {
    samplesList.innerHTML = `<div class="empty">Failed to load samples: ${escapeHtml(error.message)}</div>`;
  }
}

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = pdfFile.files[0];
  if (!file) {
    setStatus('Choose a PDF first.', 'warn');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  setStatus(`Parsing ${file.name}...`, 'idle');
  reportView.textContent = 'Processing...';
  fieldStatus.textContent = 'Processing...';
  previewOutput.textContent = 'Processing...';
  jsonOutput.textContent = 'Parsing in progress...';
  metaChips.innerHTML = '';

  try {
    const response = await fetch('/parse-pdf', { method: 'POST', body: formData });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Request failed');
    }

    renderReport(data);
    renderFieldStatus(data);
    previewOutput.textContent = data.raw_text_preview || 'No preview available.';
    jsonOutput.textContent = JSON.stringify(data, null, 2);
    setChips(data);
    setStatus(data.warnings?.length ? 'Parsed with warnings.' : 'Document parsed successfully.', data.warnings?.length ? 'warn' : 'good');
  } catch (error) {
    reportView.textContent = 'No result due to an error.';
    fieldStatus.textContent = 'No field data due to an error.';
    previewOutput.textContent = error.stack || String(error);
    jsonOutput.textContent = error.stack || String(error);
    setStatus(`Parse failed: ${error.message}`, 'warn');
  }
});

loadSamplesBtn.addEventListener('click', loadSamples);
refreshSamplesBtn.addEventListener('click', loadSamples);
loadSamples();
