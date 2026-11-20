"""Unified Command Line Interface for Banamex Assistant."""

import argparse
import sys

from .engine import Engine
from .semantic import add_semantic_options, policy_from_args


def cli_serve(args):
    from app import serve
    serve(args.port, args.ollama_model, args.embeddings, policy_from_args(args))


def cli_eval(args):
    from scripts.evaluate import main as eval_main
    sys.argv = [sys.argv[0]]
    if args.ollama_model:
        sys.argv.extend(["--ollama-model", args.ollama_model])
    if args.embeddings:
        sys.argv.append("--embeddings")
    sys.argv.extend(["--semantic-min-score", str(args.semantic_min_score),
                     "--semantic-min-margin", str(args.semantic_min_margin)])
    if args.output:
        sys.argv.extend(["--output", args.output])
    eval_main()


def cli_prepare(args):
    from scripts.prepare_embeddings import prepare_model
    prepare_model()


def cli_chat(args):
    print("Iniciando Asistente Banamex en terminal. Escribe 'salir' para terminar.\n")
    engine = Engine(model=args.ollama_model, embeddings=args.embeddings, semantic_policy=policy_from_args(args))
    if args.embeddings:
        if not engine.index_embeddings():
            print(f"E5 no está disponible; se conserva la ruta local. {engine.semantic.error}")
    followup = None
    while True:
        try:
            question = input("\nUsuario: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego.")
            break
        if not question or question.lower() in ("salir", "exit", "quit"):
            print("Hasta luego.")
            break
        res = engine.answer(question, followup=followup)
        print(f"\nAsistente ({res['route']}):\n{res['text']}")
        if res.get("citations"):
            print("\nFuentes:")
            for c in res["citations"]:
                print(f" - {c['title']}: {c['url']}")
        followup = res.get("followup")


def main():
    parser = argparse.ArgumentParser(description="Banamex Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # serve
    p_serve = subparsers.add_parser("serve", help="Inicia el servidor web local")
    p_serve.add_argument("--port", type=int, default=8000, help="Puerto HTTP (defecto: 8000)")
    p_serve.add_argument("--ollama-model", choices=("qwen3:4b",), help="Modelo local Ollama")
    p_serve.add_argument("--embeddings", action="store_true", help="Búsqueda semántica ONNX")
    add_semantic_options(p_serve)
    p_serve.set_defaults(func=cli_serve)

    # eval
    p_eval = subparsers.add_parser("eval", help="Ejecuta la suite de evaluación")
    p_eval.add_argument("--ollama-model", choices=("qwen3:4b",), help="Modelo local Ollama")
    p_eval.add_argument("--embeddings", action="store_true", help="Búsqueda semántica ONNX")
    p_eval.add_argument("--output", help="Carpeta para los nuevos reportes")
    add_semantic_options(p_eval)
    p_eval.set_defaults(func=cli_eval)

    # prepare-embeddings
    p_prep = subparsers.add_parser("prepare-embeddings", help="Descarga y valida el modelo ONNX")
    p_prep.set_defaults(func=cli_prepare)

    # chat
    p_chat = subparsers.add_parser("chat", help="Modo interactivo en consola")
    p_chat.add_argument("--ollama-model", choices=("qwen3:4b",), help="Modelo local Ollama")
    p_chat.add_argument("--embeddings", action="store_true", help="Búsqueda semántica ONNX")
    add_semantic_options(p_chat)
    p_chat.set_defaults(func=cli_chat)

    args = parser.parse_args()
    if hasattr(args, "semantic_min_score"):
        try:
            policy_from_args(args)
        except ValueError as error:
            parser.error(str(error))
    args.func(args)


if __name__ == "__main__":
    main()
