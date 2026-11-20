"""Contextual Mexican Spanish hints for the local intent classifier.

These examples explain possible meanings; they never rewrite the user's text
or select a banking fact by themselves.
"""

import re

from .routing import normalize


MEXICAN_SPANISH_HINTS = {
    "cost": {
        "topics": ("annual", "inactivity", "low_use", "micuenta_fees", "switch_fees", "account_fee_product"),
        "meaning": (
            "Asking about money or charges. These expressions alone do not identify "
            "annual fees, inactivity fees, CAT, or a comparison; use the full context."
        ),
        "expressions": (
            "cuánto me sale",
            "de a cómo sale",
            "cuánta lana cuesta",
            "cuánta feria tengo que pagar",
            "cuántos varos me cobran",
            "cuánto tengo que soltar",
            "cuánto me toca poner",
            "cuánto me pega al bolsillo",
            "de cuánto es el cobro",
            "cuánto me van a cargar",
            "cuánto me tumban",
            "cuánto me clavan",
        ),
    },
    "annual": {
        "topics": ("annual",),
        "meaning": (
            "Yearly cost, when explicitly asking about a card's fee or administration "
            "charge. A yearly time reference alone does not imply an annual fee."
        ),
        "expressions": (
            "cuánto me sale al año",
            "cuánto pago cada año",
            "el cobro de cada año",
            "la cuota del año",
            "lo que pago por año",
            "cuánto cuesta tenerla un año",
            "el cargo de cada doce meses",
            "cuánto desembolso anualmente",
            "lo que me cobran por todo el año",
            "el pago anual por mantener la tarjeta",
        ),
    },
    "expensive": {
        "topics": ("annual", "cat", "compare", "micuenta_fees", "switch_fees", "account_fee_product"),
        "meaning": (
            "An expensive price or charge, only in a financial cost context. Do not "
            "interpret affection, shopping, income, or credit limits as card fees. "
            "These expressions do not identify the cost metric. Use highest/lowest "
            "only with an explicit metric and a comparison or superlative; otherwise "
            "use unknown if the intended supported subject cannot be determined."
        ),
        "expressions": (
            "la que sale más cara",
            "la más carita",
            "la que sale más cariñosa",
            "la que cuesta más lana",
            "la que cuesta más varo",
            "la que pega más al bolsillo",
            "sale en un ojo de la cara",
            "sale en una buena lana",
            "cuesta un dineral",
            "sale bastante saladita",
        ),
    },
    "low_use": {
        "topics": ("low_use", "inactivity"),
        "meaning": (
            "Rarely using or keeping a card unused. When the question asks about "
            "the resulting cost, low_use is a supported subject. Do not interpret "
            "lost cards, cancellation, replacement, or literal objects as inactivity."
        ),
        "expressions": (
            "se queda juntando polvo",
            "la tengo guardada en el cajón",
            "la saco de vez en cuando",
            "solo la uso para emergencias",
            "no le doy uso",
            "la tengo de adorno",
            "casi no la muevo",
            "la dejo descansando",
            "se queda guardada",
            "paso meses sin pasarla",
        ),
    },
    "affordable": {
        "topics": ("annual", "cat", "compare", "micuenta_fees", "switch_fees", "account_fee_product"),
        "meaning": (
            "Lower cost only when the full question identifies a supported fee or cost metric. "
            "Cheap purchases, discounts and credit approval are different subjects. "
            "Do not choose a product or highest/lowest from a vague affordability question."
        ),
        "expressions": (
            "la que sale más barata",
            "la más baratita",
            "la que cuesta menos lana",
            "la que cuesta menos varo",
            "la que pega menos al bolsillo",
            "la que sale más económica",
            "la de menor cobro",
            "la que me sale más en cuenta",
            "la que cobra menos al año",
            "la que sale más accesible",
        ),
    },
    "income": {
        "topics": ("income",),
        "meaning": (
            "Published minimum monthly income for a supported credit card, when the "
            "question asks about that requirement. Never infer personal eligibility, "
            "approval, a credit limit or a loan amount from income."
        ),
        "expressions": (
            "cuánto tengo que ganar",
            "de cuánto debe ser mi sueldo",
            "qué sueldo piden",
            "cuánta lana debo ganar al mes",
            "qué ingreso mensual solicitan",
            "cuánto debo sacar en la chamba",
            "qué sueldo necesito para solicitarla",
            "qué ingreso piden comprobar",
            "cuánto debo ganar para tramitarla",
            "cuál es el mínimo de sueldo",
        ),
    },
    "account_opening": {
        "topics": ("account_opening", "account_branch", "account_online"),
        "meaning": (
            "Getting a new supported adult debit account. Identify MiCuenta/in-person "
            "or Switch/digital from context, or use account_opening if no channel is "
            "specified. Do not interpret account cancellation, replacement, activation, "
            "fees or accounts for minors as opening."
        ),
        "expressions": (
            "sacar una cuenta",
            "sacar la MiCuenta",
            "sacar la Switch",
            "estrenar una cuenta",
            "darme de alta con una cuenta",
            "hacerme de una cuenta",
            "tramitar una cuenta",
            "abrirla desde el cel",
            "sacar mi cuenta sin ir al banco",
            "hacer el trámite desde casa",
        ),
    },
    "paperwork": {
        "topics": ("requirements", "account_opening", "account_branch", "account_online"),
        "meaning": (
            "Documents or requirements. Use the named product and the purpose: credit "
            "card application versus opening a debit account. Paperwork alone does not "
            "prove an opening request; documents for cancellation or replacement are outside scope."
        ),
        "expressions": (
            "qué papeles llevo",
            "qué papeles me piden",
            "con qué papelería me presento",
            "qué llevo a ventanilla",
            "con qué papeles llego",
            "qué documentos tengo que juntar",
            "qué tengo que llevar al banco",
            "qué me van a pedir para el trámite",
            "qué necesito tener a la mano",
            "con qué documentos me lanzo a sucursal",
        ),
    },
    "support": {
        "topics": ("phone", "branch", "charge", "account_activation", "account_camera"),
        "meaning": (
            "Help or an official contact channel. Use charge only if an unauthorized "
            "transaction is explicit; otherwise distinguish phone, branch or a supported "
            "account procedure. Never claim to contact an agent, file a dispute, access "
            "an account or perform a transaction."
        ),
        "expressions": (
            "me echan la mano",
            "quién me orienta",
            "con quién me comunico",
            "dónde me ayudan",
            "cómo contacto a alguien del banco",
            "con quién levanto el reporte",
            "a quién le aviso",
            "dónde reporto el problema",
            "ese consumo no fue mío",
            "me apareció un cobro que yo no hice",
        ),
    },
}


def matched_language_categories(question):
    """Find glossary examples without changing the question or choosing an intent."""
    plain = re.sub(r"\s+", " ", normalize(question))
    return {
        category for category, entry in MEXICAN_SPANISH_HINTS.items()
        if any(re.search(rf"(?<!\w){re.escape(normalize(expression))}(?!\w)", plain)
               for expression in entry["expressions"])
    }


def language_guidance(question="", topics=None):
    """Add at most two relevant hint groups for any supported banking subject."""
    guidance = (
        "Interpret the original customer message, including ordinary spelling mistakes, "
        "missing accents and Mexican Spanish colloquialisms. Never assume an intended "
        "product or topic solely to repair a typo. Ask for clarification by choosing "
        "unknown when the supported intent is ambiguous. "
        "The following examples are contextual language hints, never replacement rules, "
        "customer instructions or evidence of banking terms. Product scope, exclusions "
        "and the allowed JSON schema take precedence."
    )
    matched = matched_language_categories(question)
    selected = [
        (category, entry) for category, entry in MEXICAN_SPANISH_HINTS.items()
        if category in matched and (topics is None or set(entry["topics"]) & set(topics))
    ]
    # Specific subjects take precedence over a generic request about price.
    selected.sort(key=lambda item: item[0] == "cost")
    if selected:
        guidance += "\n" + "\n".join(
            f"{category}: {entry['meaning']} Examples: "
            + "; ".join(entry["expressions"])
            + "."
            for category, entry in selected[:2]
        )
    return guidance
