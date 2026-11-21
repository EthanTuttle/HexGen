#!/bin/bash
# Double-click in Finder to start the story editor (runs offline).
cd "$(dirname "$0")"
exec python3 server.py
