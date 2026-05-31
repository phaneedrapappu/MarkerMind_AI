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

function showToast(msg, type = 'info', duration = 3500) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warn: '⚠️' };
  const el = document.createElement('div');
  el.className = 'mm-toast';
  el.innerHTML = `<span style="font-size:18px">${icons[type]||'ℹ️'}</span><span>${msg}</span>`;
  const c = document.getElementById('toastContainer');
  if (c) {
    c.appendChild(el);
    setTimeout(() => { el.style.opacity='0'; el.style.transition='opacity .4s'; setTimeout(()=>el.remove(),400); }, duration);
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
let _tgSubscribers = -1;  // -1 = loading, 0 = none subscribed, N = ready
let _runModal = null;

function openRunModal() {
  // Run Analysis requires an authenticated session
  if (typeof MM_LOGGED_IN !== 'undefined' && !MM_LOGGED_IN) {
    showToast('Please log in to run analysis', 'warn');
    setTimeout(() => { window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname); }, 1200);
    return;
  }
  if (!_runModal) _runModal = new bootstrap.Modal(document.getElementById('runModal'));
  _tgSubscribers = -1;  // reset so updateRunSummary starts in "loading" state
  loadStockCatalog();
  loadRunPresets();
  loadRunTelegramInfo();
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

let _runPresetsLoaded = false;
async function loadRunPresets() {
  if (_runPresetsLoaded) return;
  const cont = document.getElementById('runPresetBtns');
  if (!cont) return;
  try {
    const r = await fetch('/api/stocks/presets');
    const presets = await r.json();
    cont.innerHTML = presets.map(p =>
      `<button class="mm-preset-btn" onclick="selectPreset(${JSON.stringify(p.stocks)})">${p.label}</button>`
    ).join('');
    _runPresetsLoaded = true;
  } catch {
    cont.innerHTML = [
      ['IT Leaders', ['TCS','INFY','WIPRO','HCLTECH','TECHM']],
      ['Banking',    ['HDFCBANK','ICICIBANK','SBIN','KOTAKBANK']],
      ['Energy',     ['RELIANCE','ONGC','NTPC','TATAPOWER']],
      ['Nifty Mix',  ['TCS','INFY','HDFCBANK','RELIANCE','DMART']],
    ].map(([l,s]) =>
      `<button class="mm-preset-btn" onclick="selectPreset(${JSON.stringify(s)})">${l}</button>`
    ).join('');
  }
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
  const tgLoading = _tgSubscribers === -1;
  const tgReady   = _tgSubscribers > 0;
  const hasOutput = ec > 0 || tgReady;
  const summaryEl = document.getElementById('runSummary');
  const runBtn    = document.getElementById('runBtn');

  if (summaryEl) {
    if (tgLoading && !ec) {
      // Still waiting for Telegram status, no email either — show a spinner
      summaryEl.innerHTML =
        '<span class="text-muted">' +
        '<span class="spinner-border spinner-border-sm me-1" style="width:10px;height:10px"></span>' +
        'Checking output channels…</span>';
    } else if (!sc) {
      summaryEl.textContent = 'Select at least 1 stock to continue';
    } else if (!hasOutput) {
      summaryEl.innerHTML =
        '<span class="text-warning">' +
        '<i class="bi bi-exclamation-triangle-fill me-1"></i>' +
        'No output channel — add an email recipient <strong>or</strong> ' +
        '<a href="/portfolio" target="_blank" class="text-warning">subscribe via Telegram</a> ' +
        'and add stocks to your Watchlist</span>';
    } else {
      const parts = [];
      if (ec)      parts.push(`<span class="text-accent">${ec}</span> email(s)`);
      if (tgReady) parts.push(
        `<i class="bi bi-telegram me-1"></i>` +
        `<span class="text-accent">${_tgSubscribers}</span> Telegram subscriber(s)`
      );
      summaryEl.innerHTML =
        `<span class="text-accent">${sc}</span> stock(s) &nbsp;&middot;&nbsp; ` +
        parts.join(' &amp; ');
    }
  }

  // Run enabled only when: stocks chosen AND at least one output ready AND not still loading
  if (runBtn) runBtn.disabled = tgLoading ? !ec : (!sc || !hasOutput);
}

async function launchPipeline() {
  const stocks = [..._selectedStocks];
  const emails = [..._emailTags];  // may be empty — email is optional
  if (!stocks.length) { showToast('Select at least 1 stock', 'warn'); return; }
  bootstrap.Modal.getInstance(document.getElementById('runModal'))?.hide();
  setBadge('running', 'Running…');
  const msg = emails.length
    ? `Analysing ${stocks.length} stock(s) — report will be emailed…`
    : `Analysing ${stocks.length} stock(s) — Telegram alerts will fire if subscribed…`;
  showToast(msg, 'info');
  try {
    const body = {stocks};
    if (emails.length) body.email = emails;
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    if (res.status === 401) {
      setBadge('idle', 'Idle');
      showToast('Session expired — please log in again', 'error');
      setTimeout(() => { window.location.href = '/login'; }, 1500);
      return;
    }
    const data = await res.json();
    if (res.status === 400 && data.setup_required) {
      setBadge('error', 'Not configured');
      showToast(data.error, 'error', 8000);
      return;
    }
    if (data.status === 'started') { showToast('Pipeline started', 'success'); pollPipelineStatus(); }
    else if (data.status === 'already_running') { showToast('Already running', 'warn'); pollPipelineStatus(); }
    else { setBadge('error','Error'); showToast(data.error || 'Failed to start', 'error'); }
  } catch(err) { setBadge('error','Error'); showToast('Could not reach server — is it running?', 'error'); }
}

function pollPipelineStatus() {
  const iv = setInterval(async () => {
    try {
      const d = await fetch('/api/pipeline/status').then(r=>r.json());
      if (!d.running) {
        clearInterval(iv);
        if (d.last_error) {
          setBadge('error', 'Failed');
          showToast('Pipeline error: ' + d.last_error, 'error', 10000);
        } else {
          setBadge('done','Done ✓');
          showToast('Analysis complete – refreshing…', 'success');
          setTimeout(()=>location.reload(), 2000);
        }
      }
    } catch { clearInterval(iv); setBadge('idle','Idle'); }
  }, 3000);
}

function triggerPipeline() { openRunModal(); }

// ── Email section toggle (collapsible) ───────────────────────────────────────
let _emailSectionOpen = true;
function toggleEmailSection() {
  _emailSectionOpen = !_emailSectionOpen;
  const sec = document.getElementById('emailSection');
  const chev = document.getElementById('emailChevron');
  if (sec) sec.style.display = _emailSectionOpen ? '' : 'none';
  if (chev) chev.style.transform = _emailSectionOpen ? '' : 'rotate(-90deg)';
}

// ── Telegram subscriber info for the run modal ───────────────────────────────
async function loadRunTelegramInfo() {
  const el = document.getElementById('runTelegramInfo');
  if (!el) return;
  try {
    const d = await (await fetch('/api/telegram/run-info')).json();
    if (!d.server_configured) {
      _tgSubscribers = 0;
      el.innerHTML =
        '<i class="bi bi-telegram me-1"></i>Telegram not configured on this server — ' +
        'add email recipients to receive output.';
    } else if (d.subscribers === 0) {
      _tgSubscribers = 0;
      el.innerHTML =
        '<i class="bi bi-exclamation-triangle text-warning me-1"></i>' +
        'No Telegram subscribers yet. ' +
        '<a href="/portfolio" target="_blank">Subscribe on the Portfolio page</a> ' +
        'and add stocks to your Watchlist — <em>or</em> add an email recipient above.';
    } else {
      _tgSubscribers = d.subscribers;
      el.innerHTML =
        `<i class="bi bi-check-circle text-success me-1"></i>` +
        `<strong>${d.subscribers}</strong> user(s) subscribed. ` +
        `Alerts will fire for whichever selected stocks are in their watchlist.`;
    }
  } catch {
    _tgSubscribers = 0;
    el.innerHTML = '<span class="text-muted">Could not load Telegram info.</span>';
  }
  updateRunSummary();  // re-evaluate run button now that tg state is known
}

document.addEventListener('DOMContentLoaded', () => {
  fetch('/api/pipeline/status').then(r=>r.json()).then(d=>{
    if (d.running) { setBadge('running','Running…'); pollPipelineStatus(); }
  }).catch(()=>{});
});
