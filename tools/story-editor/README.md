# Story editor

A local tool for writing the branching scenes in `design/scenes/` and keeping the character files in `design/characters/`. It runs offline: a small Python server (standard library only, macOS already has it) serves the page and saves each change into the repo. The scene format is in [design/scenes/README.md](../../design/scenes/README.md).

## Start it

- **Desktop app:** double-click **Story Editor** on the Desktop. It starts the editor in the background (no Terminal window) and stops on its own 10 minutes after you close the last editor tab. Its log is `~/Library/Logs/StoryEditor.log`. To make the app (again, or after the repo moves), run `bash tools/story-editor/make_desktop_app.sh` from the shared checkout.
- **Or** double-click **Start Story Editor.command** in Finder (the first time, macOS may ask you to allow it: right-click → Open). This one runs in a Terminal window: close it, or press Ctrl+C, to stop.
- **Or** in a terminal: `python3 tools/story-editor/server.py`

Each way opens http://127.0.0.1:47380 in the browser. If the editor is already running, starting it again just opens the page.

## Using it

**Scenes** and **Characters** are the two tabs at the top.

### Characters

- **The list** groups characters by role (companions, mentors, story NPCs, villains). Search covers everything in their files.
- **A character's page** edits their file in `design/characters/`: profile (role, background path, race, class, subclass, home, proficiencies, voice sheet status), background, personality, personal quest, relationships, voice sheet, notes and their non-scene lines. Click the name to rename them. **Insert template** fills an empty voice sheet with the template from the Writing guide.
- **Used in** (right) lists the scenes they're in (as a speaker, a Person trigger, a chime-in or a party condition), every line they say in scenes (click one to jump to it), their inn banter from Pairs.md, and who names them as a relationship.
- **+ Character** makes a new file. Renaming updates the scenes and relationships that use the old name; links to the file in the design docs need updating by hand (or by Claude).
- Sections the editor doesn't know about are kept as they are, and a file nobody edits is never rewritten.

### Scenes

- **Scenes** are on the left. Search covers titles, triggers and every line. The Places and People tabs group scenes by what starts them and who speaks in them.
- **The canvas** holds the nodes. Drag a node by its coloured header. Drag on empty space, or scroll with two fingers, to move around; pinch (or ⌘ + scroll) to zoom. **F** fits the scene in view.
- **Adding nodes:** use the bar at the bottom, or double-click empty space. With a node selected, a new node is placed to its right and linked from its first free output.
- **Linking:** drag from a dot on the right of a node onto another node. Drop on empty space to make a new node that's already linked. Click a link to remove it.
- **Editing:** click a node to edit it on the right. With nothing selected, the right panel edits the scene (title, triggers, notes, file name).
- **Problems** lists what needs a look: dead ends, unreachable nodes, checks without a fail branch, hero options written as speech, narration in the first person, "(a beat)", and flags that nothing sets.
- **Keys:** ⌘Z / ⇧⌘Z undo and redo, Delete removes the selected node, ⌘D duplicates it, Esc deselects.
- **Lists** edits the names in the dropdowns (`design/scenes/_lists.json`).

Every change saves on its own within a second ("Saved" in the top right). If the server stops, the status turns red and edits are kept in the browser. Next time the editor opens, it offers to restore them.

The editor doesn't commit: commit `design/scenes/` like any other doc change.

## Planned features

Picked by Ethan, Nov 21, 2026, in this order of value. Not built yet.

- **Play-through preview:** pick a hero (background, class, subclass, race, party, flags) and click through a scene with real coin flips. Shows which options appear, pass and fail, chime-ins on a miss by exactly 1, and the flags that get set.
- **Voice sheet side panel:** while you edit a line, shows the speaker's voice sheet (from `design/characters/`) and the tells-to-avoid list beside it.
- **Flags & quests overview:** every flag, which scenes set it and which read it, with a note on what it means.
- **Jump links and shared bits:** link to a node in another scene, and reuse small pieces (a haggle, a farewell) in many scenes instead of copying them.
- **Later: Godot scene loader** that runs scene files on the social encounter screen (also in [design/scenes](../../design/scenes/README.md) → Open questions).

Built Nov 21, 2026: the character view (every line a character says), as part of the Characters tab.

Not picked for now: blind test mode, draft/approved line status, script export, fill-in token checks, stronger tell checks, canvas notes and groups, tidy layout and minimap, markdown lines in the tool, and importing the sword pull scene.
