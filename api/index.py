"""Vercel entry point: serves the /api routes from website/serve.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "website"))

import serve  # noqa: E402

serve.SITE = serve.Site(serve.DB)


class handler(serve.Handler):
    pass
