/* MarketMind AI · Client JS */

function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-bs-theme') === 'dark';
  html.setAttribute('data-bs-theme', isDark ? 'light' : 'dark');
  document.getElementById('themeIcon').className = isDark ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
  localStorage.setItem('mm-theme', isDark ? 'light' : 'dark');
}
(function () {
  const saved = localStorage.getItem('mm-theme') || 'dark';
  document.documentElement.setAttribute('data-bs-theme', saved);
  const icon = document.getElementById('themeIcon');
  if (icon) icon.className = saved === 'light' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
})();

function showToast(msg, type = 'info') {
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warn: '⚠️' };
  const el = document.createElement('div');
  el.className = 'mm-toast';
  el.innerHTML = `<span style="font-size:18px">${icons[type]||'ℹ️'}</span><span>${msg}</span>`;
  const c = document.getElementById('toastContainer');
  if (c) {
    c.appendChild(el);
    setTimeout(() => { el.style.opacity='0'; el.style.transition='opacity .4s'; setTimeout(()=>el.remove(),400); }, 3500);
  }
}

function setBadge(state, text) {
  const b = document.getElementById('pipeline-badge');
  if (!b) return;
  b.className = `mm-badge badge-${state}`;
  const spinIcon = state === 'running' ? '<i class="bi bi-arrow-repeat me-1" style="display:inline-block;animation:spin .8s linear infinite"></i>' : '<i class="bi bi-circle-fill me-1" style="font-size:7px"></i>';
  b.innerHTML = spinIcon + text;
}
(function(){
  const s = document.createElement('style');
  s.textContent = '@keyframes spin{to{transform:rotate(360deg)}}';
  document.head.appendChild(s);
})();

let _catalog = {};
let _selectedStocks = new Set();
let _activeSector = 'all';
let _emailTags = [];
let _runModal = null;

function openRunModal() {
  if (!_runModal) _runModal = new bootstrap.Modal(document.getElementById('runModal'));
  loadStockCatalog();
  updateRunSummary();
  _runModal.show();
}

async function loadStockCatalog() {
  if (Object.keys(_catalog).length) { renderStockGrid(); return; }
  try {
    // Try the live NSE equity list first (may include 1000+ stocks)
    const res = await fetch('/api/stocks/live');
    const data = await res.json();
    const rawCatalog = data.catalog || data;
    // Normalize: each sector value may be [{symbol,name},...] or [sym,...]
    _catalog = {};
    for (const [sector, items] of Object.entries(rawCatalog)) {
      if (!Array.isArray(items)) continue;
      _catalog[sector] = items.map(i => (typeof i === 'object' ? i.symbol : i));
    }
    if (data.source === 'live') {
      // Show a small badge in the modal header
      const hdr = document.querySelector('#runModal .mm-section-header .text-muted.small');
      if (hdr) hdr.innerHTML = 'Pick the NSE stocks to analyse &nbsp;<span class="mm-live-badge"><span class="mm-live-dot"></span>Live NSE list</span>';
    }
  } catch {
    // Fallback to hardcoded catalog
    try {
      const res = await fetch('/api/stocks');
      _catalog = await res.json();
    } catch(e) {
      document.getElementById('stockGrid').innerHTML = '<div class="text-muted small text-center py-3">Failed to load stocks.</div>';
      return;
    }
  }
  buildSectorTabs();
  renderStockGrid();
}

function buildSectorTabs() {
  const tabs = document.getElementById('sectorTabs');
  let html = '<button class="mm-sector-tab active" onclick="filterSector(\'all\',this)">All</button>';
  for (const sector of Object.keys(_catalog)) {
    html += `<button class="mm-sector-tab" onclick="filterSector('${sector.replace(/'/g,"\\'")}',this)">${sector}</button>`;
  }
  tabs.innerHTML = html;
}

function renderStockGrid(q='') {
  const grid = document.getElementById('stockGrid');
  q = q.trim().toUpperCase();
  let html = '';
  let shown = 0;
  for (const [sector, stocks] of Object.entries(_catalog)) {
    if (_activeSector !== 'all' && sector !== _activeSector) continue;
    for (const sym of stocks) {
      if (q && !sym.includes(q)) continue;
      const sel = _selectedStocks.has(sym) ? 'selected' : '';
      html += `<button class="mm-chip ${sel}" onclick="toggleStock('${sym}')" data-sym="${sym}" data-sector="${sector}">${sym}</button>`;
      shown++;
    }
  }
  if (!shown) html = '<div class="empty-state" style="padding:20px"><i class="bi bi-search"></i>No stocks match</div>';
  grid.innerHTML = html;
  updateSelectedCount();
}

function toggleStock(sym) {
  if (_selectedStocks.has(sym)) _selectedStocks.delete(sym);
  else _selectedStocks.add(sym);
  document.querySelectorAll(`[data-sym="${sym}"]`).forEach(el => el.classList.toggle('selected', _selectedStocks.has(sym)));
  updateSelectedCount();
  updateRunSummary();
}

function filterSector(sector, btn) {
  _activeSector = sector;
  document.querySelectorAll('.mm-sector-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  renderStockGrid(document.getElementById('stockSearch')?.value || '');
}

function filterStocks(q) { renderStockGrid(q); }

function clearStockSelection() {
  _selectedStocks.clear();
  renderStockGrid(document.getElementById('stockSearch')?.value || '');
  updateRunSummary();
}

function selectPreset(stocks) {
  _selectedStocks.clear();
  stocks.forEach(s => _selectedStocks.add(s));
  renderStockGrid(document.getElementById('stockSearch')?.value || '');
  updateRunSummary();
  showToast(`Selected ${stocks.length} stocks`, 'info');
}

function updateSelectedCount() {
  const n = _selectedStocks.size;
  const el = document.getElementById('selectedCount');
  if (el) el.textContent = n === 0 ? '0 selected' : `${n} selected`;
}

function addEmailTag(email) {
  email = email.trim().toLowerCase();
  if (!email || _emailTags.includes(email)) return;
  if (!email.includes('@') || !email.includes('.')) { showToast('Invalid email', 'warn'); return; }
  _emailTags.push(email);
  renderEmailTags();
  const inp = document.getElementById('emailInput');
  if (inp) inp.value = '';
  updateRunSummary();
}

function removeEmailTag(email) {
  _emailTags = _emailTags.filter(e => e !== email);
  renderEmailTags();
  updateRunSummary();
}

function renderEmailTags() {
  const c = document.getElementById('emailTags');
  if (!c) return;
  c.innerHTML = _emailTags.map(e =>
    `<span class="mm-email-tag">${e}<button onclick="removeEmailTag('${e}')" title="Remove">×</button></span>`
  ).join('');
}

function handleEmailKey(e) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault();
    addEmailTag(e.target.value.replace(',',''));
  } else if (e.key === 'Backspace' && !e.target.value && _emailTags.length) {
    removeEmailTag(_emailTags[_emailTags.length-1]);
  }
}

function handleEmailInput(input) {
  if (input.value.endsWith(',')) addEmailTag(input.value.slice(0,-1));
}

function updateRunSummary() {
  const sc = _selectedStocks.size, ec = _emailTags.length;
  const summaryEl = document.getElementById('runSummary');
  const runBtn = document.getElementById('runBtn');
  if (summaryEl) {
    if (!sc && !ec) summaryEl.textContent = 'Select stocks and add recipients to start';
    else if (!sc) summaryEl.textContent = `${ec} recipient(s) – select stocks to continue`;
    else if (!ec) summaryEl.textContent = `${sc} stock(s) – add at least 1 recipient`;
    else summaryEl.innerHTML = `<span class="text-accent">${sc}</span> stocks · <span class="text-accent">${ec}</span> recipient(s)`;
  }
  if (runBtn) runBtn.disabled = (!sc || !ec);
}

async function launchPipeline() {
  const stocks = [..._selectedStocks];
  const emails = [..._emailTags];
  if (!stocks.length || !emails.length) { showToast('Select stocks and add a recipient', 'warn'); return; }
  bootstrap.Modal.getInstance(document.getElementById('runModal'))?.hide();
  setBadge('running', 'Running…');
  showToast(`Analysing ${stocks.length} stock(s)…`, 'info');
  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({stocks, email: emails}),
    });
    const data = await res.json();
    if (data.status === 'started') { showToast('Pipeline started', 'success'); pollPipelineStatus(); }
    else if (data.status === 'already_running') { showToast('Already running', 'warn'); pollPipelineStatus(); }
    else { setBadge('error','Error'); showToast('Failed to start', 'error'); }
  } catch(err) { setBadge('error','Error'); showToast('Network error', 'error'); }
}

function pollPipelineStatus() {
  const iv = setInterval(async () => {
    try {
      const d = await fetch('/api/pipeline/status').then(r=>r.json());
      if (!d.running) {
        clearInterval(iv);
        setBadge('done','Done ✓');
        showToast('Analysis complete – refreshing…', 'success');
        setTimeout(()=>location.reload(), 2000);
      }
    } catch { clearInterval(iv); setBadge('idle','Idle'); }
  }, 3000);
}

function triggerPipeline() { openRunModal(); }

document.addEventListener('DOMContentLoaded', () => {
  fetch('/api/pipeline/status').then(r=>r.json()).then(d=>{
    if (d.running) { setBadge('running','Running…'); pollPipelineStatus(); }
  }).catch(()=>{});
});
