"""Comprueba las dependencias mínimas antes de descargar o iniciar modelos."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def check():
    if sys.version_info < (3, 11):
        raise RuntimeError("Se necesita Python 3.11 o posterior.")
    with closing(sqlite3.connect(":memory:")) as connection:
        try:
            connection.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
            connection.execute("INSERT INTO probe VALUES ('consulta')")
            assert connection.execute("SELECT count(*) FROM probe WHERE probe MATCH 'consulta'").fetchone()[0] == 1
        except sqlite3.DatabaseError as error:
            raise RuntimeError("Este Python no incluye SQLite FTS5; usa el Python privado del iniciador.") from error
    ZoneInfo("America/Mexico_City")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair", action="store_true", help="Prepara tzdata solo dentro de un entorno virtual")
    args = parser.parse_args()
    try:
        check()
    except ZoneInfoNotFoundError as error:
        if not args.repair:
            raise RuntimeError("Falta la base de zonas horarias. Ejecuta el iniciador para preparar tzdata.") from error
        if sys.prefix == sys.base_prefix:
            raise RuntimeError("La reparación requiere un entorno virtual del proyecto; no se instalarán paquetes globales.") from error
        requirements = Path(__file__).resolve().parent.parent / "requirements-quick.txt"
        subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:", "-r", str(requirements)], check=True)
        # Un intérprete nuevo verifica los datos recién instalados, sin cachés.
        subprocess.run([sys.executable, "-m", "scripts.runtime_check"], check=True)
        return
    print("Entorno base verificado: Python, SQLite FTS5 y zonas horarias.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Entorno incompleto: {error}", file=sys.stderr)
        sys.exit(1)
