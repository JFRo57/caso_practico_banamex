"""Preparación nativa sin cambios globales ni dependencia de Docker."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener, urlopen
import webbrowser
import zipfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parent.parent
MODEL = "qwen3:4b"
VERSION = "0.40.16"
HTTP = build_opener(ProxyHandler({}))
OLLAMA_ASSETS = {
    ("linux", "x86_64"): ("ollama-linux-amd64.tar.zst", "87bfafb2acbc89b2e6a1be0a9043de6aa75fb450696f86bc426e65fc448f788d"),
    ("linux", "arm64"): ("ollama-linux-arm64.tar.zst", "e45b8e6dcb86cb9f3057396351655079c9a4879b4ced2678c9350d375dcbc224"),
    ("darwin", "x86_64"): ("ollama-darwin.tgz", "a743717494315da7cd352982b805f6b992d4b4452ca117fd5fbf86c4ee46fca0"),
    ("darwin", "arm64"): ("ollama-darwin.tgz", "a743717494315da7cd352982b805f6b992d4b4452ca117fd5fbf86c4ee46fca0"),
    ("win32", "x86_64"): ("ollama-windows-amd64.zip", "50fcf5ad54277f2fa5d173ebfc93bcb017adbc0c9ef2314daabc96ca9e6aa64e"),
    ("win32", "arm64"): ("ollama-windows-arm64.zip", "86d2b329cae3125684ff29b506623710b68e1393f679594f1c6aa267beac31c2"),
}


def machine():
    value = platform.machine().lower()
    return {"amd64": "x86_64", "aarch64": "arm64"}.get(value, value)


def native_python():
    return ROOT / ".runtime" / "venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def local_endpoint():
    value = os.environ.get("BANAMEX_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(value)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise RuntimeError("El iniciador necesita una URL Ollama local http://127.0.0.1:puerto.")
    _ = parsed.port
    return value


def api(path, timeout=5):
    with HTTP.open(local_endpoint() + "/api/" + path, timeout=timeout) as response:
        return json.load(response)


def run(*args):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)


def validate_platform():
    if sys.version_info < (3, 11) or (sys.platform, machine()) not in OLLAMA_ASSETS:
        raise RuntimeError("Se necesita Windows/macOS/Linux de 64 bits y Python 3.11+. Usa el iniciador de tu sistema.")
    if sys.platform == "darwin":
        if tuple(int(v) for v in platform.mac_ver()[0].split('.')[:2]) < (14, 0):
            raise RuntimeError("Ollama necesita macOS 14 o posterior.")
        if machine() == "x86_64" and sys.version_info >= (3, 14):
            raise RuntimeError("Mac Intel necesita Python 3.13 para ONNX. Usa sh iniciar.sh.")


def download(url, destination, expected=None):
    for attempt in range(3):
        try:
            digest = hashlib.sha256()
            with urlopen(url, timeout=90) as source, destination.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
                    target.write(chunk)
            if expected and digest.hexdigest() != expected:
                raise RuntimeError("SHA256 incorrecto: " + destination.name)
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2)


def ensure_windows_runtime():
    if sys.platform != "win32":
        return
    def available():
        try:
            ctypes.WinDLL("msvcp140.dll")
            ctypes.WinDLL("vcruntime140_1.dll")
            return True
        except OSError:
            return False
    if available():
        return
    print("Falta Microsoft Visual C++. Se abrirá su instalador oficial; Windows solicitará tu autorización.", flush=True)
    arch = "arm64" if machine() == "arm64" else "x64"
    installer = ROOT / ".runtime" / f"vc_redist.{arch}.exe"
    installer.parent.mkdir(parents=True, exist_ok=True)
    download(f"https://aka.ms/vc14/vc_redist.{arch}.exe", installer)
    # Microsoft actualiza este instalador: se exige firma Authenticode válida,
    # sin ejecutar un binario descargado sin verificar ni cambiar políticas.
    command = (
        "$ErrorActionPreference='Stop'; "
        "$s=Get-AuthenticodeSignature -LiteralPath $env:BANAMEX_VC_INSTALLER; "
        "if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation(?:,|$)') "
        "{ throw 'Firma Microsoft inválida; instalación detenida' }; "
        "$p=Start-Process -FilePath $env:BANAMEX_VC_INSTALLER -ArgumentList '/install','/norestart' "
        "-Verb RunAs -Wait -PassThru; "
        "if ($p.ExitCode -notin @(0,3010,1638)) { exit $p.ExitCode }"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                   env=dict(os.environ, BANAMEX_VC_INSTALLER=str(installer)), check=True)
    if not available():
        raise RuntimeError("Visual C++ aún no está disponible; completa su instalación o reinicia Windows y vuelve a abrir el iniciador.")


def install_ollama(python):
    name, expected = OLLAMA_ASSETS[(sys.platform, machine())]
    target = ROOT / ".runtime" / f"ollama-{VERSION}-{sys.platform}-{machine()}"
    binary_name = "ollama.exe" if sys.platform == "win32" else "ollama"
    existing = [p for p in target.rglob(binary_name) if p.is_file()] if target.exists() else []
    if existing and (target / ".complete").exists():
        return existing[0]
    target.mkdir(parents=True, exist_ok=True)
    print("Descargando Ollama privado; no cambia servicios ni PATH del sistema.", flush=True)
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / name
        download(f"https://github.com/ollama/ollama/releases/download/v{VERSION}/{name}", archive, expected)
        if name.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                for member in z.namelist():
                    if not (target / member).resolve().is_relative_to(target.resolve()):
                        raise RuntimeError("Ruta inválida en archivo Ollama.")
                z.extractall(target)
        elif name.endswith(".zst"):
            run(python, "-c", "import sys,tarfile,zstandard; "
                "f=open(sys.argv[1],'rb'); s=zstandard.ZstdDecompressor().stream_reader(f); "
                "t=tarfile.open(fileobj=s,mode='r|'); t.extractall(sys.argv[2],filter='data')", archive, target)
        else:
            with tarfile.open(archive) as t:
                t.extractall(target, filter="data")
    binaries = [p for p in target.rglob(binary_name) if p.is_file()]
    if len(binaries) != 1:
        raise RuntimeError("No se encontró un ejecutable Ollama único en la descarga.")
    (target / ".complete").write_text(expected)
    return binaries[0]


def stop_server(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def ensure_server(python):
    try:
        api("tags")
        return None
    except OSError:
        pass
    binary = install_ollama(python)
    runtime = ROOT / ".runtime"
    env = dict(os.environ, OLLAMA_HOST=local_endpoint().removeprefix("http://"),
               OLLAMA_MODELS=str(runtime / "ollama-models"))
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32" else {"start_new_session": True}
    with (runtime / "ollama.log").open("ab") as log:
        process = subprocess.Popen([str(binary), "serve"], cwd=binary.parent, env=env,
                                   stdout=log, stderr=log, **options)
    try:
        for _ in range(120):
            try:
                api("tags")
                return process
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("Ollama terminó. Revisa .runtime/ollama.log.")
                time.sleep(0.5)
        raise RuntimeError("Ollama no inició. Revisa .runtime/ollama.log.")
    except BaseException:
        stop_server(process)
        raise


def check_resources(python):
    run(python, "-m", "scripts.runtime_check")
    run(python, "-c", "from scripts.prepare_embeddings import MODEL_DIRECTORY,MODEL_FILES; "
        "import hashlib; "
        "assert all((MODEL_DIRECTORY/n).is_file() and hashlib.sha256((MODEL_DIRECTORY/n).read_bytes()).hexdigest()==h for n,h in MODEL_FILES.items()), 'E5 incompleto'; "
        "from asistente_banamex import Engine; e=Engine(embeddings=True); "
        "assert e.index_embeddings(), e.semantic.error")
    models = api("tags")
    if MODEL not in {m.get("name") for m in models.get("models", [])}:
        raise RuntimeError("Falta qwen3:4b. Ejecuta el iniciador sin --check.")


def quick_python(check=False):
    if sys.version_info < (3, 11):
        raise RuntimeError("El modo rápido necesita Python 3.11 o posterior.")
    try:
        ZoneInfo("America/Mexico_City")
        return Path(sys.executable)
    except ZoneInfoNotFoundError:
        python = ROOT / ".runtime" / "quick-venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if check:
            if not python.exists():
                raise RuntimeError("Faltan las zonas horarias. Ejecuta el iniciador rápido sin --check.")
            return python
        if not python.exists():
            run(sys.executable, "-m", "venv", python.parent.parent)
        run(python, "-m", "pip", "install", "--only-binary=:all:", "-r", "requirements-quick.txt")
        return python


def start_chat(python, port, browser, quick=False):
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"El puerto {port} está ocupado. Cierra la otra instancia o usa --port.") from error
    url = f"http://127.0.0.1:{port}"
    env = dict(os.environ, BANAMEX_BIND_HOST="127.0.0.1")
    command = [str(python), "app.py", "--port", str(port)]
    if not quick:
        env["BANAMEX_OLLAMA_URL"] = local_endpoint()
        command.extend(["--embeddings", "--ollama-model", MODEL])
    process = subprocess.Popen(command, cwd=ROOT, env=env)
    try:
        for _ in range(180):
            if process.poll() is not None:
                raise RuntimeError("El chat terminó durante el arranque.")
            try:
                with HTTP.open(url + "/api/status", timeout=2) as response:
                    state = json.load(response)
                if quick:
                    if state.get("model") or state.get("embeddings") or state.get("routing_mode") != "local":
                        raise RuntimeError("El modo rápido no debe activar modelos ni respaldo LLM.")
                elif not state.get("embeddings") or state.get("routing_mode") != "adaptive":
                    raise RuntimeError("El chat no activó E5 y Qwen3.")
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("El chat no confirmó disponibilidad.")
        print("Chat listo: " + url + " — Ctrl+C para detener.", flush=True)
        if browser:
            webbrowser.open(url)
        return process.wait()
    finally:
        stop_server(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="No instala, descarga, inicia servidores ni infiere con Qwen3")
    parser.add_argument("--start", action="store_true", help="Prepara, verifica y abre el chat")
    parser.add_argument("--quick", action="store_true", help="Solo reglas y FTS5; sin E5, Ollama, Qwen3 ni respaldo LLM")
    parser.add_argument("--prepare-only", action="store_true", help="Prepara y verifica sin abrir el chat")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.prepare_only:
        args.start = False
    if args.check and args.start:
        parser.error("--check y --start son excluyentes")
    if not 1 <= args.port <= 65535:
        parser.error("Puerto inválido")
    if args.quick:
        python = quick_python(args.check)
        run(python, "-m", "scripts.runtime_check")
        run(python, "-c", "from zoneinfo import ZoneInfo; ZoneInfo('America/Mexico_City'); "
            "from asistente_banamex import Engine; e=Engine(); "
            "assert e.model is None and e.semantic is None; "
            "assert e.answer('¿Cuál es la anualidad de Joy?')['action']=='answer'")
        print("Modo rápido: reglas y búsqueda local. Sin E5, Ollama ni Qwen3. No hay respaldo hacia un LLM.", flush=True)
        return start_chat(python, args.port, not args.no_browser, quick=True) if args.start else 0
    validate_platform()
    local_endpoint()
    python = native_python()
    if args.check:
        if not python.exists():
            raise RuntimeError("Falta el entorno nativo. Ejecuta el iniciador.")
        check_resources(python)
        print("OK: E5 ejecutado y Qwen3 instalado; --check no realizó inferencia Qwen3.")
        return 0
    print("Primera preparación: internet, varios GB y varios minutos; no requiere Docker.", flush=True)
    ensure_windows_runtime()
    if not python.exists():
        run(sys.executable, "-m", "venv", python.parent.parent)
    run(python, "-m", "pip", "install", "--only-binary=:all:", "-r", "requirements-native.txt")
    run(python, "-m", "scripts.runtime_check", "--repair")
    server = ensure_server(python)
    try:
        env = dict(os.environ, BANAMEX_OLLAMA_URL=local_endpoint())
        subprocess.run([str(python), "-m", "scripts.container_start", "--prepare-only"], cwd=ROOT, env=env, check=True)
        print("Preparación nativa verificada.", flush=True)
        return start_chat(python, args.port, not args.no_browser) if args.start else 0
    finally:
        stop_server(server)
