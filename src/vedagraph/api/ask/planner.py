"""Keyword/pattern-based query planner. No LLM required for planning.

The planner is deterministic: the same question always produces the same query plan,
making behavior predictable and testable without network access.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Final

from vedagraph.api.ask.models import AskMode, QueryIntent

#: Passage key pattern: ``RV 1.1.1``, ``AV 2.3.4``, ``VSM 1.1``, and the Samaveda's
#: section-named citations ``SV ARANYA 1.1`` and ``SV UTTARA 9.2.10.1``.
#:
#: The section token is not decoration, and omitting it was not a cosmetic gap. Every
#: Samavedic citation this graph emits carries one -- the Kauthuma arcika is held as
#: ARANYA, UTTARA, CHANDA and MAHANAMNYA -- so a pattern expecting digits immediately
#: after the Veda code matched *none* of the 1,844 Samavedic mantras. Passage lookup then
#: never ran, the packet came back empty, and synthesis was asked about a verse that is
#: present in the corpus while holding no evidence that it exists. Observed live: "What
#: does SV ARANYA 1.1 contain?" was answered "VedaGraph does not contain any Aranyaka
#: texts" -- about a passage this graph stores.
#:
#: A fourth numeric group is allowed for the same reason: Uttararcika loci are four deep.
#: Two numeric parts remain the minimum, so a bare "RV 10" is still not read as a locus.
_PASSAGE_KEY_RE: Final = re.compile(
    r"\b(RV|AV|AVS|SV|YV|VS|VSM)\s*"
    r"(?:(ARANYA|UTTARA|CHANDA|MAHANAMNYA)\s+)?"
    r"[\.\s_-]?\s*(\d+)[\.\s_-](\d+)(?:[\.\s_-](\d+))?(?:[\.\s_-](\d+))?\b",
    re.IGNORECASE,
)

# Major Vedic entities — used for entity detection
_KNOWN_DEITIES: Final[frozenset[str]] = frozenset(
    {
        "indra",
        "agni",
        "soma",
        "varuna",
        "mitra",
        "vishnu",
        "rudra",
        "surya",
        "savitr",
        "savitri",
        "usha",
        "ushas",
        "dawn",
        "dyaus",
        "prithvi",
        "vayu",
        "marut",
        "maruts",
        "parjanya",
        "pushan",
        "tvastr",
        "brihaspati",
        "brahmanaspati",
        "yama",
        "nirrti",
        "ila",
        "sarasvati",
        "vac",
        "apas",
        "apo",
        "ap",
        "apah",
        "rta",
        "rita",
        "aditi",
        "adityas",
        "vasus",
        "rbhu",
        "vibhu",
        "vaja",
        "rbhus",
        "aryaman",
        "bhaga",
        "daksha",
        "amsha",
        "indrani",
        "agnayi",
        "rohita",
        "vishvakarma",
        "prajapati",
        "hiranyagarbha",
        "narashamsa",
        "purusha",
    }
)

_KNOWN_RISHIS: Final[frozenset[str]] = frozenset(
    {
        "vishvamitra",
        "vamadeva",
        "atri",
        "bharadvaja",
        "gautama",
        "jamadagni",
        "vasishtha",
        "kanva",
        "gritsamada",
        "angiras",
        "nodhas",
        "kakshivat",
        "shaunaka",
        "dirghatamas",
    }
)

# Cross-veda comparison keywords
_CROSS_VEDA_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(across|compare|comparison|differ|different|all four|each veda"
        r"|all vedas|cross-veda|crossveda|between.*veda|veda.*veda)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(rigveda|samaveda|yajurveda|atharvaveda)\b"
        r".*\b(rigveda|samaveda|yajurveda|atharvaveda)\b",
        re.IGNORECASE,
    ),
]

# Graph/connection keywords
_GRAPH_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(connect|connection|relationship|related|link|path|between|how.*and)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(explain.*connect|why.*connect|how.*connect)\b", re.IGNORECASE),
]

# Formula/reuse keywords
_FORMULA_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(formula|phrase|recurring|recurrence|reuse|reused|parallel|spread"
        r"|appear.*else|occur.*else)\b",
        re.IGNORECASE,
    ),
]

# Interpretive/scholarly keywords
_INTERPRETIVE_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(interpret|scholar|scholarly|debate|disagree|opinion|mean|signif|symbol|represent)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(is.*really|actually|historically|tradition)\b", re.IGNORECASE),
]

# Statistics keywords
_STATS_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(how many|count|total|number|most|least|frequent|statistics|distribution)\b",
        re.IGNORECASE,
    ),
]

# Ritual keywords
_RITUAL_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(ritual|rite|ceremony|sacrifice|yajna|yajña|offering|oblation|soma press|pressing)\b",
        re.IGNORECASE,
    ),
]

# Condition/disease keywords (AV)
_CONDITION_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(disease|fever|illness|sickness|takman|healing|cure|affliction"
        r"|demon|rakshas|rakshasa)\b",
        re.IGNORECASE,
    ),
]


#: Questions asking whether a word *occurs*, as opposed to what it means. These are the
#: questions whose wrong answer is the dangerous one: asked "does the Yajurveda mention
#: ayas", a system that finds no row and says "no" has asserted textual absence from a
#: retrieval artefact. Matching here routes to the lexical-presence channel, which reports
#: the searchable surface alongside the hit count and so can tell the two apart.
_LEXICAL_PRESENCE_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(mention|mentions|mentioned|occur|occurs|occurrence|contain|contains|"
        r"appear|appears|attested|found in|present in|use|uses|does .* have)\b",
        re.IGNORECASE,
    ),
]

#: A quoted or italicised Sanskrit term, or a lone lowercase non-English-looking token.
#: Used only to pick the term a presence question is *about*.
# The quote characters ARE the point -- a researcher pasting a term from a PDF brings
# curly quotes with it, so the RUF001 suppressions below are deliberate. The character
# class also spans U+0080-U+024F, whose first character is invisible in an editor.
_QUOTED_TERM: Final = re.compile(
    "['\"‘’“”]"  # noqa: RUF001
    "([A-Za-z-ɏ]{2,30})"
    "['\"‘’“”]"  # noqa: RUF001
)


@dataclass
class QueryPlan:
    intents: list[QueryIntent] = field(default_factory=list)
    entities_mentioned: list[str] = field(default_factory=list)
    veda_scope: str = "ALL"
    retrieval_channels: list[str] = field(default_factory=list)
    search_term: str = ""
    passage_key: str | None = None
    lexical_terms: list[str] = field(default_factory=list)
    """Terms whose *presence* the question asks about. Drives the lexical channel."""
    is_adversarial: bool = False
    planning_ms: float = 0.0


_VEDA_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "RV": re.compile(r"\b(rigveda|rig veda|rv\b|r\.v\.|ṛgveda)\b", re.IGNORECASE),
    "SV": re.compile(r"\b(samaveda|sama veda|sv\b|s\.v\.)\b", re.IGNORECASE),
    "YV": re.compile(r"\b(yajurveda|yajur veda|yv\b|y\.v\.|yajur)\b", re.IGNORECASE),
    "AV": re.compile(r"\b(atharvaveda|atharva veda|av\b|a\.v\.|atharva)\b", re.IGNORECASE),
}


def _detect_veda_scope(question: str, explicit_veda: str | None) -> str:
    if explicit_veda and explicit_veda != "ALL":
        return explicit_veda
    vedas_mentioned = [veda for veda, pat in _VEDA_PATTERNS.items() if pat.search(question)]
    if len(vedas_mentioned) == 1:
        return vedas_mentioned[0]
    return "ALL"


#: Words that are never entity names, whatever their capitalisation. Includes the corpus
#: names themselves: "Rigveda" resolves the Veda scope, not an entity, and offering it to
#: the resolver spends a graph round trip to match nothing.
_ENTITY_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "how",
        "what",
        "where",
        "which",
        "who",
        "whom",
        "whose",
        "why",
        "when",
        "does",
        "do",
        "did",
        "is",
        "are",
        "was",
        "were",
        "can",
        "could",
        "should",
        "show",
        "give",
        "tell",
        "list",
        "find",
        "explain",
        "describe",
        "compare",
        "the",
        "this",
        "that",
        "these",
        "those",
        "and",
        "or",
        "but",
        "about",
        "veda",
        "vedas",
        "vedic",
        "sanskrit",
        "mantra",
        "hymn",
        "verse",
        "passage",
        "rigveda",
        "samaveda",
        "yajurveda",
        "atharvaveda",
        "rig",
        "sama",
        "yajur",
        "atharva",
        "complete",
        "exact",
        "correct",
        "right",
        "scholars",
        "musical",
        "notation",
        "connected",
        "mentions",
        "mentioned",
        # Interrogative and discourse filler that survives the capitalisation test.
        "there",
        "here",
        "also",
        "more",
        "most",
        "many",
        "some",
        "any",
        "all",
        "with",
        "from",
        "into",
        "over",
        "under",
        "between",
        "across",
        "within",
        "say",
        "says",
        "said",
        "appear",
        "appears",
        "occur",
        "occurs",
        "contain",
        "contains",
        "differ",
        "differs",
        "different",
        "difference",
        "associated",
        "used",
        "use",
        "uses",
        "using",
        "really",
        "actually",
        "definitely",
        "elsewhere",
        "four",
        "three",
        "two",
        "one",
        "first",
        "last",
        "next",
        "text",
        "texts",
        "word",
        "words",
        "term",
        "terms",
        "name",
        "names",
    }
)

#: Candidate entity words in the question. Deliberately broad -- the registry decides.
#:
#: Restricting nomination to capitalised words and a hardcoded deity list was a real
#: retrieval gap: asked "What does the Atharvaveda say about fever?", the planner
#: nominated *nothing*, because "fever" is lowercase and not a deity. The resolver can
#: reach ``VG:CONCEPT:TAKMAN-FEVER`` from the word "fever" perfectly well -- it was simply
#: never offered it -- so a question with a real answer returned an empty packet.
#:
#: The registry is the right filter, not a word list here: a nominated word that names
#: nothing resolves to nothing and costs only its share of one batched query. So this
#: nominates every content word and lets :func:`~vedagraph.api.ask.resolver.resolve_entities`
#: reject what the graph does not know.
_CANDIDATE_WORD: Final = re.compile(r"\b[A-Za-zāīūṛṝḷḹṅñṇṃṁṭḍḥśṣēō]{3,24}\b")


def _detect_entities(question: str) -> tuple[list[str], int]:
    """Candidate entity names strongest-first, and how many of them are *strong*.

    Two return values because nomination and classification want different thresholds.
    Resolution should see every content word -- that is what fixed "fever" reaching the
    takman concept. Intent classification should not: a question whose only candidate is
    an incidental lowercase noun ("tell me something about the corpus") is not an entity
    question, and labelling it ``ENTITY_PROFILE`` because "corpus" got nominated would
    report an intent the question does not visibly have.

    Strong nominations are known deities and seers, and capitalised words. They lead the
    list, so the count is a prefix length. Ordering matters downstream too: the retriever
    profiles only the first few resolved entities, so a named deity must come before an
    incidental noun.

    Word-boundary matched, never substring. Substring matching is the trap here: the
    deity *Ap* (the waters) is a substring of "appear", so ``"ap" in question.lower()``
    nominates a deity for any question containing the word, and the packet then carries a
    deity the question never mentioned.
    """
    known_hits: list[str] = []
    for known in sorted((*_KNOWN_DEITIES, *_KNOWN_RISHIS), key=len, reverse=True):
        if re.search(rf"\b{re.escape(known)}\b", question, re.IGNORECASE):
            known_hits.append(known.capitalize())

    # Capitalised words: entity names the hardcoded list does not carry. Diacritics are
    # in the class because IAST spellings (Varuṇa, Ṛta) are how a researcher types them.
    capitalised = [
        word
        for word in re.findall(r"\b[A-ZĀĪŪṚṬḌṆŚṢ][a-zāīūṛṭḍṇśṣṃḥ]+\b", question)
        if word.lower() not in _ENTITY_STOPWORDS
    ]

    # Every other content word, for the registry to accept or reject.
    other = [
        word
        for word in _CANDIDATE_WORD.findall(question)
        if word.lower() not in _ENTITY_STOPWORDS and not word[0].isupper()
    ]

    def dedupe(words: list[str], seen: set[str]) -> list[str]:
        out: list[str] = []
        for word in words:
            key = word.lower()
            if key in seen or key in _ENTITY_STOPWORDS:
                continue
            seen.add(key)
            out.append(word)
        return out

    seen: set[str] = set()
    strong = dedupe([*known_hits, *capitalised], seen)
    speculative = dedupe(other, seen)
    return [*strong, *speculative], len(strong)


def _detect_passage_key(question: str) -> str | None:
    m = _PASSAGE_KEY_RE.search(question)
    if not m:
        return None
    veda_prefix = m.group(1).upper()
    section = m.group(2)
    parts = [g for g in m.groups()[2:] if g is not None]
    locus = ".".join(parts)
    # The graph cites a sectioned locus as "SV ARANYA 1.1" and the lookup matches
    # canonical_citation, so the section travels inside the key rather than being dropped.
    if section:
        return f"{veda_prefix} {section.upper()} {locus}"
    return f"{veda_prefix} {locus}"


def _detect_lexical_terms(question: str, entities: list[str]) -> list[str]:
    """The terms a presence question is asking about, most likely first.

    Only populated when the question asks whether something *occurs* -- see
    :data:`_LEXICAL_PRESENCE_PATTERNS`. A quoted term wins, then a nominated entity name,
    then any lowercase token that is not an English function word. The point is to give
    the lexical channel something to count, so that "does the Yajurveda mention ayas"
    produces a measured surface report rather than an unexamined empty result.

    **Order is the whole contract here**, because the retriever searches
    ``lexical_terms[0]``. Asked "Does Yajurveda mention ayas?" this once returned
    ``["mention", "ayas"]`` -- the interrogative verb first -- so the corpus was scanned
    for the English word *mention* and the answer reported its surface figures while
    saying nothing measured about *ayas*. The term is the subject of the question, never
    the verb that frames it, so every candidate passes the function-word filter regardless
    of which source nominated it.
    """
    if not any(pat.search(question) for pat in _LEXICAL_PRESENCE_PATTERNS):
        return []

    candidates: list[str] = [m.group(1) for m in _QUOTED_TERM.finditer(question)]
    candidates.extend(entities)
    # Lowercase non-English tokens: a transliterated Sanskrit word a researcher typed
    # without quotes or capitals, which is how `ayas` and `takman` actually arrive.
    candidates.extend(re.findall(r"\b[a-zāīūṛṭḍṇśṣṃḥ]{3,20}\b", question))

    terms: list[str] = []
    for candidate in candidates:
        folded = candidate.lower()
        if folded in _LEXICAL_FUNCTION_WORDS or folded in _ENTITY_STOPWORDS:
            continue
        if candidate not in terms:
            terms.append(candidate)

    return terms[:3]


#: English words that will never be the subject of a presence question. Separate from
#: :data:`_ENTITY_STOPWORDS` because that set is about entity *naming* and this one is
#: about what a lexical search should not waste a corpus scan on.
_LEXICAL_FUNCTION_WORDS: Final[frozenset[str]] = frozenset(
    {
        "does",
        "did",
        "the",
        "and",
        "but",
        "not",
        "any",
        "all",
        "how",
        "who",
        "what",
        "which",
        "where",
        "when",
        "why",
        "are",
        "was",
        "were",
        "has",
        "have",
        "had",
        "mention",
        "mentions",
        "mentioned",
        "occur",
        "occurs",
        "occurrence",
        "contain",
        "contains",
        "appear",
        "appears",
        "attested",
        "present",
        "use",
        "uses",
        "used",
        "say",
        "says",
        "about",
        "there",
        "this",
        "that",
        "these",
        "those",
        "right",
        "correct",
        "really",
        "actually",
        "some",
        "many",
        "most",
        "more",
        "also",
        "show",
        "give",
        "tell",
        "list",
        "find",
        "complete",
        "exact",
        "veda",
        "vedas",
        "vedic",
        "sanskrit",
        "text",
        "texts",
        "word",
        "words",
        "term",
        "terms",
        "hymn",
        "hymns",
        "verse",
        "verses",
        "mantra",
        "mantras",
        "passage",
        "passages",
    }
)


def plan(
    question: str, *, explicit_veda: str | None = None, mode: AskMode = AskMode.AUTO
) -> QueryPlan:
    """Classify question intent and select retrieval channels."""
    start = time.monotonic()
    intents: list[QueryIntent] = []
    channels: list[str] = []

    passage_key = _detect_passage_key(question)
    entities, strong_count = _detect_entities(question)
    veda_scope = _detect_veda_scope(question, explicit_veda)

    if passage_key:
        intents.append(QueryIntent.PASSAGE_LOOKUP)
        channels.append("passages")

    if any(pat.search(question) for pat in _CROSS_VEDA_PATTERNS):
        intents.append(QueryIntent.CROSS_VEDA)
        channels.append("cross_veda")

    if any(pat.search(question) for pat in _GRAPH_PATTERNS) and strong_count >= 2:
        intents.append(QueryIntent.GRAPH_CONNECTION)
        channels.append("graph_paths")

    if any(pat.search(question) for pat in _FORMULA_PATTERNS):
        intents.append(QueryIntent.FORMULA)
        intents.append(QueryIntent.TEXTUAL_REUSE)
        channels.append("formulas")

    if any(pat.search(question) for pat in _RITUAL_PATTERNS):
        intents.append(QueryIntent.RITUAL)
        channels.append("rituals")

    if any(pat.search(question) for pat in _CONDITION_PATTERNS):
        intents.append(QueryIntent.HUMAN_CONCERN)
        channels.append("conditions")

    if any(pat.search(question) for pat in _INTERPRETIVE_PATTERNS):
        intents.append(QueryIntent.INTERPRETIVE_CLAIM)
        channels.append("interpretive_claims")

    if any(pat.search(question) for pat in _STATS_PATTERNS):
        intents.append(QueryIntent.STATISTICS)
        channels.append("statistics")

    # Intent fires on a *strong* nomination only -- see _detect_entities. The entity
    # channel is still added whenever anything was nominated, because resolution is
    # what decides whether a lowercase noun like "fever" names a real concept.
    if entities:
        channels.append("entities")
    if strong_count and QueryIntent.ENTITY_PROFILE not in intents:
        intents.append(QueryIntent.ENTITY_PROFILE)

    # A question about whether a word occurs routes to the one channel that reports the
    # searchable surface as well as the hit count. Without it, "does the Yajurveda
    # mention ayas" is answered from an absent row.
    lexical_terms = _detect_lexical_terms(question, entities)
    if lexical_terms:
        channels.append("lexical")

    # Always include general search as a fallback channel
    channels.append("search")

    if not intents:
        intents.append(QueryIntent.GENERAL_VEDIC_QUERY)

    # Deduplicate preserving order
    intents = list(dict.fromkeys(intents))
    channels = list(dict.fromkeys(channels))

    # Build a safe search term (no Cypher, no Lucene metacharacters)
    search_term = re.sub(r"[\"'\\{}()\[\]~*?:^]", " ", question)
    search_term = " ".join(search_term.split())[:200]

    return QueryPlan(
        intents=intents,
        entities_mentioned=entities,
        veda_scope=veda_scope,
        retrieval_channels=channels,
        search_term=search_term,
        passage_key=passage_key,
        lexical_terms=lexical_terms,
        planning_ms=(time.monotonic() - start) * 1000,
    )
