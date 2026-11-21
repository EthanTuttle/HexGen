# Scenes

Branching scenes: social encounters, narration tied to places and people, and any conversation with choices (set up Nov 21, 2026). **The scene files here are canon for those scenes.** Docs link to a scene instead of copying its lines.

- **Write them in the story editor:** double-click `tools/story-editor/Start Story Editor.command` (or run `python3 tools/story-editor/server.py`). It opens in the browser, runs offline, and saves each change straight into this folder. How it works: [tools/story-editor/README.md](../../tools/story-editor/README.md).
- **The rules still live in the docs.** Dialogue rules and tells to avoid: [characters → Writing guide](../characters/00%20Writing%20guide.md). Check rules (approaches, who flips, chime-ins, failure): [Classes & combat](../03%20Classes%20%26%20combat.md) → Checks outside combat. How scenes show: [Presentation](../07%20Presentation.md) → Social encounter screen.
- **What stays in markdown:** voice sheets, generic chime-in lines, inn banter ([Pairs](../characters/Pairs.md)) and place slot lines ([Places](../characters/Places.md)). Those are lists, not trees.
- **Lines come from Ethan**, as everywhere else: a scene file holds approved lines only. Drafts go in the scene's notes, or in chat until Ethan picks them.

## Files

- One `<scene-id>.json` per scene, named in lowercase with dashes (`lady-of-the-lake.json`).
- `_lists.json` holds the names that fill the editor's dropdowns (companions, places, backgrounds, classes, proficiencies…). They're copied from the docs, so update them when the docs change (the editor's **Lists** button).

## Scene format

```
{
  "id": "lady-of-the-lake",
  "title": "The Lady of the Lake",
  "notes": "What the scene is for, open points",
  "triggers": [{ "kind": "place", "value": "Lady of the Lake" }],
  "start": "n1",
  "nodes": { "n1": { ... }, "n2": { ... } }
}
```

**Triggers** say what starts the scene: `place`, `person`, `encounter`, `quest` or `other`, each with a name. The editor groups scenes by place and by person (a scene is also listed under everyone who speaks in it).

**Nodes.** Every node has a `type` and its `x`/`y` on the canvas. Links name the next node's id.

| Type | Fields | Links |
| --- | --- | --- |
| `line` | `speaker`, `stage` (stage note), `text` | `next` |
| `narration` | `text` | `next` |
| `choice` | `options` (below) | per option |
| `branch` | `conditions`, `match` (`all` or `any`) | `yes`, `no` |
| `setflag` | `flags`: `[{ "name", "op": "set" or "clear" }]` | `next` |
| `end` | `outcome` (`leave`, `fight`, `scene`), `scene` (for `scene`), `reward`, `notes` | none |

**Options** (in a `choice`): `id`, `intent` (the hero's intent, never their words), `once` (hide after it's picked), `conditions` (all must hold for the option to show) and an optional `check`:

```
"check": {
  "type": "approach" | "proficiency" | "ability",
  "skill": "Persuade",
  "failCost": "She just says no",
  "fight": true,
  "chimeIns": [{ "who": "Chelmsford", "text": "..." }]
}
```

An option without a check links with `next`. An option with a check links with `pass` and `fail`. `chimeIns` are the special lines for big story NPCs; without one, a companion's generic chime-in line plays. Bare ability checks have none.

**Conditions:** `{ "kind", "value" }`, where kind is `background`, `class`, `subclass`, `race`, `companion` (in the party), `nocompanion`, `flag` (set) or `noflag`.

**Flags** are shared by all scenes: one scene sets `met-hermit`, another shows an option only if it's set.

## Open questions

- [ ] How the game loads scene files (Godot reads the JSON; not built yet)
- [ ] Move the existing sword pull scene ([World & story](../01%20World%20%26%20story.md) → The sword pull scene) into a scene file?
- Already open elsewhere, and the format leaves room for both: whether a failed social check can be retried in the same conversation ([Classes & combat](../03%20Classes%20%26%20combat.md) → Open questions), and the coins and heads needed per dialogue check.
