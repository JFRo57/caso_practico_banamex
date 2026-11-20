"""Private, loopback-only chat server."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os

from asistente_banamex import Engine, ROOT
from asistente_banamex.semantic import EMBEDDING_MODEL, add_semantic_options, policy_from_args

HOST = "127.0.0.1"
BIND_HOST = os.environ.get("BANAMEX_BIND_HOST", HOST)

# Resolve web assets from web/ or root fallback
WEB_DIR = ROOT / "web"
INDEX_PATH = (WEB_DIR / "index.html") if (WEB_DIR / "index.html").is_file() else (ROOT / "index.html")
STATIC_DIR = (WEB_DIR / "static") if (WEB_DIR / "static").is_dir() else (ROOT / "static")

WEB_ASSETS = {
    "/": (INDEX_PATH.read_bytes(), "text/html; charset=utf-8"),
    "/static/chat.css": ((STATIC_DIR / "chat.css").read_bytes(), "text/css; charset=utf-8"),
    "/static/chat.js": ((STATIC_DIR / "chat.js").read_bytes(), "text/javascript; charset=utf-8"),
}


class ChatHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        # No HTTP access log. A browser may contain personal data.
        return

    def _send(self, code, payload, mime):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; connect-src 'self'; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, code, value):
        self._send(code, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _local_host(self):
        return self.headers.get("Host") in {f"{HOST}:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self._local_host():
            self._json(403, {"error": "Usa la dirección local del prototipo."})
        elif self.path in WEB_ASSETS:
            self._send(200, *WEB_ASSETS[self.path])
        elif self.path == "/api/status":
            semantic = self.server.engine.semantic
            self._json(200, {
                "snapshot": self.server.engine.snapshot, "model": self.server.model_name,
                "embeddings": bool(semantic and semantic.vectors),
                "embedding_model": EMBEDDING_MODEL if semantic and semantic.vectors else None,
                "embeddings_requested": semantic is not None,
                "embedding_error": semantic.error if semantic else None,
                "routing_mode": (
                    "adaptive" if semantic and semantic.vectors and self.server.engine.model
                    else "embeddings_only" if semantic and semantic.vectors
                    else "hybrid" if self.server.engine.model else "local"
                ),
            })
        else:
            self._json(404, {"error": "Ruta no disponible."})

    def do_POST(self):
        origin = self.headers.get("Origin")
        if not self._local_host() or (origin and origin != f"http://{self.headers.get('Host')}"):
            self._json(403, {"error": "Origen inválido."})
            return
        if self.path != "/api/chat":
            self._json(404, {"error": "Ruta no disponible."})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "Se esperaba JSON."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                raise ValueError
            data = json.loads(self.rfile.read(length))
            question = data.get("question") if isinstance(data, dict) else None
            if not isinstance(question, str) or not 0 < len(question.strip()) <= 750:
                raise ValueError
        except (ValueError, UnicodeError):
            self._json(400, {"error": "Escribe una pregunta de 1 a 750 caracteres."})
            return
        response_language = data.get("response_language")
        if response_language not in (None, "es", "en"):
            self._json(400, {"error": "Idioma inválido."})
            return
        self._json(200, self.server.engine.answer(question, data.get("followup"), response_language))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ollama-model", choices=("qwen3:4b",), help="Activa la interpretación con el modelo local")
    parser.add_argument("--embeddings", action="store_true", help="Añade búsqueda semántica local con ONNX Runtime")
    parser.add_argument("--port", type=int, default=8000)
    add_semantic_options(parser)
    args = parser.parse_args()
    try:
        semantic_policy = policy_from_args(args)
    except ValueError as error:
        parser.error(str(error))
    serve(args.port, args.ollama_model, args.embeddings, semantic_policy)


def serve(port, model=None, embeddings=False, semantic_policy=None):
    server = None
    candidate_ports = [port]
    if port == 8000:
        candidate_ports.extend([8002, 8080, 8888])
    for p in candidate_ports:
        try:
            server = ThreadingHTTPServer((BIND_HOST, p), ChatHandler)
            if p != port:
                print(f"Puerto {port} ocupado. Usando puerto alternativo {p}.", flush=True)
            break
        except OSError:
            if p == candidate_ports[-1]:
                raise

    with server:
        server.engine = Engine(model=model, embeddings=embeddings, semantic_policy=semantic_policy)
        server.model_name = model
        if embeddings:
            print("Indexando fichas con embeddings locales…", flush=True)
            if not server.engine.index_embeddings():
                print(f"El chat inicia con la ruta habitual. {server.engine.semantic.error}", flush=True)
        if server.engine.model and not embeddings:
            print("Preparando Ollama local…", flush=True)
            _, route = server.engine.model.warmup()
            if route == "fallback":
                print("Ollama aún no está disponible. El chat inicia con la ruta local.", flush=True)
        elif server.engine.model:
            print("Qwen3 se consultará bajo demanda si la ruta anterior no resuelve la pregunta.", flush=True)
        print(f"Prototipo local en http://{HOST}:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main()
