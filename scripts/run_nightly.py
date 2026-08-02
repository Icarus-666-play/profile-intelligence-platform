#!/usr/bin/env python3
"""Run the nightly automation workflow (for cron / Task Scheduler).

Example crontab (02:15 local time)::

    15 2 * * * /path/to/.venv/bin/python /path/to/scripts/run_nightly.py

Or::

    pip-app nightly
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from profile_intelligence.main import main

if __name__ == "__main__":
    raise SystemExit(main(["nightly", *sys.argv[1:]]))
