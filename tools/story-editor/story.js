// Story: the campaign outline in design/story/<Path>.md and Main campaign.md.
// Each "## " heading is a chapter. Links are plain markdown:
//   scenes      [Title](../scenes/<id>.json)    (a missing file means "to write")
//   characters  [Name](../characters/<Name>.md)
'use strict';

const MAIN_FILE = 'Main campaign';
const LINK_RE = /\[([^\]\n]+)\]\(\.\.\/(scenes|characters)\/([^)\s]+)\)/g;
const encName = (n) => n.replace(/%/g, '%25').replace(/ /g, '%20').replace(/'/g, '%27').replace(/\(/g, '%28').replace(/\)/g, '%29');
function decName(s) { try { return decodeURIComponent(s); } catch (e) { return s; } }
const sceneLink = (title, id) => `[${title}](../scenes/${id}.json)`;
const charLink = (name) => `[${name}](../characters/${encName(name)}.md)`;

// ---------- model ----------
// 'Soldier path' for a background, the file's own name for anything else
const storyLabel = (f) => (listOf('backgrounds').includes(f) ? f + ' path' : f);
function storyOrder() {
  const paths = listOf('backgrounds');
  const files = Object.keys(S.story);
  const rank = (f) => (paths.includes(f) ? paths.indexOf(f) : f === MAIN_FILE ? 100 : 500);
  return files.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
}
function chapters(text) {
  const out = [];
  const re = /^## (.+)$/gm;
  let m;
  while ((m = re.exec(text))) out.push({ title: m[1].trim(), index: m.index });
  return out;
}
// the intro (text above the first chapter, minus the # title) is the file's summary
function summaryOf(text) {
  const chs = chapters(text);
  const intro = (chs.length ? text.slice(0, chs[0].index) : text).replace(/^# .*$/m, '').trim();
  return intro.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/\*\*?/g, '');
}
function chapterAt(chs, index) {
  let cur = null;
  for (const c of chs) if (c.index <= index) cur = c;
  return cur;
}
function links(text) {
  const out = [];
  let m;
  LINK_RE.lastIndex = 0;
  while ((m = LINK_RE.exec(text))) {
    const target = m[2] === 'scenes' ? m[3].replace(/\.json$/, '') : decName(m[3].replace(/\.md$/, ''));
    out.push({ label: m[1], kind: m[2], target, index: m.index, end: m.index + m[0].length });
  }
  return out;
}
// every story link to one scene or character, for back-links
function storyRefs(kind, target) {
  const out = [];
  for (const f of storyOrder()) {
    const text = S.story[f].text;
    const chs = chapters(text);
    for (const l of links(text)) if (l.kind === kind && l.target === target) {
      const ch = chapterAt(chs, l.index);
      const chapter = ch ? ch.title : '(intro)';
      // one entry per chapter, however often it links
      if (!out.some((r) => r.file === f && r.chapter === chapter)) out.push({ file: f, chapter, index: l.index });
    }
  }
  return out;
}
// keeps story links working after a scene or character is renamed
// the name a link should show: the character's name or the scene's current title
function linkLabel(kind, target, fallback) {
  if (kind === 'characters' && S.chars[target]) return S.chars[target].name;
  if (kind === 'scenes' && S.scenes[target]) return S.scenes[target].title || fallback;
  return fallback;
}
// rewrites every link to one scene or character: where it points and the name it shows
function relinkText(text, kind, oldTarget, newTarget, newLabel) {
  const re = /\[([^\]\n]+)\]\(\.\.\/(scenes|characters)\/([^)\s]+)\)/g;
  return text.replace(re, (all, label, k, path) => {
    if (k !== kind) return all;
    const t = k === 'scenes' ? path.replace(/\.json$/, '') : decName(path.replace(/\.md$/, ''));
    if (t !== oldTarget) return all;
    return k === 'scenes' ? `[${newLabel}](../scenes/${newTarget}.json)` : `[${newLabel}](../characters/${encName(newTarget)}.md)`;
  });
}
function relinkStory(kind, oldTarget, newTarget, newLabel, oldLabel) {
  for (const f in S.story) {
    const next = relinkText(S.story[f].text, kind, oldTarget, newTarget, newLabel);
    if (next !== S.story[f].text) { S.story[f].text = next; storyChanged(f); }
  }
  for (const c of Object.values(S.chars)) {
    let hit = false;
    for (const s of c.sections) {
      const next = relinkText(s.body, kind, oldTarget, newTarget, newLabel);
      if (next !== s.body) { s.body = next; hit = true; }
    }
    if (hit) charChanged(c);
  }
  // the design docs outside the editor's folders are rewritten by the server
  api('POST', 'relink', { kind, old: oldTarget, new: newTarget, oldLabel: oldLabel || null, newLabel }).catch(() => {});
}

// ---------- saving ----------
function storyChanged(file) {
  S.sdirty.add(file);
  try { localStorage.setItem('se-sbackup-' + file, JSON.stringify({ t: Date.now(), storyFile: file, text: S.story[file].text })); } catch (e) {}
  setStatus();
  clearTimeout(S.ssaveTimer);
  S.ssaveTimer = setTimeout(saveStory, 600);
}
async function saveStory() {
  for (const file of [...S.sdirty]) {
    try {
      await api('PUT', 'story/' + encodeURIComponent(file), { text: S.story[file].text });
      S.sdirty.delete(file);
      try { localStorage.removeItem('se-sbackup-' + file); } catch (e) {}
      S.offline = false;
    } catch (e) {
      S.offline = true;
      S.ssaveTimer = setTimeout(saveStory, 3000);
      break;
    }
  }
  setStatus();
}

// ---------- following links ----------
function followLink(l) {
  if (l.kind === 'characters') { if (S.chars[l.target]) { setMode('characters'); openChar(l.target); } return; }
  if (S.scenes[l.target]) goToNode(l.target);
  else if (confirm(`"${l.label}" hasn't been written yet. Create the scene now?`)) createLinkedScene(l.target, l.label, true);
}
function createLinkedScene(id, title, open) {
  if (S.scenes[id]) return;
  const sc = { id, title, notes: '', triggers: [], start: null, nodes: {} };
  makeNode(sc, 'line', 0, 0);
  S.scenes[id] = sc;
  markDirty(id);
  if (open) goToNode(id); else { renderStorySide(); refreshChips(); }
}

// ---------- story tab ----------
function openStory(file, index) {
  S.scur = file;
  try { localStorage.setItem('se-story', file); } catch (e) {}
  renderStoryList();
  renderStoryPage();
  if (index != null && file !== '__map') jumpTo(index);
  pushNav();
}
function jumpTo(index) {
  const ed = $('#story-rich');
  if (ed) {
    const k = chapters(S.story[S.scur].text).filter((c) => c.index <= index).length - 1;
    const target = k >= 0 ? ed.querySelectorAll('h2')[k] : ed.firstElementChild;
    if (target) {
      ed.scrollTop = target.offsetTop - ed.offsetTop - 10;
      const r = document.createRange(); r.selectNodeContents(target); r.collapse(false);
      ed.focus({ preventScroll: true });
      const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
    }
    return;
  }
  const ta = $('#story-text');
  if (!ta) return;
  // measure where that line sits, then scroll the box to it
  const div = document.createElement('div');
  const cs = getComputedStyle(ta);
  for (const p of ['fontFamily', 'fontSize', 'lineHeight', 'paddingLeft', 'paddingRight', 'letterSpacing'])
    div.style[p] = cs[p];
  div.style.cssText += ';position:absolute;visibility:hidden;white-space:pre-wrap;overflow-wrap:break-word;width:' + ta.clientWidth + 'px';
  div.textContent = ta.value.slice(0, index);
  document.body.append(div);
  ta.scrollTop = Math.max(0, div.offsetHeight - 30);
  div.remove();
  ta.focus({ preventScroll: true });
  ta.setSelectionRange(index, index);
}
function renderStoryList() {
  const box = $('#story-list');
  box.innerHTML = '';
  box.append(h('div', { class: 'scene-item' + (S.scur === '__map' ? ' active' : ''), onclick: () => openStory('__map') },
    h('div', { text: 'Branch map' }), h('div', { class: 'sub', text: 'Every path into the main campaign' })));
  const paths = listOf('backgrounds');
  let head = null;
  for (const f of storyOrder()) {
    const group = f === MAIN_FILE ? 'Campaign' : paths.includes(f) ? 'Background paths' : 'Quests and more';
    if (group !== head) { box.append(h('div', { class: 'group-head', text: group })); head = group; }
    const chs = chapters(S.story[f].text);
    box.append(h('div', { class: 'scene-item' + (f === S.scur ? ' active' : ''), onclick: () => openStory(f) },
      h('div', { text: f }), h('div', { class: 'sub', text: chs.length + (chs.length === 1 ? ' chapter' : ' chapters') })));
    if (f === S.scur) for (const c of chs)
      box.append(h('div', { class: 'outline-item', title: 'Jump to this chapter', onclick: () => jumpTo(c.index) }, c.title));
  }
}
function renderStoryPage() {
  const page = $('#story-page');
  page.innerHTML = '';
  closeLinkPop();
  if (S.scur === '__map' || !S.story[S.scur]) { renderBranchMap(page); renderStorySide(); return; }
  const f = S.scur;
  const raw = S.storyView === 'markdown';
  const viewTabs = h('div', { class: 'mode-tabs view-tabs' }, [['edit', 'Formatted'], ['markdown', 'Markdown']].map(([v, label]) => h('button', {
    class: (raw ? 'markdown' : 'edit') === v ? 'active' : '', text: label,
    title: v === 'edit' ? 'Write with chapters, bold and links shown as they look' : 'The same text as raw markdown',
    onclick: () => { S.storyView = v; try { localStorage.setItem('se-storyview', v); } catch (e) {} renderStoryPage(); },
  })));
  const changed = (text) => {
    S.story[f].text = text;
    storyChanged(f);
    clearTimeout(S.storyRender);
    S.storyRender = setTimeout(() => { renderStoryList(); renderStorySide(); }, 300);
  };
  let box;
  if (raw) {
    box = h('textarea', { id: 'story-text', class: 'story-text', spellcheck: 'true', value: S.story[f].text, oninput: (e) => changed(e.target.value) });
    mdKeys(box);
  } else {
    box = richEditor(S.story[f].text, (md) => changed(md + '\n'), {
      id: 'story-rich', cls: 'story-rich',
      placeholder: 'Write the story here. Start a chapter with the Chapter button; link scenes and characters with the link buttons, ⌘K or [[.',
    });
  }
  page.append(h('div', { class: 'story-head' },
    h('h2', { text: storyLabel(f) }), viewTabs,
    h('span', { class: 'hint', text: raw ? '⌘-click a link to open it' : 'Click a link to open it' })),
  mdToolbar(() => $('#story-rich') || $('#story-text'), { chapters: true }), box);
  renderStorySide();
}
function renderStorySide() {
  const box = $('#story-side');
  box.innerHTML = '';
  const body = h('div', { class: 'used-body' });
  box.append(h('div', { class: 'tabs' }, h('button', { class: 'active', text: S.scur === '__map' ? 'To write' : 'Links in this file' })), body);
  const files = S.scur === '__map' ? storyOrder() : S.story[S.scur] ? [S.scur] : [];
  let any = false;
  for (const f of files) {
    const text = S.story[f].text;
    const chs = chapters(text);
    const ls = links(text).filter((l) => S.scur !== '__map' || (l.kind === 'scenes' && !S.scenes[l.target]));
    if (!ls.length) continue;
    any = true;
    let curCh;
    if (S.scur === '__map') body.append(h('h3', { text: f }));
    for (const l of ls) {
      const ch = chapterAt(chs, l.index);
      const chTitle = ch ? ch.title : 'Intro';
      if (S.scur !== '__map' && chTitle !== curCh) { body.append(h('h3', { text: chTitle })); curCh = chTitle; }
      const exists = l.kind === 'scenes' ? !!S.scenes[l.target] : !!S.chars[l.target];
      const tag = l.kind === 'characters' ? (exists ? 'character' : 'no such character') : exists ? 'scene' : 'to write';
      body.append(h('div', { class: 'used-line', onclick: () => { if (S.scur === '__map') openStory(f, l.index); else jumpTo(l.index); } },
        h('div', {}, h('span', { text: linkLabel(l.kind, l.target, l.label) }), ' ', h('span', { class: 'status-badge ' + (exists ? 'approved' : 'draft'), text: tag })),
        h('div', { class: 'btn-row', style: 'margin-top:4px' },
          exists ? h('button', { class: 'small', text: 'Open', onclick: (e) => { e.stopPropagation(); followLink(l); } }) : null,
          !exists && l.kind === 'scenes' ? h('button', { class: 'small primary', text: 'Create scene', onclick: (e) => { e.stopPropagation(); createLinkedScene(l.target, l.label, false); } }) : null)));
    }
  }
  if (!any) body.append(h('p', { class: 'hint', text: S.scur === '__map' ? 'No scenes waiting to be written. Name a new scene in a link (type [[ and a name) to plan one.' : 'No links yet. Use Link scene / Link character, or type [[.' }));
}

// ---------- branch map ----------
function renderBranchMap(page) {
  const paths = listOf('backgrounds').filter((p) => S.story[p]);
  const BW = 180, BH = 58, GX = 34, LANE = 78, LABEL = 110, TOP = 60;
  const stats = (f, ch, next) => {
    const ls = links(S.story[f].text).filter((l) => l.kind === 'scenes' && l.index >= ch.index && (!next || l.index < next.index));
    const todo = ls.filter((l) => !S.scenes[l.target]).length;
    const n = ls.length - todo;
    return n + (n === 1 ? ' scene' : ' scenes') + (todo ? ' · ' + todo + ' to write' : '');
  };
  const laneLen = Math.max(1, ...paths.map((p) => chapters(S.story[p].text).length));
  const gx = LABEL + laneLen * (BW + GX) + 30;
  const gy = TOP + (paths.length * LANE) / 2 - BH / 2;
  const mainChs = S.story[MAIN_FILE] ? chapters(S.story[MAIN_FILE].text) : [];
  const width = gx + 150 + Math.max(1, mainChs.length) * (BW + GX) + 40;
  const height = TOP + paths.length * LANE + 40;
  const wrap = h('div', { class: 'map-wrap' });
  const canvas = h('div', { class: 'map-canvas', style: `width:${width}px;height:${height}px` });
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('width', width); svg.setAttribute('height', height); svg.setAttribute('class', 'map-lines');
  const line = (x1, y1, x2, y2) => {
    const p = document.createElementNS(ns, 'path');
    const dx = Math.max(30, (x2 - x1) / 2);
    p.setAttribute('d', `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`);
    svg.append(p);
  };
  const box = (x, y, title, sub, onclick, cls) => canvas.append(h('div', { class: 'map-box ' + (cls || ''), style: `left:${x}px;top:${y}px;width:${BW}px;height:${BH}px`, onclick, title: 'Open' },
    h('div', { class: 'mb-title', text: title }), sub ? h('div', { class: 'mb-sub', text: sub }) : null));
  canvas.append(h('div', { class: 'map-head', style: `left:${LABEL}px`, text: 'Background paths' }));
  canvas.append(h('div', { class: 'map-head', style: `left:${gx + 150}px`, text: 'Main campaign' }));
  paths.forEach((p, i) => {
    const y = TOP + i * LANE;
    canvas.append(h('div', { class: 'map-lane', style: `top:${y}px;height:${BH}px;width:${LABEL - 10}px`, text: p, title: summaryOf(S.story[p].text) || 'No summary yet', onclick: () => openStory(p) }));
    const chs = chapters(S.story[p].text);
    let lastX = LABEL - 10;
    if (!chs.length) { box(LABEL, y, 'No chapters yet', 'Open to write', () => openStory(p), 'empty'); lastX = LABEL + BW; }
    chs.forEach((c, j) => {
      const x = LABEL + j * (BW + GX);
      if (j) line(x - GX, y + BH / 2, x, y + BH / 2);
      box(x, y, c.title, stats(p, c, chs[j + 1]), () => openStory(p, c.index));
      lastX = x + BW;
    });
    line(lastX, y + BH / 2, gx, gy + BH / 2);
  });
  canvas.append(h('div', { class: 'map-box hub', style: `left:${gx}px;top:${gy}px;width:120px;height:${BH}px` }, h('div', { class: 'mb-title', text: 'Gronogon' }), h('div', { class: 'mb-sub', text: 'the paths meet' })));
  let px = gx + 120;
  if (!mainChs.length) { line(px, gy + BH / 2, gx + 150, gy + BH / 2); box(gx + 150, gy, 'No chapters yet', 'Open to write', () => openStory(MAIN_FILE), 'empty'); }
  mainChs.forEach((c, j) => {
    const x = gx + 150 + j * (BW + GX);
    line(px, gy + BH / 2, x, gy + BH / 2);
    box(x, gy, c.title, stats(MAIN_FILE, c, mainChs[j + 1]), () => openStory(MAIN_FILE, c.index));
    px = x + BW;
  });
  canvas.prepend(svg);
  wrap.append(canvas);
  page.append(h('div', { class: 'story-head' }, h('h2', { text: 'Branch map' }),
    h('span', { class: 'hint', text: 'Each box is a chapter (a Chapter heading). Click one to write it.' })), wrap);
}

// ---------- boot ----------
async function initStory() {
  S.story = {}; S.sdirty = new Set(); S.scur = '__map'; S.storyView = 'edit';
  try { S.storyView = localStorage.getItem('se-storyview') === 'markdown' ? 'markdown' : 'edit'; } catch (e) {}
  try { for (const f of await api('GET', 'story')) S.story[f.file] = { file: f.file, text: f.text }; } catch (e) {}
  try { const f = localStorage.getItem('se-story'); if (f && (f === '__map' || S.story[f])) S.scur = f; } catch (e) {}
}
boot();
