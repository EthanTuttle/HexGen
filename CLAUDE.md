# HexGen — instructions for Claude

This repo holds the design docs for HexGen, Ethan's card-driven, D&D-style hex-crawl RPG for PC and mobile. The art style is Dorfromantik-like. Players place map cards to build the world, then walk their hero through it, fight on a tactical grid with coin flips, and refresh their hand through fights, quests and finished regions.

## Source of truth

- The design docs in `design/` are the canon. Before answering or proposing anything, read the relevant doc. If something isn't in the docs, it hasn't been decided.
- When a decision is made, write it into the right doc in the same turn. Update every place it touches so nothing contradicts it, and tick it off or add it to the Open questions list.
- Commit finished doc changes and push them. Don't just paste the text into chat.

## Working with git (several sessions run at once)

- Start every session by pulling the latest `main` (`git pull`), and read a doc fresh from disk right before editing it.
- Work on your own branch per session (e.g. `claude/<topic>`), commit small, and merge back to `main` often. Don't leave branches open for days on docs another session is editing.
- Before merging, pull `main` again. If there's a conflict, merge both sides by hand so neither session's decisions are lost, and tell Ethan what you merged. Never resolve a conflict by throwing one side away.
- The master open-questions list in `design/00 Index.md` is touched by most decisions, so expect conflicts there and merge them line by line.

## How to work with Ethan

- Content comes only from Ethan. Never invent design decisions, names, numbers or lore and present them as settled. You can propose ideas, but nothing goes into a doc until he picks or approves it.
- Work through decisions with the multiple-choice question tool. For detailed content, such as mastery trees, quests or NPCs, go one branch or tier at a time, with 3–4 distinct options for each choice.
- Before asking about an existing thing (a weapon, class, NPC or region), remind him what the docs already say about it. Put that reminder in the question text itself.
- Flag conflicts and balance risks instead of quietly accepting them. Examples: Fighters can mix mastery branches, so look at what their combined nodes do; a new rule can contradict an older section; a card can overlap an existing one.
- If an answer is ambiguous or doesn't fit the question, ask a short follow-up rather than guessing.
- Write in plain language, keep explanations short, and use tables when comparing options.

## Doc organisation

- Split the design by area, with one doc each: World & story; Classes & combat; Weapons & gear; Map & exploration; Cards & progression; Multiplayer & tech (plus Presentation). Keep a short index doc (`design/00 Index.md`) that links them all.
- Write each rule in one place only. Other docs link to it rather than restating it.
- Each doc ends with its own open questions, and the index keeps the master list.
- Production briefs live in `design/briefs/`.
- Character writing lives in `design/characters/`: `00 Writing guide.md` (rules, tells to avoid, how we write, voice sheet template), one file per character (voice sheet, then every line they say) `Pairs.md` for lines shared by two companions, and `Places.md` for lines in generated places (towns), written per moment slot. Read the guide and the character's voice sheet before drafting any line.

## Mockups

- The rules for every screen live in `design/07 Presentation.md`. Mockups only illustrate them.
- Mockup versions are never changed or overwritten: always make a copy and bump the version (v2, v3a…). Rejected versions stay for reference.
- The live mockups are Design canvases on claude.ai (links in `design/07 Presentation.md` → Mockup index). `mockups/` holds a copy of each canvas's source (see `mockups/README.md`). The `.dc.html` files need the canvas runtime to render, so they don't open on their own in a browser.
- Keep `mockups/` in sync: whenever you change a canvas, copy every changed file (artboards and `canvas.json`) into its folder in `mockups/` and commit it in the same turn. A new canvas gets a new folder and a row in `mockups/README.md`.
