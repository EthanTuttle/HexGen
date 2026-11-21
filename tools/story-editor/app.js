// Heads or Hexes story editor. Plain JS, no libraries, so it runs offline.
// Scene format: see design/scenes/README.md.
'use strict';

// ---------- state ----------
const S = {
  lists: {},
  scenes: {},          // id -> scene
  cur: null,           // current scene id
  sel: null,           // selected node id
  view: { x: 80, y: 80, z: 1 },
  group: 'all',
  search: '',
  tab: 'edit',
  undo: [], redo: [], lastKey: null, lastTime: 0,
  dirty: new Set(), saving: false, saveTimer: null, offline: false,
  mode: 'scenes', chars: {}, cdirty: new Set(), ccur: null, csearch: '',
};

const NODE_TYPES = {
  line:      { label: 'NPC line',    hint: 'An NPC or companion speaks a written line.' },
  narration: { label: 'Narration',   hint: 'No speaker: short, neutral, second person. Says what the party sees, never what the hero thinks.' },
  choice:    { label: 'Hero choice', hint: 'The hero picks an option. Options are intent, never the hero\'s words.' },
  branch:    { label: 'Condition',   hint: 'Splits on who the hero is or what has happened (background, class, party, flags). The player never sees it.' },
  setflag:   { label: 'Set flag',    hint: 'Remembers something for later scenes (a quest step, a past choice).' },
  end:       { label: 'End',         hint: 'The scene ends here.' },
};
const TRIGGER_KINDS = { place: 'Place', person: 'Person', encounter: 'Encounter', quest: 'Quest', other: 'Other' };
const COND_KINDS = {
  background: 'Background is', class: 'Class is', subclass: 'Subclass is', race: 'Race is',
  companion: 'In party:', nocompanion: 'Not in party:', flag: 'Flag is set:', noflag: 'Flag not set:',
};
const CHECK_TYPES = { approach: 'Social approach', proficiency: 'Proficiency', ability: 'Bare ability' };
const END_KINDS = { leave: 'Conversation ends', fight: 'A fight starts', scene: 'Go to another scene' };

// ---------- helpers ----------
const $ = (s) => document.querySelector(s);
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const k in attrs || {}) {
    const v = attrs[k];
    if (v == null || v === false) continue;
    if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k === 'value') el.value = v;
    else if (k === 'checked') el.checked = !!v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) el.append(c.nodeType ? c : document.createTextNode(c));
  return el;
}
const clone = (o) => JSON.parse(JSON.stringify(o));
const uniq = (a) => a.filter((v, i) => v && a.indexOf(v) === i);
const slug = (t) => (t || 'scene').toLowerCase().replace(/['’]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'scene';
const scene = () => S.scenes[S.cur];
const listOf = (k) => S.lists[k] || [];

async function api(method, path, body) {
  const r = await fetch('/api/' + path, {
    method, headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.statusText);
  return r.json();
}

function newId(sc, prefix) {
  let max = 0;
  const scan = (id) => { const m = /^[a-z]+(\d+)$/.exec(id || ''); if (m) max = Math.max(max, +m[1]); };
  for (const id in sc.nodes) {
    scan(id);
    for (const o of sc.nodes[id].options || []) scan(o.id);
  }
  return prefix + (max + 1);
}

// ---------- node outputs ----------
// Each output is a link slot: a key, a label and where it points.
function outputs(n) {
  switch (n.type) {
    case 'line': case 'narration': case 'setflag':
      return [{ key: 'next', label: 'Next' }];
    case 'branch':
      return [{ key: 'yes', label: 'Yes', cls: 'pass' }, { key: 'no', label: 'No', cls: 'fail' }];
    case 'choice': {
      const out = [];
      for (const o of n.options || []) {
        if (o.check) {
          out.push({ key: 'o:' + o.id + ':pass', label: 'Pass', cls: 'pass', opt: o });
          out.push({ key: 'o:' + o.id + ':fail', label: 'Fail', cls: 'fail', opt: o });
        } else out.push({ key: 'o:' + o.id + ':next', label: '', opt: o });
      }
      return out;
    }
    default: return [];
  }
}
function getLink(n, key) {
  if (key.startsWith('o:')) {
    const [, oid, slot] = key.split(':');
    const o = (n.options || []).find((x) => x.id === oid);
    return o ? o[slot] || null : null;
  }
  return n[key] || null;
}
function setLink(n, key, target) {
  if (key.startsWith('o:')) {
    const [, oid, slot] = key.split(':');
    const o = (n.options || []).find((x) => x.id === oid);
    if (o) { if (target) o[slot] = target; else delete o[slot]; }
  } else if (target) n[key] = target; else delete n[key];
}

// ---------- mutation, undo, save ----------
function mutate(fn, opts = {}) {
  const sc = scene();
  if (!sc) return;
  const now = Date.now();
  const coalesce = opts.key && opts.key === S.lastKey && now - S.lastTime < 1500;
  if (!coalesce) { S.undo.push(JSON.stringify(sc)); if (S.undo.length > 200) S.undo.shift(); S.redo = []; }
  S.lastKey = opts.key || null; S.lastTime = now;
  fn(sc);
  markDirty(sc.id);
  renderCanvas();
  renderProblems();
  if (opts.inspector !== false) renderInspector();
  if (opts.list) renderSceneList();
}
function undo(back = true) {
  const from = back ? S.undo : S.redo, to = back ? S.redo : S.undo;
  if (!from.length || !scene()) return;
  to.push(JSON.stringify(scene()));
  S.scenes[S.cur] = JSON.parse(from.pop());
  S.lastKey = null;
  if (S.sel && !scene().nodes[S.sel]) S.sel = null;
  markDirty(S.cur);
  renderAll();
}
function markDirty(id) {
  S.dirty.add(id);
  try { localStorage.setItem('se-backup-' + id, JSON.stringify({ t: Date.now(), scene: S.scenes[id] })); } catch (e) {}
  setStatus();
  clearTimeout(S.saveTimer);
  S.saveTimer = setTimeout(saveNow, 500);
}
async function saveNow() {
  if (S.saving) { S.saveTimer = setTimeout(saveNow, 300); return; }
  S.saving = true;
  for (const id of [...S.dirty]) {
    const sc = S.scenes[id];
    try {
      if (sc) await api('PUT', 'scenes/' + id, sc);
      S.dirty.delete(id);
      try { localStorage.removeItem('se-backup-' + id); } catch (e) {}
      S.offline = false;
    } catch (e) {
      S.offline = true;
      S.saveTimer = setTimeout(saveNow, 3000);
      break;
    }
  }
  S.saving = false;
  setStatus();
}
function setStatus() {
  const el = $('#save-status');
  el.classList.toggle('bad', S.offline);
  el.textContent = S.offline ? 'Not saved: start the server' : S.dirty.size || S.cdirty.size ? 'Saving…' : 'Saved';
}

// ---------- scene list ----------
function sceneText(sc) {
  const parts = [sc.title, sc.notes];
  for (const t of sc.triggers || []) parts.push(t.value);
  for (const id in sc.nodes || {}) {
    const n = sc.nodes[id];
    parts.push(n.text, n.speaker, n.stage);
    for (const o of n.options || []) parts.push(o.intent);
  }
  return parts.filter(Boolean).join(' ').toLowerCase();
}
function renderSceneList() {
  const box = $('#scene-list');
  box.innerHTML = '';
  const q = S.search.trim().toLowerCase();
  const all = Object.values(S.scenes).filter((sc) => !q || sceneText(sc).includes(q));
  const groups = new Map();
  const add = (name, sc) => { if (!groups.has(name)) groups.set(name, []); groups.get(name).push(sc); };
  for (const sc of all) {
    const tr = sc.triggers || [];
    if (S.group === 'all') add('', sc);
    else if (S.group === 'place' || S.group === 'person') {
      for (const t of tr) if (t.kind === S.group && t.value) add(t.value, sc);
      if (S.group === 'person') {
        const people = new Set(speakers(sc));
        for (const p of people) if (!tr.some((t) => t.kind === 'person' && t.value === p)) add(p, sc);
      }
    } else if (!tr.some((t) => t.kind === 'place' || t.kind === 'person')) add('', sc);
  }
  const names = [...groups.keys()].sort((a, b) => a.localeCompare(b));
  if (!names.length) box.append(h('div', { class: 'hint', style: 'padding:12px', text: q ? 'No matches.' : 'No scenes here yet.' }));
  for (const name of names) {
    if (name) box.append(h('div', { class: 'group-head', text: name }));
    for (const sc of groups.get(name).sort((a, b) => (a.title || '').localeCompare(b.title || ''))) {
      const sub = (sc.triggers || []).map((t) => t.value).filter(Boolean).join(' · ');
      box.append(h('div', {
        class: 'scene-item' + (sc.id === S.cur ? ' active' : ''),
        onclick: () => openScene(sc.id),
      }, h('div', { text: sc.title || sc.id }), sub ? h('div', { class: 'sub', text: sub }) : null));
    }
  }
}
function speakers(sc) {
  const out = new Set();
  for (const id in sc.nodes || {}) if (sc.nodes[id].type === 'line' && sc.nodes[id].speaker) out.add(sc.nodes[id].speaker);
  return [...out];
}
function openScene(id) {
  S.cur = id; S.sel = null; S.undo = []; S.redo = [];
  try { localStorage.setItem('se-last', id); } catch (e) {}
  renderAll();
  fitView();
}

// ---------- canvas ----------
function applyView() {
  $('#world').style.transform = `translate(${S.view.x}px, ${S.view.y}px) scale(${S.view.z})`;
}
function preview(text, n = 140) {
  text = (text || '').trim();
  return text.length > n ? text.slice(0, n - 1) + '…' : text;
}
function tagText(c) {
  if (!c) return '';
  return c.type === 'ability' ? c.skill : c.skill;
}
function condText(c) {
  return (COND_KINDS[c.kind] || c.kind) + ' ' + (c.value || '?');
}
function renderCanvas() {
  const sc = scene();
  const box = $('#nodes');
  box.innerHTML = '';
  $('#empty-hint').classList.toggle('hidden', !!sc);
  $('#palette').classList.toggle('hidden', !sc);
  $('#scene-title').textContent = sc ? '— ' + (sc.title || sc.id) : '';
  if (!sc) { $('#edges').innerHTML = ''; return; }
  const errNodes = new Set(problems(sc).filter((p) => p.level === 'error').map((p) => p.node));
  for (const id in sc.nodes) {
    const n = sc.nodes[id];
    const el = h('div', {
      class: `node t-${n.type}` + (id === S.sel ? ' selected' : '') + (errNodes.has(id) ? ' has-err' : ''),
      'data-id': id, style: `left:${n.x || 0}px; top:${n.y || 0}px`,
    });
    let who = '';
    if (n.type === 'line') who = n.speaker || 'no speaker';
    if (n.type === 'branch') who = n.match === 'any' ? 'any of' : 'all of';
    if (n.type === 'end') who = END_KINDS[n.outcome || 'leave'];
    el.append(h('div', { class: 'head' },
      h('span', { text: NODE_TYPES[n.type].label }),
      who ? h('span', { class: 'who', text: '· ' + who }) : null,
      sc.start === id ? h('span', { class: 'start-badge', text: 'START' }) : null));
    if (sc.start !== id) el.append(h('div', { class: 'in-port' }));

    let body = null;
    if (n.type === 'line') body = h('div', { class: 'body' }, n.stage ? h('div', { class: 'stage', text: '(' + n.stage + ')' }) : null, preview(n.text) || h('i', { text: 'empty line' }));
    else if (n.type === 'narration') body = h('div', { class: 'body' + (n.text ? '' : ' placeholder'), text: preview(n.text) || 'empty narration' });
    else if (n.type === 'branch') body = h('div', { class: 'body' + ((n.conditions || []).length ? '' : ' placeholder'), text: (n.conditions || []).map(condText).join('\n') || 'no conditions' });
    else if (n.type === 'setflag') body = h('div', { class: 'body' + ((n.flags || []).length ? '' : ' placeholder'), text: (n.flags || []).map((f) => (f.op === 'clear' ? 'clear ' : 'set ') + (f.name || '?')).join('\n') || 'no flags' });
    else if (n.type === 'end') {
      const bits = [];
      if (n.outcome === 'scene') bits.push('→ ' + ((S.scenes[n.scene] || {}).title || n.scene || '?'));
      if (n.reward) bits.push('Reward: ' + n.reward);
      if (n.notes) bits.push(n.notes);
      if (bits.length) body = h('div', { class: 'body', text: preview(bits.join('\n')) });
    } else if (n.type === 'choice' && !(n.options || []).length) body = h('div', { class: 'body placeholder', text: 'no options yet' });
    if (body) el.append(body);

    const outs = outputs(n);
    if (outs.length) {
      const wrap = h('div', { class: 'outs' });
      let lastOpt = null;
      for (const o of outs) {
        if (o.opt && o.opt !== lastOpt && o.opt.check) {
          wrap.append(optRow(o.opt, null));
        }
        lastOpt = o.opt;
        if (o.opt && !o.opt.check) wrap.append(optRow(o.opt, h('span', { class: 'port' + (getLink(n, o.key) ? ' linked' : ''), 'data-port': id + '|' + o.key })));
        else wrap.append(h('div', { class: 'out ' + (o.cls || ''), style: o.opt ? 'padding-left:20px' : '' },
          o.label, h('span', { class: 'port' + (getLink(n, o.key) ? ' linked' : ''), 'data-port': id + '|' + o.key })));
      }
      el.append(wrap);
    }
    box.append(el);
  }
  applyView();
  drawEdges();
}
function optRow(o, port) {
  return h('div', { class: 'out' },
    o.check ? h('span', { class: 'tag', text: tagText(o.check) }) : null,
    preview(o.intent, 80) || h('i', { text: 'empty option' }),
    (o.conditions || []).length ? h('div', { class: 'cond', text: 'if ' + o.conditions.map(condText).join(', ') }) : null,
    port);
}
function toWorld(cx, cy) {
  const r = $('#canvas').getBoundingClientRect();
  return { x: (cx - r.left - S.view.x) / S.view.z, y: (cy - r.top - S.view.y) / S.view.z };
}
function portPos(el) {
  const r = el.getBoundingClientRect();
  return toWorld(r.left + r.width / 2, r.top + r.height / 2);
}
function curve(a, b) {
  const dx = Math.max(40, Math.abs(b.x - a.x) * 0.5);
  return `M${a.x},${a.y} C${a.x + dx},${a.y} ${b.x - dx},${b.y} ${b.x},${b.y}`;
}
function drawEdges() {
  const svg = $('#edges');
  svg.innerHTML = '';
  const sc = scene();
  if (!sc) return;
  const ns = 'http://www.w3.org/2000/svg';
  for (const id in sc.nodes) {
    const n = sc.nodes[id];
    for (const o of outputs(n)) {
      const t = getLink(n, o.key);
      if (!t || !sc.nodes[t]) continue;
      const pe = document.querySelector(`[data-port="${id}|${o.key}"]`);
      if (!pe) continue;
      const a = portPos(pe);
      const tn = sc.nodes[t];
      const b = { x: (tn.x || 0) - 1, y: (tn.y || 0) + 15 };
      const d = curve(a, b);
      const hit = document.createElementNS(ns, 'path');
      hit.setAttribute('d', d); hit.setAttribute('class', 'hit');
      const title = document.createElementNS(ns, 'title');
      title.textContent = 'Click to remove this link';
      hit.append(title);
      hit.addEventListener('click', () => mutate((s) => setLink(s.nodes[id], o.key, null)));
      const p = document.createElementNS(ns, 'path');
      p.setAttribute('d', d);
      if (o.cls) p.setAttribute('class', o.cls);
      svg.append(hit, p);
    }
  }
}
function fitView() {
  const sc = scene();
  const c = $('#canvas').getBoundingClientRect();
  if (!sc || !Object.keys(sc.nodes).length) { S.view = { x: 80, y: 80, z: 1 }; applyView(); return; }
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  document.querySelectorAll('.node').forEach((el) => {
    const n = sc.nodes[el.dataset.id];
    x0 = Math.min(x0, n.x || 0); y0 = Math.min(y0, n.y || 0);
    x1 = Math.max(x1, (n.x || 0) + el.offsetWidth); y1 = Math.max(y1, (n.y || 0) + el.offsetHeight);
  });
  const pad = 60;
  const z = Math.min(1.2, Math.max(0.25, Math.min((c.width - pad * 2) / (x1 - x0), (c.height - pad * 2 - 50) / (y1 - y0))));
  S.view = { z, x: (c.width - (x1 - x0) * z) / 2 - x0 * z, y: (c.height - 50 - (y1 - y0) * z) / 2 - y0 * z };
  applyView();
}

// ---------- creating nodes ----------
function makeNode(sc, type, x, y) {
  const n = { type, x: Math.round(x), y: Math.round(y) };
  if (type === 'line') { n.speaker = ''; n.text = ''; }
  if (type === 'narration') n.text = '';
  if (type === 'choice') n.options = [{ id: newId(sc, 'o'), intent: '' }];
  if (type === 'branch') { n.conditions = []; n.match = 'all'; }
  if (type === 'setflag') n.flags = [{ name: '', op: 'set' }];
  if (type === 'end') n.outcome = 'leave';
  const id = newId(sc, 'n');
  // newId scans options too, so option and node numbers never clash
  sc.nodes[id] = n;
  if (!sc.start) sc.start = id;
  return id;
}
function addNode(type) {
  const sc = scene();
  if (!sc) return;
  let x, y, from = null;
  const sel = S.sel && sc.nodes[S.sel];
  if (sel) {
    const free = outputs(sel).find((o) => !getLink(sel, o.key));
    if (free) from = { id: S.sel, key: free.key };
    x = (sel.x || 0) + 300; y = sel.y || 0;
  } else {
    const c = $('#canvas').getBoundingClientRect();
    ({ x, y } = toWorld(c.left + c.width / 2 - 120, c.top + c.height / 2 - 60));
  }
  mutate((s) => {
    const id = makeNode(s, type, x, y);
    if (from) setLink(s.nodes[from.id], from.key, id);
    S.sel = id;
  });
}
function deleteNode(id) {
  mutate((s) => {
    delete s.nodes[id];
    for (const nid in s.nodes) for (const o of outputs(s.nodes[nid])) if (getLink(s.nodes[nid], o.key) === id) setLink(s.nodes[nid], o.key, null);
    if (s.start === id) s.start = Object.keys(s.nodes)[0] || null;
    if (S.sel === id) S.sel = null;
  });
}
function duplicateNode(id) {
  mutate((s) => {
    const n = clone(s.nodes[id]);
    delete n.next; delete n.yes; delete n.no;
    let k = +newId(s, 'o').slice(1);
    for (const o of n.options || []) { o.id = 'o' + k++; delete o.next; delete o.pass; delete o.fail; }
    n.x = (n.x || 0) + 30; n.y = (n.y || 0) + 30;
    const nid = newId(s, 'n');
    s.nodes[nid] = n;
    S.sel = nid;
  });
}

// ---------- canvas interaction ----------
let drag = null;
function initCanvas() {
  const canvas = $('#canvas');
  canvas.addEventListener('mousedown', (e) => {
    if (e.button !== 0 || !scene() || e.target.closest('.palette, .drop-menu')) return;
    hideDropMenu();
    const port = e.target.closest('.port');
    const nodeEl = e.target.closest('.node');
    if (port) {
      const [id, key] = port.dataset.port.split('|');
      drag = { kind: 'link', id, key, from: portPos(port) };
      e.preventDefault();
      return;
    }
    if (nodeEl) {
      const id = nodeEl.dataset.id;
      if (S.sel !== id) { S.sel = id; renderCanvas(); renderInspector(); }
      if (e.target.closest('.head')) {
        const n = scene().nodes[id];
        const w = toWorld(e.clientX, e.clientY);
        drag = { kind: 'node', id, dx: w.x - (n.x || 0), dy: w.y - (n.y || 0), moved: false };
        e.preventDefault();
      }
      return;
    }
    drag = { kind: 'pan', sx: e.clientX, sy: e.clientY, vx: S.view.x, vy: S.view.y, moved: false };
    canvas.classList.add('panning');
  });
  window.addEventListener('mousemove', (e) => {
    if (!drag) return;
    if (drag.kind === 'pan') {
      S.view.x = drag.vx + e.clientX - drag.sx; S.view.y = drag.vy + e.clientY - drag.sy;
      if (Math.abs(e.clientX - drag.sx) + Math.abs(e.clientY - drag.sy) > 3) drag.moved = true;
      applyView();
    } else if (drag.kind === 'node') {
      const sc = scene(), n = sc.nodes[drag.id];
      if (!drag.moved) { S.undo.push(JSON.stringify(sc)); S.redo = []; S.lastKey = null; drag.moved = true; }
      const w = toWorld(e.clientX, e.clientY);
      n.x = Math.round(w.x - drag.dx); n.y = Math.round(w.y - drag.dy);
      const el = document.querySelector(`.node[data-id="${drag.id}"]`);
      el.style.left = n.x + 'px'; el.style.top = n.y + 'px';
      drawEdges();
    } else if (drag.kind === 'link') {
      drawEdges();
      const ns = 'http://www.w3.org/2000/svg';
      const p = document.createElementNS(ns, 'path');
      p.setAttribute('class', 'temp');
      p.setAttribute('d', curve(drag.from, toWorld(e.clientX, e.clientY)));
      $('#edges').append(p);
      document.querySelectorAll('.node.drop-target').forEach((x) => x.classList.remove('drop-target'));
      const over = document.elementFromPoint(e.clientX, e.clientY);
      const t = over && over.closest('.node');
      if (t && t.dataset.id !== drag.id) t.classList.add('drop-target');
    }
  });
  window.addEventListener('mouseup', (e) => {
    if (!drag) return;
    const d = drag; drag = null;
    canvas.classList.remove('panning');
    if (d.kind === 'pan' && !d.moved && S.sel) { S.sel = null; renderCanvas(); renderInspector(); }
    if (d.kind === 'node' && d.moved) { markDirty(S.cur); }
    if (d.kind === 'link') {
      document.querySelectorAll('.node.drop-target').forEach((x) => x.classList.remove('drop-target'));
      const over = document.elementFromPoint(e.clientX, e.clientY);
      const t = over && over.closest('.node');
      if (t && t.dataset.id !== d.id) mutate((s) => setLink(s.nodes[d.id], d.key, t.dataset.id));
      else if (!t && over && over.closest('#canvas')) showDropMenu(e.clientX, e.clientY, d);
      else drawEdges();
    }
  });
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) {
      const r = canvas.getBoundingClientRect();
      const mx = e.clientX - r.left, my = e.clientY - r.top;
      const z = Math.min(2, Math.max(0.2, S.view.z * Math.exp(-e.deltaY * 0.01)));
      S.view.x = mx - (mx - S.view.x) * (z / S.view.z);
      S.view.y = my - (my - S.view.y) * (z / S.view.z);
      S.view.z = z;
    } else { S.view.x -= e.deltaX; S.view.y -= e.deltaY; }
    applyView();
  }, { passive: false });
  canvas.addEventListener('dblclick', (e) => {
    if (!scene() || e.target.closest('.node')) return;
    showDropMenu(e.clientX, e.clientY, null);
  });
  document.querySelectorAll('[data-add]').forEach((b) => b.addEventListener('click', () => addNode(b.dataset.add)));
}
function showDropMenu(cx, cy, link) {
  const m = $('#drop-menu');
  const r = $('#canvas').getBoundingClientRect();
  m.innerHTML = '';
  m.append(h('div', { class: 'hint', style: 'padding:2px 8px', text: link ? 'New node, linked:' : 'New node here:' }));
  for (const t in NODE_TYPES) {
    m.append(h('button', {
      text: NODE_TYPES[t].label,
      onclick: () => {
        hideDropMenu();
        const w = toWorld(cx, cy);
        mutate((s) => {
          const id = makeNode(s, t, w.x, w.y - 15);
          if (link) setLink(s.nodes[link.id], link.key, id);
          S.sel = id;
        });
      },
    }));
  }
  m.classList.remove('hidden');
  m.style.left = Math.min(cx - r.left, r.width - m.offsetWidth - 8) + 'px';
  m.style.top = Math.min(cy - r.top, r.height - m.offsetHeight - 8) + 'px';
  if (link) drawEdges();
}
function hideDropMenu() { $('#drop-menu').classList.add('hidden'); }

// ---------- inspector ----------
function datalists() {
  const old = $('#datalists');
  if (old) old.remove();
  const flags = allFlags();
  const sets = {
    'dl-speakers': uniq([...charNames(), ...listOf('companions'), ...listOf('npcs')]),
    'dl-people': uniq([...charNames(), ...listOf('companions'), ...listOf('npcs')]),
    'dl-allchars': charNames(),
    'dl-places': listOf('places'),
    'dl-encounters': listOf('encounters'),
    'dl-flags': [...flags.set, ...flags.used].filter((v, i, a) => a.indexOf(v) === i).sort(),
    'dl-background': listOf('backgrounds'), 'dl-class': listOf('classes'), 'dl-subclass': listOf('subclasses'),
    'dl-race': listOf('races'), 'dl-companion': uniq([...charNames('Companion'), ...listOf('companions')]),
  };
  const wrap = h('div', { id: 'datalists', class: 'hidden' });
  for (const id in sets) wrap.append(h('datalist', { id }, sets[id].map((v) => h('option', { value: v }))));
  document.body.append(wrap);
}
function condList(kind) {
  if (kind === 'flag' || kind === 'noflag') return 'dl-flags';
  if (kind === 'nocompanion') return 'dl-companion';
  return 'dl-' + kind;
}
// A text field whose edits don't rebuild the inspector, so typing keeps focus.
function textField(label, value, onset, opts = {}) {
  const key = opts.key || label + Math.random();
  const attrs = {
    value: value || '', placeholder: opts.placeholder || '', list: opts.list || null,
    oninput: (e) => mutate((s) => onset(s, e.target.value), { key, inspector: false, list: opts.relist }),
  };
  const input = opts.area ? h('textarea', Object.assign({ rows: opts.rows || 4 }, attrs)) : h('input', attrs);
  return label ? [h('label', { text: label }), input] : input;
}
function select(value, options, onset) {
  return h('select', { onchange: (e) => mutate((s) => onset(s, e.target.value)) },
    Object.keys(options).map((k) => h('option', { value: k, selected: k === value ? true : null, text: options[k] })));
}
function conditionsEditor(path, conds, title) {
  // path(s) returns the live conditions array inside scene s
  const box = h('div', {});
  box.append(h('label', { text: title }));
  conds.forEach((c, i) => {
    box.append(h('div', { class: 'row' },
      select(c.kind, COND_KINDS, (s, v) => { path(s)[i].kind = v; }),
      textField(null, c.value, (s, v) => { path(s)[i].value = v; }, { list: condList(c.kind), key: 'cond' + i + c.kind }),
      h('button', { class: 'small danger', text: '×', title: 'Remove', onclick: () => mutate((s) => path(s).splice(i, 1)) })));
  });
  box.append(h('div', { class: 'btn-row' }, h('button', { class: 'small', text: '+ Condition', onclick: () => mutate((s) => path(s).push({ kind: 'background', value: '' })) })));
  return box;
}

function renderInspector() {
  datalists();
  const box = $('#insp-edit');
  box.innerHTML = '';
  const sc = scene();
  if (!sc) { box.append(h('p', { class: 'hint', style: 'margin-top:16px', text: 'No scene open.' })); return; }
  const n = S.sel && sc.nodes[S.sel];
  if (!n) return sceneInspector(box, sc);
  const id = S.sel;
  const N = (s) => s.nodes[id];
  box.append(h('h3', { text: NODE_TYPES[n.type].label }), h('p', { class: 'hint', text: NODE_TYPES[n.type].hint }));

  if (n.type === 'line') {
    box.append(...textField('Speaker', n.speaker, (s, v) => { N(s).speaker = v; }, { list: 'dl-speakers', placeholder: 'Who talks', relist: true }));
    box.append(...textField('Stage note (shows small and italic above the line)', n.stage, (s, v) => { N(s).stage = v; }, { placeholder: 'cracks his knuckles' }));
    box.append(...textField('Line', n.text, (s, v) => { N(s).text = v; }, { area: true, rows: 7 }));
  }
  if (n.type === 'narration') box.append(...textField('Narration', n.text, (s, v) => { N(s).text = v; }, { area: true, rows: 7, placeholder: 'The stone stands alone beneath an open sky.' }));

  if (n.type === 'choice') {
    (n.options || []).forEach((o, i) => box.append(optionCard(sc, id, o, i, n.options.length)));
    box.append(h('div', { class: 'btn-row' }, h('button', {
      class: 'primary', text: '+ Option',
      onclick: () => mutate((s) => N(s).options.push({ id: newId(s, 'o'), intent: '' })),
    })));
  }

  if (n.type === 'branch') {
    box.append(h('label', { text: 'Match' }), select(n.match || 'all', { all: 'All conditions hold', any: 'Any condition holds' }, (s, v) => { N(s).match = v; }));
    box.append(conditionsEditor((s) => N(s).conditions, n.conditions || [], 'Conditions'));
    box.append(h('p', { class: 'hint', text: 'Yes goes one way, No the other. Use it for NPCs reacting to who the hero is.' }));
  }

  if (n.type === 'setflag') {
    box.append(h('label', { text: 'Flags' }));
    (n.flags || []).forEach((f, i) => box.append(h('div', { class: 'row' },
      select(f.op || 'set', { set: 'Set', clear: 'Clear' }, (s, v) => { N(s).flags[i].op = v; }),
      textField(null, f.name, (s, v) => { N(s).flags[i].name = v; }, { list: 'dl-flags', placeholder: 'lady-refused-sword', key: 'flag' + i }),
      h('button', { class: 'small danger', text: '×', onclick: () => mutate((s) => N(s).flags.splice(i, 1)) }))));
    box.append(h('div', { class: 'btn-row' }, h('button', { class: 'small', text: '+ Flag', onclick: () => mutate((s) => N(s).flags.push({ name: '', op: 'set' })) })));
    box.append(h('p', { class: 'hint', text: 'Flags are shared across all scenes. Name them in lowercase with dashes.' }));
  }

  if (n.type === 'end') {
    box.append(h('label', { text: 'Outcome' }), select(n.outcome || 'leave', END_KINDS, (s, v) => { N(s).outcome = v; }));
    if (n.outcome === 'scene') {
      const opts = {};
      for (const sid in S.scenes) if (sid !== sc.id) opts[sid] = S.scenes[sid].title || sid;
      box.append(h('label', { text: 'Scene' }), select(n.scene || '', Object.assign({ '': '— pick a scene —' }, opts), (s, v) => { N(s).scene = v; }));
    }
    box.append(...textField('Reward (shows as chips on screen)', n.reward, (s, v) => { N(s).reward = v; }, { placeholder: 'e.g. Excalibur' }));
    box.append(...textField('Notes for the game', n.notes, (s, v) => { N(s).notes = v; }, { area: true, rows: 3 }));
  }

  box.append(h('div', { class: 'btn-row' },
    sc.start !== id ? h('button', { text: 'Make this the start', onclick: () => mutate((s) => { s.start = id; }) }) : null,
    h('button', { text: 'Duplicate', title: '⌘D', onclick: () => duplicateNode(id) }),
    h('button', { class: 'danger', text: 'Delete', title: 'Delete key', onclick: () => deleteNode(id) })));
  box.append(h('p', { class: 'hint', style: 'margin-top:14px', text: 'Node ' + id + '. Drag from a dot on the right of a node to link it; drop on empty space to make a new linked node.' }));
}

function optionCard(sc, nid, o, i, count) {
  const O = (s) => s.nodes[nid].options.find((x) => x.id === o.id);
  const card = h('div', { class: 'card' });
  card.append(h('div', { class: 'card-head' },
    h('span', { class: 'grow', text: 'Option ' + (i + 1) }),
    i > 0 ? h('button', { class: 'small', text: '↑', title: 'Move up', onclick: () => mutate((s) => { const a = s.nodes[nid].options; a.splice(i - 1, 0, a.splice(i, 1)[0]); }) }) : null,
    i < count - 1 ? h('button', { class: 'small', text: '↓', title: 'Move down', onclick: () => mutate((s) => { const a = s.nodes[nid].options; a.splice(i + 1, 0, a.splice(i, 1)[0]); }) }) : null,
    h('button', { class: 'small danger', text: '×', title: 'Remove option', onclick: () => mutate((s) => s.nodes[nid].options.splice(i, 1)) })));
  card.append(...textField('Intent (what the hero wants or does)', o.intent, (s, v) => { O(s).intent = v; }, { area: true, rows: 2, placeholder: 'Appeal to her honour' }));
  card.append(h('label', { class: 'check-label' },
    h('input', { type: 'checkbox', checked: o.once, onchange: (e) => mutate((s) => { if (e.target.checked) O(s).once = true; else delete O(s).once; }) }),
    'Hide this option once picked'));
  card.append(h('label', { class: 'check-label' },
    h('input', {
      type: 'checkbox', checked: !!o.check,
      onchange: (e) => mutate((s) => {
        const x = O(s);
        if (e.target.checked) { x.check = { type: 'approach', skill: listOf('approaches')[0] || 'Persuade', failCost: '' }; if (x.next) { x.pass = x.next; delete x.next; } }
        else { if (x.pass) x.next = x.pass; delete x.check; delete x.pass; delete x.fail; }
      }),
    }), 'Needs a check'));

  if (o.check) {
    const c = o.check;
    const skills = c.type === 'approach' ? listOf('approaches') : c.type === 'proficiency' ? listOf('proficiencies') : listOf('abilities');
    const sub = h('div', { class: 'sub-card' });
    sub.append(h('div', { class: 'row' },
      select(c.type, CHECK_TYPES, (s, v) => {
        const k = O(s).check; k.type = v;
        const l = v === 'approach' ? listOf('approaches') : v === 'proficiency' ? listOf('proficiencies') : listOf('abilities');
        if (!l.includes(k.skill)) k.skill = l[0] || '';
        if (v === 'ability') delete k.chimeIns;
      }),
      select(c.skill, Object.fromEntries(skills.map((x) => [x, x])), (s, v) => { O(s).check.skill = v; })));
    sub.append(h('p', { class: 'hint', text: c.type === 'approach' ? 'Flipped by the hero: social checks are always the hero\'s.' : 'The player picks who tries this check.' }));
    sub.append(...textField('Cost of failing', c.failCost, (s, v) => { O(s).check.failCost = v; }, { placeholder: 'She just says no / she fights back' }));
    sub.append(h('label', { class: 'check-label' },
      h('input', { type: 'checkbox', checked: c.fight, onchange: (e) => mutate((s) => { if (e.target.checked) O(s).check.fight = true; else delete O(s).check.fight; }) }),
      'Failing starts a fight'));
    if (c.type !== 'ability') {
      sub.append(h('label', { text: 'Special chime-ins (miss by exactly 1; otherwise each companion\'s generic line plays)' }));
      (c.chimeIns || []).forEach((ci, j) => {
        sub.append(h('div', { class: 'row' },
          textField(null, ci.who, (s, v) => { O(s).check.chimeIns[j].who = v; }, { list: 'dl-companion', placeholder: 'Companion', key: 'ciw' + o.id + j }),
          h('button', { class: 'small danger', text: '×', onclick: () => mutate((s) => O(s).check.chimeIns.splice(j, 1)) })));
        sub.append(textField(null, ci.text, (s, v) => { O(s).check.chimeIns[j].text = v; }, { area: true, rows: 2, key: 'cit' + o.id + j, placeholder: 'Their line' }));
      });
      sub.append(h('div', { class: 'btn-row' }, h('button', { class: 'small', text: '+ Chime-in', onclick: () => mutate((s) => { const k = O(s).check; (k.chimeIns = k.chimeIns || []).push({ who: '', text: '' }); }) })));
    } else sub.append(h('p', { class: 'hint', text: 'Bare ability checks get no chime-in.' }));
    card.append(sub);
  }
  card.append(conditionsEditor((s) => { const x = O(s); return (x.conditions = x.conditions || []); }, o.conditions || [], 'Only shows if (all hold)'));
  return card;
}

function sceneInspector(box, sc) {
  box.append(h('h3', { text: 'Scene' }), h('p', { class: 'hint', text: 'Click a node to edit it. Double-click empty space to add one.' }));
  box.append(...textField('Title', sc.title, (s, v) => { s.title = v; }, { relist: true }));
  const idInput = h('input', { value: sc.id });
  box.append(h('label', { text: 'File name (design/scenes/…json)' }), h('div', { class: 'row' }, idInput,
    h('button', { class: 'small', text: 'Rename', onclick: () => renameScene(sc.id, idInput.value) })));
  box.append(...textField('Notes (what this scene is for, open points)', sc.notes, (s, v) => { s.notes = v; }, { area: true, rows: 4 }));

  box.append(h('label', { text: 'Triggers (what starts this scene)' }));
  (sc.triggers || []).forEach((t, i) => box.append(h('div', { class: 'row' },
    select(t.kind, TRIGGER_KINDS, (s, v) => { s.triggers[i].kind = v; }),
    textField(null, t.value, (s, v) => { s.triggers[i].value = v; }, {
      list: t.kind === 'place' ? 'dl-places' : t.kind === 'person' ? 'dl-people' : t.kind === 'encounter' ? 'dl-encounters' : null,
      key: 'trig' + i, relist: true,
    }),
    h('button', { class: 'small danger', text: '×', onclick: () => mutate((s) => s.triggers.splice(i, 1), { list: true }) }))));
  box.append(h('div', { class: 'btn-row' }, h('button', { class: 'small', text: '+ Trigger', onclick: () => mutate((s) => { (s.triggers = s.triggers || []).push({ kind: 'place', value: '' }); }, { list: true }) })));

  const who = speakers(sc);
  box.append(h('label', { text: 'Speakers in this scene' }), h('div', { class: 'pill-list' }, who.length ? who.map((w) => h('span', { class: 'pill', text: w })) : h('span', { class: 'hint', text: 'none yet' })));
  const f = sceneFlags(sc);
  if (f.set.size || f.used.size) {
    box.append(h('label', { text: 'Flags set here' }), h('div', { class: 'pill-list' }, [...f.set].map((w) => h('span', { class: 'pill', text: w }))));
    box.append(h('label', { text: 'Flags read here' }), h('div', { class: 'pill-list' }, [...f.used].map((w) => h('span', { class: 'pill', text: w }))));
  }
  box.append(h('div', { class: 'btn-row' },
    h('button', { text: 'Duplicate scene', onclick: duplicateScene }),
    h('button', { class: 'danger', text: 'Delete scene', onclick: deleteScene })));
}

// ---------- scenes: new / rename / delete ----------
function uniqueId(base) {
  let id = base, i = 2;
  while (S.scenes[id]) id = base + '-' + i++;
  return id;
}
function newScene() {
  modal(h('div', {},
    h('h2', { text: 'New scene' }),
    h('label', { text: 'Title' }),
    h('input', { id: 'new-title', placeholder: 'The Lady of the Lake', onkeydown: (e) => { if (e.key === 'Enter') $('#new-ok').click(); } }),
    h('div', { class: 'btn-row' },
      h('button', { id: 'new-ok', class: 'primary', text: 'Create', onclick: () => {
        const title = $('#new-title').value.trim() || 'Untitled scene';
        const id = uniqueId(slug(title));
        const sc = { id, title, notes: '', triggers: [], start: null, nodes: {} };
        makeNode(sc, 'line', 0, 0);
        S.scenes[id] = sc;
        closeModal();
        markDirty(id);
        openScene(id);
        S.sel = sc.start; renderAll();
      } }),
      h('button', { text: 'Cancel', onclick: closeModal }))));
  $('#new-title').focus();
}
async function renameScene(oldId, raw) {
  const id = slug(raw);
  if (id === oldId) return;
  if (S.scenes[id]) { alert('A scene called ' + id + ' already exists.'); return; }
  const sc = S.scenes[oldId];
  sc.id = id;
  S.scenes[id] = sc; delete S.scenes[oldId];
  for (const sid in S.scenes) for (const nid in S.scenes[sid].nodes) {
    const n = S.scenes[sid].nodes[nid];
    if (n.type === 'end' && n.scene === oldId) { n.scene = id; markDirty(sid); }
  }
  S.cur = id;
  S.dirty.delete(oldId);
  markDirty(id);
  try { await saveNow(); await api('DELETE', 'scenes/' + oldId); } catch (e) {}
  renderAll();
}
function duplicateScene() {
  const sc = clone(scene());
  sc.id = uniqueId(sc.id + '-copy'); sc.title = (sc.title || '') + ' (copy)';
  S.scenes[sc.id] = sc;
  markDirty(sc.id);
  openScene(sc.id);
}
async function deleteScene() {
  const sc = scene();
  if (!confirm(`Delete "${sc.title || sc.id}"? Its file is removed from design/scenes/ (git still has it if it was committed).`)) return;
  delete S.scenes[sc.id];
  S.dirty.delete(sc.id);
  try { await api('DELETE', 'scenes/' + sc.id); } catch (e) {}
  S.cur = null; S.sel = null;
  renderAll();
}

// ---------- problems (light checks) ----------
const FIRST_PERSON = /\b(I|I'm|I'll|I've|I'd|me|my|mine|we|we're|our|us)\b/;
const QUOTES = /["“”]/;
function sceneFlags(sc) {
  const set = new Set(), used = new Set();
  for (const id in sc.nodes || {}) {
    const n = sc.nodes[id];
    for (const f of n.flags || []) if (f.name) set.add(f.name);
    const conds = [...(n.conditions || [])];
    for (const o of n.options || []) conds.push(...(o.conditions || []));
    for (const c of conds) if ((c.kind === 'flag' || c.kind === 'noflag') && c.value) used.add(c.value);
  }
  return { set, used };
}
function allFlags() {
  const set = new Set(), used = new Set();
  for (const id in S.scenes) { const f = sceneFlags(S.scenes[id]); f.set.forEach((x) => set.add(x)); f.used.forEach((x) => used.add(x)); }
  return { set: [...set], used: [...used] };
}
function problems(sc) {
  const out = [];
  const P = (level, node, msg) => out.push({ level, node, msg });
  const nodes = sc.nodes || {};
  if (!sc.start || !nodes[sc.start]) P('error', null, 'The scene has no start node.');
  // reachability
  const seen = new Set();
  const stack = sc.start && nodes[sc.start] ? [sc.start] : [];
  while (stack.length) {
    const id = stack.pop();
    if (seen.has(id)) continue;
    seen.add(id);
    for (const o of outputs(nodes[id])) { const t = getLink(nodes[id], o.key); if (t && nodes[t]) stack.push(t); }
  }
  const allSet = new Set(allFlags().set);
  for (const id in nodes) {
    const n = nodes[id];
    const label = NODE_TYPES[n.type].label + (n.speaker ? ' (' + n.speaker + ')' : '');
    if (!seen.has(id) && sc.start) P('warn', id, `${label} can't be reached from the start.`);
    for (const o of outputs(n)) {
      const t = getLink(n, o.key);
      const what = o.opt ? `Option "${preview(o.opt.intent, 30) || 'empty'}"${o.label ? ' ' + o.label.toLowerCase() : ''}` : `${label}${o.label !== 'Next' ? ' ' + o.label : ''}`;
      if (t && !nodes[t]) P('error', id, `${what} points to a missing node.`);
      else if (!t) P(o.cls === 'fail' && o.opt ? 'error' : 'warn', id, o.cls === 'fail' && o.opt ? `${what}: a check needs a fail branch.` : `${what} goes nowhere (link it, or add an End).`);
    }
    if (n.type === 'line') {
      if (!n.speaker) P('warn', id, 'NPC line has no speaker.');
      if (!(n.text || '').trim()) P('warn', id, `${label} is empty.`);
    }
    if (n.type === 'narration') {
      if (!(n.text || '').trim()) P('warn', id, 'Narration is empty.');
      else {
        if (FIRST_PERSON.test(n.text.replace(/["“][^"”]*["”]/g, ''))) P('warn', id, 'Narration uses first person (I, we, my…). It should be second person and never say what the hero thinks.');
        if (QUOTES.test(n.text)) P('info', id, 'Narration has quotes. Should someone speak this as an NPC line instead?');
      }
    }
    if (n.type === 'choice') {
      if (!(n.options || []).length) P('error', id, 'Hero choice has no options.');
      for (const o of n.options || []) {
        const t = o.intent || '';
        if (!t.trim()) P('warn', id, 'A hero option is empty.');
        if (QUOTES.test(t) || FIRST_PERSON.test(t)) P('warn', id, `Option "${preview(t, 40)}" reads like speech. Hero options name the intent ("Ask about the sword"), never the hero's words.`);
        if (o.check && !(o.check.failCost || '').trim()) P('info', id, `Option "${preview(t, 30)}" has no cost of failing written.`);
        for (const c of o.conditions || []) if (!c.value) P('warn', id, `Option "${preview(t, 30)}" has a condition with no value.`);
      }
    }
    if (n.type === 'branch') {
      if (!(n.conditions || []).length) P('warn', id, 'Condition node has no conditions.');
      for (const c of n.conditions || []) if (!c.value) P('warn', id, 'A condition has no value.');
    }
    if (n.type === 'setflag') for (const f of n.flags || []) if (!f.name) P('warn', id, 'A flag has no name.');
    if (n.type === 'end' && n.outcome === 'scene' && !S.scenes[n.scene]) P('error', id, 'End goes to a scene that does not exist.');
    const texts = [n.text, n.stage, ...(n.options || []).map((o) => o.intent)];
    if (texts.some((x) => /\(a beat\)/i.test(x || ''))) P('warn', id, '"(a beat)" is on the tells-to-avoid list.');
    const conds = [...(n.conditions || []), ...(n.options || []).flatMap((o) => o.conditions || [])];
    for (const c of conds) if ((c.kind === 'flag' || c.kind === 'noflag') && c.value && !allSet.has(c.value)) P('info', id, `Flag "${c.value}" is never set in any scene (fine if the game sets it).`);
  }
  return out;
}
function renderProblems() {
  const box = $('#insp-problems');
  box.innerHTML = '';
  const sc = scene();
  const list = sc ? problems(sc) : [];
  const errs = list.filter((p) => p.level === 'error').length;
  const warns = list.filter((p) => p.level === 'warn').length;
  const cnt = $('#problem-count');
  cnt.textContent = errs || warns || '';
  cnt.classList.toggle('warn', !errs && !!warns);
  if (!sc) return;
  if (!list.length) { box.append(h('div', { class: 'ok-msg', text: 'No problems found.' })); return; }
  const order = { error: 0, warn: 1, info: 2 };
  for (const p of list.sort((a, b) => order[a.level] - order[b.level])) {
    box.append(h('div', {
      class: 'problem ' + p.level,
      onclick: () => { if (p.node) { S.sel = p.node; focusNode(p.node); switchTab('edit'); renderCanvas(); renderInspector(); } },
    }, h('span', { class: 'lvl', text: p.level === 'warn' ? 'check' : p.level }), p.msg));
  }
}
function focusNode(id) {
  const n = scene().nodes[id];
  const c = $('#canvas').getBoundingClientRect();
  S.view.x = c.width / 2 - ((n.x || 0) + 120) * S.view.z;
  S.view.y = c.height / 2 - ((n.y || 0) + 40) * S.view.z;
  applyView();
}
function switchTab(t) {
  S.tab = t;
  document.querySelectorAll('#insp-tabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === t));
  $('#insp-edit').classList.toggle('hidden', t !== 'edit');
  $('#insp-problems').classList.toggle('hidden', t !== 'problems');
}

// ---------- lists editor ----------
const LIST_LABELS = {
  companions: 'Companions', npcs: 'Other speakers (story NPCs, keepers)', places: 'Places', backgrounds: 'Backgrounds',
  classes: 'Classes', subclasses: 'Subclasses', races: 'Races', approaches: 'Social approaches',
  proficiencies: 'Other proficiencies', abilities: 'Abilities', encounters: 'Encounter kinds',
};
function editLists() {
  const areas = {};
  const grid = h('div', { class: 'lists-grid' });
  for (const k in LIST_LABELS) {
    areas[k] = h('textarea', { value: listOf(k).join('\n') });
    grid.append(h('div', {}, h('label', { text: LIST_LABELS[k] }), areas[k]));
  }
  modal(h('div', {},
    h('h2', { text: 'Name lists' }),
    h('p', { class: 'hint', text: 'One per line. These fill the suggestion dropdowns; they come from the design docs, so keep them in step when the docs change. Saved to design/scenes/_lists.json.' }),
    grid,
    h('div', { class: 'btn-row' },
      h('button', { class: 'primary', text: 'Save', onclick: async () => {
        for (const k in areas) S.lists[k] = areas[k].value.split('\n').map((x) => x.trim()).filter(Boolean);
        try { await api('PUT', 'lists', S.lists); closeModal(); renderInspector(); }
        catch (e) { alert('Could not save the lists: ' + e.message); }
      } }),
      h('button', { text: 'Cancel', onclick: closeModal }))));
}

// ---------- modal ----------
function modal(content) { const b = $('#modal-box'); b.innerHTML = ''; b.append(content); $('#modal').classList.remove('hidden'); }
function closeModal() { $('#modal').classList.add('hidden'); }

// ---------- keys ----------
function initKeys() {
  window.addEventListener('keydown', (e) => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
    const mod = e.metaKey || e.ctrlKey;
    if (e.key === 'Escape') { hideDropMenu(); closeModal(); if (!typing && S.sel) { S.sel = null; renderCanvas(); renderInspector(); } }
    if (typing || S.mode !== 'scenes') { if (mod && e.key === 's') { e.preventDefault(); saveNow(); saveChars(); } return; }
    if (mod && e.key.toLowerCase() === 'z') { e.preventDefault(); undo(!e.shiftKey); }
    else if (mod && e.key === 'y') { e.preventDefault(); undo(false); }
    else if (mod && e.key === 's') { e.preventDefault(); saveNow(); }
    else if (mod && e.key === 'd' && S.sel) { e.preventDefault(); duplicateNode(S.sel); }
    else if ((e.key === 'Delete' || e.key === 'Backspace') && S.sel) { e.preventDefault(); deleteNode(S.sel); }
    else if (e.key === 'f' && !mod) fitView();
  });
  window.addEventListener('beforeunload', (e) => { if (S.dirty.size || S.cdirty.size) { e.preventDefault(); e.returnValue = ''; } });
}

// ---------- boot ----------
function renderAll() { renderSceneList(); renderCanvas(); renderInspector(); renderProblems(); setStatus(); }

async function boot() {
  initCanvas(); initKeys();
  $('#btn-new').onclick = newScene;
  $('#btn-undo').onclick = () => undo(true);
  $('#btn-redo').onclick = () => undo(false);
  $('#btn-fit').onclick = fitView;
  $('#btn-lists').onclick = editLists;
  $('#search').oninput = (e) => { S.search = e.target.value; renderSceneList(); };
  document.querySelectorAll('#group-tabs button').forEach((b) => b.onclick = () => {
    S.group = b.dataset.group;
    document.querySelectorAll('#group-tabs button').forEach((x) => x.classList.toggle('active', x === b));
    renderSceneList();
  });
  document.querySelectorAll('#insp-tabs button').forEach((b) => b.onclick = () => switchTab(b.dataset.tab));
  $('#modal').addEventListener('mousedown', (e) => { if (e.target.id === 'modal') closeModal(); });
  window.addEventListener('resize', drawEdges);
  // tells a background server (Desktop app) that a tab is still open
  setInterval(() => fetch('/api/ping').catch(() => {}), 30000);

  try {
    S.lists = await api('GET', 'lists');
    for (const sc of await api('GET', 'scenes')) {
      if (sc.error) { console.warn('Could not read', sc.id, sc.error); continue; }
      sc.nodes = sc.nodes || {}; sc.triggers = sc.triggers || [];
      S.scenes[sc.id] = sc;
    }
    await initCharacters();
  } catch (e) {
    S.offline = true;
    $('#empty-hint').textContent = 'Can\'t reach the editor server. Start it with "Start Story Editor.command" (or python3 tools/story-editor/server.py), then reload.';
  }
  // offer to restore edits that never reached disk
  const backups = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith('se-backup-')) backups.push(JSON.parse(localStorage.getItem(k)));
      if (k && k.startsWith('se-cbackup-')) backups.push(JSON.parse(localStorage.getItem(k)));
    }
  } catch (e) {}
  if (backups.length && !S.offline) {
    modal(h('div', {},
      h('h2', { text: 'Unsaved edits found' }),
      h('p', { text: 'These scenes had edits that never reached disk (the server was stopped):' }),
      h('ul', {}, backups.map((b) => h('li', { text: `${b.scene ? b.scene.title || b.scene.id : b.file + ' (character)'} — ${new Date(b.t).toLocaleString()}` }))),
      h('div', { class: 'btn-row' },
        h('button', { class: 'primary', text: 'Restore them', onclick: () => {
          for (const b of backups) {
            if (b.scene) { S.scenes[b.scene.id] = b.scene; markDirty(b.scene.id); }
            else { S.chars[b.file] = parseChar(b.file, b.text); charChanged(S.chars[b.file]); }
          }
          closeModal(); renderAll(); if (S.mode === 'characters') setMode('characters');
        } }),
        h('button', { text: 'Discard', onclick: () => {
          for (const b of backups) try { localStorage.removeItem(b.scene ? 'se-backup-' + b.scene.id : 'se-cbackup-' + b.file); } catch (e) {}
          closeModal();
        } }))));
  }
  let last = null;
  try { last = localStorage.getItem('se-last'); } catch (e) {}
  if (last && S.scenes[last]) openScene(last); else renderAll();
  let mode = 'scenes';
  try { mode = localStorage.getItem('se-mode') || 'scenes'; } catch (e) {}
  if (mode === 'characters') setMode('characters');
  setStatus();
}
// boot() runs at the end of characters.js, once both scripts are loaded
