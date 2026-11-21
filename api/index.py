# Vercel serverless entry point.
# Vercel's Python runtime looks for a BaseHTTPRequestHandler subclass named
# "handler" in api/*.py files. ScamShield's full request handler already lives
# in server.py (project root), so we simply re-export it here.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import Handler as handler  # noqa: E402,F401
