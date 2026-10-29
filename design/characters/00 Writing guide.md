# Writing guide

How HexGen's characters are written (set up Oct 28, 2026, after the first bar lines read as "AI written"). Each character's voice sheet and lines live in this folder, one file per character, so writing for someone means opening one file.

- **This guide:** the rules for dialogue and narration, the line types, the tells to avoid, how we write, and the voice sheet template.
- **One file per companion:** [Fluffy](Fluffy.md), [Chelmsford](Chelmsford.md), [Mel](Mel.md), [Grant Augustus](Grant%20Augustus.md), [Kris Huntington](Kris%20Huntington.md), [Timothy](Timothy.md), [Dolmund](Dolmund.md), [Lilian](Lilian.md), [Frim](Frim.md), [Grimhold](Grimhold.md), [Leo Conley](Leo%20Conley.md), [Reginald](Reginald.md). Each holds their voice sheet, then every line they say, grouped by where it's said.
- **[Pairs](Pairs.md):** inn banter between two companions. A line that belongs to two characters is written there, once.
- **Story NPCs** get a file when they have enough lines. Until then their lines stay with their scene in [World & story](../01%20World%20%26%20story.md) (e.g. The Lady of the Lake).
- Bios, homes and personal quests stay in [World & story](../01%20World%20%26%20story.md) → NPC homes and stories; proficiencies in World & story → Companion proficiencies.

## Dialogue rules

Patterns for writing social encounters (decided Oct 28, 2026). Check rules: [Classes & combat](../03%20Classes%20%26%20combat.md) → Checks outside combat. How it shows: [Presentation](../07%20Presentation.md) → Social encounter screen.

- **The hero speaks as intent only.** A hero option names what the hero wants or does ("Ask about the sword"); the hero's own words are never written out. Every other character, NPCs and companions alike, speaks in written lines.
- **The hero's voice is neutral.** Options fit any hero. Backgrounds add flavour where it matters: an extra option for that background, or an NPC reacting to who the hero is (see Background variances under Shared main story).
- **NPC lines have no set length.** Write what the moment needs; long speeches page with a tap.
- **A tagged option names the angle.** The text says what the hero leans on ("Appeal to her honour", "Claim a knight's right", "Threaten the lake"), and the tag names the approach (Persuade, Deceive, Intimidate).
- **Replies show the consequence.** After a check, pass or fail, the NPC reacts in character and says what changes in the world ("Then the sword stays hidden from you"), so the cost of failing is clear in the story. Rewards also show as chips on screen.
- **Scenes with no speaker use narration** (decided Oct 28, 2026): short, neutral and in the second person ("The stone stands alone beneath an open sky"). It describes what the party sees and what happens, never what the hero thinks or says.
- **Choices are free per scene.** No fixed count or mix of options: each conversation offers what fits, tagged or not, and any kind of check can be an option ([Classes & combat](03 Classes & combat.md) → Checks outside combat).
- **Failure costs fit the approach.** A gentle approach failing can cost little (the NPC says no); a harsh one can cost a lot, even a fight. Whether an NPC fights back is set per scene.
- **Accents and dialect spelling** (decided Oct 28, 2026): a character's spoken lines can use their own spelling and words, like an accent: Chelmsford's lines are in British spelling and terms ("armour", "colour", "cuppa"). UI text, item names and narration keep the game's own spelling.
- **Stage notes** go in brackets and show in small italics above the line, e.g. "(cracks his knuckles)". They describe what we see, not explain the joke.

## Line types

- **Companion chime-ins:** each companion has a generic line per approach they're proficient in, said in any conversation, plus hand-written special lines for big story NPCs (e.g. Chelmsford with the Lady of the Lake). For now, one generic line per approach; more can be added later so they repeat less.
- **Inn banter** (decided Oct 28, 2026; how it shows: [Presentation](../07%20Presentation.md) → Town screen): a night at an inn's bar is where the party's personality shows. Companions talk to each other in **pair banter**, short written exchanges for particular pairs ([Pairs](Pairs.md)), with one **fallback bar line** per companion (in their file) for pairs that have no exchange. **Which pairs:** the six path pairs first (the two companions each background brings), then cross-path pairs that clash or click; lines can't lean on shared history, since outside their own path the two meet separately. The night ends with **the toast as a choice**: the hero picks an intent option and a narration beat answers it, with no companion line.

| Toast | Narration |
| --- | --- |
| Stand on the table and raise a toast | "You climb onto the table. Mugs go up all over the room, and the whole inn roars." |
| Toast whoever's paying | "The table cheers. Behind the bar, the innkeeper starts adding up the tab." |
| Toast absent friends | "The table goes quiet. Mugs touch, softly, and nobody says anything for a while." |

## Tells to avoid

Patterns that make lines read as machine-written (listed Oct 28, 2026). Check every draft against this list.

- **Every line a setup and a punchline.** Most lines in a scene should just be talk: plain, awkward, mid-thought, sincere or a little off-topic. One joke in a scene lands better than four.
- **The same rhythms.** The three-beat build ("I can tell. I can always tell."), "X. Not Y.", a "(a beat)" pause before the payoff, and a one-word tag on the end ("Truly.", "Honestly.", "Personally.", "Rhythmically.").
- **Too many jokes are the character's trait** (softened Oct 29, 2026). Fluffy is royal, Mel steals, Kris hunts, Grant rhymes. A line that leans on the trait is fine ("Ha! Dwarves are built for this."), but if most of a character's lines only point at their bio, they become a summary of themselves. Mix in lines that show the trait sideways, or show something else.
- **Tics carrying the voice.** "Ja", "darling", "sweetheart" and the stammer are seasoning, not the voice. Take them out: if the line no longer sounds like the character, it wasn't in their voice.
- **Nothing specific.** Name the dish, the place, the person, or something that happened on this run. A generic inn and generic ale read as filler.
- **Forgetting who they are.** Check the bio before every line: Mel is a small girl, so no drinking at the bar; Grant is a bard, so he can rhyme.
- **Everyone equally clever.** Characters can be wrong, slow, rambling, rude, boring or not in on the joke.

## How we write

1. **Voice sheet first.** No new lines for a character until their voice sheet is filled in and Ethan has approved it.
2. **Who drafts.** Ethan's rough lines or voice notes come first where he has them; Claude tidies and files them. When Claude drafts, the options are mixed, not four quips: one plain, one earnest, one odd, one funny (or a single draft for Ethan to rewrite).
3. **Check the tells** above before offering any line.
4. **Blind test.** Hide the name: if you can't tell who's talking, it isn't in their voice yet.
5. **Pair lines wait for both voices** (decided Oct 28, 2026): a pair's exchange is reviewed and changed only once both companions' voice sheets are done, so one half isn't rewritten against a partner who may still change.
6. **Filing.** A line goes in the speaker's file under where it's said (a pair's line in [Pairs](Pairs.md)), with the date it was written.

## Voice sheet template

- **How they talk:** sentence length, formal or loose, fast or slow, what their grammar does.
- **Words they use / never use:**
- **What they want and what worries them** (right now, in the story):
- **Sounds like:** a real or fictional person to steer by.
- **When they're not joking:** how they sound when it's serious, tired or sad.
- **Sample lines** (Ethan's, as anchors):

## Open questions

- [ ] Voice sheets for the other 5 companions (Fluffy's, Chelmsford's, Mel's, Grant's and Kris's are done, Oct 28, 2026, and Timothy's and Dolmund's, Oct 29: Ethan's sample lines first, then the fields as choices)
- [ ] Review the lines written before the voice sheets (chime-ins and bar lines, Oct 28, 2026) against each sheet and the tells list, and redo the weakest
- [ ] Inn banter still to write, after the voice sheets: fallback bar lines for Lilian (about wanting to dance), Frim, Grimhold, Leo Conley and Reginald; then cross-path pairs
- [ ] More chime-in lines per proficiency later, so they repeat less
