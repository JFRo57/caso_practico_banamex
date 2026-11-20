#!/usr/bin/env python3
"""CLI evaluation shim delegating to scripts/evaluate.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate import main

if __name__ == "__main__":
    main()
