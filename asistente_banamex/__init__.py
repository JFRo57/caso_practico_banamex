"""Paquete central del asistente virtual para clientes Banamex."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
ROOT = PROJECT_DIR if (
    (PROJECT_DIR / "pyproject.toml").is_file()
    and (PROJECT_DIR / "data" / "facts.json").is_file()
    and (PROJECT_DIR / "web" / "index.html").is_file()
) else PACKAGE_DIR
WORK_DIR = ROOT if ROOT == PROJECT_DIR else Path.cwd()

from .engine import Engine

__all__ = ["Engine", "ROOT"]
