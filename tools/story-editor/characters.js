// Characters: reads and writes design/characters/<Name>.md.
// Sections the editor doesn't know are kept as they are.
'use strict';

const SECTION_ORDER = ['Profile', 'Background', 'Personality', 'Personal quest', 'Relationships', 'Voice sheet', 'Notes', 'Lines'];
const PROFILE_KEYS = ['Role', 'Path', 'Race', 'Class', 'Subclass', 'Home', 'Proficiencies', 'Status'];
const ROLES = ['Companion', 'Mentor', 'Story NPC', 'Villain'];
const VOICE_STATES = { 'not started': 'Not started', draft: 'Draft', approved: 'Approved' };
const CHAR_INTRO = 'How to write: [Writing guide](00%20Writing%20guide.md).';
const BULLET = /^- \*\*(.+?):\*\*\s?(.*)$/;

// ---------- markdown model ----------
function parseChar(file, text) {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  let i = 0, name = file;
  while (i < lines.length && !lines[i].trim()) i++;
  if ((lines[i] || '').startsWith('# ')) { name = lines[i].slice(2).trim(); i++; }
  const intro = [];
  while (i < lines.length && !lines[i].startsWith('## ')) intro.push(lines[i++]);
  const sections = [];
  for (; i < lines.length; i++) {
    if (lines[i].startsWith('## ')) sections.push({ h: lines[i].slice(3).trim(), body: [] });
    else sections[sections.length - 1].body.push(lines[i]);
  }
  for (const s of sections) s.body = s.body.join('\n').trim();
  return { file, name, intro: intro.join('\n').trim(), sections };
}
function serializeChar(c) {
  let out = '# ' + c.name + '\n\n';
  if (c.intro.trim()) out += c.intro.trim() + '\n\n';
  out += c.sections.filter((s) => s.body.trim()).map((s) => '## ' + s.h + '\n\n' + s.body.trim() + '\n').join('\n');
  return out.replace(/\n+$/, '') + '\n';
}
function getSec(c, h) { const s = c.sections.find((x) => x.h === h); return s ? s.body : ''; }
function setSec(c, h, body) {
  const s = c.sections.find((x) => x.h === h);
  if (s) { s.body = body; return; }
  const rank = SECTION_ORDER.indexOf(h);
  const at = c.sections.findIndex((x) => SECTION_ORDER.indexOf(x.h) > rank);
  if (at < 0) c.sections.push({ h, body }); else c.sections.splice(at, 0, { h, body });
}
// "- **Key:** value" bullets; other lines are kept in .extra
function parseBullets(body) {
  const items = [], extra = [];
  for (const line of body.split('\n')) {
    const m = BULLET.exec(line);
    if (m) items.push({ k: m[1], v: m[2] });
    else if (line.trim()) extra.push(line);
  }
  return { items, extra };
}
function bulletsText(items, extra) {
  return items.filter((x) => x.k && (x.v || '').trim()).map((x) => `- **${x.k}:** ${x.v.trim()}`).concat(extra || []).join('\n');
}
function profile(c) {
  const { items, extra } = parseBullets(getSec(c, 'Profile'));
  const map = {};
  for (const x of items) map[x.k] = x.v;
  return { map, order: items.map((x) => x.k), extra };
}
function setProfile(c, key, value) {
  const p = profile(c);
  p.map[key] = value;
  const keys = PROFILE_KEYS.concat(p.order.filter((k) => !PROFILE_KEYS.includes(k)));
  setSec(c, 'Profile', bulletsText(keys.map((k) => ({ k, v: p.map[k] || '' })), p.extra));
}
const roles = (c) => (profile(c).map.Role || '').split(',').map((x) => x.trim()).filter(Boolean);
function voiceStatus(c) {
  const raw = profile(c).map.Status || '';
  const m = /^voice sheet (not started|draft|approved)(?:,\s*(.*))?$/i.exec(raw);
  return m ? { state: m[1].toLowerCase(), note: m[2] || '' } : { state: raw ? '' : 'not started', note: raw };
}
function charNames(role) {
  return Object.values(S.chars).filter((c) => !role || roles(c).includes(role)).map((c) => c.name).sort();
}

// ---------- saving ----------
function charChanged(c, opts = {}) {
  S.cdirty.add(c.file);
  try { localStorage.setItem('se-cbackup-' + c.file, JSON.stringify({ t: Date.now(), file: c.file, text: serializeChar(c) })); } catch (e) {}
  setStatus();
  clearTimeout(S.csaveTimer);
  S.csaveTimer = setTimeout(saveChars, 600);
  if (opts.list) renderCharList();
  if (opts.page) renderCharPage();
}
async function saveChars() {
  for (const file of [...S.cdirty]) {
    const c = S.chars[file];
    try {
      if (c) await api('PUT', 'characters/' + encodeURIComponent(file), { text: serializeChar(c) });
      S.cdirty.delete(file);
      try { localStorage.removeItem('se-cbackup-' + file); } catch (e) {}
      S.offline = false;
    } catch (e) {
      S.offline = true;
      S.csaveTimer = setTimeout(saveChars, 3000);
      break;
    }
  }
  setStatus();
}

// ---------- mode ----------
function setMode(m) {
  S.mode = m;
  try { localStorage.setItem('se-mode', m); } catch (e) {}
  const parts = {
    scenes: ['#sidebar', '#canvas', '#inspector'],
    characters: ['#char-sidebar', '#char-page', '#char-used'],
    story: ['#story-sidebar', '#story-page', '#story-side'],
  };
  for (const k in parts) for (const id of parts[k]) $(id).classList.toggle('hidden', k !== m);
  document.querySelector('.scene-only').classList.toggle('hidden', m !== 'scenes');
  $('#scene-title').classList.toggle('hidden', m !== 'scenes');
  document.querySelectorAll('#mode-tabs button').forEach((b) => b.classList.toggle('active', b.dataset.mode === m));
  hideDropMenu();
  closeLinkPop();
  if (m === 'characters') { renderCharList(); renderCharPage(); }
  else if (m === 'story') { renderStoryList(); renderStoryPage(); }
  else renderAll();
}

// ---------- list ----------
function renderCharList() {
  const box = $('#char-list');
  box.innerHTML = '';
  const q = S.csearch.trim().toLowerCase();
  const all = Object.values(S.chars).filter((c) => !q || serializeChar(c).toLowerCase().includes(q));
  const groups = ROLES.concat(['Other']);
  let any = false;
  for (const g of groups) {
    const list = all.filter((c) => (g === 'Other' ? !roles(c).some((r) => ROLES.includes(r)) : roles(c).includes(g)))
      .sort((a, b) => a.name.replace(/^The /, '').localeCompare(b.name.replace(/^The /, '')));
    if (!list.length) continue;
    any = true;
    box.append(h('div', { class: 'group-head', text: g === 'Story NPC' ? 'Story NPCs' : g + 's' }));
    for (const c of list) {
      const p = profile(c).map;
      const sub = [p.Path, p.Class].filter(Boolean).join(' · ');
      box.append(h('div', { class: 'scene-item' + (c.file === S.ccur ? ' active' : ''), onclick: () => openChar(c.file) },
        h('div', { text: c.name }), sub ? h('div', { class: 'sub', text: sub }) : null));
    }
  }
  if (!any) box.append(h('div', { class: 'hint', style: 'padding:12px', text: q ? 'No matches.' : 'No characters yet.' }));
}
function openChar(file) {
  S.ccur = file;
  try { localStorage.setItem('se-char', file); } catch (e) {}
  renderCharList();
  renderCharPage();
  $('#char-page').scrollTop = 0;
}

// ---------- page ----------
function autoGrow(el) { el.style.height = 'auto'; el.style.height = (el.scrollHeight + 2) + 'px'; }
function charArea(c, h2, opts = {}) {
  const ta = h('textarea', {
    class: opts.cls || '', placeholder: opts.placeholder || '', value: getSec(c, h2),
    oninput: (e) => { autoGrow(e.target); setSec(c, h2, e.target.value); charChanged(c); renderCharUsed(); },
    onfocus: (e) => { S.lastCharTa = e.target; },
  });
  mdKeys(ta);
  requestAnimationFrame(() => autoGrow(ta));
  return ta;
}
function sec(title, ...kids) {
  return h('div', { class: 'char-sec' }, h('h2', {}, ...(Array.isArray(title) ? title : [title])), ...kids);
}
function chipSet(options, selected, onToggle) {
  return h('div', { class: 'chips' }, options.map((o) => h('label', { class: 'chip' + (selected.includes(o) ? ' on' : '') },
    h('input', { type: 'checkbox', checked: selected.includes(o), onchange: (e) => onToggle(o, e.target.checked) }), o)));
}
function renderCharPage() {
  const page = $('#char-page');
  const keep = page.scrollTop;
  page.innerHTML = '';
  datalists();
  const c = S.chars[S.ccur];
  renderCharUsed();
  if (!c) {
    page.append(h('div', { class: 'char-wrap' }, h('p', { class: 'hint', style: 'margin-top:40px;text-align:center', text: 'Pick a character on the left, or add a new one.' })));
    return;
  }
  const p = profile(c).map;
  const vs = voiceStatus(c);
  const wrap = h('div', { class: 'char-wrap' });
  S.lastCharTa = null;
  page.append(h('div', { class: 'char-toolbar' }, mdToolbar(() => (S.lastCharTa && document.body.contains(S.lastCharTa) ? S.lastCharTa : null)),
    h('span', { class: 'hint', text: 'Formats the text box you were last in.' })));
  const nameInput = h('input', {
    class: 'char-name', value: c.name, title: 'Click to rename',
    onkeydown: (e) => { if (e.key === 'Enter') e.target.blur(); if (e.key === 'Escape') { e.target.value = c.name; e.target.blur(); } },
    onchange: (e) => renameChar(c.file, e.target.value),
  });
  wrap.append(h('div', { class: 'row', style: 'display:flex;align-items:center;gap:10px' }, nameInput,
    h('span', { class: 'status-badge ' + vs.state, text: 'Voice sheet: ' + (VOICE_STATES[vs.state] || vs.note || '—') })));

  // profile
  const set = (k) => (v) => { setProfile(c, k, v); charChanged(c, { list: true }); };
  const field = (label, key, list) => h('div', {}, h('label', { text: label }),
    h('input', { value: p[key] || '', list: list || null, oninput: (e) => set(key)(e.target.value) }));
  const selectField = (label, key, options) => h('div', {}, h('label', { text: label }),
    h('select', { onchange: (e) => set(key)(e.target.value) },
      h('option', { value: '', text: '—' }),
      options.map((o) => h('option', { value: o, text: o, selected: (p[key] || '') === o ? true : null })),
      p[key] && !options.includes(p[key]) ? h('option', { value: p[key], text: p[key], selected: true }) : null));
  const curRoles = roles(c);
  const profs = (p.Proficiencies || '').split(',').map((x) => x.trim()).filter(Boolean);
  const allProfs = listOf('approaches').concat(listOf('proficiencies'));
  wrap.append(sec('Profile',
    h('label', { text: 'Role' }),
    chipSet(ROLES.concat(curRoles.filter((r) => !ROLES.includes(r))), curRoles, (r, on) => {
      const next = on ? curRoles.concat([r]) : curRoles.filter((x) => x !== r);
      setProfile(c, 'Role', ROLES.filter((x) => next.includes(x)).concat(next.filter((x) => !ROLES.includes(x))).join(', '));
      charChanged(c, { list: true, page: true });
    }),
    h('div', { class: 'profile-grid' },
      selectField('Background path', 'Path', listOf('backgrounds')),
      field('Race', 'Race', 'dl-race'),
      selectField('Class', 'Class', listOf('classes')),
      field('Subclass', 'Subclass', 'dl-subclass'),
      h('div', { style: 'grid-column: 1 / -1' }, h('label', { text: 'Home' }), h('input', { value: p.Home || '', list: 'dl-places', oninput: (e) => set('Home')(e.target.value) }))),
    h('label', { text: 'Proficiencies' }),
    chipSet(allProfs.concat(profs.filter((x) => !allProfs.includes(x))), profs, (x, on) => {
      const next = on ? profs.concat([x]) : profs.filter((y) => y !== x);
      setProfile(c, 'Proficiencies', allProfs.filter((y) => next.includes(y)).concat(next.filter((y) => !allProfs.includes(y))).join(', '));
      charChanged(c, { page: true });
    }),
    h('div', { class: 'profile-grid' },
      h('div', {}, h('label', { text: 'Voice sheet status' }),
        h('select', { onchange: (e) => { const st = voiceStatus(c); setProfile(c, 'Status', e.target.value ? 'Voice sheet ' + e.target.value + (st.note ? ', ' + st.note : '') : st.note); charChanged(c, { page: true }); } },
          vs.state ? null : h('option', { value: '', text: '(custom)', selected: true }),
          Object.keys(VOICE_STATES).map((k) => h('option', { value: k, text: VOICE_STATES[k], selected: k === vs.state ? true : null })))),
      h('div', {}, h('label', { text: 'Date / note' }),
        h('input', { value: vs.note, placeholder: 'Nov 21, 2026', oninput: (e) => { const st = voiceStatus(c); setProfile(c, 'Status', st.state ? 'Voice sheet ' + st.state + (e.target.value.trim() ? ', ' + e.target.value.trim() : '') : e.target.value); charChanged(c); } })))));

  wrap.append(sec('Background', charArea(c, 'Background', { placeholder: 'Who they are, where they come from, what happened to them.' })));
  wrap.append(sec('Personality', charArea(c, 'Personality', { placeholder: 'How they act and come across.' })));
  wrap.append(sec('Personal quest', charArea(c, 'Personal quest', { placeholder: 'Companions: the quest that powers them up.' })));
  wrap.append(relationsEditor(c));

  const voice = charArea(c, 'Voice sheet', { placeholder: 'How they talk, words they use and never use, what they want, sounds like, when they\'re not joking, sample lines.' });
  wrap.append(sec(['Voice sheet', h('span', { class: 'grow' }),
    getSec(c, 'Voice sheet').trim() ? null : h('button', { class: 'small', text: 'Insert template', onclick: async () => {
      setSec(c, 'Voice sheet', await voiceTemplate());
      charChanged(c, { page: true });
    } })],
  h('p', { class: 'hint', text: 'The voice standards for every line they say. Rules and tells to avoid: Writing guide.' }), voice));

  wrap.append(sec('Notes', charArea(c, 'Notes', { placeholder: 'Open points, ideas, things to check.' })));
  wrap.append(sec('Lines', h('p', { class: 'hint', text: 'Lines outside scenes (chime-ins, inn bar lines), as markdown. Scene lines are listed on the right.' }),
    charArea(c, 'Lines', { cls: 'lines' })));

  const extra = c.sections.filter((s) => !SECTION_ORDER.includes(s.h));
  for (const s of extra) wrap.append(sec(s.h, charArea(c, s.h)));

  wrap.append(h('div', { class: 'btn-row', style: 'margin-top:30px' },
    h('button', { class: 'danger', text: 'Delete character', onclick: () => deleteChar(c.file) })));
  wrap.append(h('p', { class: 'hint', text: 'Saved to design/characters/' + c.file + '.md' }));
  page.append(wrap);
  page.scrollTop = keep;
}
function relationsEditor(c) {
  const parsed = parseBullets(getSec(c, 'Relationships'));
  const save = (items) => { setSec(c, 'Relationships', bulletsText(items, parsed.extra)); charChanged(c); };
  const box = sec('Relationships');
  parsed.items.forEach((r, i) => {
    box.append(h('div', { class: 'row', style: 'display:flex;gap:6px;margin-top:4px' },
      h('input', { value: r.k, list: 'dl-allchars', placeholder: 'Who', style: 'flex:0 0 34%', oninput: (e) => { parsed.items[i].k = e.target.value; save(parsed.items); } }),
      h('input', { value: r.v, placeholder: 'How they relate', style: 'flex:1', oninput: (e) => { parsed.items[i].v = e.target.value; save(parsed.items); } }),
      S.chars[r.k] ? h('button', { class: 'small', text: '→', title: 'Open ' + r.k, onclick: () => openChar(r.k) }) : null,
      h('button', { class: 'small danger', text: '×', onclick: () => { parsed.items.splice(i, 1); save(parsed.items); renderCharPage(); } })));
  });
  for (const line of parsed.extra) box.append(h('p', { class: 'hint', text: line }));
  box.append(h('div', { class: 'btn-row' }, h('button', { class: 'small', text: '+ Relationship', onclick: () => {
    // a blank row isn't saved until it has text, so keep it on screen only
    parsed.items.push({ k: '', v: '' });
    const i = parsed.items.length - 1;
    box.insertBefore(h('div', { class: 'row', style: 'display:flex;gap:6px;margin-top:4px' },
      h('input', { list: 'dl-allchars', placeholder: 'Who', style: 'flex:0 0 34%', oninput: (e) => { parsed.items[i].k = e.target.value; save(parsed.items); } }),
      h('input', { placeholder: 'How they relate', style: 'flex:1', oninput: (e) => { parsed.items[i].v = e.target.value; save(parsed.items); } })), box.lastChild);
  } })));
  return box;
}
async function voiceTemplate() {
  if (!S.guideText) S.guideText = (await api('GET', 'chardoc/guide').catch(() => ({ text: '' }))).text || '';
  const m = /## Voice sheet template\n([\s\S]*?)(\n## |$)/.exec(S.guideText);
  return m ? m[1].trim() : '- **How they talk:**\n- **Words they use / never use:**\n- **What they want and what worries them:**\n- **Sounds like:**\n- **When they\'re not joking:**\n- **Sample lines:**';
}

// ---------- used in ----------
function usage(name) {
  const out = [];
  for (const sc of Object.values(S.scenes)) {
    const u = { sc, lines: [], trigger: false, cond: false };
    for (const t of sc.triggers || []) if (t.kind === 'person' && t.value === name) u.trigger = true;
    for (const id in sc.nodes) {
      const n = sc.nodes[id];
      if (n.type === 'line' && n.speaker === name) u.lines.push({ id, stage: n.stage, text: n.text });
      for (const o of n.options || []) {
        for (const ci of (o.check && o.check.chimeIns) || []) if (ci.who === name) u.lines.push({ id, stage: 'chime-in', text: ci.text });
        for (const cd of o.conditions || []) if ((cd.kind === 'companion' || cd.kind === 'nocompanion') && cd.value === name) u.cond = true;
      }
      for (const cd of n.conditions || []) if ((cd.kind === 'companion' || cd.kind === 'nocompanion') && cd.value === name) u.cond = true;
    }
    if (u.lines.length || u.trigger || u.cond) out.push(u);
  }
  return out.sort((a, b) => (a.sc.title || '').localeCompare(b.sc.title || ''));
}
function pairLines(name) {
  const out = [];
  for (const line of (S.pairsText || '').split('\n')) {
    const cells = line.trim().replace(/^\||\|$/g, '').split('|').map((x) => x.trim());
    if (cells.length < 2 || cells[0] === 'Pair' || cells[0].startsWith('---')) continue;
    if (cells[0].split(' and ').map((x) => x.trim()).includes(name)) out.push({ pair: cells[0], text: cells[1] });
  }
  return out;
}
function goToNode(sceneId, nodeId) {
  setMode('scenes');
  openScene(sceneId);
  if (nodeId) { S.sel = nodeId; renderCanvas(); renderInspector(); focusNode(nodeId); }
}
function renderCharUsed() {
  const box = $('#char-used');
  box.innerHTML = '';
  const c = S.chars[S.ccur];
  const body = h('div', { class: 'used-body' });
  box.append(h('div', { class: 'tabs' }, h('button', { class: 'active', text: 'Used in' })), body);
  if (!c) return;
  const uses = usage(c.name);
  body.append(h('h3', { text: 'Scenes' }));
  if (!uses.length) body.append(h('p', { class: 'hint', text: 'Not in any scene yet. Scenes find a character by name: as a speaker, a Person trigger, a chime-in or a party condition.' }));
  for (const u of uses) {
    const why = [u.lines.length ? u.lines.length + (u.lines.length === 1 ? ' line' : ' lines') : '', u.trigger ? 'trigger' : '', u.cond ? 'party condition' : ''].filter(Boolean).join(', ');
    body.append(h('div', { class: 'used-line', onclick: () => goToNode(u.sc.id) },
      h('div', { text: u.sc.title || u.sc.id }), h('div', { class: 'where', text: why })));
  }
  const lines = uses.flatMap((u) => u.lines.map((l) => Object.assign({ sc: u.sc }, l)));
  if (lines.length) {
    body.append(h('h3', { text: 'Every scene line' }));
    for (const l of lines) body.append(h('div', { class: 'used-line', onclick: () => goToNode(l.sc.id, l.id) },
      h('div', { class: 'where', text: l.sc.title || l.sc.id }),
      l.stage ? h('div', { class: 'stage', text: '(' + l.stage + ')' }) : null,
      h('div', { text: l.text || '(empty)' })));
  }
  const pairs = pairLines(c.name);
  if (pairs.length) {
    body.append(h('h3', { text: 'Inn banter (Pairs)' }));
    for (const p of pairs) body.append(h('div', { class: 'used-line', style: 'cursor:default' }, h('div', { class: 'where', text: p.pair }), h('div', { text: p.text })));
  }
  const refs = storyRefs('characters', c.name);
  if (refs.length) {
    body.append(h('h3', { text: 'In the story' }));
    for (const r of refs) body.append(h('div', { class: 'used-line', onclick: () => { setMode('story'); openStory(r.file, r.index); } },
      h('div', { text: r.chapter }), h('div', { class: 'where', text: r.file === MAIN_FILE ? 'Main campaign' : r.file + ' path' })));
  }
  const rel = Object.values(S.chars).filter((o) => o !== c && parseBullets(getSec(o, 'Relationships')).items.some((r) => r.k === c.name));
  if (rel.length) {
    body.append(h('h3', { text: 'Named by' }));
    for (const o of rel) {
      const r = parseBullets(getSec(o, 'Relationships')).items.find((x) => x.k === c.name);
      body.append(h('div', { class: 'used-line', onclick: () => openChar(o.file) }, h('div', { text: o.name }), h('div', { class: 'where', text: r.v })));
    }
  }
}

// ---------- new / rename / delete ----------
function badName(name, except) {
  if (!name) return 'Give them a name.';
  if (/[\/\\]/.test(name) || name.startsWith('.')) return 'Names can\'t contain / or \\ or start with a dot.';
  if (['00 Writing guide', 'Pairs', 'Places'].includes(name)) return 'That name is taken by a doc in characters/.';
  if (Object.keys(S.chars).some((f) => f !== except && f.toLowerCase() === name.toLowerCase())) return 'There is already a character called ' + name + '.';
  return null;
}
function newChar() {
  modal(h('div', {},
    h('h2', { text: 'New character' }),
    h('label', { text: 'Name (also the file name)' }),
    h('input', { id: 'nc-name', placeholder: 'King Grel', onkeydown: (e) => { if (e.key === 'Enter') $('#nc-ok').click(); } }),
    h('label', { text: 'Role' }),
    h('select', { id: 'nc-role' }, ROLES.map((r) => h('option', { value: r, text: r }))),
    h('p', { class: 'hint', id: 'nc-err' }),
    h('div', { class: 'btn-row' },
      h('button', { id: 'nc-ok', class: 'primary', text: 'Create', onclick: () => {
        const name = $('#nc-name').value.trim();
        const err = badName(name);
        if (err) { $('#nc-err').textContent = err; return; }
        const c = { file: name, name, intro: CHAR_INTRO, sections: [] };
        setProfile(c, 'Role', $('#nc-role').value);
        setProfile(c, 'Status', 'Voice sheet not started');
        S.chars[name] = c;
        closeModal();
        charChanged(c);
        openChar(name);
      } }),
      h('button', { text: 'Cancel', onclick: closeModal }))));
  $('#nc-name').focus();
}
async function renameChar(oldFile, raw) {
  const name = raw.trim();
  const c = S.chars[oldFile];
  if (!c || name === c.name) return;
  const err = badName(name, oldFile);
  if (err) { alert(err); renderCharPage(); return; }
  if (!confirm(`Rename ${c.name} to ${name}? The file becomes ${name}.md, and scenes, story links and relationships that use the old name are updated. Links to the old file in the design docs need updating too (ask Claude).`)) { renderCharPage(); return; }
  const old = c.name;
  c.name = name; c.file = name;
  delete S.chars[oldFile]; S.chars[name] = c;
  S.cdirty.delete(oldFile);
  try { localStorage.removeItem('se-cbackup-' + oldFile); } catch (e) {}
  for (const sc of Object.values(S.scenes)) {
    let hit = false;
    const fix = (obj, key) => { if (obj && obj[key] === old) { obj[key] = name; hit = true; } };
    for (const t of sc.triggers || []) if (t.kind === 'person') fix(t, 'value');
    for (const id in sc.nodes) {
      const n = sc.nodes[id];
      if (n.type === 'line') fix(n, 'speaker');
      for (const cd of n.conditions || []) fix(cd, 'value');
      for (const o of n.options || []) {
        for (const cd of o.conditions || []) fix(cd, 'value');
        for (const ci of (o.check && o.check.chimeIns) || []) fix(ci, 'who');
      }
    }
    if (hit) markDirty(sc.id);
  }
  for (const o of Object.values(S.chars)) {
    const pr = parseBullets(getSec(o, 'Relationships'));
    if (pr.items.some((r) => r.k === old)) {
      for (const r of pr.items) if (r.k === old) r.k = name;
      setSec(o, 'Relationships', bulletsText(pr.items, pr.extra));
      charChanged(o);
    }
  }
  relinkStory('characters', old, name);
  charChanged(c);
  await saveChars();
  try { await api('DELETE', 'characters/' + encodeURIComponent(oldFile)); } catch (e) {}
  S.ccur = name;
  renderCharList(); renderCharPage();
}
async function deleteChar(file) {
  const c = S.chars[file];
  if (!confirm(`Delete ${c.name}? The file design/characters/${file}.md is removed (git still has it if it was committed).`)) return;
  delete S.chars[file];
  S.cdirty.delete(file);
  try { await api('DELETE', 'characters/' + encodeURIComponent(file)); } catch (e) {}
  S.ccur = null;
  renderCharList(); renderCharPage();
}

// ---------- boot ----------
async function initCharacters() {
  S.chars = {}; S.cdirty = new Set(); S.ccur = null; S.csearch = '';
  try {
    for (const f of await api('GET', 'characters')) S.chars[f.file] = parseChar(f.file, f.text);
    S.pairsText = (await api('GET', 'chardoc/pairs')).text;
  } catch (e) {}
  $('#btn-new-char').onclick = newChar;
  $('#char-search').oninput = (e) => { S.csearch = e.target.value; renderCharList(); };
  document.querySelectorAll('#mode-tabs button').forEach((b) => b.onclick = () => setMode(b.dataset.mode));
  try { const f = localStorage.getItem('se-char'); if (f && S.chars[f]) S.ccur = f; } catch (e) {}
}
