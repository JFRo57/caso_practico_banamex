"""Build cited bilingual responses and enforce the evidence requirements."""

from decimal import Decimal
import re

from .routing import ACCOUNT_FACTS, ACCOUNT_SERVICE_FACTS, PRODUCTS, PRODUCT_TOPICS


NAMES = {"joy": "Joy", "clasica": "Clásica"}
POLICY = {
    "personal": (
        "Esta consulta requiere el canal oficial. No puedo revisar tu cuenta ni determinar ofertas personales.",
        "This requires the official bank channel. I cannot access your account or determine personal offers.",
    ),
    "advice": (
        "Puedo explicar información publicada. Para una recomendación de inversión personalizada, consulta a un asesor por un canal oficial.",
        "I can explain published information. For personalized investment advice, contact an adviser through an official channel.",
    ),
    "unknown": (
        "No tengo evidencia para esa consulta. Puedo ayudarte con Joy, Clásica, apertura de cuentas, canales de atención y seguridad básica.",
        "I don't have evidence for that question. I can help with Joy, Clásica, opening an account, official contact channels and basic security.",
    ),
    "outside": (
        "Esa consulta está fuera de mi alcance. Puedo ayudarte con Joy, Clásica, apertura de cuentas, canales de atención y seguridad básica.",
        "That question is outside my scope. I can help with Joy, Clásica, opening an account, official contact channels and basic security.",
    ),
    "exchange": (
        "No puedo confirmar el tipo de cambio del día con las fuentes de este prototipo.",
        "I can't verify today's exchange rate with the sources available in this prototype.",
    ),
    "sensitive": (
        "No compartas NIP, CVV, contraseñas, códigos o números de tarjeta en este chat. Usa un canal oficial si necesitas ayuda con tu cuenta.",
        "Keep PINs, CVVs, passwords, codes and card numbers out of this chat. Use an official channel for help with your account.",
    ),
}


def money(cents):
    units, remainder = divmod(cents, 100)
    return f"${units:,}" + (f".{remainder:02d}" if remainder else "") + " MXN"


def render_fact(fact, lang):
    topic = fact["topic"]
    if "text" in fact:
        return fact["text"][lang]
    name = NAMES[fact["product"]]
    if topic == "annual":
        amount = money(fact["amount_cents"])
        if not fact["amount_cents"]:
            return (f"{name} no cobra comisión por administración ({amount})." if lang == "es"
                    else f"{name} has no annual administration fee ({amount}).")
        month = money(fact["monthly_cents"])
        if lang == "en":
            return (f"{name} lists {amount} before VAT as the administration fee in its annual CAT disclosure. "
                    f"The published monthly charge is {month} before VAT. "
                    f"If you paid this fee before {fact['transition_date']}, the bank says it will not charge an additional fee before your anniversary.")
        return (f"{name} publica {amount} sin IVA como comisión por administración en el desglose del CAT anual. "
                f"El cobro mensual publicado es de {month} al mes sin IVA. "
                f"Si pagaste la comisión antes del {fact['transition_date']}, el banco indica que no habrá otro cargo hasta tu aniversario.")
    if topic == "inactivity":
        fee, minimum = money(fact["amount_cents"]), money(fact["minimum_cents"])
        if lang == "en":
            return (f"{name} charges an inactivity fee of {fee} per month before VAT unless you spend at least {minimum} in purchases that month. "
                    "Recurring charges count. Installments on interest-free purchases do not.")
        return (f"{name} cobra {fee} al mes sin IVA por inactividad si no acumulas al menos {minimum} en compras durante el mes. "
                "Los cargos recurrentes cuentan. Las parcialidades a meses sin intereses no cuentan.")
    if topic == "cat":
        if lang == "en":
            return (f"{name} has an average CAT of {fact['percent']}% before VAT, "
                    f"calculated on {fact['valid_from']} and valid through {fact['valid_to']}.")
        return (f"{name} tiene un CAT promedio de {fact['percent']}% sin IVA, "
                f"calculado el {fact['valid_from']} y vigente al {fact['valid_to']}.")
    if topic == "income":
        amount = money(fact["amount_cents"])
        return (f"Para {name}, el ingreso mensual mínimo publicado es de {amount}." if lang == "es"
                else f"For {name}, the published minimum monthly income is {amount}.")
    raise ValueError(f"Unsupported fact {topic}")


class AnswerBuilder:
    def __init__(self, corpus):
        self.corpus = corpus

    def _result(self, action, route, lang, reason, text, facts=(), candidates=(), redacted=False):
        unique = {}
        for fact in facts:
            source = self.corpus.sources[fact["source"]]
            unique.setdefault(
                (fact["source"], fact["section"]),
                {"url": source["url"], "title": source["title"], "section": fact["section"], "date": source["date"]},
            )
        return {
            "action": action, "reason": reason, "route": route, "language": lang, "text": text,
            "citations": list(unique.values()), "facts": [fact["id"] for fact in facts],
            "candidates": list(candidates), "redacted": redacted,
        }

    def policy(self, reason, lang):
        text = POLICY[reason][lang == "en"]
        facts = ()
        if reason in {"personal", "advice"} and (official := self.corpus.fact("phone")) and self.corpus.is_usable(official):
            facts = (official,)
        return self._result("derive" if facts else "abstain", "local", lang, reason, text, facts, redacted=reason == "sensitive")

    def clarify(self, lang, route, reason="product", candidates=(), followup=None):
        prompts = {
            "account_opening": ("¿Quieres conocer los requisitos para abrir MiCuenta en sucursal o Switch en línea?",
                                "Would you like the requirements for opening MiCuenta at a branch or Switch online?"),
            "account_fee": ("¿Consultas las comisiones de MiCuenta o de Switch?", "Are you asking about MiCuenta or Switch account fees?"),
            "product": ("¿Te refieres a Joy o a Clásica?", "Do you mean Joy or Clásica?"),
            "branch_intent": ("¿Quieres ubicar una sucursal o saber si puedes solicitar la tarjeta sin acudir?",
                              "Do you want to locate a branch or find out whether you can apply without visiting one?"),
            "requirements": ("¿Buscas los requisitos para abrir una cuenta de débito o para solicitar una tarjeta Joy o Clásica?",
                             "Are you asking about opening a debit account or applying for a Joy or Clásica credit card?"),
            "topic": ("¿Quieres consultar la anualidad, el cargo por poco uso o el CAT de Joy y Clásica?",
                      "Would you like the annual fee, inactivity charges or CAT for Joy and Clásica?"),
        }
        result = self._result("clarify", route, lang, reason, prompts[reason][lang == "en"], candidates=candidates)
        if followup:
            result["followup"] = {"topic": followup, "language": lang}
        return result

    def resolve(self, plan, question, lang, route, candidates):
        topic, products = plan.topic, plan.products
        if topic == "card_application_channel" and not products:
            return self.clarify(lang, route, candidates=candidates, followup=topic)
        if topic in PRODUCT_TOPICS and len(products) == 0 and plan.operation == "detail":
            return self.clarify(lang, route, candidates=candidates, followup=topic)
        if topic in {"annual", "cat", "income"} and plan.operation in {"highest", "lowest", "compare"}:
            products = PRODUCTS
        if topic in PRODUCT_TOPICS:
            facts = [self.corpus.fact(topic, product) for product in products]
            # A Joy administration fee answer must disclose its separate inactivity charge.
            if topic == "annual" and "joy" in products:
                facts.append(self.corpus.fact("inactivity", "joy"))
        elif topic in {"compare", "low_use"}:
            selected = products if topic == "low_use" and products else PRODUCTS
            facts = [self.corpus.fact("annual", product) for product in selected]
            if "joy" in selected:
                facts.append(self.corpus.fact("inactivity", "joy"))
            if topic == "compare":
                facts.extend(self.corpus.fact(concept, product) for product in PRODUCTS for concept in ("benefit", "income"))
        elif topic in ACCOUNT_SERVICE_FACTS:
            facts = [self.corpus.fact(fact_id) for fact_id in ACCOUNT_SERVICE_FACTS[topic]]
        elif topic in ACCOUNT_FACTS:
            facts = [self.corpus.fact(fact_id) for fact_id in ACCOUNT_FACTS[topic]]
        elif topic == "card_application_channel":
            facts = [self.corpus.fact("requirements", product) for product in products]
        elif topic == "requirements":
            facts = []
            if products and re.search(r"\b(linea|online|internet|digital|sin (?:ir a )?sucursal|no ir a (?:la )?sucursal)\b", question):
                facts.append(self.corpus.fact("requirements"))
            if products:
                facts.extend(self.corpus.fact(topic, product) for product in products)
            else:
                facts.append(self.corpus.fact(topic))
            facts.extend(self.corpus.fact("income", product) for product in (products or PRODUCTS))
        else:
            facts = [self.corpus.fact(topic)]
        wants_live_fee = topic in {"annual", "inactivity", "compare", "low_use", "micuenta_fees", "switch_fees"} and re.search(
            r"\b(hoy|ahorita|today|right now)\b|vigente (?:en este momento|al momento)", question,
        )
        if wants_live_fee or not facts or not all(fact and self.corpus.is_usable(fact) for fact in facts):
            available = [fact for fact in facts if fact]
            text = ("No puedo confirmar ese dato para el alcance indicado con las fichas disponibles. Consulta la fuente oficial."
                    if lang == "es" else "I can't confirm that from the available facts. Please check the official source.")
            result = self._result("abstain", route, lang, "missing_evidence", text, available, candidates)
            result["facts"] = []
            return result
        if topic == "card_application_channel":
            names = ", ".join(NAMES[product] for product in products)
            text = (
                f"Sobre solicitar {names} sin ir a una sucursal: las fichas disponibles no confirman "
                "que todo el trámite pueda completarse a distancia. Revisa las opciones de solicitud "
                "y sus condiciones en la ficha oficial de la tarjeta enlazada abajo."
                if lang == "es" else
                f"For applying for {names} without visiting a branch, the available facts do not confirm "
                "that the entire process can be completed remotely. Check the application options "
                "and conditions on the official card page linked below."
            )
            result = self._result("abstain", route, lang, "missing_evidence", text, facts, candidates)
            result["followup"] = {"topic": topic, "products": list(products), "language": lang}
            return result
        lines = [render_fact(fact, lang) for fact in facts]
        if plan.operation in {"highest", "lowest"}:
            key = "amount_cents" if topic == "annual" else "percent"
            compared = [fact for fact in facts if fact["topic"] == topic]
            target = (max if plan.operation == "highest" else min)(Decimal(fact[key]) for fact in compared)
            winners = [NAMES[fact["product"]] for fact in compared if Decimal(fact[key]) == target]
            label = ("anualidad" if topic == "annual" else "CAT") if lang == "es" else ("annual fee" if topic == "annual" else "CAT")
            if len(winners) == 1:
                direction = ("más alto" if plan.operation == "highest" else "más bajo") if lang == "es" else ("highest" if plan.operation == "highest" else "lowest")
                if lang == "es" and topic == "annual":
                    direction = direction[:-1] + "a"
                header = (f"Entre Joy y Clásica, {winners[0]} tiene {'la' if topic == 'annual' else 'el'} {label} {direction}."
                          if lang == "es" else f"Of Joy and Clásica, {winners[0]} has the {direction} {label}.")
            else:
                header = (f"Joy y Clásica tienen el mismo valor de {label}." if lang == "es"
                          else f"Joy and Clásica have the same {label}.")
            lines.insert(0, header)
        if topic == "cat_definition" and re.search(r"esta tarjeta|esa tarjeta|this card|which card|cual es el de", question):
            lines.append("¿Quieres el CAT de Joy o de Clásica?" if lang == "es" else "Would you like the CAT for Joy or Clásica?")
            result = self._result("clarify", route, lang, topic, "\n\n".join(lines), facts, candidates)
            result["followup"] = {"topic": "cat", "language": lang}
            return result
        result = self._result("answer", route, lang, topic, "\n\n".join(lines), facts, candidates)
        if topic == "requirements":
            result["followup"] = {"topic": topic, "products": list(products), "language": lang}
        return result

    def abstain(self, reason, route, lang, candidates):
        return self._result("abstain", route, lang, reason, POLICY[reason][lang == "en"], candidates=candidates)
