"""Download the pinned official ONNX model and tokenizer for offline inference."""

import hashlib
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asistente_banamex.semantic import MODEL_DIRECTORY, MODEL_FILES, MODEL_REPOSITORY, MODEL_REVISION


def prepare_model():
    MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for name, expected in MODEL_FILES.items():
        destination = MODEL_DIRECTORY / name
        if destination.is_file():
            with destination.open("rb") as existing:
                if hashlib.file_digest(existing, "sha256").hexdigest() == expected:
                    continue
        url = f"https://huggingface.co/{MODEL_REPOSITORY}/resolve/{MODEL_REVISION}/onnx/{name}?download=true"
        digest = hashlib.sha256()
        output = NamedTemporaryFile(dir=MODEL_DIRECTORY, delete=False)
        temporary = Path(output.name)
        try:
            with output, urlopen(url, timeout=45) as response:
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    output.write(chunk)
            if digest.hexdigest() != expected:
                raise ValueError(f"SHA-256 incorrecta para {name}")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    print(f"Modelo ONNX verificado en {MODEL_DIRECTORY}")


if __name__ == "__main__":
    prepare_model()
