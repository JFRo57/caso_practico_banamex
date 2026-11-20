"""Evaluate Mexican Spanish cases with local rules, real E5 or local Ollama.

These cases were written with the change. They are not an independent test set.
Historical 75-case reports are never overwritten by this command.
Use --mode embeddings to run without Ollama, or --mode adaptive to combine them.
"""

import argparse
import csv
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asistente_banamex import Engine, ROOT, WORK_DIR
from asistente_banamex import PACKAGE_DIR
from scripts.evaluate import compare, counts
from asistente_banamex.semantic import add_semantic_options, policy_from_args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embeddings", action="store_true")
    parser.add_argument("--mode", choices=("local", "embeddings", "hybrid", "adaptive"), default="hybrid")
    parser.add_argument("--timeout", type=float, default=25)
    parser.add_argument("--output", type=Path, default=WORK_DIR / "evaluation" / "language_revision")
    add_semantic_options(parser)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout debe ser positivo")
    facts = ROOT / "data" / "facts.json"
    if not facts.is_file():
        facts = PACKAGE_DIR / "data" / "facts.json"
    try:
        semantic_policy = policy_from_args(args)
    except ValueError as error:
        parser.error(str(error))
    model = "qwen3:4b" if args.mode in {"hybrid", "adaptive"} else None
    embeddings = args.embeddings or args.mode in {"embeddings", "adaptive"}
    engine = Engine(path=facts, model=model, embeddings=embeddings, semantic_policy=semantic_policy)
    if engine.model:
        engine.model.timeout = args.timeout
        _, route = engine.model.warmup()
        if route == "fallback":
            parser.exit(1, "Ollama local no está disponible. No se generó una evaluación de Qwen3.\n")
    if embeddings and not engine.index_embeddings():
        parser.exit(1, f"No se pudo preparar E5: {engine.semantic.error}\n")
    cases_path = PACKAGE_DIR / "evaluation" / "cases" / "language_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    for case in cases:
        case["block"] = "lenguaje_mexicano"
    rows = compare(engine, cases)
    summary = {
        "model": model, "embeddings": embeddings,
        "mode": "adaptive" if model and embeddings else "hybrid" if model else "embeddings" if embeddings else "local",
        "scope": "regression_cases_written_with_language_revision_not_independent",
        "timeout_seconds": args.timeout,
        "results": counts(rows),
        "failed_cases": [row["case"] for row in rows if not row["passed"]],
        "fallback_cases": [row["case"] for row in rows if row["route"] == "fallback"],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "results.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
