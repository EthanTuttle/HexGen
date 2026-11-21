#!/usr/bin/env python3
"""Story editor server for Heads or Hexes.

Serves the editor page and reads/writes scene files in design/scenes/.
Runs fully offline with only the Python standard library.

    python3 tools/story-editor/server.py            # opens http://127.0.0.1:47380
    python3 tools/story-editor/server.py --port 9000 --no-browser
    python3 tools/story-editor/server.py --data /some/other/folder
    python3 tools/story-editor/server.py --idle-exit 600   # stop 10 min after the last tab closes
"""

import argparse
import json
import os
import re
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_DATA = os.path.join(REPO, "design", "scenes")
DEFAULT_CHARS = os.path.join(REPO, "design", "characters")
DEFAULT_STORY = os.path.join(REPO, "design", "story")
LISTS_FILE = "_lists.json"
# files in design/characters/ that aren't characters
NOT_CHARACTERS = {"00 Writing guide.md", "Pairs.md", "Places.md"}
CHAR_RE = re.compile(r"^[^/\\.\x00][^/\\\x00]{0,79}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
last_seen = [time.time()]  # last request from an open editor tab


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


LINK_RE = re.compile(r"\[([^\]\n]+)\]\(((?:\.\./)*)(scenes|characters)/([^)\s]+)\.(json|md)\)")


def relink_docs(chars_dir, d):
    """After a rename, fixes links in the design docs the editor doesn't hold itself.

    A link's target follows the rename; its text follows too when it was the old name.
    The editor's own folders (story, scenes, characters) are left to the editor.
    """
    design = os.path.dirname(os.path.abspath(chars_dir))
    skip = {os.path.join(design, x) for x in ("story", "scenes", "characters")}
    kind, old, new = d["kind"], d["old"], d["new"]
    old_label, new_label = d.get("oldLabel"), d.get("newLabel") or new
    ext = "json" if kind == "scenes" else "md"
    changed = []

    def fix(m):
        label, up, k, path, e = m.groups()
        if k != kind or e != ext or unquote(path) != old:
            return m.group(0)
        if old_label is not None and label == old_label:
            label = new_label
        target = new if kind == "scenes" else quote(new, safe="")
        return "[%s](%s%s/%s.%s)" % (label, up, k, target, e)

    for root, dirs, files in os.walk(design):
        if root in skip or any(root.startswith(s + os.sep) for s in skip):
            dirs[:] = []
            continue
        for name in files:
            if not name.endswith(".md"):
                continue
            p = os.path.join(root, name)
            with open(p, encoding="utf-8") as f:
                text = f.read()
            out = LINK_RE.sub(fix, text)
            if out != text:
                write_text(p, out)
                changed.append(os.path.relpath(p, design))
    return changed


class Handler(SimpleHTTPRequestHandler):
    data_dir = DEFAULT_DATA
    chars_dir = DEFAULT_CHARS
    story_dir = DEFAULT_STORY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def log_message(self, fmt, *args):
        if "/api/" in (str(args[0]) if args else ""):
            return  # autosave would flood the terminal
        super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    # --- helpers ---
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def route(self):
        last_seen[0] = time.time()
        path = unquote(urlparse(self.path).path)
        if not path.startswith("/api/"):
            return None, None
        parts = path[len("/api/"):].strip("/").split("/")
        return parts[0], (parts[1] if len(parts) > 1 else None)

    def scene_path(self, scene_id):
        if not scene_id or not ID_RE.match(scene_id):
            return None
        return os.path.join(self.data_dir, scene_id + ".json")

    def story_path(self, name):
        if not name or not CHAR_RE.match(name) or name == "README":
            return None
        return os.path.join(self.story_dir, name + ".md")

    def char_path(self, name):
        if not name or not CHAR_RE.match(name) or (name + ".md") in NOT_CHARACTERS:
            return None
        return os.path.join(self.chars_dir, name + ".md")

    # --- verbs ---
    def do_GET(self):
        kind, arg = self.route()
        if kind is None:
            return super().do_GET()
        try:
            if kind == "scenes" and arg is None:
                out = []
                for name in sorted(os.listdir(self.data_dir)):
                    if not name.endswith(".json") or name.startswith("_"):
                        continue
                    try:
                        s = read_json(os.path.join(self.data_dir, name))
                    except (ValueError, OSError) as e:
                        out.append({"id": name[:-5], "title": name, "error": str(e)})
                        continue
                    out.append(s)
                return self.send_json(out)
            if kind == "scenes":
                p = self.scene_path(arg)
                if not p or not os.path.exists(p):
                    return self.send_json({"error": "not found"}, 404)
                return self.send_json(read_json(p))
            if kind == "lists":
                p = os.path.join(self.data_dir, LISTS_FILE)
                return self.send_json(read_json(p) if os.path.exists(p) else {})
            if kind == "characters":
                out = []
                for name in sorted(os.listdir(self.chars_dir)):
                    if name.endswith(".md") and name not in NOT_CHARACTERS:
                        with open(os.path.join(self.chars_dir, name), encoding="utf-8") as f:
                            out.append({"file": name[:-3], "text": f.read()})
                return self.send_json(out)
            if kind == "story":
                out = []
                for name in sorted(os.listdir(self.story_dir)):
                    if name.endswith(".md") and name != "README.md":
                        with open(os.path.join(self.story_dir, name), encoding="utf-8") as f:
                            out.append({"file": name[:-3], "text": f.read()})
                return self.send_json(out)
            if kind == "chardoc":  # read-only docs beside the characters (Pairs, Writing guide)
                name = {"pairs": "Pairs.md", "guide": "00 Writing guide.md"}.get(arg)
                p = name and os.path.join(self.chars_dir, name)
                if not p or not os.path.exists(p):
                    return self.send_json({"text": ""})
                with open(p, encoding="utf-8") as f:
                    return self.send_json({"text": f.read()})
            if kind == "ping":
                return self.send_json({"ok": True, "data": self.data_dir})
        except Exception as e:  # keep the editor alive on any read error
            return self.send_json({"error": str(e)}, 500)
        self.send_json({"error": "unknown"}, 404)

    def do_PUT(self):
        kind, arg = self.route()
        try:
            data = self.read_body()
            if kind == "scenes":
                p = self.scene_path(arg)
                if not p:
                    return self.send_json({"error": "bad scene id"}, 400)
                data["id"] = arg
                write_json(p, data)
                return self.send_json({"ok": True})
            if kind == "characters":
                p = self.char_path(arg)
                if not p:
                    return self.send_json({"error": "bad character name"}, 400)
                write_text(p, data["text"])
                return self.send_json({"ok": True})
            if kind == "story":
                p = self.story_path(arg)
                if not p:
                    return self.send_json({"error": "bad story file name"}, 400)
                write_text(p, data["text"])
                return self.send_json({"ok": True})
            if kind == "lists":
                write_json(os.path.join(self.data_dir, LISTS_FILE), data)
                return self.send_json({"ok": True})
        except Exception as e:
            return self.send_json({"error": str(e)}, 500)
        self.send_json({"error": "unknown"}, 404)

    def do_POST(self):
        kind, arg = self.route()
        if kind != "relink":
            return self.send_json({"error": "unknown"}, 404)
        try:
            d = self.read_body()
            return self.send_json({"changed": relink_docs(self.chars_dir, d)})
        except Exception as e:
            return self.send_json({"error": str(e)}, 500)

    def do_DELETE(self):
        kind, arg = self.route()
        if kind == "scenes":
            p = self.scene_path(arg)
            if p and os.path.exists(p):
                os.remove(p)
                return self.send_json({"ok": True})
            return self.send_json({"error": "not found"}, 404)
        if kind == "characters":
            p = self.char_path(arg)
            if p and os.path.exists(p):
                os.remove(p)
                return self.send_json({"ok": True})
            return self.send_json({"error": "not found"}, 404)
        self.send_json({"error": "unknown"}, 404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=47380)
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--chars", default=DEFAULT_CHARS)
    ap.add_argument("--story", default=DEFAULT_STORY)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--idle-exit", type=int, default=0,
                    help="stop after this many seconds with no editor tab open (0 = never)")
    args = ap.parse_args()

    Handler.data_dir = os.path.abspath(args.data)
    Handler.chars_dir = os.path.abspath(args.chars)
    Handler.story_dir = os.path.abspath(args.story)
    os.makedirs(Handler.story_dir, exist_ok=True)
    os.makedirs(Handler.data_dir, exist_ok=True)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        url = "http://127.0.0.1:%d" % args.port
        try:
            from urllib.request import urlopen
            json.load(urlopen(url + "/api/ping", timeout=2))["ok"]
        except Exception:
            print("Port %d is used by another program. Try --port with another number." % args.port)
            sys.exit(1)
        print("The editor is already running at %s" % url)
        if not args.no_browser:
            webbrowser.open(url)
        sys.exit(0)
    url = "http://127.0.0.1:%d" % args.port
    print("Story editor: %s" % url)
    print("Scenes folder: %s" % Handler.data_dir)
    print("Characters folder: %s" % Handler.chars_dir)
    print("Story folder: %s" % Handler.story_dir)
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    if args.idle_exit:
        def watch():
            while True:
                time.sleep(15)
                if time.time() - last_seen[0] > args.idle_exit:
                    print("No editor tab open for %ds; stopping." % args.idle_exit)
                    server.shutdown()
                    return
        threading.Thread(target=watch, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
