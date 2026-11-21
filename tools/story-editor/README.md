# Story editor

A local tool for writing the branching scenes in `design/scenes/`. It runs offline: a small Python server (standard library only, macOS already has it) serves the page and saves each change into the repo. The scene format is in [design/scenes/README.md](../../design/scenes/README.md).

## Start it

- Double-click **Start Story Editor.command** in Finder. The first time, macOS may ask you to allow it (right-click → Open).
- Or in a terminal: `python3 tools/story-editor/server.py`

It opens http://127.0.0.1:8765 in the browser. Leave the terminal window open while you write, and close it (or press Ctrl+C) to stop. If the editor is already running, starting it again just opens the page.

## Using it

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
