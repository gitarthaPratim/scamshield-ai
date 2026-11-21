#!/bin/sh
cd "$(dirname "$0")"
echo "Starting ScamShield at http://localhost:8000"
(sleep 2 && (xdg-open http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null)) &
python3 server.py
