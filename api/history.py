# Vercel serverless route: /api/history
# Re-exports ScamShield's request handler from server.py (project root).
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import Handler as handler  # noqa: E402,F401
