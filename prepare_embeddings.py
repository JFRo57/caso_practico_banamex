#!/usr/bin/env python3
"""CLI embeddings preparation shim delegating to scripts/prepare_embeddings.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_embeddings import prepare_model

if __name__ == "__main__":
    prepare_model()
