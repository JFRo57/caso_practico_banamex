#!/bin/sh
set -eu
cd -P "$(dirname "$0")"
for python in python3 python; do
    if command -v "$python" >/dev/null 2>&1 && "$python" -c '
import importlib.util, sqlite3, sys
if sys.version_info < (3, 11):
    sys.exit(1)
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
with sqlite3.connect(":memory:") as connection:
    connection.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
try:
    ZoneInfo("America/Mexico_City")
except ZoneInfoNotFoundError:
    if importlib.util.find_spec("ensurepip") is None:
        sys.exit(1)
' 2>/dev/null; then
        exec "$python" preparar.py --start --quick "$@"
    fi
done
exec sh iniciar.sh --quick "$@"
