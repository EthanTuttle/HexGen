// Text editing for the story and character pages.
// The formatted editor shows markdown as finished text (chapters as headings, links as
// chips) and writes markdown back. The raw markdown box shares the same toolbar and picker.
'use strict';

// ---------- markdown -> html ----------
function escHtml(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function linkInfo(href) {
  let m = /^\.\.\/scenes\/([^)\s]+)\.json$/.exec(href);
  if (m) return { kind: 'scenes', target: m[1] };
  m = /^\.\.\/characters\/([^)\s]+)\.md$/.exec(href);
  if (m) return { kind: 'characters', target: decName(m[1]) };
  return { kind: 'doc', target: href };
}
function chipClass(href) {
  const li = linkInfo(href);
  const missing = (li.kind === 'scenes' && !S.scenes[li.target]) || (li.kind === 'characters' && !S.chars[li.target]);
  return 'chip-link ' + li.kind + (missing ? ' todo' : '');
}
function chipTitle(href) {
  const li = linkInfo(href);
  if (li.kind === 'doc') return 'Link to ' + decName(href);
  return chipClass(href).includes('todo') ? (li.kind === 'scenes' ? 'Not written yet: click to create' : 'No character file with this name') : 'Click to open';
}
function chipHtml(label, href) {
  return `<a class="${chipClass(href)}" contenteditable="false" data-href="${escHtml(href)}" title="${escHtml(chipTitle(href))}">${escHtml(label)}</a>`;
}
function inlineToHtml(md) {
  const chips = [];
  let s = md.replace(/\[([^\]\n]+)\]\(([^)\s]+)\)/g, (_, label, href) => { chips.push(chipHtml(label, href)); return '\u0000' + (chips.length - 1) + '\u0000'; });
  s = escHtml(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<i>$2</i>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => chips[+i]);
}
const RAW_LINE = /^\s*(\||```)/;          // tables and code stay as typed
const LIST_LINE = /^(\s*)- (.*)$/;
function mdToHtml(md) {
  const lines = md.replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    const hm = /^(#{1,3}) (.*)$/.exec(l);
    if (hm) { out.push(`<h${hm[1].length}>${inlineToHtml(hm[2])}</h${hm[1].length}>`); i++; continue; }
    if (LIST_LINE.test(l)) {
      const items = [];
      while (i < lines.length && LIST_LINE.test(lines[i])) {
        const m = LIST_LINE.exec(lines[i++]);
        items.push({ d: Math.floor(m[1].length / 2), t: m[2] });
      }
      out.push(listHtml(items));
      continue;
    }
    if (RAW_LINE.test(l)) {
      const raw = [];
      while (i < lines.length && lines[i].trim() && RAW_LINE.test(lines[i])) raw.push(lines[i++]);
      out.push(`<pre class="md-raw">${escHtml(raw.join('\n'))}</pre>`);
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^#{1,3} /.test(lines[i]) && !LIST_LINE.test(lines[i]) && !RAW_LINE.test(lines[i])) para.push(lines[i++]);
    out.push(`<p>${para.map(inlineToHtml).join('<br>')}</p>`);
  }
  return out.join('');
}
function listHtml(items) {
  let html = '', depth = -1;
  for (const it of items) {
    const d = Math.min(it.d, depth + 1);
    if (d > depth) { html += '<ul>'; depth = d; }
    else { html += '</li>'; while (depth > d) { html += '</ul></li>'; depth--; } }
    html += '<li>' + inlineToHtml(it.t);
  }
  html += '</li>';
  while (depth > 0) { html += '</ul></li>'; depth--; }
  return html + '</ul>';
}

// ---------- html -> markdown ----------
function wrapMark(t, m) {
  const core = t.trim();
  if (!core) return t;
  return /^\s*/.exec(t)[0] + m + core + m + /\s*$/.exec(t)[0];
}
function inlineMd(node) {
  let out = '';
  for (const n of node.childNodes) {
    if (n.nodeType === 3) { out += n.nodeValue.replace(/ /g, ' '); continue; }
    if (n.nodeType !== 1) continue;
    const tag = n.tagName;
    if (tag === 'BR') out += '\n';
    else if (n.classList.contains('chip-link')) out += `[${n.textContent}](${n.dataset.href})`;
    else if (tag === 'B' || tag === 'STRONG') out += wrapMark(inlineMd(n), '**');
    else if (tag === 'I' || tag === 'EM') out += wrapMark(inlineMd(n), '*');
    else if (tag === 'UL' || tag === 'OL') continue;   // handled by listMd
    else out += inlineMd(n);                            // spans, pasted links, underline…
  }
  return out;
}
function listMd(list, depth, lines) {
  for (const n of list.childNodes) {
    if (n.nodeType !== 1) continue;
    if (n.tagName === 'LI') {
      const t = inlineMd(n).replace(/\n+$/, '').replace(/\n/g, ' ');
      const nested = [...n.children].filter((c) => c.tagName === 'UL' || c.tagName === 'OL');
      if (t.trim() || !nested.length) { if (t.trim()) lines.push('  '.repeat(depth) + '- ' + t); }
      for (const c of nested) listMd(c, depth + 1, lines);
    } else if (n.tagName === 'UL' || n.tagName === 'OL') listMd(n, depth + 1, lines);
  }
}
const BLOCK_TAGS = /^(H[1-6]|UL|OL|P|DIV|PRE|BLOCKQUOTE)$/;
function htmlToMd(root) {
  const blocks = [];
  const walk = (parent) => {
    let inline = null;
    const flush = () => { if (inline !== null) { const t = inline.replace(/\n+$/, ''); if (t.trim()) blocks.push(t); inline = null; } };
    for (const n of parent.childNodes) {
      const tag = n.nodeType === 1 ? n.tagName : '';
      if (/^H[1-6]$/.test(tag)) {
        flush();
        const t = inlineMd(n).replace(/\n/g, ' ').trim();
        if (t) blocks.push('#'.repeat(Math.min(3, +tag[1])) + ' ' + t);
      } else if (tag === 'UL' || tag === 'OL') {
        flush();
        const lines = [];
        listMd(n, 0, lines);
        if (lines.length) blocks.push(lines.join('\n'));
      } else if (tag === 'PRE') {
        flush();
        const t = n.textContent.replace(/\n+$/, '');
        if (t.trim()) blocks.push(t);
      } else if (tag === 'P' || tag === 'DIV' || tag === 'BLOCKQUOTE') {
        flush();
        if ([...n.children].some((c) => BLOCK_TAGS.test(c.tagName))) walk(n);
        else { const t = inlineMd(n).replace(/\n+$/, ''); if (t.trim()) blocks.push(t); }
      } else {
        const wrap = document.createElement('span');
        wrap.append(n.cloneNode(true));
        inline = (inline || '') + inlineMd(wrap);
      }
    }
    flush();
  };
  walk(root);
  return blocks.join('\n\n');
}

// ---------- the formatted editor ----------
try { document.execCommand('defaultParagraphSeparator', false, 'p'); } catch (e) {}
function richEditor(md, onChange, opts = {}) {
  const el = h('div', {
    class: 'rich' + (opts.cls ? ' ' + opts.cls : ''), id: opts.id || null,
    contenteditable: 'true', spellcheck: 'true', 'data-placeholder': opts.placeholder || '',
  });
  el.innerHTML = mdToHtml(md);
  let last = md;
  el.classList.toggle('is-empty', !md.trim());
  // only a real edit writes markdown back, so a field nobody touches stays as it was
  el.addEventListener('input', () => {
    const out = htmlToMd(el);
    el.classList.toggle('is-empty', !out.trim());
    if (out !== last) { last = out; onChange(out); }
    if (editQuery(el)) openLinkPop(el, S.linkPop && S.linkPop.el === el ? S.linkPop.kind : null);
    else if (S.linkPop && S.linkPop.el === el) closeLinkPop();
  });
  el.addEventListener('paste', (e) => {
    e.preventDefault();
    document.execCommand('insertText', false, (e.clipboardData || window.clipboardData).getData('text/plain'));
  });
  el.addEventListener('keydown', (e) => {
    if (linkPopKeys(e, el)) return;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); startLink(el, null); }
  });
  el.addEventListener('click', (e) => {
    const a = e.target.closest('.chip-link');
    if (!a) return;
    e.preventDefault();
    const li = linkInfo(a.dataset.href);
    if (li.kind !== 'doc') followLink({ kind: li.kind, target: li.target, label: a.textContent });
  });
  el.addEventListener('focus', () => { if (opts.onFocus) opts.onFocus(el); });
  el.addEventListener('blur', () => setTimeout(() => { if (S.linkPop && S.linkPop.el === el) closeLinkPop(); }, 150));
  return el;
}
// after a scene or character is created, chips that pointed at nothing update
function refreshChips() {
  document.querySelectorAll('.rich .chip-link').forEach((a) => { a.className = chipClass(a.dataset.href); a.title = chipTitle(a.dataset.href); });
}
const isRich = (el) => el && el.tagName !== 'TEXTAREA';
function richBlock(el) {
  const sel = getSelection();
  if (!sel.rangeCount) return null;
  let n = sel.anchorNode;
  while (n && n.parentNode !== el) n = n.parentNode;
  return n && n.nodeType === 1 ? n : null;
}
function richHeading(el, level) {
  const b = richBlock(el);
  document.execCommand('formatBlock', false, b && b.tagName === 'H' + level ? 'P' : 'H' + level);
}

// ---------- raw markdown box helpers ----------
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
function mdKeys(ta) {
  ta.addEventListener('keydown', (e) => {
    if (linkPopKeys(e, ta)) return;
    if (!(e.metaKey || e.ctrlKey)) return;
    const k = e.key.toLowerCase();
    if (k === 'b') { e.preventDefault(); wrapSel(ta, '**'); }
    else if (k === 'i') { e.preventDefault(); wrapSel(ta, '*'); }
    else if (k === 'k') { e.preventDefault(); startLink(ta, null); }
  });
  ta.addEventListener('input', () => {
    if (editQuery(ta)) openLinkPop(ta, S.linkPop && S.linkPop.el === ta ? S.linkPop.kind : null);
    else if (S.linkPop && S.linkPop.el === ta) closeLinkPop();
  });
  ta.addEventListener('blur', () => setTimeout(() => { if (S.linkPop && S.linkPop.el === ta) closeLinkPop(); }, 150));
  ta.addEventListener('click', (e) => {
    if (!(e.metaKey || e.ctrlKey)) return;
    const at = ta.selectionStart;
    const l = links(ta.value).find((x) => x.index <= at && at <= x.end);
    if (l) followLink(l);
  });
}

// ---------- toolbar (works on either kind of box) ----------
function startLink(el, kind) {
  if (isRich(el)) { el.focus(); document.execCommand('insertText', false, '[['); }
  else {
    const a = el.selectionStart, b = el.selectionEnd;
    const sel = el.value.slice(a, b);
    replaceRange(el, a, b, '[[' + sel, a + 2 + sel.length);
  }
  openLinkPop(el, kind);
}
function mdToolbar(getEl, opts = {}) {
  const btn = (label, title, rich, plain, style) => h('button', {
    class: 'small', title, style: style || null,
    onmousedown: (e) => e.preventDefault(),   // keeps the caret where it was
    onclick: (e) => {
      e.preventDefault();
      const el = getEl();
      if (!el) return;
      if (isRich(el)) { if (document.activeElement !== el) el.focus(); rich(el); } else plain(el);
    },
  }, label);
  return h('div', { class: 'md-toolbar' },
    opts.chapters ? btn('Chapter', 'Start a chapter here (shows in the outline and the branch map)', (el) => richHeading(el, 2), (ta) => toggleHeading(ta, 2)) : null,
    btn('Heading', 'A smaller heading', (el) => richHeading(el, 3), (ta) => toggleHeading(ta, 3)),
    btn('B', 'Bold (⌘B)', () => document.execCommand('bold'), (ta) => wrapSel(ta, '**'), 'font-weight:700'),
    btn('I', 'Italic (⌘I)', () => document.execCommand('italic'), (ta) => wrapSel(ta, '*'), 'font-style:italic'),
    btn('• List', 'Bullet list', () => document.execCommand('insertUnorderedList'), toggleList),
    h('span', { class: 'tb-gap' }),
    btn('Link scene', 'Link a scene, or name one to write later (⌘K, or type [[)', (el) => startLink(el, 'scenes'), (ta) => startLink(ta, 'scenes')),
    btn('Link character', 'Link a character', (el) => startLink(el, 'characters'), (ta) => startLink(ta, 'characters')));
}

// ---------- [[ link picker ----------
function editQuery(el) {
  if (!isRich(el)) {
    const before = el.value.slice(0, el.selectionStart);
    const m = /\[\[([^\]\n]*)$/.exec(before);
    return m ? { q: m[1], start: el.selectionStart - m[0].length } : null;
  }
  const sel = getSelection();
  if (!sel.rangeCount) return null;
  const r = sel.getRangeAt(0);
  const node = r.startContainer;
  if (node.nodeType !== 3 || !el.contains(node)) return null;
  const m = /\[\[([^\]\n]*)$/.exec(node.nodeValue.slice(0, r.startOffset));
  return m ? { q: m[1], node, start: r.startOffset - m[0].length, end: r.startOffset } : null;
}
function caretXY(ta) {
  const cs = getComputedStyle(ta);
  const div = document.createElement('div');
  for (const p of ['fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'paddingTop', 'paddingLeft', 'paddingRight', 'borderTopWidth', 'borderLeftWidth', 'boxSizing'])
    div.style[p] = cs[p];
  div.style.cssText += ';position:absolute;visibility:hidden;white-space:pre-wrap;overflow-wrap:break-word;width:' + ta.clientWidth + 'px';
  div.textContent = ta.value.slice(0, ta.selectionStart);
  const span = document.createElement('span');
  span.textContent = '​';
  div.append(span);
  document.body.append(div);
  const r = ta.getBoundingClientRect();
  const x = r.left + span.offsetLeft - ta.scrollLeft;
  const y = r.top + span.offsetTop - ta.scrollTop + (parseFloat(cs.lineHeight) || 20);
  div.remove();
  return { x, y };
}
function caretPos(el) {
  if (!isRich(el)) return caretXY(el);
  const r = getSelection().getRangeAt(0);
  let rect = r.getClientRects()[0];
  if (!rect) rect = el.getBoundingClientRect();
  return { x: rect.left, y: rect.bottom };
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
function openLinkPop(el, kind) {
  const q = editQuery(el);
  if (!q) return closeLinkPop();
  const items = linkChoices(q.q, kind);
  const keepI = S.linkPop && S.linkPop.el === el ? S.linkPop.i : 0;
  S.linkPop = { el, kind, items, i: Math.min(keepI, Math.max(0, items.length - 1)) };
  let pop = $('#link-pop');
  if (!pop) { pop = h('div', { id: 'link-pop', class: 'link-pop' }); document.body.append(pop); }
  pop.innerHTML = '';
  pop.append(h('div', { class: 'hint', style: 'padding:3px 8px', text: kind === 'characters' ? 'Link a character' : kind === 'scenes' ? 'Link a scene (type a new name to plan one)' : 'Link a scene or character' }));
  if (!items.length) pop.append(h('div', { class: 'hint', style: 'padding:3px 8px', text: 'Type a name…' }));
  items.forEach((it, i) => pop.append(h('div', {
    class: 'pop-item' + (i === S.linkPop.i ? ' on' : ''),
    onmousedown: (e) => { e.preventDefault(); S.linkPop.i = i; pickLink(); },
  }, h('span', { text: it.label }), h('span', { class: 'sub', text: it.sub }))));
  const { x, y } = caretPos(el);
  pop.style.left = Math.max(8, Math.min(x, innerWidth - 300)) + 'px';
  pop.style.top = Math.min(y + 4, innerHeight - 260) + 'px';
  pop.classList.remove('hidden');
}
function closeLinkPop() { const p = $('#link-pop'); if (p) p.classList.add('hidden'); S.linkPop = null; }
function linkPopKeys(e, el) {
  const lp = S.linkPop;
  if (!lp || lp.el !== el || $('#link-pop').classList.contains('hidden')) return false;
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    lp.i = (lp.i + (e.key === 'ArrowDown' ? 1 : -1) + lp.items.length) % Math.max(1, lp.items.length);
    openLinkPop(el, lp.kind);
    return true;
  }
  if ((e.key === 'Enter' || e.key === 'Tab') && lp.items.length) { e.preventDefault(); pickLink(); return true; }
  if (e.key === 'Escape') { e.preventDefault(); closeLinkPop(); return true; }
  return false;
}
function pickLink() {
  const lp = S.linkPop;
  const it = lp && lp.items[lp.i];
  if (!it) return;
  let label = it.label, href;
  if (it.kind === 'characters') href = `../characters/${encName(it.label)}.md`;
  else if (it.target) href = `../scenes/${it.target}.json`;
  else {
    // a scene to write later: the link names a file that doesn't exist yet
    const taken = new Set(Object.keys(S.scenes));
    for (const f in S.story) for (const l of links(S.story[f].text)) if (l.kind === 'scenes') taken.add(l.target);
    let id = slug(it.label), n = 2;
    while (taken.has(id)) id = slug(it.label) + '-' + n++;
    href = `../scenes/${id}.json`;
  }
  const el = lp.el;
  const q = editQuery(el);
  closeLinkPop();
  if (!q) return;
  if (isRich(el)) {
    const r = document.createRange();
    r.setStart(q.node, q.start); r.setEnd(q.node, q.end);
    // placed by hand: the browser's insertHTML lifts the chip out of its paragraph
    r.deleteContents();
    const tmp = document.createElement('span');
    tmp.innerHTML = chipHtml(label, href);
    const chip = tmp.firstChild;
    r.insertNode(chip);
    const space = document.createTextNode(' ');
    chip.after(space);
    const after = document.createRange();
    after.setStart(space, 1); after.collapse(true);
    const sel = getSelection();
    sel.removeAllRanges(); sel.addRange(after);
    el.dispatchEvent(new Event('input'));
  } else {
    const text = `[${label}](${href})`;
    replaceRange(el, q.start, el.selectionStart, text, q.start + text.length);
  }
}
