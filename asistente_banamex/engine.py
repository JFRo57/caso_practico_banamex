"""Coordinate scope checks, retrieval, classification, and cited responses."""

import re

from . import ROOT
from .answers import AnswerBuilder, render_fact
from .colloquialisms import matched_language_categories
from .ollama import OllamaPlanner
from .retrieval import SEARCH_TERMS, Corpus
from .routing import (
    ACCOUNT_FACTS, ACCOUNT_HINT, ACCOUNT_SERVICE_FACTS, ACCOUNT_TERMS, FTS_PHRASES, PRODUCT_TOPICS, PRODUCTS, Plan,
    ambiguous_branch_request, branch_is_negated,
    account_channel, account_opening_plan, account_service_plan, language, lexical_plan, named_products,
    account_topic_matches_channel, normalize, policy, semantic_opening_allowed,
)
from .semantic import SemanticIndex, SemanticPolicy


class Engine:
    def __init__(self, path=None, model=None, embeddings=False, semantic_policy=None):
        if path is None:
            data_path = ROOT / "data" / "facts.json"
            path = data_path if data_path.is_file() else (ROOT / "corpus" / "facts.json")
        self.corpus = Corpus(path)
        self.facts = self.corpus.facts
        self.sources = self.corpus.sources
        self.snapshot = self.corpus.snapshot
        self.answers = AnswerBuilder(self.corpus)
        self.model = OllamaPlanner(model) if model else None
        self.semantic = SemanticIndex() if embeddings else None
        self.semantic_policy = semantic_policy if semantic_policy is not None else SemanticPolicy()

    def index_embeddings(self):
        profiles = {}
        for topic, fact_ids in ACCOUNT_FACTS.items():
            facts = [self.facts[fact_id] for fact_id in fact_ids if fact_id in self.facts]
            excerpts = [
                f"{fact['section']}. {render_fact(fact, 'es')}"
                for fact in facts if self.corpus.is_usable(fact)
            ]
            if len(excerpts) == len(fact_ids):
                context = SEARCH_TERMS.get(topic, "Requisitos y documentos para abrir una cuenta de débito Banamex")
                profiles[topic] = "\n".join([context, *excerpts])
        return self.semantic.build(profiles)

    def answer(self, question, followup=None, response_language=None):
        question = question.strip()[:750]
        plain = normalize(question)
        lang = response_language if response_language in ("es", "en") else language(plain)
        followup_topic = followup.get("topic") if isinstance(followup, dict) else None
        if followup_topic == "requirements" and re.fullmatch(
            r"(?:(?:una?|la|an?|the) )?(?:(?:debit |checking |bank )?account|cuenta(?: de debito)?|micuenta|switch|joy|clasica|(?:credit )?card|tarjeta(?: de credito)?)[.!? ]*", plain,
        ):
            plain += " requisitos"
            if response_language is None:
                lang = "en" if followup.get("language") == "en" else "es"

        # Check scope before retrieval and model calls.
        if reason := policy(plain):
            return self.answers.policy(reason, lang)
        if followup_topic in ("requirements", "card_application_channel", "branch_intent"):
            previous = followup.get("products")
            if (not named_products(plain) and not re.search(ACCOUNT_TERMS, plain)
                    and branch_is_negated(plain) and isinstance(previous, list)
                    and previous and all(isinstance(p, str) and p in PRODUCTS for p in previous)):
                plain += " " + " ".join(previous)
                if response_language is None:
                    lang = "en" if followup.get("language") == "en" else "es"
            if followup_topic == "card_application_channel" and re.fullmatch(r"(?:la |the )?(joy|clasica)[.!? ]*", plain):
                plain += " solicitar en linea"
        if followup_topic == "account_fee" and re.fullmatch(r"(?:mi\s?cuenta|switch)[.!? ]*", plain):
            plain += " fees"
            if response_language is None:
                lang = "en" if followup.get("language") == "en" else "es"
        service = account_service_plan(plain)
        if service and service.topic == "account_fee_product":
            return self.answers.clarify(lang, "local", "account_fee", followup="account_fee")
        if service:
            return self.answers.resolve(service, plain, lang, "local", self.corpus.search(plain))
        opening = account_opening_plan(plain)
        account_scope_unclear = not opening and bool(re.search(ACCOUNT_HINT, plain))
        if account_scope_unclear and not self.semantic and not self.model:
            return self.answers.policy("outside", lang)
        candidates = self.corpus.search(plain)
        if re.search(r"\b(todas las tarjetas|all (?:the )?(?:banamex )?cards)\b", plain):
            return self.answers.clarify(lang, "local", "topic", candidates)
        if re.fullmatch(r"(?:requirements?|documents?|requisitos?|documentos?)[.!? ]*", plain):
            return self.answers.clarify(lang, "local", "requirements", candidates, followup="requirements")
        plan = opening or (lexical_plan(plain) if not account_scope_unclear else None)
        route = "local"
        explicit = named_products(plain)
        branch_ambiguous = ambiguous_branch_request(plain)
        if not plan and not account_scope_unclear and isinstance(followup, dict) and len(explicit) == 1:
            topic = followup.get("topic")
            if isinstance(topic, str) and topic in PRODUCT_TOPICS and re.fullmatch(r"(?:la |the )?(joy|clasica)[.!? ]*", plain):
                plan = Plan(topic, explicit)
                if response_language is None:
                    lang = "en" if followup.get("language") == "en" else "es"
        if not plan and not account_scope_unclear:
            for fact_id in candidates:
                topic = self.facts[fact_id]["topic"]
                if any(re.search(rf"\b{re.escape(phrase)}\b", plain) for phrase in FTS_PHRASES.get(topic, ())):
                    plan = Plan(topic, explicit)
                    break

        # E5 may resolve a clear supported opening intent without invoking Ollama.
        semantic_result = None
        semantic_decision = None
        comparison_topics = None
        shortlist = ()
        classifier_attempted = False
        if not plan and self.semantic:
            service_language = matched_language_categories(question) & {
                "cost", "expensive", "affordable", "low_use", "income", "support",
            }
            if not explicit and semantic_opening_allowed(plain) and not service_language:
                lexical_topics = {self.facts[fact_id]["topic"] for fact_id in candidates}
                semantic_result = self.semantic.search(question, lexical_topics)
                shortlist = semantic_result.candidates
                if account_channel(plain) != "account_opening":
                    # The general profile contains both channels; it is not a rival
                    # when the customer has already specified a channel/product.
                    comparison_topics = {"account_branch", "account_online"}
                topic = semantic_result.direct_topic(self.semantic_policy, comparison_topics)
                if topic in ACCOUNT_FACTS and account_topic_matches_channel(topic, plain):
                    plan = Plan(topic)
                    route = "semantic"
                    semantic_decision = "direct"
                else:
                    semantic_decision = "uncertain" if not semantic_result.error else "unavailable"
                    if topic is not None:
                        semantic_decision = "channel_conflict"
                        # Do not hide the explicitly requested channel from the classifier.
                        shortlist = ()

        # The classifier is optional and only sees questions left unresolved.
        if not plan and self.model:
            classifier_attempted = True
            plan, route = self.model.plan(question, shortlist=shortlist)
            if shortlist and route == "ollama":
                route = "semantic_ollama"
            if semantic_result is not None:
                semantic_decision = "escalated_" + semantic_decision
            account_topics = set(ACCOUNT_FACTS) | set(ACCOUNT_SERVICE_FACTS) | {"account_fee_product"}
            if plan and explicit and plan.topic in account_topics:
                plan = None
            if plan and account_scope_unclear and plan.topic in PRODUCT_TOPICS | {"compare", "low_use", "requirements"}:
                plan = None
            if plan and explicit and plan.products and plan.products != explicit:
                plan = None
            if plan and explicit and not plan.products:
                plan = Plan(plan.topic, explicit, plan.operation)
            if plan and plan.topic == "branch" and branch_ambiguous:
                plan = None
            if plan and plan.topic in ACCOUNT_FACTS:
                channel = account_channel(plain)
                if plan.products:
                    plan = None
                elif channel != "account_opening":
                    plan = Plan(channel) if not shortlist or channel in shortlist else None

        if not plan and semantic_result is not None and not self.model:
            result = self.answers.clarify(
                lang, "semantic" if not semantic_result.error else "fallback",
                "account_opening", candidates, followup="requirements",
            )
            result["semantic"] = semantic_result.describe(self.semantic_policy, semantic_decision, comparison_topics)
            return result
        if not plan:
            if branch_ambiguous:
                result = self.answers.clarify(lang, route, "branch_intent", candidates, followup="branch_intent")
                result["followup"]["products"] = list(explicit)
            elif account_scope_unclear:
                result = self.answers.abstain("outside", route, lang, candidates)
            elif explicit or re.search(r"\b(tarjetas?|cards?)\b", plain):
                result = self.answers.clarify(lang, route, "topic", candidates)
            else:
                result = self.answers.abstain("unknown", route, lang, candidates)
        elif plan.topic == "account_fee_product":
            result = self.answers.clarify(lang, route, "account_fee", candidates, followup="account_fee")
        else:
            result = self.answers.resolve(plan, plain, lang, route, candidates)
        if semantic_result is not None:
            result["semantic"] = semantic_result.describe(self.semantic_policy, semantic_decision, comparison_topics)
        result["classifier_attempted"] = classifier_attempted
        return result
