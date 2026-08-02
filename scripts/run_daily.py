#!/usr/bin/env python3
"""Run the Daily automation workflow (for cron / Task Scheduler).

```
Daily
 ↓
Import Folder
 ↓
Detect new files
 ↓
Import
 ↓
Update
 ↓
Generate Excel
 ↓
Create Dashboard
 ↓
Email Report (future)
```

Example crontab (02:15 local time)::

    15 2 * * * /path/to/.venv/bin/python /path/to/scripts/run_daily.py

Or::

    pip-app daily
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
    raise SystemExit(main(["daily", *sys.argv[1:]]))
