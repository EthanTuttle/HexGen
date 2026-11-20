# Showcase site

A local web page that shows off Heads or Hexes: what you do in the game, screenshots from the prototype, the approved art, the combat maps, and how the art grew from first try to approved. It's the start of a public site or Steam page. For now it runs locally.

## Opening it

The page reads images from `art/` and fonts from `godot/fonts`, so serve it from the repo root (opening the file directly blocks the fonts):

```bash
python3 -m http.server 8642
```

Then open http://localhost:8642/site/. In the Claude app the `site` launch config does the same.

## Updating it

```bash
python3 site/build_gallery.py
```

This rebuilds `gallery.js` and the thumbnails (`thumbs/`, not committed; needs a Mac for `sips`). Run it after new verdicts land in `art/reviews.md`.

| Section | Comes from |
| --- | --- |
| What you do | Written in `index.html`. Top line and the six blurbs picked by Ethan, Nov 20, 2026. Blurb 4 mentions high ground before its rule is settled (uphill cost is an open question in 03), on purpose |
| In the game | Every image or video in `site/shots/` |
| The world | Every **approved** file in `art/reviews.md` that's on disk, newest first |
| Combat maps | The in-use maps in `art/combat/maps/README.md`, with their tactical idea |
| How it grew | Approved renders with 3+ versions of the same view in `art/preview`, with the notes from `reviews.md` |

Nothing unapproved shows up in The world or as the end of a How it grew comparison: rejected versions only appear as the earlier steps.

`picks.json` tunes it by hand:

- `featured`: the renders the top of the page fades between.
- `hide`: approved files to leave out (diagnostic renders such as pose checks).
- `titles`: better names than the ones made from file names.

## Adding game screenshots

The Godot demo plays itself and saves screenshots (see `godot/README.md` → A demo that plays itself). From the repo root:

```bash
mkdir -p godot/screens
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1688x780 -- --demo --shots --quit
```

Copy the ones worth showing into `site/shots/` (names sort the order) and rebuild. Leave out shots with placeholder text.
