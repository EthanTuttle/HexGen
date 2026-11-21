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
function storyOrder() {
  const paths = listOf('backgrounds');
  const files = Object.keys(S.story);
  const rank = (f) => (f === MAIN_FILE ? 1000 : paths.includes(f) ? paths.indexOf(f) : 500);
  return files.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
}
function chapters(text) {
  const out = [];
  const re = /^## (.+)$/gm;
  let m;
  while ((m = re.exec(text))) out.push({ title: m[1].trim(), index: m.index });
  return out;
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
      out.push({ file: f, chapter: ch ? ch.title : '(intro)', index: l.index });
    }
  }
  return out;
}
// keeps story links working after a scene or character is renamed
function relinkStory(kind, oldTarget, newTarget) {
  const from = kind === 'scenes' ? `../scenes/${oldTarget}.json)` : `../characters/${encName(oldTarget)}.md)`;
  const to = kind === 'scenes' ? `../scenes/${newTarget}.json)` : `../characters/${encName(newTarget)}.md)`;
  for (const f in S.story) if (S.story[f].text.includes(from)) {
    S.story[f].text = S.story[f].text.split(from).join(to);
    storyChanged(f);
  }
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

// ---------- markdown toolbar (story and character text) ----------
// Edits go through execCommand so the browser's own undo (⌘Z) keeps working.
function replaceRange(ta, a, b, text, selA, selB) {
  ta.focus();
  ta.setSelectionRange(a, b);
  if (!document.execCommand('insertText', false, text)) {
    ta.setRangeText(text, a, b, 'end');
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  }
  if (selA != null) ta.setSelectionRange(selA, selB == null ? selA : selB);
}
function wrapSel(ta, mark) {
  const a = ta.selectionStart, b = ta.selectionEnd, v = ta.value;
  const n = mark.length;
  if (v.slice(a - n, a) === mark && v.slice(b, b + n) === mark) {
    replaceRange(ta, a - n, b + n, v.slice(a, b), a - n, b - n);
  } else {
    const inner = v.slice(a, b) || (mark === '**' ? 'bold' : 'italic');
    replaceRange(ta, a, b, mark + inner + mark, a + n, a + n + inner.length);
  }
}
function lineBounds(v, a, b) {
  const start = v.lastIndexOf('\n', a - 1) + 1;
  let end = v.indexOf('\n', b);
  if (end < 0) end = v.length;
  return [start, end];
}
function toggleHeading(ta, level) {
  const v = ta.value;
  const [s, e] = lineBounds(v, ta.selectionStart, ta.selectionStart);
  const line = v.slice(s, e);
  const prefix = '#'.repeat(level) + ' ';
  const bare = line.replace(/^#{1,6}\s+/, '');
  const next = line.startsWith(prefix) ? bare : prefix + (bare || (level === 2 ? 'New chapter' : 'Heading'));
  // a fresh heading selects its placeholder, so typing replaces it
  if (!bare && !line.startsWith(prefix)) replaceRange(ta, s, e, next, s + prefix.length, s + next.length);
  else replaceRange(ta, s, e, next, s + next.length);
}
function toggleList(ta) {
  const v = ta.value;
  const [s, e] = lineBounds(v, ta.selectionStart, ta.selectionEnd);
  const lines = v.slice(s, e).split('\n');
  const all = lines.every((l) => /^- /.test(l) || !l.trim());
  const out = lines.map((l) => (all ? l.replace(/^- /, '') : l.trim() && !/^- /.test(l) ? '- ' + l : l)).join('\n');
  replaceRange(ta, s, e, out, s, s + out.length);
}
function startLink(ta, kind) {
  const a = ta.selectionStart, b = ta.selectionEnd;
  const sel = ta.value.slice(a, b);
  replaceRange(ta, a, b, '[[' + sel, a + 2 + sel.length);
  openLinkPop(ta, kind);
}
function mdToolbar(getTa, opts = {}) {
  const act = (fn) => (e) => { e.preventDefault(); const ta = getTa(); if (ta) fn(ta); };
  const btn = (label, title, fn, style) => h('button', { class: 'small', title, style: style || null, onmousedown: (e) => e.preventDefault(), onclick: act(fn) }, label);
  return h('div', { class: 'md-toolbar' },
    opts.chapters ? btn('Chapter', 'Start a chapter here (shows in the outline and the branch map)', (ta) => toggleHeading(ta, 2)) : null,
    btn('Heading', 'A smaller heading', (ta) => toggleHeading(ta, 3)),
    btn('B', 'Bold (⌘B)', (ta) => wrapSel(ta, '**'), 'font-weight:700'),
    btn('I', 'Italic (⌘I)', (ta) => wrapSel(ta, '*'), 'font-style:italic'),
    btn('• List', 'Bullet list', toggleList),
    h('span', { class: 'tb-gap' }),
    btn('Link scene', 'Link a scene, or name one to write later (⌘K, or type [[)', (ta) => startLink(ta, 'scenes')),
    btn('Link character', 'Link a character', (ta) => startLink(ta, 'characters')));
}
// shortcuts and the [[ picker for any textarea that uses the toolbar
function mdKeys(ta) {
  ta.addEventListener('keydown', (e) => {
    if (linkPopKeys(e, ta)) return;
    const mod = e.metaKey || e.ctrlKey;
    if (!mod) return;
    const k = e.key.toLowerCase();
    if (k === 'b') { e.preventDefault(); wrapSel(ta, '**'); }
    else if (k === 'i') { e.preventDefault(); wrapSel(ta, '*'); }
    else if (k === 'k') { e.preventDefault(); startLink(ta, null); }
  });
  ta.addEventListener('input', () => {
    const before = ta.value.slice(0, ta.selectionStart);
    if (/\[\[[^\]\n]*$/.test(before)) openLinkPop(ta, S.linkPop && S.linkPop.ta === ta ? S.linkPop.kind : null);
    else closeLinkPop();
  });
  ta.addEventListener('blur', () => setTimeout(closeLinkPop, 150));
  ta.addEventListener('click', (e) => {
    if (!(e.metaKey || e.ctrlKey)) return;
    const at = ta.selectionStart;
    const l = links(ta.value).find((x) => x.index <= at && at <= x.end);
    if (l) followLink(l);
  });
}

// ---------- [[ link picker ----------
function caretXY(ta) {
  const cs = getComputedStyle(ta);
  const div = document.createElement('div');
  for (const p of ['fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'paddingTop', 'paddingLeft', 'paddingRight', 'borderTopWidth', 'borderLeftWidth', 'boxSizing', 'whiteSpace', 'wordWrap', 'tabSize'])
    div.style[p] = cs[p];
  div.style.position = 'absolute'; div.style.visibility = 'hidden'; div.style.whiteSpace = 'pre-wrap'; div.style.overflowWrap = 'break-word';
  div.style.width = ta.clientWidth + 'px';
  div.textContent = ta.value.slice(0, ta.selectionStart);
  const span = document.createElement('span');
  span.textContent = '​';
  div.append(span);
  document.body.append(div);
  const r = ta.getBoundingClientRect();
  const x = r.left + span.offsetLeft - ta.scrollLeft;
  const y = r.top + span.offsetTop - ta.scrollTop + parseFloat(cs.lineHeight || 20);
  div.remove();
  return { x, y };
}
function linkChoices(q, kind) {
  const ql = q.toLowerCase().trim();
  const out = [];
  if (kind !== 'characters') {
    for (const sc of Object.values(S.scenes)) if (!ql || (sc.title || sc.id).toLowerCase().includes(ql))
      out.push({ kind: 'scenes', label: sc.title || sc.id, sub: 'scene', target: sc.id });
  }
  if (kind !== 'scenes') {
    for (const c of Object.values(S.chars)) if (!ql || c.name.toLowerCase().includes(ql))
      out.push({ kind: 'characters', label: c.name, sub: 'character', target: c.name });
  }
  out.sort((a, b) => a.label.localeCompare(b.label));
  const exact = Object.values(S.scenes).some((sc) => (sc.title || '').toLowerCase() === ql);
  if (ql && kind !== 'characters' && !exact) out.push({ kind: 'scenes', label: q.trim(), sub: 'new scene to write', target: null });
  return out.slice(0, 40);
}
function openLinkPop(ta, kind) {
  const before = ta.value.slice(0, ta.selectionStart);
  const m = /\[\[([^\]\n]*)$/.exec(before);
  if (!m) return closeLinkPop();
  const items = linkChoices(m[1], kind);
  S.linkPop = { ta, kind, start: ta.selectionStart - m[0].length, items, i: Math.min((S.linkPop && S.linkPop.i) || 0, Math.max(0, items.length - 1)) };
  let pop = $('#link-pop');
  if (!pop) { pop = h('div', { id: 'link-pop', class: 'link-pop' }); document.body.append(pop); }
  pop.innerHTML = '';
  pop.append(h('div', { class: 'hint', style: 'padding:3px 8px', text: kind === 'characters' ? 'Link a character' : kind === 'scenes' ? 'Link a scene (type a new name to plan one)' : 'Link a scene or character' }));
  if (!items.length) pop.append(h('div', { class: 'hint', style: 'padding:3px 8px', text: 'Type a name…' }));
  items.forEach((it, i) => pop.append(h('div', {
    class: 'pop-item' + (i === S.linkPop.i ? ' on' : ''),
    onmousedown: (e) => { e.preventDefault(); S.linkPop.i = i; pickLink(); },
  }, h('span', { text: it.label }), h('span', { class: 'sub', text: it.sub }))));
  const { x, y } = caretXY(ta);
  pop.style.left = Math.min(x, innerWidth - 300) + 'px';
  pop.style.top = Math.min(y + 4, innerHeight - 260) + 'px';
  pop.classList.remove('hidden');
}
function closeLinkPop() { const p = $('#link-pop'); if (p) p.classList.add('hidden'); S.linkPop = null; }
function linkPopKeys(e, ta) {
  const lp = S.linkPop;
  if (!lp || lp.ta !== ta || $('#link-pop').classList.contains('hidden')) return false;
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    lp.i = (lp.i + (e.key === 'ArrowDown' ? 1 : -1) + lp.items.length) % Math.max(1, lp.items.length);
    openLinkPop(ta, lp.kind);
    return true;
  }
  if (e.key === 'Enter' || e.key === 'Tab') { if (lp.items.length) { e.preventDefault(); pickLink(); return true; } }
  if (e.key === 'Escape') { e.preventDefault(); closeLinkPop(); return true; }
  return false;
}
function pickLink() {
  const lp = S.linkPop;
  const it = lp.items[lp.i];
  if (!it) return;
  let text;
  if (it.kind === 'characters') text = charLink(it.label);
  else if (it.target) text = sceneLink(it.label, it.target);
  else {
    // a scene to write later: the link names a file that doesn't exist yet
    const taken = new Set(Object.keys(S.scenes));
    for (const f in S.story) for (const l of links(S.story[f].text)) if (l.kind === 'scenes') taken.add(l.target);
    let id = slug(it.label), n = 2;
    while (taken.has(id)) id = slug(it.label) + '-' + n++;
    text = sceneLink(it.label, id);
  }
  const ta = lp.ta;
  closeLinkPop();
  replaceRange(ta, lp.start, ta.selectionStart, text, lp.start + text.length);
}
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
  if (open) goToNode(id); else { renderStorySide(); if (S.storyView === 'read') renderStoryPage(); }
}

// ---------- story tab ----------
function openStory(file, index) {
  S.scur = file;
  try { localStorage.setItem('se-story', file); } catch (e) {}
  renderStoryList();
  renderStoryPage();
  if (index != null && file !== '__map') jumpTo(index);
}
function jumpTo(index) {
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
    const group = f === MAIN_FILE ? 'Campaign' : paths.includes(f) ? 'Background paths' : 'Other';
    if (group !== head) { box.append(h('div', { class: 'group-head', text: group })); head = group; }
    const chs = chapters(S.story[f].text);
    box.append(h('div', { class: 'scene-item' + (f === S.scur ? ' active' : ''), onclick: () => openStory(f) },
      h('div', { text: f }), h('div', { class: 'sub', text: chs.length + (chs.length === 1 ? ' chapter' : ' chapters') })));
    if (f === S.scur) for (const c of chs)
      box.append(h('div', { class: 'outline-item', title: 'Jump to this chapter', onclick: () => jumpTo(c.index) }, c.title));
  }
}
// ---------- read view: the markdown shown as finished text ----------
function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function inlineMd(text) {
  const parts = [];
  let last = 0, m;
  const re = /\[([^\]\n]+)\]\(([^)\s]+)\)/g;
  while ((m = re.exec(text))) {
    parts.push(fmt(text.slice(last, m.index)));
    const l = links(m[0])[0];
    if (l) {
      const exists = l.kind === 'scenes' ? !!S.scenes[l.target] : !!S.chars[l.target];
      const cls = 'chip-link ' + l.kind + (exists ? '' : ' todo');
      parts.push(`<a class="${cls}" data-kind="${l.kind}" data-target="${esc(l.target)}" data-label="${esc(l.label)}" title="${exists ? 'Open' : 'Not written yet: click to create'}">${fmt(l.label)}</a>`);
    } else parts.push(`<span class="doc-link">${fmt(m[1])}</span>`);
    last = m.index + m[0].length;
  }
  parts.push(fmt(text.slice(last)));
  return parts.join('');
}
function fmt(s) {
  return esc(s).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<i>$2</i>');
}
function renderRead(text) {
  const out = h('div', { class: 'story-read' });
  const lines = text.split('\n');
  let i = 0, offset = 0;
  const offs = [];
  for (const l of lines) { offs.push(offset); offset += l.length + 1; }
  while (i < lines.length) {
    const line = lines[i];
    const at = offs[i];
    let el = null;
    const hm = /^(#{1,3}) (.*)$/.exec(line);
    if (!line.trim()) { i++; continue; }
    if (hm) { el = document.createElement('h' + hm[1].length); el.innerHTML = inlineMd(hm[2]); i++; }
    else if (/^\s*- /.test(line)) {
      el = document.createElement('ul');
      while (i < lines.length && /^\s*- /.test(lines[i])) {
        const li = document.createElement('li');
        li.innerHTML = inlineMd(lines[i].replace(/^\s*- /, ''));
        li.dataset.at = offs[i];
        el.append(li); i++;
      }
    } else {
      const para = [];
      while (i < lines.length && lines[i].trim() && !/^(#{1,3} |\s*- )/.test(lines[i])) para.push(lines[i++]);
      el = document.createElement('p'); el.innerHTML = inlineMd(para.join(' '));
    }
    el.dataset.at = el.dataset.at || at;
    out.append(el);
  }
  out.addEventListener('click', (e) => {
    const a = e.target.closest('.chip-link');
    if (a) { followLink({ kind: a.dataset.kind, target: a.dataset.target, label: a.dataset.label }); return; }
    // clicking the text switches to Write at that spot
    const blk = e.target.closest('[data-at]');
    if (blk) { S.storyView = 'write'; renderStoryPage(); jumpTo(+blk.dataset.at); }
  });
  return out;
}

function renderStoryPage() {
  const page = $('#story-page');
  page.innerHTML = '';
  if (S.scur === '__map' || !S.story[S.scur]) { renderBranchMap(page); renderStorySide(); return; }
  const f = S.scur;
  const viewTabs = h('div', { class: 'mode-tabs view-tabs' }, ['write', 'read'].map((v) => h('button', {
    class: S.storyView === v ? 'active' : '', text: v === 'write' ? 'Write' : 'Read',
    onclick: () => { S.storyView = v; try { localStorage.setItem('se-storyview', v); } catch (e) {} renderStoryPage(); },
  })));
  if (S.storyView === 'read') {
    page.append(h('div', { class: 'story-head' }, h('h2', { text: f === MAIN_FILE ? 'Main campaign' : f + ' path' }), viewTabs,
      h('span', { class: 'hint', text: 'Click a link to open it, or any text to edit it' })), renderRead(S.story[f].text));
    renderStorySide();
    return;
  }
  const ta = h('textarea', {
    id: 'story-text', class: 'story-text', spellcheck: 'true', value: S.story[f].text,
    placeholder: 'Write the story here. Start a chapter with the Chapter button; link scenes and characters with the link buttons or by typing [[.',
    oninput: (e) => {
      S.story[f].text = e.target.value;
      storyChanged(f);
      clearTimeout(S.storyRender);
      S.storyRender = setTimeout(() => { renderStoryList(); renderStorySide(); }, 300);
    },
  });
  mdKeys(ta);
  page.append(h('div', { class: 'story-head' },
    h('h2', { text: f === MAIN_FILE ? 'Main campaign' : f + ' path' }), viewTabs,
    h('span', { class: 'hint', text: '⌘-click a link to open it' })),
  mdToolbar(() => $('#story-text'), { chapters: true }), ta);
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
        h('div', {}, h('span', { text: l.label }), ' ', h('span', { class: 'status-badge ' + (exists ? 'approved' : 'draft'), text: tag })),
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
    canvas.append(h('div', { class: 'map-lane', style: `top:${y}px;height:${BH}px;width:${LABEL - 10}px`, text: p, onclick: () => openStory(p) }));
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
  S.story = {}; S.sdirty = new Set(); S.scur = '__map'; S.storyView = 'write';
  try { S.storyView = localStorage.getItem('se-storyview') || 'write'; } catch (e) {}
  try { for (const f of await api('GET', 'story')) S.story[f.file] = { file: f.file, text: f.text }; } catch (e) {}
  try { const f = localStorage.getItem('se-story'); if (f && (f === '__map' || S.story[f])) S.scur = f; } catch (e) {}
}
boot();
