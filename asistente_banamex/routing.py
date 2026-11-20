"""Normalize questions, enforce scope, and identify supported intents."""

from dataclasses import dataclass
import re
import unicodedata


PRODUCTS = ("joy", "clasica")
TOPICS = {
    "annual", "inactivity", "low_use", "compare", "cat", "cat_definition",
    "requirements", "income", "phone", "branch", "pin", "charge", "card_application_channel",
}
OPERATIONS = {
    "annual": ("detail", "compare", "highest", "lowest"),
    "cat": ("detail", "compare", "highest", "lowest"),
    "income": ("detail", "compare"),
}
PRODUCT_TOPICS = {"annual", "inactivity", "cat", "income"}
ACCOUNT_FACTS = {
    "account_opening": ("account_branch", "account_online", "switch-requirements"),
    "account_branch": ("account_branch",),
    "account_online": ("account_online", "switch-requirements"),
}
ACCOUNT_SERVICE_FACTS = {
    "micuenta_fees": ("micuenta-fees",),
    "switch_fees": ("switch-fees",),
    "account_camera": ("account-camera",),
    "account_activation": ("micuenta-activation",),
}
ACCOUNT_PLACE = r"\b(micuenta|mi\s?cuenta banamex)\b"
ACCOUNT_HINT = r"\b(switch|micuenta|debito|debit|checking account)\b"
ACCOUNT_TERMS = r"\b(cuentas?|accounts?|micuenta|switch|checking|debito|debit)\b"
ACCOUNT_OUTSIDE = (
    r"\b(cuenta base|cuenta de ahorro|savings account|cuenta (?:empresarial|infantil)|business account|"
    r"for (?:a minor|my (?:son|daughter|child))|para (?:un menor|mi hij[oa])|\d{1,2}[- ]year[- ]old)\b"
)
ACCOUNT_SERVICING = (
    r"\b(cerrar|cierre|cancelar|cancelacion|dar de baja|desactivar|reposicion|reemplazo|reemplazar|"
    r"reponer|close|closing|shut down|get rid of|terminate|deactivate|reopen|reopening|replacement|replacing|replace)\b"
)
SEMANTIC_OPENING_CUES = (
    r"\b(sacar|estrenar|obtener|papeles|papeleria|tramitar|llevar|llevo|llego|juntar|"
    r"paperwork|bring|get|getting|sign up|set up|onboard)\b"
)
SEMANTIC_SERVICE_CUES = (
    r"\b(comision\w*|cobr\w*|carg\w*|cuest\w*|cost\w*|fees?|charges?|pagar|pay|"
    r"saldo|balance|lana|feria|varos?|ingres\w*|sueldo|income|salary|"
    r"transfer\w*|retir\w*|withdraw\w*|perdi\w*|lost|stolen|robo|"
    r"activar|activacion|activation|activate|camara|camera|permisos?|permissions?|"
    r"nip|pin|cvv|bloque\w*|block\w*)\b"
)
PATTERNS = {
    "phone": r"\b(horarios?|telefonos?|telefono de atencion|llamar|marcar|a donde marc\w*|audiomatico|hotline|phone|opening hours|support hours|call center)\b",
    "branch": r"\b(sucursal(?:es)?|branch(?:es)?|atms?|cajeros?|localizador)\b",
    "annual": r"\b(anualidad(?:es)?|anulidad|comision (?:por|de) administracion|cuota anual|cobro anual|annual (fee|charge))\b",
    "inactivity": r"\b(inactividad|inactivity|inactive)\b",
    "low_use": r"no (la |lo )?us[oa]|casi no (la |lo )?us|poco uso|uso poco|si la dejo guardada|rarely use|hardly use",
    "cat": r"\bcat\b|costo anual total|total annual cost",
    "cat_definition": r"que (es|significa) (el )?cat\b|what (is|does) (the )?cat\b|cat stand for",
    "requirements": r"\brequisit\w*\b|documentos|pedir (la|una) tarjeta|solicitar (una |mi |la )?tarjeta|requirements|what (do i need|documents)",
    "income": r"ingreso(s)? minimo(s)?|minimum (monthly )?income|\b(gano|sueldo|salario|ganar)\b",
    "compare": r"\b(compar\w*|diferen\w*|versus|vs|difference|compare)\b",
}
FTS_PHRASES = {
    "annual": ("coste anual", "costo anual de la tarjeta", "cuota de administracion"),
    "branch": ("buscar sucursal", "ubicacion del banco"),
    "pin": ("seguridad de mi nip", "seguridad telefonica"),
    "phone": ("support number", "horario de servicio"),
}


@dataclass(frozen=True)
class Plan:
    topic: str
    products: tuple = ()
    operation: str = "detail"


def normalize(value):
    return "".join(
        part for part in unicodedata.normalize("NFKD", value.casefold())
        if unicodedata.category(part) != "Mn"
    )


def language(question):
    tokens = set(re.findall(r"[a-z]+", question))
    english = tokens & set("which what when where how does do can could cost highest lowest fee card annual compare income rarely barely branch need please checking stolen hello hi phone would charged drawer swipe if with open opening account accounts requirements documents".split())
    spanish = tokens & set("que cual cuando donde como tarjeta tarjetas cuanto cunato costo cuesta cual tiene puedo quiero uso necesito perdon ayuda hola monto al mas caro cara abrir apertura cuenta cuentas requisitos documentos sucursal".split())
    return "en" if len(english) > len(spanish) else "es"


def policy(question):
    if re.search(r"(?<!\d)(?:\d[ -]?){14,19}(?!\d)|\b[\w.+-]+@[\w.-]+\.\w{2,}", question):
        return "sensitive"
    secret = r"(?:nip|pin|cvv|clabe|contrasena|password|codigo(?: sms)?|netkey)"
    if re.search(rf"\b{secret}\b\s*(?:(?:es|is|:|=)\s*)?\d{{3,}}\b|\b{secret}\b\s*(?:es|is|:|=)\s*\S+", question):
        return "sensitive"
    if re.search(r"(te (?:doy|paso|mando|comparto)|i(?:'ll| will) (?:give|send|share)|(?:dime|dame|repite|muestrame|reveal|tell me)\s+(?:mi|tu|el|my|your|the))\b.{0,28}\b" + secret + r"\b", question):
        return "sensitive"
    if re.search(r"lista enlazada|linked list|capital de |capital of |receta|recipe|ignora (?:las |tus )?instrucciones|ignore (?:all |the |your )?instructions|\bpython\b|system prompt", question):
        return "outside"
    if re.search(r"tipo de cambio|exchange rate|dolar hoy", question):
        return "exchange"
    if re.search(r"cuanto me prest|me pueden prestar|me autoriz|mi saldo|saldo (?:de mi|disponible)|my (?:account )?balance|balance (?:in|of) my account|how much (?:can i (?:borrow|get)|will (?:you|the bank) lend)|(?:mi|my) (?:estado de cuenta|statement)|credit limit.*\bmy\b|\bmy\b.*credit limit", question):
        return "personal"
    if re.search(r"(recomiend\w*|conviene|debo|should i|recommend).{0,36}(accion|invert|stocks?|shares?|invest)", question):
        return "advice"
    if re.search(r"\b(oro|premier|platinum|costco|affinity|teleton|hipotecari[oa]|seguros?|inversion(?:es)?|mortgage|insurance|credito personal|personal loan)\b", question):
        return "outside"
    if re.search(ACCOUNT_OUTSIDE, question):
        return "outside"
    if re.search(ACCOUNT_TERMS, question) and re.search(ACCOUNT_SERVICING, question):
        return "outside"
    if re.search(ACCOUNT_TERMS, question) and re.search(r"\b(transferencias?|transfers?|retiros?|withdrawals?|emision|issuance)\b", question) and re.search(r"\b(comision\w*|cobr\w*|cost\w*|cuest\w*|fees?|charge\w*)\b", question):
        return "outside"
    return None


def named_products(question):
    return tuple(product for product in PRODUCTS if re.search(rf"\b{product}\b", question))


def account_service_plan(question):
    if named_products(question) or not re.search(ACCOUNT_TERMS, question):
        return None
    if re.search(r"\b(activar|activo|activacion|activate|activation)\b", question):
        return Plan("account_activation") if re.search(ACCOUNT_PLACE, question) else None
    if re.search(r"\b(camara|camera|ubicacion|location|selfie|permisos|permissions)\b", question):
        return Plan("account_camera") if re.search(r"\bswitch\b", question) else None
    if re.search(r"\b(transferencias?|transfers?|retiros?|withdrawals?|emision|issuance)\b", question):
        return None
    if re.search(r"\b(comision\w*|cobr\w*|carg\w*|cost\w*|cuest\w*|fees?|charge\w*|pay|pagar|manejo|maintenance|saldo minimo|saldo integral|minimum balance|waiv\w*)\b", question):
        micuenta = bool(re.search(ACCOUNT_PLACE, question))
        switch = bool(re.search(r"\bswitch\b", question))
        if micuenta == switch:
            return Plan("account_fee_product")
        return Plan("micuenta_fees" if micuenta else "switch_fees")
    return None


def account_opening_plan(question):
    if not re.search(r"\b(cuentas?|accounts?|micuenta|switch)\b", question):
        return None
    if not re.search(r"\b(abrir|abro|apertura|contratar|solicitar|requisitos?|documentos?|que necesito|quiero|sacar|tramitar|obtener|want|get|open(?! (?:for|until|today|tomorrow)\b)|opening(?! hours\b)|apply|set up|requirements?|documents?|what do i need)\b", question):
        return None
    if re.search(r"\b(tarjeta de credito|credit card)\b", question) or named_products(question):
        return None
    return Plan(account_channel(question))


def account_channel(question):
    micuenta = re.search(ACCOUNT_PLACE, question)
    switch = re.search(r"\bswitch\b", question)
    if micuenta and switch:
        return "account_opening"
    if micuenta:
        return "account_branch"
    if switch or re.search(r"\b(app|aplicacion|en linea|online|digital|celular|movil|browser|website|(?:on|using) (?:my|a|the) phone|without (?:(?:having|needing) to (?:go|visit)|going to|visiting)?\s*(?:a |the )?branch|sin (?:tener que |necesidad de |requerir )?(?:ir a |visitar |pisar )?(?:una |la )?sucursal|no (?:quiero |puedo |voy a |deseo )?(?:tener que )?(?:ir a |visitar |pisar )?(?:una |la )?sucursal|desde (?:mi )?(?:casa|celular)|sin salir|sin deposito|sin monto de apertura)\b", question):
        return "account_online"
    if re.search(r"\b(sucursal(?:es)?|branch(?:es)?|in person)\b", question):
        return "account_branch"
    return "account_opening"


def semantic_opening_allowed(question):
    """A similar opening profile is insufficient for an unrelated account procedure."""
    return (
        bool(re.search(ACCOUNT_TERMS, question))
        and bool(re.search(SEMANTIC_OPENING_CUES, question))
        and not re.search(ACCOUNT_SERVICING, question)
        and not re.search(ACCOUNT_OUTSIDE, question)
        and not re.search(SEMANTIC_SERVICE_CUES, question)
    )


def account_topic_matches_channel(topic, question):
    channel = account_channel(question)
    both_accounts = re.search(ACCOUNT_PLACE, question) and re.search(r"\bswitch\b", question)
    if both_accounts:
        return topic == "account_opening"
    return channel == "account_opening" or topic == channel


def planner_input(question):
    # Keep the original for the lexical baseline. The hybrid can expand
    # local colloquialisms before asking the model for a typed operation.
    if re.search(r"\b(tarjetas?|joy|clasica)\b", normalize(question)):
        replacements = (
            (r"\bcunato\b", "cuánto"),
            (r"\bmadrazo\b", "cobro"),
            (r"\bpor añejo\b", "anual"),
            (r"\bm[aá]s cariños[ao]\b", "más cara"),
        )
        for pattern, replacement in replacements:
            question = re.sub(pattern, replacement, question, flags=re.I)
    return question


def branch_is_negated(question):
    return bool(re.search(
        r"\b(without (?:(?:having|needing) to (?:go|visit)|going to|visiting)?\s*(?:a |the )?branch|sin (?:tener que |necesidad de |requerir )?(?:ir a |visitar |pisar )?(?:una |la )?sucursal|no (?:quiero |puedo |voy a |deseo )?(?:tener que )?(?:ir a |visitar |pisar )?(?:una |la )?sucursal)\b",
        question,
    ))


def card_channel_request(question):
    card = named_products(question) or re.search(r"\b(tarjetas?|cards?)\b", question)
    remote_application = re.search(
        r"\b(online|en linea|internet|desde (?:mi )?casa|digital)\b", question,
    ) and re.search(r"\b(quiero|solicitar|tramitar|sacar|contratar|obtener|pedir|requisitos?|want|apply|get)\b", question)
    return bool(card and (branch_is_negated(question) or remote_application))


def ambiguous_branch_request(question):
    return bool(
        (named_products(question) or re.search(r"\b(tarjetas?|cards?)\b", question))
        and re.search(PATTERNS["branch"], question)
        and not branch_is_negated(question)
        and not re.search(
            r"\b(donde|ubicacion|localizador|cerca|cercana|cercano|buscar|busco|horarios?|"
            r"where|location|locator|nearest|nearby|find|hours)\b", question,
        )
    )


def lexical_plan(question):
    products = named_products(question)
    if re.search(r"\b(clonad\w*|clonar\w*|robo|robad\w*|robaron|perdi\w*|pierd\w*|extravio|extraviad\w*|perder|perdiste|us[ao]r?on? mi tarjeta|sin (?:mi )?autorizaci\w*|compra.{0,25}no hice|cargo[s]? (?:que |no )?(?:no )?reconozc\w*|cargos? no reconoci\w*|no reconozc\w*|unrecognized (?:charge|transaction)|unauthorized (?:charge|transaction)|stolen card|lost (?:my )?card)\b", question):
        return Plan("charge")
    if re.search(r"\b(nip|pin)\b", question) and re.search(r"pedir|pid|solicit|por telefono|llamada|seguro|ask|phone|call|share|request", question):
        return Plan("pin")
    if re.search(r"\b(mas barat[ao]|mas economic[ao]|sin anualidad|sin comision (?:por |de )?administracion|cero anualidad|anualidad cero|no (?:quiero |deseo )?(?:pagar |tener |cobre? )?(?:de )?anualidad|cheapest)\b", question):
        return Plan("annual", PRODUCTS, "lowest")
    if re.search(PATTERNS["low_use"], question):
        return Plan("low_use", products)
    if re.search(PATTERNS["annual"], question):
        if re.search(r"mas (?:alta|car[ao])|mayor|highest|more expensive|mas elevad", question):
            return Plan("annual", PRODUCTS, "highest")
        if re.search(r"mas (?:baja|barat[ao]|basic[ao])|menor|lowest|cheapest", question):
            return Plan("annual", PRODUCTS, "lowest")
        return Plan("annual", products, "compare" if len(products) == 2 else "detail")
    if re.search(PATTERNS["inactivity"], question):
        return Plan("inactivity", products)
    if re.search(PATTERNS["cat_definition"], question) and not products:
        return Plan("cat_definition")
    if re.search(PATTERNS["cat"], question):
        return Plan("cat", products, "compare" if len(products) == 2 else "detail")
    branch_negated = branch_is_negated(question)
    if card_channel_request(question):
        return Plan("card_application_channel", products)
    for topic in ("phone", "branch", "income", "requirements", "compare"):
        if re.search(PATTERNS[topic], question):
            if topic == "branch" and (branch_negated or ambiguous_branch_request(question)):
                continue
            if topic == "compare" and not (products or re.search(r"tarjetas?|cards?", question)):
                return None
            if topic in ("income", "requirements") and not (products or re.search(r"credito|credit|tarjetas?|cards?", question)):
                return None
            target_products = PRODUCTS if (topic == "income" and not products and re.search(r"\b(cu[aá]l|alcanz\w*|puedo|todas)\b", question)) else products
            return Plan(topic, target_products, "compare" if topic == "income" and len(target_products) == 2 else "detail")
    return None
