"""Preparación automática del modo completo; falla si falta un componente."""
import argparse
import json
import os
import time
from urllib.request import ProxyHandler, Request, build_opener

from scripts.prepare_embeddings import prepare_model
from asistente_banamex import Engine
from asistente_banamex.ollama import OllamaPlanner
from scripts.runtime_check import check as check_runtime

MODEL = "qwen3:4b"
HTTP = build_opener(ProxyHandler({}))


def api(path, body=None, timeout=5):
    base = os.environ.get("BANAMEX_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    req = Request(base + "/api/" + path,
                  data=json.dumps(body).encode() if body is not None else None,
                  headers={"Content-Type": "application/json"})
    with HTTP.open(req, timeout=timeout) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError(result["error"])
    return result


def health():
    with HTTP.open("http://127.0.0.1:8000/api/status", timeout=3) as response:
        status = json.load(response)
    if not (status.get("routing_mode") == "adaptive" and status.get("embeddings")
            and status.get("model") == MODEL):
        raise RuntimeError("El modo completo no está listo.")
    models = api("tags")
    if MODEL not in {m.get("name") for m in models.get("models", [])}:
        raise RuntimeError("Qwen3 ya no está disponible.")


def prepare():
    check_runtime()
    print("Preparando E5 y Qwen3 CPU. La primera ejecución descarga varios GB.", flush=True)
    for attempt in range(60):
        try:
            models = api("tags")
            break
        except OSError:
            if attempt == 59:
                raise RuntimeError("Ollama no respondió; revisa docker compose logs ollama.")
            time.sleep(1)
    prepare_model()
    engine = Engine(embeddings=True)
    if not engine.index_embeddings():
        raise RuntimeError("No se pudo ejecutar E5: " + str(engine.semantic.error))
    if MODEL not in {m.get("name") for m in models.get("models", [])}:
        print("Descargando qwen3:4b; espera a que termine antes de abrir el chat.", flush=True)
        result = api("pull", {"model": MODEL, "stream": False}, timeout=3600)
        if result.get("status") != "success":
            raise RuntimeError("La descarga de Qwen3 no confirmó éxito.")
    # La preparación tiene su propio margen; el chat mantiene su límite de 25 s.
    loaded = api("generate", {"model": MODEL, "prompt": "", "stream": False,
                              "keep_alive": "20m", "options": {"num_gpu": 0, "num_ctx": 2048}}, timeout=180)
    if not loaded.get("done"):
        raise RuntimeError("Qwen3 no confirmó su carga en CPU.")
    plan, route = OllamaPlanner(MODEL).plan("What is the annual fee for the Joy credit card?")
    if route != "ollama" or plan is None:
        raise RuntimeError("No se verificó inferencia real con un plan válido de Qwen3.")
    print("VERIFICADO: E5 ejecutado y Qwen3 respondió con un plan válido en CPU.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.health:
        health()
        return
    prepare()
    if not args.prepare_only:
        from app import serve
        serve(8000, MODEL, True)


if __name__ == "__main__":
    main()
