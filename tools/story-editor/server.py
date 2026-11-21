#!/usr/bin/env python3
"""Story editor server for Heads or Hexes.

Serves the editor page and reads/writes scene files in design/scenes/.
Runs fully offline with only the Python standard library.

    python3 tools/story-editor/server.py            # opens http://127.0.0.1:8765
    python3 tools/story-editor/server.py --port 9000 --no-browser
    python3 tools/story-editor/server.py --data /some/other/folder
"""

import argparse
import json
import os
import re
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_DATA = os.path.join(REPO, "design", "scenes")
LISTS_FILE = "_lists.json"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Handler(SimpleHTTPRequestHandler):
    data_dir = DEFAULT_DATA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
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
        path = unquote(urlparse(self.path).path)
        if not path.startswith("/api/"):
            return None, None
        parts = path[len("/api/"):].strip("/").split("/")
        return parts[0], (parts[1] if len(parts) > 1 else None)

    def scene_path(self, scene_id):
        if not scene_id or not ID_RE.match(scene_id):
            return None
        return os.path.join(self.data_dir, scene_id + ".json")

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
            if kind == "lists":
                write_json(os.path.join(self.data_dir, LISTS_FILE), data)
                return self.send_json({"ok": True})
        except Exception as e:
            return self.send_json({"error": str(e)}, 500)
        self.send_json({"error": "unknown"}, 404)

    def do_DELETE(self):
        kind, arg = self.route()
        if kind == "scenes":
            p = self.scene_path(arg)
            if p and os.path.exists(p):
                os.remove(p)
                return self.send_json({"ok": True})
            return self.send_json({"error": "not found"}, 404)
        self.send_json({"error": "unknown"}, 404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    Handler.data_dir = os.path.abspath(args.data)
    os.makedirs(Handler.data_dir, exist_ok=True)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        url = "http://127.0.0.1:%d" % args.port
        print("Port %d is busy; the editor is probably already running at %s" % (args.port, url))
        if not args.no_browser:
            webbrowser.open(url)
        sys.exit(0)
    url = "http://127.0.0.1:%d" % args.port
    print("Story editor: %s" % url)
    print("Scenes folder: %s" % Handler.data_dir)
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
