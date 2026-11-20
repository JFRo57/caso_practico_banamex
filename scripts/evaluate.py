"""Re-run the private evaluation and audit citations against downloaded HTML."""

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import json
from math import ceil
from pathlib import Path
import sys
from time import perf_counter
from xml.etree import ElementTree
from zipfile import ZipFile

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asistente_banamex import Engine, ROOT, WORK_DIR
from asistente_banamex.semantic import EMBEDDING_MODEL, add_semantic_options, policy_from_args

OUTPUT = WORK_DIR / "evaluation"
CASES = ROOT / "evaluation" / "cases"
XLSX = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXPECTATIONS = {
    1: ("answer", ["requirements", "joy-income", "clasica-income"], None),
    2: ("answer", ["joy-annual", "clasica-annual", "joy-inactivity"], "Joy tiene la anualidad más baja"),
    3: ("answer", ["joy-annual", "clasica-annual", "joy-inactivity", "joy-benefit", "clasica-benefit"], None),
    4: ("clarify", ["cat_definition"], "¿Quieres el CAT de Joy o de Clásica?"),
    5: ("answer", ["account_branch", "account_online", "switch-requirements"], "comprobante de domicilio"),
    6: ("answer", ["account_online", "switch-requirements"], "navegador del celular"),
    7: ("clarify", [], "MiCuenta o de Switch"), 8: ("abstain", [], None),
    9: ("derive", ["phone"], None),
    10: ("abstain", [], None), 11: ("abstain", [], None), 12: ("abstain", [], None),
    13: ("answer", ["phone"], "55 1226 2639"), 14: ("answer", ["branch"], None),
    15: ("answer", ["pin"], None), 16: ("answer", ["charge"], None),
    17: ("abstain", [], None), 18: ("derive", ["phone"], None), 19: ("abstain", [], None),
    20: ("answer", ["joy-annual", "clasica-annual", "joy-inactivity"], None),
}


def excel_cases():
    excel_path = CASES / "preguntas_prueba.xlsx"
    if not excel_path.is_file():
        excel_path = OUTPUT / "preguntas_prueba.xlsx"
    with ZipFile(excel_path) as workbook:
        shared = ["".join(t.text or "" for t in item.iter(XLSX + "t"))
                  for item in ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))]
        sheet = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        for row in list(sheet.iter(XLSX + "row"))[1:]:
            values = {}
            for cell in row.findall(XLSX + "c"):
                value = cell.findtext(XLSX + "v")
                if value is not None:
                    values[cell.get("r")[0]] = shared[int(value)] if cell.get("t") == "s" else value
            number = int(values["A"])
            action, facts, contains = EXPECTATIONS[number]
            yield {
                "id": str(number), "block": "excel", "question": values["C"], "reference_behavior": values["D"],
                "action": action, "facts": facts, "contains": contains,
                "optional_facts": ["joy-income", "clasica-income"] if number == 3 else [],
            }


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skipping = None
        self.words = []

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script", "noscript"}:
            self.skipping = tag

    def handle_endtag(self, tag):
        if tag == self.skipping:
            self.skipping = None

    def handle_data(self, data):
        if not self.skipping:
            self.words.extend(data.split())


def audit_sources(engine):
    texts = {}
    data_dir = (ROOT / "data") if (ROOT / "data").is_dir() else (ROOT / "corpus")
    for source_id, source in engine.sources.items():
        raw = (data_dir / source["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"Snapshot changed without review: {source_id}")
        parser = VisibleText()
        parser.feed(raw.decode("utf-8"))
        texts[source_id] = " ".join(parser.words)
    count = 0
    for fact in engine.facts.values():
        for excerpt in fact["evidence"]:
            if excerpt not in texts[fact["source"]]:
                raise ValueError(f"{fact['id']}: missing excerpt {excerpt!r}")
            count += 1
    return count


def percentile(values, percentile):
    return round(sorted(values)[ceil(len(values) * percentile) - 1], 2) if values else None


def compare(engine, cases):
    rows = []
    for case in cases:
        start = perf_counter()
        result = engine.answer(case["question"], case.get("followup"))
        duration_ms = (perf_counter() - start) * 1000
        expected = set(case["facts"])
        deployed = set(result["facts"])
        allowed = expected | set(case.get("optional_facts", []))
        field_check = expected.issubset(deployed) and deployed.issubset(allowed)
        if result["action"] != case["action"]:
            field_check = False
        if case.get("contains") and case["contains"].casefold() not in result["text"].casefold():
            field_check = False
        if any(text.casefold() in result["text"].casefold() for text in case.get("forbidden", [])):
            field_check = False
        if case.get("language") and result["language"] != case["language"]:
            field_check = False
        if case.get("redact") and not result["redacted"]:
            field_check = False
        if deployed and not result["citations"]:
            field_check = False
        critical = (result["action"] == "answer" and (case["action"] != "answer" or not field_check))
        if case.get("redact") and not result["redacted"]:
            critical = True
        rows.append({
            "block": case["block"], "case": case["id"], "question": case["question"],
            "continuation": bool(case.get("followup")),
            "expected_behavior": case.get("reference_behavior", ""),
            "expected_action": case["action"], "actual_action": result["action"],
            "route": result["route"], "passed": field_check, "critical_error": critical, "ms": round(duration_ms, 3),
            "classifier_attempted": result.get("classifier_attempted", False),
            "semantic_decision": result.get("semantic", {}).get("decision", "not_attempted"),
            "semantic_margin": result.get("semantic", {}).get("margin"),
            "semantic_scores": json.dumps(result.get("semantic", {}).get("scores", {}), ensure_ascii=False),
            "expected_facts": ", ".join(sorted(expected)), "used_facts": ", ".join(result["facts"]),
            "fts_candidates": ", ".join(result["candidates"]), "response": result["text"],
            "urls": " | ".join(dict.fromkeys(source["url"] for source in result["citations"])),
        })
    return rows


def counts(rows):
    answerable = [row for row in rows if row["expected_action"] == "answer" and not row["continuation"]]
    limits = [row for row in rows if row["expected_action"] != "answer"]
    return {
        "total": len(rows), "passed": sum(row["passed"] for row in rows),
        "first_turn": {"resolved": sum(row["passed"] for row in answerable), "answerable": len(answerable)},
        "limits": {"correct": sum(row["passed"] for row in limits), "total": len(limits)},
        "critical_errors": sum(row["critical_error"] for row in rows),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ollama-model", choices=("qwen3:4b",))
    parser.add_argument("--embeddings", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT / "adaptive_revision")
    add_semantic_options(parser)
    args = parser.parse_args()
    try:
        semantic_policy = policy_from_args(args)
    except ValueError as error:
        parser.error(str(error))

    local = Engine()
    checked = audit_sources(local)
    cases = list(excel_cases())
    for filename in ("extra_cases.json", "semantic_cases.json", "account_cases.json"):
        case_file = CASES / filename
        if not case_file.is_file():
            case_file = OUTPUT / filename
        cases.extend(json.loads(case_file.read_text(encoding="utf-8")))
    variants = {"local": local}
    warmup = None
    embedding_warmup_ms = {}
    if args.ollama_model:
        hybrid = Engine(model=args.ollama_model)
        # Warm up the real model separately so cold start and request latency stay distinct.
        start = perf_counter()
        _, route = hybrid.model.warmup()
        warmup = {"route": route, "ms": round((perf_counter() - start) * 1000, 2)}
        if route == "fallback":
            raise RuntimeError(f"Ollama did not answer the warmup: {warmup}")
        variants["hybrid"] = hybrid
    if args.embeddings:
        variants["embeddings_only"] = Engine(embeddings=True, semantic_policy=semantic_policy)
        if args.ollama_model:
            variants["adaptive"] = Engine(model=args.ollama_model, embeddings=True, semantic_policy=semantic_policy)

    results = {}
    for name, engine in variants.items():
        if engine.semantic:
            start = perf_counter()
            if not engine.index_embeddings():
                raise RuntimeError(f"Could not build the local index for {EMBEDDING_MODEL}: {engine.semantic.error}")
            embedding_warmup_ms[name] = round((perf_counter() - start) * 1000, 2)
        print(f"Evaluating {name} on {len(cases)} identical cases", flush=True)
        rows = compare(engine, cases)
        results[name] = (rows, {
            block: counts([row for row in rows if row["block"] == block])
            for block in dict.fromkeys(row["block"] for row in rows)
        })

    summary = {
        "snapshot": local.snapshot, "source_count": len(local.sources), "audited_excerpts": checked,
        "model": args.ollama_model, "warmup": warmup,
        "embedding_model": EMBEDDING_MODEL if args.embeddings else None,
        "embedding_warmup_ms": embedding_warmup_ms, "variants": {},
        "routing_revision": "e5_direct_then_optional_qwen",
        "semantic_policy": {"min_score": semantic_policy.min_score, "min_margin": semantic_policy.min_margin,
                            "thresholds_provisional": True},
    }
    for name, (rows, blocks) in results.items():
        summary["variants"][name] = {
            "blocks": blocks,
            "all": counts(rows),
            "p50_ms": percentile([row["ms"] for row in rows], 0.50),
            "p95_ms": percentile([row["ms"] for row in rows], 0.95),
            "model_p95_ms": percentile([row["ms"] for row in rows if row["classifier_attempted"]], 0.95),
            "ollama_count": sum(row["route"] == "ollama" for row in rows),
            "semantic_count": sum(row["route"] == "semantic" for row in rows),
            "semantic_ollama_count": sum(row["route"] == "semantic_ollama" for row in rows),
            "direct_e5_answers": sum(row["route"] == "semantic" and row["actual_action"] == "answer" for row in rows),
            "classifier_attempts": sum(row["classifier_attempted"] for row in rows),
            "escalation_rate": round(sum(row["classifier_attempted"] for row in rows) / len(rows), 4),
            "fallback_count": sum(row["route"] == "fallback" for row in rows),
        }
    for control, variant, key in (
        ("local", "hybrid", "paired"),
        ("local", "embeddings_only", "paired_embeddings_only"),
        ("hybrid", "adaptive", "paired_embeddings"),
        ("embeddings_only", "adaptive", "paired_qwen_after_e5"),
    ):
        if control in results and variant in results:
            pairs = list(zip(results[control][0], results[variant][0], strict=True))
            summary[key] = {
                "gains": [row["case"] for left, row in pairs if row["passed"] and not left["passed"]],
                "regressions": [row["case"] for left, row in pairs if left["passed"] and not row["passed"]],
            }
    args.output.mkdir(parents=True, exist_ok=True)
    for name, (rows, _) in results.items():
        with (args.output / f"results_{name}.csv").open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    (args.output / "summary.json").write_text(summary_json, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
