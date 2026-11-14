/* ═══════════════════════════════════════════════════════════════
   Video Downloader Dashboard — المنطق التفاعلي
   ═══════════════════════════════════════════════════════════════ */
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const PLATFORM_AR = { youtube: 'يوتيوب', tiktok: 'تيك توك', instagram: 'إنستجرام', facebook: 'فيسبوك', x: 'إكس', spotify: 'سبوتيفاي', anghami: 'أنجامي', soundcloud: 'ساوند كلاود', other: 'أخرى' };
const PLATFORM_EMOJI = { youtube: '▶️', tiktok: '🎵', instagram: '📸', facebook: '📘', x: '𝕏', spotify: '🟢', anghami: '🟣', soundcloud: '🟠', other: '🔗' };
const PLATFORM_COLOR = { youtube: '#f87171', tiktok: '#2dd4bf', instagram: '#f472b6', facebook: '#60a5fa', x: '#e2e8f0', spotify: '#4ade80', anghami: '#c084fc', soundcloud: '#fb923c', other: '#94a3b8' };
const MONTHS_AR = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
const QUALITY_AR = { max: '🚀 بلا حدود' };

const fmtNum = n => (n ?? 0).toLocaleString('en-US');
const fmtCompact = n => new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(n ?? 0);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function fmtBytes(bytes) {
  if (!bytes) return '0 بايت';
  const units = ['بايت', 'ك.بايت', 'م.بايت', 'ج.بايت', 'ت.بايت'];
  let i = 0, n = Number(bytes);
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n >= 100 ? n.toFixed(0) : n.toFixed(1)} ${units[i]}`;
}

function parseUTC(s) { return new Date(String(s).replace(' ', 'T') + 'Z'); }

function timeAgo(iso) {
  const diff = Date.now() - parseUTC(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'الآن';
  if (min < 60) return `منذ ${min} د`;
  const h = Math.floor(min / 60);
  if (h < 24) return `منذ ${h} س`;
  const d = Math.floor(h / 24);
  if (d < 30) return `منذ ${d} يوم`;
  return parseUTC(iso).toLocaleDateString('ar', { day: 'numeric', month: 'short' });
}

const fmtDateTime = iso => parseUTC(iso).toLocaleString('ar', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

async function api(path, options) {
  const res = await fetch(path, options);
  if (res.status === 401) { location.href = '/login'; throw new Error('غير مصرح'); }
  if (!res.ok) { const body = await res.json().catch(() => ({})); throw new Error(body.detail || `خطأ ${res.status}`); }
  return res.status === 204 ? null : res.json();
}

/* ═══════════ التنبيهات ═══════════ */
function toast(message, type = 'success') {
  const icons = { success: '✅', error: '⚠️', info: '💡' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || '💡'}</span><span>${esc(message)}</span>`;
  $('#toasts').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(8px)'; }, 3800);
  setTimeout(() => el.remove(), 4250);
}

/* ═══════════ التنقل بين التبويبات ═══════════ */
const TAB_TITLES = {
  overview: ['نظرة عامة', 'ملخص حي لأداء البوت وتفاعل المستخدمين'],
  downloads: ['سجل التنزيلات', 'كل عمليات التحميل مع الفلترة والبحث والتصدير'],
  users: ['إدارة المستخدمين', 'حظر أو إلغاء حظر أي مستخدم بضغطة واحدة'],
  broadcast: ['الإذاعة', 'أرسل رسالة لكل مستخدمي البوت عبر تيليجرام'],
  preview: ['معاينة البوت', 'محادثة تفاعلية حقيقية تحاكي تجربة المستخدم'],
  settings: ['الإعدادات', 'حالة النظام وخطوات التشغيل'],
};

function activateTab(name) {
  $$('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  $$('.tab').forEach(s => s.classList.toggle('active', s.id === `tab-${name}`));
  const [title, sub] = TAB_TITLES[name] || TAB_TITLES.overview;
  $('#pageTitle').textContent = title;
  $('#pageSubtitle').textContent = sub;
  $('#sidebar').classList.remove('open');
  $('#overlay').hidden = true;
  window.scrollTo({ top: 0 });
  if (name === 'downloads') loadDownloads();
  if (name === 'users') loadUsers();
  if (name === 'broadcast') loadBroadcasts();
  if (name === 'settings') loadConfig();
}

$$('.nav-item').forEach(btn => btn.addEventListener('click', () => activateTab(btn.dataset.tab)));
$$('[data-goto]').forEach(btn => btn.addEventListener('click', () => activateTab(btn.dataset.goto)));
$('#hamburger').addEventListener('click', () => { $('#sidebar').classList.add('open'); $('#overlay').hidden = false; });
$('#overlay').addEventListener('click', () => { $('#sidebar').classList.remove('open'); $('#overlay').hidden = true; });

$('#refreshBtn').addEventListener('click', async () => {
  const btn = $('#refreshBtn');
  btn.classList.add('spinning');
  try {
    await loadOverview();
    toast('تم تحديث البيانات', 'info');
  } finally {
    setTimeout(() => btn.classList.remove('spinning'), 700);
  }
});

/* ترحيب حسب الساعة + التاريخ */
(function initGreeting() {
  const now = new Date();
  const h = now.getHours();
  const greet = h < 12 ? 'صباح الخير' : h < 18 ? 'طاب يومك' : 'مساء الخير';
  $('.wb-text h2').textContent = `${greet}، مشرفنا 👋`;
  $('#wbDate').textContent = new Intl.DateTimeFormat('ar', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(now);
})();

/* ═══════════ عدّادات متحركة ═══════════ */
function countUp(el, target, { duration = 900, decimals = 0, suffix = '' } = {}) {
  const start = performance.now();
  const from = 0;
  function frame(t) {
    const p = Math.min((t - start) / duration, 1);
    const eased = 1 - Math.pow(2, -8 * p);
    const value = from + (target - from) * (p === 1 ? 1 : eased);
    el.textContent = (decimals ? value.toFixed(decimals) : fmtNum(Math.round(value))) + suffix;
    if (p < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

/* ═══════════ تحميل نظرة عامة ═══════════ */
let overviewCache = null;

async function loadOverview() {
  try {
    const data = await api('/api/overview');
    overviewCache = data;
    const k = data.kpis;

    countUp($('#kpiUsers'), k.users);
    $('#kpiUsersDelta').textContent = `+${fmtNum(k.users_today)} اليوم`;

    countUp($('#kpiDownloads'), k.downloads);
    const delta = k.downloads_today - k.downloads_yesterday;
    const deltaEl = $('#kpiDownloadsDelta');
    deltaEl.textContent = `${delta >= 0 ? '+' : ''}${fmtNum(delta)} عن أمس`;
    deltaEl.classList.toggle('up', delta >= 0);

    countUp($('#kpiToday'), k.downloads_today);
    $('#kpiBytes').textContent = `${fmtBytes(k.bytes_sent)} مُرسلة إجمالاً`;

    countUp($('#kpiSuccess'), k.success_rate, { decimals: 1 });
    $('#kpiFailed').textContent = `${fmtNum(k.failed)} عملية فاشلة`;

    $('#navDownloadsBadge').textContent = fmtCompact(k.downloads);

    renderAreaChart(data.timeseries);
    renderDonut(data.platforms, k.downloads);
    renderQualityBars(data.qualities);
    renderMediaSplit(k.mp4, k.mp3);
    renderRecent(data.recent);
    renderTopUsers(data.top_users);
  } catch (err) {
    console.error(err);
    toast('تعذر تحميل البيانات من الخادم', 'error');
  }
}

/* ═══════════ الرسم البياني المساحي ═══════════ */
function fillDailySeries(timeseries, days = 30) {
  const map = new Map((timeseries || []).map(r => [r.day, r]));
  const series = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const row = map.get(key);
    series.push({ day: key, total: row ? row.total : 0, done: row ? row.done : 0, date: d });
  }
  return series;
}

function smoothPath(points) {
  if (points.length < 2) return '';
  let d = `M ${points[0].x},${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)], p1 = points[i], p2 = points[i + 1], p3 = points[Math.min(points.length - 1, i + 2)];
    const c1x = p1.x + (p2.x - p0.x) / 6, c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6, c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x},${c1y} ${c2x},${c2y} ${p2.x},${p2.y}`;
  }
  return d;
}

function niceMax(v) {
  if (v <= 5) return 5;
  const pow = Math.floor(Math.log10(v));
  const base = Math.pow(10, pow);
  const n = v / base;
  const nice = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
  return nice * base;
}

function renderAreaChart(timeseries) {
  const svg = $('#areaChart');
  const W = 720, H = 240, PT = 14, PB = 10, PL = 8, PR = 8;
  const innerW = W - PL - PR, innerH = H - PT - PB;
  const series = fillDailySeries(timeseries, 30);
  const maxVal = niceMax(Math.max(5, ...series.map(s => s.total)));

  const x = i => PL + (i / (series.length - 1)) * innerW;
  const y = v => PT + innerH - (v / maxVal) * innerH;

  const totalPts = series.map((s, i) => ({ x: x(i), y: y(s.total) }));
  const donePts = series.map((s, i) => ({ x: x(i), y: y(s.done) }));
  const lineTotal = smoothPath(totalPts);
  const lineDone = smoothPath(donePts);
  const areaTotal = `${lineTotal} L ${x(series.length - 1)},${PT + innerH} L ${x(0)},${PT + innerH} Z`;

  let grid = '';
  for (let g = 0; g <= 3; g++) {
    const gy = PT + (innerH / 3) * g;
    grid += `<line x1="${PL}" y1="${gy}" x2="${W - PR}" y2="${gy}" stroke="rgba(139,146,255,0.09)" stroke-width="1"/>`;
  }

  svg.innerHTML = `
    <defs>
      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.42"/>
        <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.02"/>
      </linearGradient>
      <linearGradient id="strokeGrad" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#8b5cf6"/><stop offset="100%" stop-color="#22d3ee"/>
      </linearGradient>
    </defs>
    ${grid}
    <path d="${areaTotal}" fill="url(#areaGrad)"/>
    <path d="${lineDone}" fill="none" stroke="#22d3ee" stroke-width="2" stroke-opacity="0.9" stroke-linecap="round"/>
    <path d="${lineTotal}" fill="none" stroke="url(#strokeGrad)" stroke-width="2.6" stroke-linecap="round"/>
    <line id="guideLine" x1="0" y1="${PT}" x2="0" y2="${PT + innerH}" stroke="rgba(255,255,255,0.25)" stroke-dasharray="4 4" visibility="hidden"/>
    <circle id="dotTotal" r="4.5" fill="#a78bfa" stroke="#0b0f1a" stroke-width="2" visibility="hidden"/>
    <circle id="dotDone" r="4" fill="#22d3ee" stroke="#0b0f1a" stroke-width="2" visibility="hidden"/>
    <rect id="hoverZone" x="0" y="0" width="${W}" height="${H}" fill="transparent"/>
  `;

  // التسميات أسفل المحور
  const labelsHost = $('#chartXLabels');
  const step = Math.ceil(series.length / 6);
  labelsHost.innerHTML = series
    .filter((_, i) => i % step === 0 || i === series.length - 1)
    .map(s => `<span>${s.date.getDate()} ${MONTHS_AR[s.date.getMonth()]}</span>`)
    .join('');

  // التلميح التفاعلي
  const tooltip = $('#areaTooltip');
  const guide = svg.querySelector('#guideLine');
  const dotT = svg.querySelector('#dotTotal');
  const dotD = svg.querySelector('#dotDone');
  const hoverZone = svg.querySelector('#hoverZone');

  hoverZone.addEventListener('mousemove', e => {
    const rect = svg.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * W;
    let idx = Math.round(((svgX - PL) / innerW) * (series.length - 1));
    idx = Math.max(0, Math.min(series.length - 1, idx));
    const s = series[idx];
    const px = x(idx);

    guide.setAttribute('x1', px); guide.setAttribute('x2', px); guide.setAttribute('visibility', 'visible');
    dotT.setAttribute('cx', px); dotT.setAttribute('cy', y(s.total)); dotT.setAttribute('visibility', 'visible');
    dotD.setAttribute('cx', px); dotD.setAttribute('cy', y(s.done)); dotD.setAttribute('visibility', 'visible');

    tooltip.hidden = false;
    tooltip.style.left = `${(px / W) * 100}%`;
    tooltip.style.top = `${(y(s.total) / H) * 100 - 6}%`;
    tooltip.innerHTML = `<b>${s.date.getDate()} ${MONTHS_AR[s.date.getMonth()]}</b><br>⬇️ التحميلات: <b>${fmtNum(s.total)}</b><br>✅ الناجحة: <b>${fmtNum(s.done)}</b>`;
  });
  hoverZone.addEventListener('mouseleave', () => {
    tooltip.hidden = true;
    guide.setAttribute('visibility', 'hidden');
    dotT.setAttribute('visibility', 'hidden');
    dotD.setAttribute('visibility', 'hidden');
  });
}

/* ═══════════ الدونت ═══════════ */
function renderDonut(platforms, totalDownloads) {
  const svg = $('#donutChart');
  const R = 56, C = 2 * Math.PI * R, CX = 80, CY = 80, STROKE = 24;
  const total = Math.max(1, (platforms || []).reduce((acc, p) => acc + p.count, 0));

  let offset = 0;
  const segs = (platforms || []).map(p => {
    const frac = p.count / total;
    const len = frac * C;
    const seg = `<circle cx="${CX}" cy="${CY}" r="${R}" fill="none"
        stroke="${PLATFORM_COLOR[p.platform] || PLATFORM_COLOR.other}"
        stroke-width="${STROKE}" stroke-dasharray="${Math.max(len - 2.5, 0.5)} ${C}"
        stroke-dashoffset="${-offset}" stroke-linecap="round"
        style="transition: stroke-dasharray 1s ease"/>`;
    offset += len;
    return seg;
  }).join('');

  svg.innerHTML = `<circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="rgba(139,146,255,0.08)" stroke-width="${STROKE}"/>${segs}`;
  $('#donutTotal').textContent = fmtCompact(totalDownloads ?? total);

  $('#platformLegend').innerHTML = (platforms || []).slice(0, 8).map(p => `
    <li>
      <span class="pl-dot" style="background:${PLATFORM_COLOR[p.platform] || PLATFORM_COLOR.other}"></span>
      <span class="pl-name">${PLATFORM_EMOJI[p.platform] || '🔗'} ${esc(PLATFORM_AR[p.platform] || p.platform)}</span>
      <span class="pl-val">${fmtNum(p.count)} · ${Math.round((p.count / total) * 100)}%</span>
    </li>`).join('');
}

/* ═══════════ الجودات ═══════════ */
function renderQualityBars(qualities) {
  const host = $('#qualityBars');
  const rows = (qualities || []).slice(0, 6);
  const max = Math.max(1, ...rows.map(r => r.count));
  host.innerHTML = rows.map(r => `
    <div class="qb-row">
      <span class="qb-label">${esc(QUALITY_AR[r.quality] || r.quality)}</span>
      <div class="qb-track"><div class="qb-fill" data-w="${(r.count / max) * 100}"></div></div>
      <span class="qb-count">${fmtNum(r.count)}</span>
    </div>`).join('');
  requestAnimationFrame(() => $$('.qb-fill', host).forEach(el => { el.style.width = `${el.dataset.w}%`; }));
}

function renderMediaSplit(mp4, mp3) {
  mp4 = mp4 || 0; mp3 = mp3 || 0;
  const total = Math.max(1, mp4 + mp3);
  $('#mp4Count').textContent = fmtNum(mp4);
  $('#mp3Count').textContent = fmtNum(mp3);
  $('#mediaBarMp4').style.width = `${(mp4 / total) * 100}%`;
}

function renderRecent(rows) {
  const tbody = $('#recentTable tbody');
  tbody.innerHTML = (rows || []).map(r => `
    <tr>
      <td>${userCell(r.first_name, r.username, r.telegram_id, true)}</td>
      <td><span class="cell-title" title="${esc(r.title)}">${esc(r.title || '—')}</span></td>
      <td><span class="cell-num">${esc(r.media_type === 'mp3' ? '🎧 ' : '🎬 ')}${esc(r.quality)}</span></td>
      <td title="${esc(fmtDateTime(r.created_at))}">${esc(timeAgo(r.created_at))}</td>
      <td>${statusPill(r.status)}</td>
    </tr>`).join('') || `<tr><td colspan="5" class="empty-state">لا توجد تنزيلات بعد</td></tr>`;
}

function renderTopUsers(rows) {
  $('#topUsersList').innerHTML = (rows || []).map((u, i) => `
    <li>
      <span class="rank">${['🥇', '🥈', '🥉'][i] || i + 1}</span>
      <div class="avatar small">${esc((u.first_name || '؟').trim().charAt(0).toUpperCase())}</div>
      <div><div class="tu-name">${esc(u.first_name || 'بدون اسم')}</div><div class="tu-sub">${u.username ? '@' + esc(u.username) : ''}</div></div>
      <span class="tu-count">${fmtNum(u.dl_count)} تحميل</span>
    </li>`).join('') || '<li class="empty-state">لا توجد بيانات</li>';
}

function userCell(first, username, telegramId, small = false) {
  const initial = (first || '؟').trim().charAt(0).toUpperCase();
  const name = first || 'بدون اسم';
  const sub = username ? `@${username}` : (telegramId ? `ID: ${telegramId}` : '');
  return `<div class="user-cell"><div class="avatar${small ? ' small' : ''}">${esc(initial)}</div><div><div style="font-weight:600">${esc(name)}</div><div class="cell-sub">${esc(sub)}</div></div></div>`;
}

const statusPill = s => s === 'done'
  ? '<span class="status-pill status-done">✅ ناجح</span>'
  : '<span class="status-pill status-failed">❌ فاشل</span>';

/* ═══════════ تبويب التنزيلات ═══════════ */
const dlState = { offset: 0, limit: 12, platform: '', status: '', search: '' };
let dlDebounce = null;

async function loadDownloads() {
  const params = new URLSearchParams({
    limit: dlState.limit, offset: dlState.offset,
    ...(dlState.platform && { platform: dlState.platform }),
    ...(dlState.status && { status: dlState.status }),
    ...(dlState.search && { search: dlState.search }),
  });
  try {
    const { rows, total } = await api(`/api/downloads?${params}`);
    $('#downloadsTable tbody').innerHTML = rows.map(r => `
      <tr>
        <td>${userCell(r.first_name, r.username, r.telegram_id, true)}</td>
        <td><span class="cell-title" title="${esc(r.title)}${r.error ? ' — ' + esc(r.error) : ''}">${esc(r.title || '—')}</span></td>
        <td><span class="platform-tag">${PLATFORM_EMOJI[r.platform] || '🔗'} ${esc(PLATFORM_AR[r.platform] || r.platform)}</span></td>
        <td>${r.media_type === 'mp3' ? '🎧 MP3' : '🎬 MP4'}</td>
        <td class="cell-num">${esc(r.quality)}</td>
        <td class="cell-num">${r.file_size ? fmtBytes(r.file_size) : '—'}</td>
        <td title="${esc(fmtDateTime(r.created_at))}">${esc(timeAgo(r.created_at))}</td>
        <td>${statusPill(r.status)}</td>
      </tr>`).join('') || `<tr><td colspan="8" class="empty-state">لا توجد نتائج مطابقة</td></tr>`;

    const from = total === 0 ? 0 : dlState.offset + 1;
    const to = Math.min(dlState.offset + dlState.limit, total);
    $('#dlRange').textContent = `عرض ${fmtNum(from)}–${fmtNum(to)} من ${fmtNum(total)}`;
    $('#dlPrev').disabled = dlState.offset === 0;
    $('#dlNext').disabled = dlState.offset + dlState.limit >= total;
  } catch (err) {
    toast('تعذر تحميل سجل التنزيلات', 'error');
  }
}

$('#dlSearch').addEventListener('input', e => {
  clearTimeout(dlDebounce);
  dlDebounce = setTimeout(() => { dlState.search = e.target.value.trim(); dlState.offset = 0; loadDownloads(); }, 320);
});
$('#dlPlatform').addEventListener('change', e => { dlState.platform = e.target.value; dlState.offset = 0; loadDownloads(); });
$('#dlStatus').addEventListener('change', e => { dlState.status = e.target.value; dlState.offset = 0; loadDownloads(); });
$('#dlPrev').addEventListener('click', () => { dlState.offset = Math.max(0, dlState.offset - dlState.limit); loadDownloads(); });
$('#dlNext').addEventListener('click', () => { dlState.offset += dlState.limit; loadDownloads(); });

$('#dlExport').addEventListener('click', async () => {
  const params = new URLSearchParams({
    limit: 100, offset: 0,
    ...(dlState.platform && { platform: dlState.platform }),
    ...(dlState.status && { status: dlState.status }),
    ...(dlState.search && { search: dlState.search }),
  });
  try {
    const { rows } = await api(`/api/downloads?${params}`);
    const header = 'الاسم,المستخدم,العنوان,المنصة,النوع,الجودة,الحجم (بايت),الحالة,التاريخ';
    const lines = rows.map(r => [
      r.first_name, r.username ? '@' + r.username : '', r.title, PLATFORM_AR[r.platform] || r.platform,
      r.media_type.toUpperCase(), r.quality, r.file_size ?? '', r.status === 'done' ? 'ناجح' : 'فاشل', r.created_at,
    ].map(v => `"${String(v ?? '').replaceAll('"', '""')}"`).join(','));
    const csv = '\uFEFF' + [header, ...lines].join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'downloads-report.csv' });
    a.click();
    URL.revokeObjectURL(a.href);
    toast(`تم تصدير ${rows.length} سجل`);
  } catch {
    toast('تعذر التصدير', 'error');
  }
});

/* ═══════════ تبويب المستخدمين ═══════════ */
const usersState = { offset: 0, limit: 12, search: '' };
let usersDebounce = null;

async function loadUsers() {
  const params = new URLSearchParams({
    limit: usersState.limit, offset: usersState.offset,
    ...(usersState.search && { search: usersState.search }),
  });
  try {
    const { rows, total } = await api(`/api/users?${params}`);
    $('#usersTable tbody').innerHTML = rows.map((u, i) => `
      <tr>
        <td class="cell-num">${usersState.offset + i + 1}</td>
        <td>${userCell(u.first_name, u.username, u.telegram_id)}</td>
        <td class="cell-num">${u.telegram_id}</td>
        <td title="${esc(fmtDateTime(u.joined_at))}">${esc(timeAgo(u.joined_at))}</td>
        <td title="${esc(fmtDateTime(u.last_seen))}">${esc(timeAgo(u.last_seen))}</td>
        <td class="cell-num">${fmtNum(u.dl_count)}</td>
        <td>${u.is_banned ? '<span class="status-pill status-banned">محظور</span>' : '<span class="status-pill status-active">نشط</span>'}</td>
        <td><button class="ban-btn ${u.is_banned ? 'unban' : ''}" data-id="${u.telegram_id}" data-banned="${u.is_banned ? 0 : 1}">${u.is_banned ? 'إلغاء الحظر' : 'حظر'}</button></td>
      </tr>`).join('') || `<tr><td colspan="8" class="empty-state">لا توجد نتائج</td></tr>`;

    $('#usersRange').textContent = `عرض ${rows.length ? usersState.offset + 1 : 0}–${usersState.offset + rows.length} من ${fmtNum(total)}`;
    $('#usersPrev').disabled = usersState.offset === 0;
    $('#usersNext').disabled = usersState.offset + usersState.limit >= total;
  } catch {
    toast('تعذر تحميل المستخدمين', 'error');
  }
}

$('#userSearch').addEventListener('input', e => {
  clearTimeout(usersDebounce);
  usersDebounce = setTimeout(() => { usersState.search = e.target.value.trim(); usersState.offset = 0; loadUsers(); }, 320);
});
$('#usersPrev').addEventListener('click', () => { usersState.offset = Math.max(0, usersState.offset - usersState.limit); loadUsers(); });
$('#usersNext').addEventListener('click', () => { usersState.offset += usersState.limit; loadUsers(); });

$('#usersTable').addEventListener('click', async e => {
  const btn = e.target.closest('.ban-btn');
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const ban = btn.dataset.banned === '1';
  btn.disabled = true;
  try {
    await api(`/api/users/${id}/ban`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ banned: ban }) });
    toast(ban ? 'تم حظر المستخدم' : 'تم إلغاء الحظر');
    loadUsers();
  } catch (err) {
    toast(err.message || 'تعذر تنفيذ الإجراء', 'error');
    btn.disabled = false;
  }
});

/* ═══════════ تبويب الإذاعة ═══════════ */
const broadcastText = $('#broadcastText');
const charCount = $('#charCount');
const previewBubble = $('#broadcastPreviewBubble');

broadcastText.addEventListener('input', () => {
  const len = broadcastText.value.length;
  charCount.textContent = `${fmtNum(len)} / 4000`;
  const text = broadcastText.value.trim();
  previewBubble.innerHTML = `📣 <b>رسالة من الإدارة</b><br><br>${text ? esc(text).replaceAll('\n', '<br>') : '<span class="muted">اكتب شيئاً لترى المعاينة…</span>'}`;
});

$('#sendBroadcastBtn').addEventListener('click', () => {
  const text = broadcastText.value.trim();
  if (text.length < 3) { toast('اكتب رسالة أطول من 3 أحرف أولاً', 'error'); return; }
  $('#confirmPreview').textContent = text;
  const users = overviewCache?.kpis?.users;
  $('#confirmCount').textContent = users ? `${fmtNum(users)} مستخدم` : 'كل';
  $('#confirmModal').hidden = false;
});
$('#confirmCancel').addEventListener('click', () => { $('#confirmModal').hidden = true; });
$('#confirmModal').addEventListener('click', e => { if (e.target.id === 'confirmModal') $('#confirmModal').hidden = true; });
document.addEventListener('keydown', e => { if (e.key === 'Escape') $('#confirmModal').hidden = true; });

$('#confirmSend').addEventListener('click', async () => {
  const text = broadcastText.value.trim();
  $('#confirmModal').hidden = true;
  try {
    await api('/api/broadcasts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
    broadcastText.value = '';
    charCount.textContent = '0 / 4000';
    broadcastText.dispatchEvent(new Event('input'));
    toast('أُضيفت الإذاعة للطابور — سيبدأ الإرسال فوراً');
    loadBroadcasts();
    pollBroadcasts();
  } catch (err) {
    toast(err.message || 'تعذر إرسال الإذاعة', 'error');
  }
});

async function loadBroadcasts() {
  try {
    const list = await api('/api/broadcasts');
    const host = $('#broadcastList');
    if (!list.length) { host.innerHTML = '<div class="empty-state">لا توجد إذاعات بعد — أرسل أول رسالة 📣</div>'; return; }
    host.innerHTML = list.map(b => {
      const pct = b.total ? Math.min(100, Math.round(((b.sent + b.failed) / b.total) * 100)) : (b.status === 'done' ? 100 : 0);
      const statusMap = { pending: ['bc-pending', '⏳ بانتظار البوت'], sending: ['bc-sending', '🚀 جارية الآن'], done: ['bc-done', '✅ اكتملت'] };
      const [cls, label] = statusMap[b.status] || statusMap.pending;
      return `
        <div class="bc-item">
          <div class="bc-top"><span class="bc-status ${cls}">${label}</span><span class="bc-meta" style="justify-content:flex-end">#${b.id} · ${esc(fmtDateTime(b.created_at))}</span></div>
          <div class="bc-text">${esc(b.text)}</div>
          <div class="bc-progress"><div class="bc-fill" style="width:${pct}%"></div></div>
          <div class="bc-meta"><span>✅ ${fmtNum(b.sent)} وصلت · ❌ ${fmtNum(b.failed)} تعذرت</span><span>${fmtNum(b.sent + b.failed)} / ${fmtNum(b.total)} (${pct}%)</span></div>
        </div>`;
    }).join('');
    return list;
  } catch {
    $('#broadcastList').innerHTML = '<div class="empty-state">تعذر تحميل سجل الإذاعات</div>';
    return [];
  }
}

let pollTimer = null;
function pollBroadcasts() {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    const list = await loadBroadcasts();
    if (!list || !list.some(b => b.status !== 'done')) clearInterval(pollTimer);
  }, 3000);
}

/* ═══════════ تبويب الإعدادات ═══════════ */
async function loadConfig() {
  try {
    const c = await api('/api/config');
    const rows = [
      ['إصدار البوت', `<span class="cfg-val">v${esc(c.version)}</span>`],
      ['توكن تيليجرام (BOT_TOKEN)', c.bot_token_configured ? '<span class="cfg-ok">مُضبط ✔</span>' : '<span class="cfg-bad">غير مُضبط ✗ — أضفه في .env</span>'],
      ['👑 المالك', `<span class="cfg-val">ID ${esc(c.owner_id)} — صلاحية كاملة</span>`],
      ['🛡 المشرفون', `<span class="cfg-val">${fmtNum(c.admin_count)} إجمالاً (${c.admins_env} من .env + ${c.admins_db} من داخل البوت)</span>`],
      ['أقصى حجم للملف المرسل', c.local_api_mode ? `<span class="cfg-ok">${c.max_file_size_mb} م.بايت — خادم Bot API محلي 🚀</span>` : `<span class="cfg-val">${c.max_file_size_mb} م.بايت — حد API العام (فعّل TELEGRAM_LOCAL_API لدعم حتى 2000)</span>`],
      ['الحد اليومي لكل مستخدم', c.daily_download_limit > 0 ? `<span class="cfg-val">${c.daily_download_limit} تحميل / يوم</span>` : '<span class="cfg-ok">بلا حدود ∞</span>'],
      ['الفاصل بين الطلبات', c.request_cooldown_seconds > 0 ? `<span class="cfg-val">${c.request_cooldown_seconds} ثانية</span>` : '<span class="cfg-ok">بلا فاصل ∞</span>'],
      ['حماية لوحة التحكم', c.dashboard_protected ? '<span class="cfg-ok">مفعلة بكلمة مرور 🔐</span>' : '<span class="cfg-bad">مفتوحة — عيّن DASHBOARD_PASSWORD للنشر</span>'],
      ['قاعدة البيانات', `<span class="cfg-val">${esc(c.database)} (SQLite مشتركة)</span>`],
    ];
    $('#configList').innerHTML = rows.map(([k, v]) => `<li class="config-row"><span class="cfg-key">${k}</span>${v}</li>`).join('');
  } catch {
    $('#configList').innerHTML = '<li class="config-row"><span class="cfg-bad">تعذر تحميل الإعدادات</span></li>';
  }
}

/* ═══════════ ساعة الهاتف ═══════════ */
function tickPhoneClock() {
  const el = $('#phoneClock');
  if (el) el.textContent = new Date().toLocaleTimeString('ar', { hour: '2-digit', minute: '2-digit' });
}
setInterval(tickPhoneClock, 20000);
tickPhoneClock();

/* ═════════════════════════════════════════════════
   معاينة البوت — محاكاة المحادثة التفاعلية
   ═════════════════════════════════════════════════ */
const tgChat = $('#tgChat');
const tgForm = $('#tgForm');
const tgInput = $('#tgInput');
const wait = ms => new Promise(r => setTimeout(r, ms));
const nowTime = () => new Date().toLocaleTimeString('ar', { hour: '2-digit', minute: '2-digit' });

const SAMPLES = {
  youtube: { match: /(youtube\.com|youtu\.be)/i, url: 'https://www.youtube.com/watch?v=AmrDiabNorElAin', platform: 'youtube', thumb: 'thumb-youtube', emoji: '▶️', title: 'عمرو دياب | نور العين (Official Video)', uploader: 'Amr Diab Official', duration: '03:48', views: '128.4 مليون مشاهدة', size: '24.6 م.بايت', sizeMp4: '24.6 م.بايت', sizeMp3: '5.5 م.بايت' },
  tiktok: { match: /tiktok\.com|vm\.tiktok/i, url: 'https://www.tiktok.com/@viraltrends/video/7301284756102936834', platform: 'tiktok', thumb: 'thumb-tiktok', emoji: '🎵', title: 'ترند الرقصة الأخيرة 😱🔥 — بدون علامة مائية', uploader: '@viraltrends', duration: '00:27', views: '4.2 مليون مشاهدة', size: '8.3 م.بايت', sizeMp4: '8.3 م.بايت', sizeMp3: '1.1 م.بايت' },
  spotify: { match: /spotify\.(com|link)/i, url: 'https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC', platform: 'spotify', thumb: 'thumb-spotify', emoji: '🟢', title: 'فيروز | نسم علينا الهوى', uploader: 'Fairuz · فيروز', duration: '04:12', views: 'أغنية · سبوتيفاي', audioOnly: true, sizeMp3: '6.1 م.بايت' },
  anghami: { match: /anghami/i, url: 'https://play.anghami.com/song/19049519', platform: 'anghami', thumb: 'thumb-anghami', emoji: '🟣', title: 'أم كلثوم | الأطلال', uploader: 'أم كلثوم · Anghami', duration: '10:24', views: 'أغنية · أنجامي', audioOnly: true, sizeMp3: '15.0 م.بايت' },
};

const FALLBACK_SAMPLE = { platform: 'generic', thumb: 'thumb-generic', emoji: '🔗', title: 'مقطع من الرابط الذي أرسلته', uploader: '—', duration: '—:—', views: 'فيديو عام', sizeMp4: '18.4 م.بايت', sizeMp3: '4.2 م.بايت' };

function appendMsg(kind, html) {
  const div = document.createElement('div');
  div.className = `msg ${kind}`;
  div.innerHTML = `${html}<span class="msg-time">${nowTime()}</span>`;
  tgChat.appendChild(div);
  scrollChat();
  return div;
}
const scrollChat = () => { tgChat.scrollTop = tgChat.scrollHeight; };

function appendTyping() {
  const div = document.createElement('div');
  div.className = 'typing';
  div.innerHTML = '<span></span><span></span><span></span>';
  tgChat.appendChild(div);
  scrollChat();
  return div;
}

function resetChat() {
  tgChat.innerHTML = '';
  const dateChip = document.createElement('div');
  dateChip.className = 'tg-date';
  dateChip.textContent = 'اليوم';
  tgChat.appendChild(dateChip);
  appendMsg('bot', '🎬🎧 <b>أهلاً بيك في بوت تحميل الفيديوهات والأغاني!</b><br><br>📎 أرسل أي رابط (يوتيوب، تيك توك، إنستجرام، فيسبوك، إكس، سبوتيفاي، أنجامي)…');
}

function findSample(url) {
  for (const s of Object.values(SAMPLES)) if (s.match.test(url)) return s;
  return { ...FALLBACK_SAMPLE, url };
}

let simBusy = false;

async function simulateFlow(rawUrl) {
  if (simBusy) return;
  simBusy = true;
  tgInput.value = '';

  const url = rawUrl.trim();
  const sample = findSample(url);
  appendMsg('user', esc(url.length > 120 ? url.slice(0, 120) + '…' : url));

  const typing1 = appendTyping();
  await wait(950);
  typing1.remove();

  const analyzing = appendMsg('bot', sample.audioOnly ? '🎶 جاري قراءة بيانات الأغنية…' : '🔍 جاري تحليل الرابط… ثوانٍ فقط');
  await wait(1150);
  analyzing.remove();

  // فقاعة المعاينة الحية + الأزرار المضمّنة
  const audioOnly = !!sample.audioOnly;
  const mp4Row = audioOnly ? '' : `
    <button data-q="360p" data-kind="mp4">🎬 360p</button>
    <button data-q="720p" data-kind="mp4">🎬 720p</button>
    <button data-q="1080p" data-kind="mp4">🎬 1080p</button>
    <button data-q="max" data-kind="mp4" style="grid-column: span 3">🚀 بلا حدود — أفضل جودة على الإطلاق</button>`;
  const kb = `
    <div class="inline-kb" role="group" aria-label="خيارات الجودة">
      ${mp4Row}
      <button data-q="128k" data-kind="mp3">🎧 128k</button>
      <button data-q="192k" data-kind="mp3">🎧 192k</button>
      <button data-q="320k" data-kind="mp3">🎧 320k</button>
      <button class="kb-cancel" data-kind="cancel">❌ إلغاء</button>
    </div>`;

  const preview = appendMsg('bot', `
    <div class="media-card">
      <div class="media-thumb ${esc(sample.thumb)}">${sample.emoji}<span class="media-duration">${esc(sample.duration)}</span></div>
      <div class="media-body">
        <div class="media-title">${esc(sample.title)}</div>
        <div class="media-meta"><span>👤 ${esc(sample.uploader)}</span><span>👁 ${esc(sample.views)}</span></div>
        <div style="font-size:11px;color:#c4b5fd;font-weight:700">👇 اختار الصيغة والجودة:</div>
        ${kb}
      </div>
    </div>`);

  // أزرار الجودة
  preview.addEventListener('click', async e => {
    const btn = e.target.closest('button[data-kind]');
    if (!btn || simBusy === 'done') return;
    const kind = btn.dataset.kind;
    if (kind === 'cancel') {
      preview.querySelectorAll('button').forEach(b => { b.disabled = true; });
      appendMsg('bot', '❌ تم الإلغاء.');
      return;
    }
    const quality = btn.dataset.q;
    preview.querySelectorAll('button').forEach(b => { b.disabled = true; });
    await runDownloadSimulation(sample, kind, quality);
  }, { once: false });

  simBusy = false;
}

async function runDownloadSimulation(sample, kind, quality) {
  const isMp3 = kind === 'mp3';
  const progressMsg = appendMsg('bot', `
    <div class="dl-progress">
      <b>${isMp3 ? '🎧' : '🎬'} جاري ${isMp3 ? 'استخراج الصوت' : 'التحميل'}…</b>
      <div class="dl-bar"><div class="dl-fill"></div></div>
      <div class="dl-stage">⬇️ الاتصال بالمنصة… 0%</div>
    </div>`);
  const fill = progressMsg.querySelector('.dl-fill');
  const stage = progressMsg.querySelector('.dl-stage');

  const stages = isMp3
    ? [[0, 45, '⬇️ جاري تحميل الصوت من يوتيوب…'], [45, 78, `🎚 استخراج MP3 بجودة ${quality}…`], [78, 100, '⬆️ الرفع إلى تيليجرام…']]
    : [[0, 50, `⬇️ جاري تحميل الفيديو بجودة ${quality}…`], [50, 82, '🎬 تجهيز ملف MP4 للبث…'], [82, 100, '⬆️ الرفع إلى تيليجرام…']];

  let pct = 0;
  while (pct < 100) {
    await wait(45);
    pct = Math.min(100, pct + Math.random() * 4.2 + 1.2);
    fill.style.width = `${pct}%`;
    const [, , text] = stages.find(([a, b]) => pct <= b) || stages[stages.length - 1];
    stage.textContent = `${text} ${Math.round(pct)}%`;
  }
  stage.textContent = '✅ اكتمل!';
  await wait(420);
  progressMsg.remove();

  const size = isMp3 ? (sample.sizeMp3 || '5.2 م.بايت') : (sample.sizeMp4 || sample.size || '18.6 م.بايت');
  const ext = isMp3 ? 'mp3' : 'mp4';
  const icon = isMp3 ? '🎧' : '🎬';
  const caption = `${icon} <b>${esc(sample.title)}</b><br>${isMp3 ? `🎚 الجودة: MP3 · ${esc(quality)}` : `📹 الجودة: MP4 · ${esc(quality)}`}<br><br>✅ تم التحميل بنجاح! بالهنا والشفا 🌟`;

  const finalMsg = appendMsg('bot', `${caption}
    <div class="file-card">
      <div class="file-icon">${icon}</div>
      <div class="file-meta">
        <div class="file-name">${esc(sample.title.slice(0, 46))}.${ext}</div>
        <div class="file-sub">${size} · ${esc(quality)} · ${isMp3 ? 'صوت عالي الجودة' : 'بث مباشر متاح ▶️'}</div>
      </div>
      ${isMp3 ? `<button class="play-btn" aria-label="تشغيل">▶</button>` : ''}
    </div>
    ${isMp3 ? `<div class="player"><div class="wave">${'<i></i>'.repeat(26)}</div><div class="player-row"><span class="player-time">0:00 / ${esc(sample.duration === '—:—' ? '3:30' : sample.duration)}</span><span class="player-time" style="margin-inline-start:auto">MP3 · ${esc(quality)}</span></div></div>` : ''}`);

  if (isMp3) wirePlayer(finalMsg);
  toast('اكتمل التحميل التجريبي بنجاح');
}

/* مشغّل صوتي WebAudio — يعزف لحناً قصيراً تجريبياً */
let audioCtx = null;
function chime() {
  audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
  const t0 = audioCtx.currentTime;
  const notes = [659.25, 987.77, 1318.51];
  notes.forEach((freq, i) => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'triangle';
    osc.frequency.value = freq;
    const start = t0 + i * 0.22;
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.22, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.9);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start(start);
    osc.stop(start + 1);
  });
}

function wirePlayer(container) {
  const btn = container.querySelector('.play-btn');
  const player = container.querySelector('.player');
  if (!btn || !player) return;
  let playing = false;
  let stopTimer = null;
  btn.addEventListener('click', () => {
    playing = !playing;
    player.classList.toggle('playing', playing);
    btn.textContent = playing ? '⏸' : '▶';
    if (playing) {
      chime();
      clearTimeout(stopTimer);
      stopTimer = setTimeout(() => { player.classList.remove('playing'); btn.textContent = '▶'; playing = false; }, 4200);
    } else {
      clearTimeout(stopTimer);
    }
  });
}

$$('.sample-chip').forEach(chip => chip.addEventListener('click', () => {
  const s = SAMPLES[chip.dataset.sample];
  if (s) simulateFlow(s.url);
}));

tgForm.addEventListener('submit', e => {
  e.preventDefault();
  const value = tgInput.value.trim();
  if (!value) return;
  if (!/https?:\/\//i.test(value)) { toast('الصق رابطاً يبدأ بـ http أو https', 'error'); return; }
  simulateFlow(value);
});

$('#clearChatBtn').addEventListener('click', resetChat);
resetChat();

/* ═══════════ تشغيل أولي ═══════════ */
loadOverview();
