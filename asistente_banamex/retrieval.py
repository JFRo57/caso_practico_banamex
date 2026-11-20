"""Load the reviewed corpus and rank candidate facts with SQLite FTS5."""

from datetime import datetime
import json
import re
import sqlite3
from threading import Lock
from weakref import finalize
from zoneinfo import ZoneInfo


SEARCH_TERMS = {
    "annual": "anualidad comisión administración cobro anual anualidad titular annual fee coste anual cuota anual",
    "inactivity": "inactividad penalización exención cargo mínimo compras mensuales inactivity fee",
    "low_use": "casi no uso tarjeta poco uso inactividad costos barely use rarely use",
    "compare": "comparación diferencia beneficios tarjetas comparar compare differences benefits",
    "cat": "cat costo anual total fecha cálculo vigencia CAT rate",
    "cat_definition": "qué significa CAT qué es el CAT what does CAT stand for",
    "requirements": "requisitos solicitar documentos identificación domicilio requirements documents",
    "account_branch": "abrir cuenta débito sucursal requisitos documentos open debit account branch requirements documents",
    "account_online": "abrir cuenta débito app en línea celular open debit account online app browser",
    "income": "ingreso mínimo ingresos mensual monthly minimum income",
    "phone": "horario teléfonos atención audiomático phone hours support",
    "branch": "sucursal cercana localizador cajeros branch locator nearest",
    "pin": "NIP pedir teléfono seguridad PIN fraud ask",
    "charge": "cargo no reconocido fraude bloquear aclaración unauthorized charge card",
}
STOP = set("a al algo cual cuales como con de del el en es esta este la las lo los mas me mi mis para por que se si su tu un una y and can for how i is it me my of or the this to what when which with you".split())


class Corpus:
    def __init__(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.facts = {fact["id"]: fact for fact in data["facts"]}
        self.sources = data["sources"]
        self.snapshot = data["snapshot"]
        self.index_lock = Lock()
        self.index = sqlite3.connect(":memory:", check_same_thread=False)
        self._close_index = finalize(self, self.index.close)
        try:
            with self.index:
                self.index.execute("CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, title, content, tokenize='unicode61 remove_diacritics 2')")
                self.index.executemany(
                    "INSERT INTO search VALUES (?, ?, ?)",
                    [(fact["id"], fact["keywords"], SEARCH_TERMS.get(fact["topic"], ""))
                     for fact in self.facts.values() if fact.get("enabled", True)],
                )
        except sqlite3.OperationalError:
            self._close_index()
            self.index = None

    def search(self, question):
        tokens = list(dict.fromkeys(word for word in re.findall(r"[a-z0-9]+", question) if len(word) > 1 and word not in STOP))
        if not tokens or self.index is None:
            return []
        match = " OR ".join(f'"{word}"' for word in tokens[:30])
        with self.index_lock:
            return [row[0] for row in self.index.execute(
                "SELECT id FROM search WHERE search MATCH ? ORDER BY bm25(search,0,2,1), id LIMIT 3", (match,)
            )]

    @staticmethod
    def is_usable(fact):
        today = datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()
        return fact.get("enabled", True) and fact.get("valid_to", "9999-12-31") >= today and fact.get("valid_from", "0000-01-01") <= today

    def fact(self, topic, product=None):
        return self.facts.get(f"{product}-{topic}" if product else topic)
