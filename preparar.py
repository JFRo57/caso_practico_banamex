#!/usr/bin/env python3
"""Prepara la demo completa en Linux/WSL; --check no instala ni descarga."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.request import ProxyHandler, Request, build_opener, urlopen

ROOT = Path(__file__).resolve().parent
MODEL = "qwen3:4b"
VERSION = "0.40.16"
HTTP = build_opener(ProxyHandler({}))


def api(path, body=None, timeout=5):
    request = Request("http://127.0.0.1:11434/api/" + path,
                      data=json.dumps(body).encode() if body is not None else None,
                      headers={"Content-Type": "application/json"})
    with HTTP.open(request, timeout=timeout) as response:
        return json.load(response)


def run(*args):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)


def install_ollama(python):
    """Instalación privada, versión fija y archivo contrastado con GitHub."""
    machine = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if not machine:
        raise RuntimeError("Arquitectura no soportada por este preparador.")
    name = f"ollama-linux-{machine}.tar.zst"
    request = Request(f"https://api.github.com/repos/ollama/ollama/releases/tags/v{VERSION}",
                      headers={"User-Agent": "banamex-preparador"})
    with urlopen(request, timeout=60) as response:
        release = json.load(response)
    asset = next(a for a in release["assets"] if a["name"] == name)
    expected = asset.get("digest", "")
    if not expected.startswith("sha256:"):
        raise RuntimeError("La publicación no ofrece SHA256; instalación detenida.")
    run(python, "-m", "pip", "install", "zstandard==0.25.0")
    # La extracción se realiza con el Python del entorno y filtro de rutas seguro.
    target = ROOT / ".runtime" / f"ollama-{VERSION}"
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / name
        digest = hashlib.sha256()
        with urlopen(asset["browser_download_url"], timeout=60) as source, archive.open("wb") as dest:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
                dest.write(chunk)
        if digest.hexdigest() != expected.removeprefix("sha256:"):
            raise RuntimeError("SHA256 de Ollama incorrecto.")
        run(python, "-c", "import sys,tarfile,zstandard; "
            "f=open(sys.argv[1],'rb'); "
            "s=zstandard.ZstdDecompressor().stream_reader(f); "
            "t=tarfile.open(fileobj=s,mode='r|'); "
            "t.extractall(sys.argv[2],filter='data')", archive, target)
    return target / "bin" / "ollama"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Comprueba recursos sin instalar, iniciar servicios ni descargar")
    args = parser.parse_args()
    if sys.version_info < (3, 11) or sys.platform != "linux":
        raise RuntimeError("Usa Linux/WSL con Python 3.11+ y soporte venv (modo completo probado con 3.14).")
    python = ROOT / ".venv" / "bin" / "python"
    if not args.check:
        print("Preparación: requiere internet si faltan dependencias o modelos; puede tardar varios minutos.", flush=True)
        if not python.exists():
            run(sys.executable, "-m", "venv", ROOT / ".venv")
        run(python, "-m", "pip", "install", "-r", "requirements-embeddings.txt")
        run(python, "prepare_embeddings.py")
    if not python.exists():
        raise RuntimeError("Falta .venv; ejecuta python3 preparar.py.")
    # Verifica los archivos sin descargar en --check y carga ONNX realmente en CPU.
    run(python, "-c", "from scripts.prepare_embeddings import MODEL_DIRECTORY,MODEL_FILES; "
        "import hashlib; "
        "assert all((MODEL_DIRECTORY/n).is_file() and hashlib.sha256((MODEL_DIRECTORY/n).read_bytes()).hexdigest()==h for n,h in MODEL_FILES.items()), 'E5 incompleto'; "
        "import onnxruntime,tokenizers; "
        "onnxruntime.InferenceSession(str(MODEL_DIRECTORY/'model_qint8_avx512_vnni.onnx'),providers=['CPUExecutionProvider']); "
        "tokenizers.Tokenizer.from_file(str(MODEL_DIRECTORY/'tokenizer.json'))")
    try:
        models = api("tags")
    except OSError:
        if args.check:
            raise RuntimeError("Ollama no está disponible en 127.0.0.1:11434.")
        candidates = [shutil.which("ollama"), str(Path.home()/".local/bin/ollama"),
                      str(ROOT/".runtime"/f"ollama-{VERSION}"/"bin/ollama")]
        binary = next((Path(p) for p in candidates if p and Path(p).is_file()), None)
        if binary is None:
            binary = install_ollama(python)
        runtime = ROOT / ".runtime"
        runtime.mkdir(exist_ok=True)
        env = dict(os.environ, OLLAMA_HOST="127.0.0.1:11434")
        with (runtime/"ollama.log").open("ab") as log:
            process = subprocess.Popen([str(binary), "serve"], env=env, stdout=log,
                                       stderr=log, start_new_session=True)
        for _ in range(60):
            try:
                models = api("tags")
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("Ollama terminó; revisa .runtime/ollama.log.")
                time.sleep(0.5)
        else:
            raise RuntimeError("Ollama no inició; revisa .runtime/ollama.log.")
    if MODEL not in {m.get("name") for m in models.get("models", [])}:
        if args.check:
            raise RuntimeError(f"Falta {MODEL}; ejecuta python3 preparar.py.")
        print(f"Descargando {MODEL}; la primera preparación requiere varios GB.", flush=True)
        result = api("pull", {"model": MODEL, "stream": False}, timeout=3600)
        if result.get("status") != "success":
            raise RuntimeError(f"No se pudo preparar {MODEL}.")
    if not args.check:
        # Calienta el mismo modelo en CPU antes de aplicar la espera de 25 s del chat.
        result = api("generate", {"model": MODEL, "prompt": "", "stream": False,
                                 "keep_alive": "20m", "options": {"num_gpu": 0, "num_ctx": 2048}}, timeout=180)
        if not result.get("done"):
            raise RuntimeError("El modelo no confirmó su carga.")
    print("OK: dependencias, E5 CPU, Ollama local y qwen3:4b disponibles.")
    print("Ejecuta: ./.venv/bin/python app.py --embeddings --ollama-model qwen3:4b")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, StopIteration) as error:
        print(f"Preparación incompleta: {error}", file=sys.stderr)
        sys.exit(1)
