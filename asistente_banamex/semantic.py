"""Rank reviewed account-opening topics with multilingual E5 on CPU."""

from dataclasses import dataclass
import math

from . import WORK_DIR


MODEL_REPOSITORY = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
EMBEDDING_MODEL = f"{MODEL_REPOSITORY} (ONNX INT8)"
MODEL_DIRECTORY = WORK_DIR / ".models" / "multilingual-e5-small"
MODEL_FILENAME = "model_qint8_avx512_vnni.onnx"
MODEL_FILES = {
    MODEL_FILENAME: "dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88",
    "tokenizer.json": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
}
MIN_SIMILARITY = 0.78


@dataclass(frozen=True)
class SemanticPolicy:
    """Provisional routing thresholds; cosine scores are not probabilities."""

    min_score: float = 0.82
    min_margin: float = 0.015

    def __post_init__(self):
        if not math.isfinite(self.min_score) or not MIN_SIMILARITY <= self.min_score <= 1:
            raise ValueError(f"La similitud directa debe estar entre {MIN_SIMILARITY} y 1.")
        if not math.isfinite(self.min_margin) or not 0 < self.min_margin <= 1:
            raise ValueError("El margen debe ser mayor que 0 y como máximo 1.")


def add_semantic_options(parser):
    parser.add_argument("--semantic-min-score", type=float, default=0.82,
                        help="Similitud mínima para responder con E5 sin Qwen3 (provisional)")
    parser.add_argument("--semantic-min-margin", type=float, default=0.015,
                        help="Separación mínima entre los dos mejores candidatos de E5 (provisional)")


def policy_from_args(args):
    return SemanticPolicy(args.semantic_min_score, args.semantic_min_margin)


@dataclass(frozen=True)
class SemanticResult:
    """Raw cosine scores plus a lexical tiebreaker for retrieval, never confidence."""

    scores: tuple = ()
    lexical_topics: frozenset = frozenset()
    error: str | None = None

    @property
    def ranked(self):
        return tuple(sorted(self.scores, key=lambda item: (-item[1], item[0])))

    @property
    def candidates(self):
        ranked = sorted(
            ((topic, score) for topic, score in self.scores if score >= MIN_SIMILARITY),
            key=lambda item: (-(item[1] + (0.025 if item[0] in self.lexical_topics else 0)), item[0]),
        )
        return tuple(topic for topic, _ in ranked[:3])

    @property
    def margin(self):
        ranked = self.ranked
        return ranked[0][1] - ranked[1][1] if len(ranked) >= 2 else None

    def comparison(self, topics=None):
        return tuple(item for item in self.ranked if topics is None or item[0] in topics)

    def comparison_margin(self, topics=None):
        ranked = self.comparison(topics)
        return ranked[0][1] - ranked[1][1] if len(ranked) >= 2 else None

    def direct_topic(self, policy, topics=None):
        ranked = self.comparison(topics)
        if self.error or len(ranked) < 2:
            return None
        if ranked[0][1] >= policy.min_score and self.comparison_margin(topics) >= policy.min_margin:
            return ranked[0][0]
        return None

    def describe(self, policy, decision, topics=None):
        margin = self.comparison_margin(topics)
        return {
            "decision": decision,
            "scores": {topic: round(score, 5) for topic, score in self.ranked},
            "margin": round(margin, 5) if margin is not None else None,
            "comparison_topics": [topic for topic, _ in self.comparison(topics)],
            "min_score": policy.min_score, "min_margin": policy.min_margin,
            "thresholds_provisional": True, "error": self.error,
        }


class OnnxEncoder:
    def __init__(self):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        if not all((MODEL_DIRECTORY / name).is_file() for name in MODEL_FILES):
            raise FileNotFoundError("Prepara los archivos con python3 prepare_embeddings.py.")

        self.np = np
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        try:
            self.session = ort.InferenceSession(
                str(MODEL_DIRECTORY / MODEL_FILENAME), sess_options=options,
                providers=["CPUExecutionProvider"],
            )
            self.tokenizer = Tokenizer.from_file(str(MODEL_DIRECTORY / "tokenizer.json"))
        except Exception as error:
            raise RuntimeError(f"No se pudo cargar el modelo ONNX: {error}") from error
        self.input_names = {item.name for item in self.session.get_inputs()}
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding(pad_id=self.tokenizer.token_to_id("<pad>"), pad_token="<pad>")

    def encode(self, texts, prefix):
        np = self.np
        tokens = self.tokenizer.encode_batch([f"{prefix}: {text}" for text in texts])
        mask = np.asarray([item.attention_mask for item in tokens], dtype=np.int64)
        inputs = {
            "input_ids": np.asarray([item.ids for item in tokens], dtype=np.int64),
            "attention_mask": mask,
        }
        if "token_type_ids" in self.input_names:
            inputs["token_type_ids"] = np.asarray([item.type_ids for item in tokens], dtype=np.int64)
        try:
            hidden, = self.session.run(["last_hidden_state"], inputs)
        except Exception as error:
            raise RuntimeError(f"Falló la inferencia ONNX: {error}") from error
        # Average non-padding tokens, then normalize for cosine similarity.
        weights = mask[..., None].astype(hidden.dtype)
        pooled = (hidden * weights).sum(axis=1) / weights.sum(axis=1)
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        if not np.isfinite(norms).all() or (norms == 0).any():
            raise ValueError("Invalid embedding vector")
        return pooled / norms


class SemanticIndex:
    def __init__(self):
        self.encoder = None
        self.vectors = {}
        self.error = None

    def build(self, profiles):
        if not profiles:
            self.error = "No hay fichas de apertura utilizables."
            return False
        try:
            encoder = OnnxEncoder()
            vectors = encoder.encode(profiles.values(), "passage")
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            self.error = str(error)
            return False
        self.encoder = encoder
        self.vectors = dict(zip(profiles, vectors, strict=True))
        self.error = None
        return True

    def search(self, question, lexical_topics=()):
        if not self.encoder:
            return SemanticResult(error=self.error or "El índice E5 no está disponible.")
        try:
            vector, = self.encoder.encode([question], "query")
        except (OSError, RuntimeError, ValueError) as error:
            return SemanticResult(error=str(error))
        scores = {topic: float(vector @ reference) for topic, reference in self.vectors.items()}
        if not all(math.isfinite(score) and -1.00001 <= score <= 1.00001 for score in scores.values()):
            return SemanticResult(error="E5 devolvió similitudes inválidas.")
        return SemanticResult(tuple(scores.items()), frozenset(lexical_topics))

    def shortlist(self, question, lexical_topics):
        """Compatibility wrapper; the engine uses search once to retain its scores."""
        return self.search(question, lexical_topics).candidates
