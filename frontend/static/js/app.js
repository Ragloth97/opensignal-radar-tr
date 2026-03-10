/**
 * OpenSignal Radar TR — Core Application JS
 * Vanilla JS, no framework dependencies
 */

// ── API Client ──────────────────────────────────────────────────────────────

const API = {
  async get(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v);
    });
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API ${res.status}: ${url}`);
    return res.json();
  },

  async post(path, body = {}) {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  },

  async patch(path, body = {}) {
    const res = await fetch(path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  },

  async delete(path) {
    const res = await fetch(path, { method: 'DELETE' });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  },
};

// ── Toast Notifications ─────────────────────────────────────────────────────

const Toast = {
  container: null,

  init() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  },

  show(message, type = 'info', duration = 3500) {
    if (!this.container) this.init();
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    this.container.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = '0.3s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  success(msg) { this.show(msg, 'success'); },
  error(msg) { this.show(msg, 'error', 5000); },
  info(msg) { this.show(msg, 'info'); },
};

// ── Score Utilities ─────────────────────────────────────────────────────────

const Scores = {
  colorClass(score) {
    if (score >= 0.70) return 'score-high';
    if (score >= 0.45) return 'score-mid';
    return 'score-low';
  },

  barColor(score) {
    if (score >= 0.70) return '#34d399';
    if (score >= 0.45) return '#fbbf24';
    return '#f87171';
  },

  format(score) {
    return (score * 100).toFixed(0);
  },
};

// ── Signal Type Utilities ───────────────────────────────────────────────────

const SignalTypes = {
  labels: {
    'new_facility': 'Yeni Tesis',
    'expansion': 'Kapasite Artışı',
    'investment': 'Yatırım',
    'incentive': 'Teşvik',
    'hiring_wave': 'İşe Alım Dalgası',
    'infrastructure_project': 'Altyapı Projesi',
    'energy_project': 'Enerji Projesi',
    'patent': 'Patent / Teknoloji',
    'partnership': 'Stratejik Ortaklık',
    'acquisition': 'Satın Alma / Birleşme',
    'supply_chain_signal': 'Tedarik Zinciri',
    'data_center': 'Veri Merkezi',
    'mining': 'Madencilik',
    'semiconductor': 'Yarı İletken',
    'automotive': 'Otomotiv',
    'defense': 'Savunma',
    'logistics': 'Lojistik',
    'irrelevant': 'İlgisiz',
  },

  label(type) {
    return this.labels[type] || type;
  },

  cssClass(type) {
    return `type-${type?.replace('_signal', '').replace('_project', '')}`;
  },
};

const Industries = {
  labels: {
    'enerji': 'Enerji',
    'veri_merkezi': 'Veri Merkezi',
    'yari_iletken': 'Yarı İletken',
    'otomotiv': 'Otomotiv',
    'lojistik': 'Lojistik',
    'madencilik': 'Madencilik',
    'uretim': 'Üretim',
    'savunma': 'Savunma',
    'insaat': 'İnşaat',
    'finans': 'Finans',
    'teknoloji': 'Teknoloji',
    'tarim': 'Tarım',
    'saglik': 'Sağlık',
    'perakende': 'Perakende',
    'telekom': 'Telekom',
    'diger': 'Diğer',
  },
  label(ind) { return this.labels[ind] || ind || '—'; },
};

// ── HTML Builders ───────────────────────────────────────────────────────────

function buildScoreBar(label, score) {
  const pct = (score * 100).toFixed(0);
  const color = Scores.barColor(score);
  return `
    <div class="score-bar">
      <span class="score-bar-label">${label}</span>
      <div class="score-bar-track">
        <div class="score-bar-fill" style="width:${pct}%;background:${color}"></div>
      </div>
      <span class="score-bar-value">${pct}</span>
    </div>`;
}

function buildSignalBadge(signal_type) {
  const label = SignalTypes.label(signal_type);
  const cssClass = SignalTypes.cssClass(signal_type);
  return `<span class="signal-type-badge ${cssClass}">${label}</span>`;
}

function buildScoreBadge(score) {
  const cls = Scores.colorClass(score);
  return `<span class="score-badge ${cls}">${Scores.format(score)}</span>`;
}

function buildSignalCard(sig) {
  const badge = buildSignalBadge(sig.signal_type);
  const company = sig.detected_company || '—';
  const country = sig.country || '';
  const industry = Industries.label(sig.industry);
  const date = sig.created_at ? formatDate(sig.created_at) : '';

  return `
    <a href="/sinyaller/${sig.id}" class="signal-card">
      <div class="signal-card-header">
        <div class="signal-card-title">${escHtml(sig.article_title || sig.summary_tr || 'Başlık yok')}</div>
        ${buildScoreBadge(sig.composite_score)}
      </div>
      <div class="signal-meta">
        ${badge}
        ${country ? `<span class="meta-item">${svgIcon('globe')} ${country}</span>` : ''}
        ${industry !== '—' ? `<span class="meta-item">${svgIcon('tag')} ${industry}</span>` : ''}
        ${company !== '—' ? `<span class="meta-item">${svgIcon('building')} ${escHtml(company)}</span>` : ''}
        <span class="meta-item ml-auto">${date}</span>
      </div>
      ${sig.summary_tr ? `<div class="signal-summary">${escHtml(sig.summary_tr)}</div>` : ''}
      <div class="signal-scores">
        ${buildScoreBar('Güven', sig.confidence_score)}
        ${buildScoreBar('Etki', sig.impact_score)}
      </div>
    </a>`;
}

// ── Pagination ──────────────────────────────────────────────────────────────

function buildPagination(current, total, onPage) {
  if (total <= 1) return '';
  const maxVisible = 7;
  let pages = [];

  if (total <= maxVisible) {
    pages = Array.from({ length: total }, (_, i) => i + 1);
  } else {
    if (current <= 4) {
      pages = [1, 2, 3, 4, 5, '...', total];
    } else if (current >= total - 3) {
      pages = [1, '...', total-4, total-3, total-2, total-1, total];
    } else {
      pages = [1, '...', current-1, current, current+1, '...', total];
    }
  }

  return `
    <div class="pagination">
      <button class="page-btn" onclick="(${onPage})(${current - 1})"
        ${current === 1 ? 'disabled' : ''}>${svgIcon('chevron-left')}</button>
      ${pages.map(p => p === '...'
        ? `<span class="page-btn" style="cursor:default">…</span>`
        : `<button class="page-btn ${p === current ? 'active' : ''}"
             onclick="(${onPage})(${p})">${p}</button>`
      ).join('')}
      <button class="page-btn" onclick="(${onPage})(${current + 1})"
        ${current === total ? 'disabled' : ''}>${svgIcon('chevron-right')}</button>
    </div>`;
}

// ── SVG Icons (minimal inline set) ─────────────────────────────────────────

const ICONS = {
  'globe': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6.5"/><ellipse cx="8" cy="8" rx="2.5" ry="6.5"/><path d="M1.5 8h13"/></svg>',
  'tag': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 2h5.5l6 6-5.5 5.5-6-6V2z"/><circle cx="4.5" cy="4.5" r="1"/></svg>',
  'building': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="1"/><path d="M6 14V9h4v5"/><path d="M5 5h1.5M9.5 5H11M5 7.5h1.5M9.5 7.5H11"/></svg>',
  'chevron-left': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 12L6 8l4-4"/></svg>',
  'chevron-right': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 12l4-4-4-4"/></svg>',
  'search': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="6.5" cy="6.5" r="4.5"/><path d="M10.5 10.5L14 14"/></svg>',
  'refresh': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13.5 8A5.5 5.5 0 1 1 8 2.5"/><path d="M13.5 2.5V6H10"/></svg>',
  'download': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2v8M5 7l3 3 3-3M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1"/></svg>',
  'check': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M2.5 8l4 4 7-7"/></svg>',
  'x': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4l8 8M12 4l-8 8"/></svg>',
  'eye': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z"/><circle cx="8" cy="8" r="2"/></svg>',
  'plus': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 2v12M2 8h12"/></svg>',
  'link': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M7 9a3 3 0 004.5.5l2-2a3 3 0 00-4.24-4.24l-1.13 1.12"/><path d="M9 7a3 3 0 00-4.5-.5l-2 2a3 3 0 004.24 4.24l1.12-1.12"/></svg>',
  'trend': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 12L5 7l3 3 4-5 3 3"/></svg>',
  'alert': '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2l6.5 11H1.5L8 2z"/><path d="M8 7v3M8 11.5v.5"/></svg>',
};

function svgIcon(name, cls = '') {
  const svg = ICONS[name] || '';
  if (!cls) return svg;
  return svg.replace('<svg', `<svg class="${cls}"`);
}

// ── Utilities ───────────────────────────────────────────────────────────────

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = (now - d) / 1000;

  if (diff < 3600) return `${Math.floor(diff / 60)} dk önce`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} sa önce`;
  if (diff < 172800) return 'Dün';
  return d.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' });
}

function formatNumber(n) {
  if (!n && n !== 0) return '—';
  return Number(n).toLocaleString('tr-TR');
}

function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ── Active Nav ──────────────────────────────────────────────────────────────

function setActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(el => {
    const href = el.getAttribute('href');
    if (href && (href === path || (href !== '/' && path.startsWith(href)))) {
      el.classList.add('active');
    }
  });
}

// ── Status Bar ──────────────────────────────────────────────────────────────

async function updateStatusBar() {
  try {
    const status = await API.get('/api/system/status');
    const el = document.getElementById('status-signal-count');
    if (el) el.textContent = formatNumber(status.database.total_signals);
    const ollamaEl = document.getElementById('status-ollama');
    if (ollamaEl) {
      ollamaEl.textContent = status.ollama.enabled ? 'AI Aktif' : 'Rules Modu';
      ollamaEl.style.color = status.ollama.enabled ? 'var(--green)' : 'var(--text-muted)';
    }
  } catch (_) {}
}

// ── Init ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  Toast.init();
  setActiveNav();
  updateStatusBar();
});

// Expose globals
window.API = API;
window.Toast = Toast;
window.Scores = Scores;
window.SignalTypes = SignalTypes;
window.Industries = Industries;
window.buildSignalCard = buildSignalCard;
window.buildPagination = buildPagination;
window.buildScoreBar = buildScoreBar;
window.buildSignalBadge = buildSignalBadge;
window.buildScoreBadge = buildScoreBadge;
window.svgIcon = svgIcon;
window.escHtml = escHtml;
window.formatDate = formatDate;
window.formatNumber = formatNumber;
window.debounce = debounce;
