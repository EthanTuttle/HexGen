// Showcase page. All content comes from gallery.js (built by build_gallery.py).
const G = window.GALLERY || { featured: [], approved: [], evolution: [], combatMaps: [], shots: [] };

const SECTIONS = { map: "The map", combat: "Combat", places: "Towns & places", minis: "Heroes & beasts" };
const PAGE = 24;

const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, props = {}, ...kids) => {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...kids.filter(k => k != null));
  return node;
};
const niceDate = d => d ? new Date(d + "T12:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";

// ---- Backdrop drifts through the day clock's pastels as you scroll (07 → Art direction) ----
const SKY = ["#F4DCCB", "#D9E7EC", "#D9E7EC", "#EDCFD7", "#A9AECB"]; // dawn, morning, midday, dusk, night
const hex = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
function paintSky() {
  const max = document.documentElement.scrollHeight - innerHeight;
  const t = max > 0 ? Math.min(1, scrollY / max) * (SKY.length - 1) : 0;
  const i = Math.min(SKY.length - 2, Math.floor(t)), f = t - i;
  const [a, b] = [hex(SKY[i]), hex(SKY[i + 1])];
  const mix = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  document.documentElement.style.setProperty("--backdrop", `rgb(${mix.join(",")})`);
}
addEventListener("scroll", paintSky, { passive: true });
addEventListener("resize", paintSky);

// ---- Hero: cross-fades the featured renders ----
function hero() {
  const box = $("#hero-art");
  const items = G.featured.length ? G.featured : G.approved.filter(a => a.kind === "image").slice(-5);
  const imgs = items.map((it, i) => {
    const img = el("img", { src: it.src, alt: it.title, loading: i ? "lazy" : "eager" });
    if (!i) img.classList.add("on");
    box.append(img);
    return img;
  });
  if (imgs.length < 2 || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  let n = 0;
  setInterval(() => {
    imgs[n].classList.remove("on");
    n = (n + 1) % imgs.length;
    imgs[n].classList.add("on");
  }, 5000);
}

// ---- Cards and the lightbox ----
let lbList = [], lbIndex = 0;

function card(item, list, meta) {
  const thumb = el("div", { className: "thumb" });
  if (item.kind === "video") {
    thumb.append(el("video", { src: item.src, muted: true, preload: "metadata", playsInline: true }),
                 el("div", { className: "play", textContent: "▶" }));
  } else {
    thumb.append(el("img", { src: item.thumb || item.src, alt: item.title, loading: "lazy" }));
  }
  const node = el("button", { className: "card", type: "button" }, thumb,
    el("div", { className: "body" },
      el("h3", { textContent: item.title }),
      meta ? el("div", { className: "meta", textContent: meta }) : null,
      item.note ? el("p", { className: "note", textContent: item.note }) : null));
  node.addEventListener("click", () => openLightbox(list, list.indexOf(item)));
  return node;
}

function openLightbox(list, index) {
  lbList = list; lbIndex = index;
  showLightbox();
  $("#lightbox").hidden = false;
  document.body.style.overflow = "hidden";
}
function showLightbox() {
  const it = lbList[lbIndex], box = $("#lightbox");
  const media = $(".lb-media", box);
  media.replaceChildren(it.kind === "video"
    ? el("video", { src: it.src, controls: true, autoplay: true, loop: true, muted: true, playsInline: true })
    : el("img", { src: it.src, alt: it.title }));
  $(".lb-title", box).textContent = it.title;
  $(".lb-meta", box).textContent = [it.variant, niceDate(it.date), `${lbIndex + 1} of ${lbList.length}`].filter(Boolean).join(" · ");
  $(".lb-note", box).textContent = it.note || "";
}
function closeLightbox() {
  $("#lightbox").hidden = true;
  $(".lb-media").replaceChildren();
  document.body.style.overflow = "";
}
function stepLightbox(d) {
  lbIndex = (lbIndex + d + lbList.length) % lbList.length;
  showLightbox();
}
$(".lb-close").addEventListener("click", closeLightbox);
$(".lb-prev").addEventListener("click", () => stepLightbox(-1));
$(".lb-next").addEventListener("click", () => stepLightbox(1));
$("#lightbox").addEventListener("click", e => { if (e.target.id === "lightbox") closeLightbox(); });
addEventListener("keydown", e => {
  if ($("#lightbox").hidden) return;
  if (e.key === "Escape") closeLightbox();
  if (e.key === "ArrowLeft") stepLightbox(-1);
  if (e.key === "ArrowRight") stepLightbox(1);
});

// ---- A filterable grid with "Show more" ----
function filteredGrid({ items, grid, filters, groupOf, groups, meta }) {
  let current = "all", shown = PAGE;
  const more = el("div", { className: "more" });
  grid.after(more);

  function render() {
    const list = current === "all" ? items : items.filter(i => groupOf(i) === current);
    grid.replaceChildren(...list.slice(0, shown).map(i => card(i, list, meta(i))));
    more.replaceChildren();
    if (list.length > shown) {
      const btn = el("button", { className: "token", type: "button", textContent: `Show more (${list.length - shown})` });
      btn.addEventListener("click", () => { shown += PAGE; render(); });
      more.append(btn);
    }
  }
  const chip = (key, label, count) => {
    const b = el("button", { className: "chip", type: "button", role: "tab" }, label, el("small", { textContent: count }));
    b.setAttribute("aria-selected", key === current);
    b.addEventListener("click", () => {
      current = key; shown = PAGE;
      filters.querySelectorAll(".chip").forEach(c => c.setAttribute("aria-selected", c === b));
      render();
    });
    return b;
  };
  filters.append(chip("all", "All", items.length),
    ...groups.map(([key, label]) => chip(key, label, items.filter(i => groupOf(i) === key).length))
      .filter(c => c.lastChild.textContent !== "0"));
  render();
}

// ---- Sections ----
function shots() {
  const grid = $("#shots");
  if (!G.shots.length) {
    grid.append(el("p", { className: "empty", textContent: "No screenshots yet. See site/README.md for how to add them." }));
    return;
  }
  grid.append(...G.shots.map(s => card(s, G.shots)));
}

function world() {
  const items = [...G.approved].reverse();
  filteredGrid({
    items, grid: $("#world-grid"), filters: $("#world-filters"),
    groupOf: i => i.section, groups: Object.entries(SECTIONS),
    meta: i => [SECTIONS[i.section], niceDate(i.date)].filter(Boolean).join(" · "),
  });
}

function combat() {
  const terrains = [...new Set(G.combatMaps.map(m => m.terrain))];
  filteredGrid({
    items: G.combatMaps, grid: $("#combat-grid"), filters: $("#combat-filters"),
    groupOf: m => m.terrain, groups: terrains.map(t => [t, t]),
    meta: m => m.variant,
  });
}

function evolution() {
  const picker = $("#evo-picker"), box = $("#evo");
  if (!G.evolution.length) return;

  function show(evo, chipBtn) {
    picker.querySelectorAll(".chip").forEach(c => c.setAttribute("aria-selected", c === chipBtn));
    const steps = evo.steps, last = steps[steps.length - 1];
    let before = steps[0];

    const beforeImg = el("img", { className: "before", alt: "" });
    const afterImg = el("img", { src: last.src, alt: last.title });
    const tagL = el("span", { className: "tag l" });
    const range = el("input", { type: "range", min: 0, max: 100, value: 50, "aria-label": "Compare" });
    const cmp = el("div", { className: "compare" }, afterImg, beforeImg,
      el("div", { className: "handle" }), tagL, el("span", { className: "tag r", textContent: `v${last.version} · approved` }), range);
    range.addEventListener("input", () => cmp.style.setProperty("--split", range.value + "%"));

    const note = el("p", { className: "evo-note" });
    const strip = el("div", { className: "steps" });

    function pick(step) {
      before = step;
      beforeImg.src = step.src;
      tagL.textContent = `v${step.version}`;
      strip.querySelectorAll(".step").forEach(b => b.setAttribute("aria-pressed", b.dataset.src === step.src));
      const verdict = step.verdict ? `${step.verdict[0].toUpperCase()}${step.verdict.slice(1)}` : "Work in progress";
      note.replaceChildren(el("strong", { textContent: `v${step.version} · ${verdict}${step.date ? " · " + niceDate(step.date) : ""}` }),
        step.note ? ` — ${step.note}` : "");
    }

    steps.slice(0, -1).forEach(s => {
      const b = el("button", { className: "step", type: "button" },
        el("img", { src: s.thumb || s.src, alt: "", loading: "lazy" }),
        el("span", { className: s.verdict ? "v-" + s.verdict : "" , textContent: `v${s.version}${s.verdict ? " · " + s.verdict : ""}` }));
      b.dataset.src = s.src;
      b.addEventListener("click", () => pick(s));
      strip.append(b);
    });

    box.replaceChildren(cmp, strip, note);
    pick(before);
  }

  G.evolution.forEach((evo, i) => {
    const b = el("button", { className: "chip", type: "button", textContent: evo.title });
    b.addEventListener("click", () => show(evo, b));
    picker.append(b);
    if (!i) show(evo, b);
  });
}

hero();
shots();
world();
combat();
evolution();
paintSky();
