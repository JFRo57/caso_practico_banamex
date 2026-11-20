"""Verifica los archivos de entrega sin instalar dependencias ni modelos."""
import hashlib
from pathlib import Path


def verify(root=None):
    root = Path(root or Path(__file__).resolve().parent.parent).resolve()
    failures = []
    count = 0
    for line in (root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            failures.append(name)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            failures.append(name)
        count += 1
    if failures:
        raise RuntimeError("Archivos ausentes o modificados: " + ", ".join(failures))
    print(f"Integridad OK: {count} archivos de entrega.")


if __name__ == "__main__":
    verify()
