""" "This passage names this god" -- across four Vedas, and never on the same evidence.

This is the layer the V2 pass named as its single highest-value backlog item and
deliberately did not attempt, on the grounds that doing it badly would be worse than not
doing it. The reason it is dangerous is worth stating before the design, because the
design is entirely a response to it.

**Why V2 refused it.** V2 built its deity-ambiguity flag from ``Devata.label_iast`` -- the
uninflected stem ``agni`` -- while the aliases it was testing were inflected. So the flag
never fired on the **vocative**, which is the one form that certainly addresses a god
rather than naming a thing. 915 edges then asserted a domain entity whose own description
reads "*NOT* the deity Agni" on the sole evidence of ``agne``, "O Agni!", and 0 of 915 were
flagged. V2's own automated screen scored that alias at 97.5% correct, because the gloss
list contained "agni" and the translator prints "Agni"; only the morphology exposed it.

**So this layer is built on morphology, not on strings, wherever morphology exists.**

Two paths, and the whole point is that they are not interchangeable:

*The Rigvedic path.* ``data/knowledge/rigveda_lexical_v1/tokens.jsonl`` carries the
University of Zurich manual morphosyntactic annotation of every Rigvedic token. A Rigvedic
theonym mention is therefore not a match at all -- a scholarly source states that this
token's lemma is ``indra-`` and that its case is vocative. There is no string search on
this path, no sandhi guessing and no host-intrusion risk, and the case feature makes the
deity-versus-common-noun question answerable for the one form where it has an answer.

*The Samavedic, Yajurvedic and Atharvavedic path.* Those three corpora have no annotation,
so the only available claim is a surface match against forms attested in the Rigveda plus
forms the adjudicators read and accepted. That is a weaker claim and it is graded as one.
Presenting the two paths as one number would let the Rigveda's precision stand in for the
corpus's, which is the most tempting dishonesty available here.

**Three things are recorded rather than resolved.** Vedic Sanskrit has one word for the
god Agni and for fire, and no amount of care invents a second. So the layer records
``referent_certainty`` per edge -- certain when the form is a vocative or the name is not
also a common noun, ambiguous otherwise -- and lets the query decide. It records
``attribution_support``, whether the Anukramani independently ascribes this passage to this
deity, as a *filterable signal* and never as a promotion. And it refuses a whole class of
Anukramani devata labels outright: ``VG:DEVATA:RATHAH`` is the deified chariot and
``ratha`` is "a chariot", so lemma identity there would assert a deity on several hundred
passages about vehicles. Those refusals live in the registry with the count each avoided.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Final

import yaml

from vedagraph.domain.ontology import DOMAIN_MODEL_VERSION, QualityTier
from vedagraph.enrich.concepts import MIN_SANDHI_ALIAS_CHARS, fold_alias
from vedagraph.enrich.corpus import Corpus, MantraRecord
from vedagraph.enrich.morphology import (
    ANNOTATION_METHOD,
    ANNOTATION_SOURCE_ID,
    AnnotatedToken,
    Annotation,
)
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    RunReport,
    TrustClass,
    run_id,
    stable_id,
)
from vedagraph.enrich.surfaces import render_for_display

REGISTRY_PATH: Final = pathlib.Path("data") / "registry" / "theonym_forms.yaml"

_STAGE: Final = "theonym-mentions"
_METHOD_ROOT: Final = "theonym-mention-v1"

#: The Rigvedic path. Not a match: a manual scholarly annotation states the lemma.
PATH_ANNOTATION: Final = "rv-lemma-annotation"
#: Whole-token surface match on the folded surface. The only path available outside the
#: Rigveda, and the stronger of the two that are.
PATH_TOKEN: Final = "sanskrit-surface-token"
#: Substring match on the boundary-free surface. Samaveda only, because that is the only
#: corpus here that prints continuous sandhi -- ``tvamindra`` is one printed token and
#: genuinely means "you, O Indra". Materially weaker: a hit may span two words.
PATH_SANDHI: Final = "sanskrit-surface-sandhi"

#: Vedas whose editions print continuous sandhi, so a substring pass recovers real
#: mentions rather than inventing them. **The default for a form that does not say**, not
#: a global gate -- see :func:`_sandhi_hits`.
#:
#: The Samaveda is the obvious case and the Yajurveda is the surprising one. This
#: repository's own surface table describes the Yajurveda as "spaced, some ASCII stand-ins",
#: and it is not: its Devanagari attaches a consonant-final word to whatever follows, so
#: **27.3% of Yajurvedic mantras contain a token of 20 or more characters** against 0.2%
#: of Rigvedic ones, its longest token is 62 characters against the Rigveda's 24, and
#: ``aditir dyaur aditir antarikṣam aditir mātā`` prints as one 37-character token
#: carrying three nominatives of Aditi. A Samaveda-only substring pass loses all of that.
SANDHI_VEDAS: Final[frozenset[str]] = frozenset({"SV", "YV"})

#: Scores are comparable within a path and meaningless across paths -- see
#: :class:`~vedagraph.enrich.provenance.Provenance`.
_SCORE_ANNOTATION: Final = 0.99
_SCORE_TOKEN: Final = 0.90
_SCORE_SANDHI: Final = 0.60

#: Form decisions the adjudicators may return that admit a form to a path.
#:
#: ``ACCEPTED_SANDHI_SV`` admits a form to **both** paths, and its absence from the token
#: set was a measured recall defect. The reasoning is an entailment, not a preference: a
#: form decided ``ACCEPTED_SANDHI_SV`` was adjudicated safe to match as a *substring*, in
#: the one corpus whose edition does not divide words reliably -- which is the riskiest
#: match this module makes, because a substring can land inside an unrelated word. A form
#: safe under that licence is necessarily safe as an *exact whole token*, where the word
#: boundary rules out host intrusion entirely. Admitting the weaker match while refusing
#: the stronger one has it backwards.
#:
#: The cost was mechanically measured over the whole corpus against a gold set: **877
#: (passage, deity) pairs were missing**, because 82 forms could reach the graph only
#: through the Samaveda-licensed substring pass and could not match even a perfect whole
#: token in the Atharvaveda or Yajurveda. Atharvavedic Indra alone lost 313 passages
#: against the 322 it had -- a 14.7% under-count of the entire non-Rigvedic layer from
#: this one condition, which would silently understate every cross-Veda deity comparison.
#:
#: The sandhi path stays Samaveda-only. That restriction is about *where a substring match
#: is defensible*, and nothing here relaxes it.
_ADMITS_TOKEN: Final[frozenset[str]] = frozenset(
    {"ACCEPTED_TOKEN", "ACCEPTED_TOKEN_AMBIGUOUS", "ACCEPTED_SANDHI_SV"}
)
_ADMITS_SANDHI: Final[frozenset[str]] = frozenset({"ACCEPTED_SANDHI_SV"})

#: Deity-level verdicts that put a deity into the layer at all.
_ACCEPTING_VERDICTS: Final[frozenset[str]] = frozenset(
    {"ACCEPTED", "ACCEPTED_WITH_AMBIGUITY", "ACCEPTED_VOCATIVE_ONLY"}
)

#: The morphological role of an address. The single most important value in this module:
#: a vocative is an address to the named being, so it settles the deity reading even for a
#: name that is also an ordinary noun.
ROLE_VOCATIVE: Final = "VOCATIVE"

#: Referent certainty, recorded per edge. Three tiers, ordered by the *kind* of evidence
#: behind them rather than by any measured rate -- see :func:`refine_referent_certainty`.
CERTAIN: Final = "DEITY_CERTAIN"
PROBABLE: Final = "DEITY_PROBABLE"
AMBIGUOUS: Final = "DEITY_AMBIGUOUS"

#: Certainty tiers in descending strength. The order is the contract: a consumer that
#: wants "at least PROBABLE" slices this tuple rather than hard-coding two strings and
#: silently missing a tier added later.
REFERENT_TIERS: Final[tuple[str, ...]] = (CERTAIN, PROBABLE, AMBIGUOUS)

#: **The product default for deity analytics.** Measured against
#: ``data/gold/theonym_mention_gold_v1.jsonl``: CERTAIN 0.9712 (135/139) and PROBABLE
#: 0.9818 (54/55) give 0.9742 (189/194) together, against 0.6142 (121/197) for what is
#: left in AMBIGUOUS and 0.7928 for the unfiltered layer. Excluding AMBIGUOUS is therefore
#: not a nicety: on the gold sample every asserted mention of ``VG:DEVATA:VAK`` is the
#: common noun "speech", and this filter is the only thing between that deity and a
#: confidently wrong answer.
DEFAULT_REFERENT_TIERS: Final[frozenset[str]] = frozenset({CERTAIN, PROBABLE})

#: Exploratory mode, which a caller must ask for by name. It buys recall over a bucket
#: measured at 0.6142 precision, so it is for candidate generation and never for an
#: answer presented as fact.
EXPLORATORY_REFERENT_TIERS: Final[frozenset[str]] = frozenset(REFERENT_TIERS)

#: The one tier a strict caller should use when a single wrong row costs more than a
#: missing one.
STRICT_REFERENT_TIERS: Final[frozenset[str]] = frozenset({CERTAIN})

#: Morphological roles that presuppose a *person*, and are therefore the promotion
#: evidence for :data:`PROBABLE`. A vocative is an address and one addresses a being, not
#: a substance; a dative theonym in this corpus is the beneficiary of an offering, and a
#: substance is not a beneficiary. Both spellings of each role are listed because the two
#: paths label roles differently -- the Rigvedic path carries the annotation's case
#: abbreviations, the surface paths carry the registry's own words.
_ADDRESS_ROLES: Final[frozenset[str]] = frozenset({ROLE_VOCATIVE, "VOC"})
_DEDICATION_ROLES: Final[frozenset[str]] = frozenset({"DATIVE", "DAT"})

#: Roles that *veto* promotion however strong the other evidence, because the theonym sits
#: inside a compound and a compound need not denote its members: soma-prsthaya ... agnaye
#: at VSM 20.78 is an offering to *Agni* "soma-backed", and apsusadam ... vyomasadam at
#: VSM 9.2 is "water-seated", not the Waters. The gold set measures the edges this vetoes
#: at 0.5789 (11/19), which is AMBIGUOUS territory, and only 6 live edges are actually
#: held back by it -- a cheap guard against a named error class.
_COMPOUND_ROLES: Final[frozenset[str]] = frozenset({"COMPOUND_INITIAL", "COMPOUND_FINAL"})

#: Bases recorded in ``referent_basis`` so a reader can see *which* rule moved an edge and
#: audit that rule on its own rather than the bucket as a whole. This project has been
#: embarrassed by an audit that sampled rows and reported 97%+ while one alias was 82.9%
#: wrong, so the per-rule and per-alias breakdown is a stored property, not a report.
BASIS_CERTAIN: Final = "certain"
BASIS_ANUKRAMANI: Final = "R1_anukramani_corroboration"
BASIS_ADDRESS: Final = "R2_address_morphology"
BASIS_DEDICATION: Final = "R3_dedication_morphology"
BASIS_COMPOUND_HOLD: Final = "compound_internal_hold"
BASIS_IDENTITY_ONLY: Final = "identity_only"

#: Deity-level ambiguity classes that make a non-vocative occurrence undecided.
_HOMONYM_CLASSES: Final[frozenset[str]] = frozenset(
    {"COMMON_NOUN_HOMONYM", "GEOGRAPHIC_HOMONYM", "DIFFERENT_LEMMA_HOMONYM"}
)


class TheonymRegistryError(ValueError):
    """The theonym registry is unusable. Raised rather than degraded."""


def refine_referent_certainty(
    certainty: str,
    roles: Iterable[str],
    attribution_support: bool,
) -> tuple[str, str]:
    """Split the two-way certainty into three tiers, and record which rule did it.

    **The defect this fixes.** :func:`_grade` produces two values, and 8,825 of 17,165
    edges -- 51.4% of the deity mention layer -- landed in ``DEITY_AMBIGUOUS``. That is a
    bucket a product cannot use: including it costs precision (measured 0.6142 against the
    gold set) and excluding it discards half the layer, so default deity analytics had to
    choose between a known-wrong answer and half an answer. Splitting it is worth more
    than any improvement to detection, because detection is already measured at 0.9949 on
    *which word*; what fails is *which sense*.

    **What promotion may rest on, and what it may not.** Everything here is consumption
    semantics over evidence already on the edge. Nothing re-derives the mention layer and
    nothing consults a new source. A row is promoted only on an **independent positive
    indication that the personal referent is meant** -- never on lemma or string identity,
    which is exactly the evidence that produced the ambiguity in the first place. Three
    such indications exist on these edges:

    ``R1`` The Anukramani independently ascribes this passage to this deity
        (``attribution_support``). Two sources agreeing about one passage is the strongest
        thing available short of observed morphology. This module refuses to let it promote
        a row to ``CERTAIN`` -- an ascription is about the passage, not about the word --
        and ``PROBABLE`` is what it is for. Measured 1.0000 (8/8).
    ``R2`` The matched form is a vocative. Refused as ``CERTAIN`` outside the Rigveda for a
        reason that still stands: for a thematic a-stem the vocative singular and the
        sandhi-reduced nominative singular are the same Samhita string, and the
        pre-consonantal share runs from effectively 100% for ``agne`` down to 47% for
        ``surya``. The address reading is therefore *available* and not *observed*, which
        is the definition of this tier. Measured 0.9737 (37/38), and the cost of the
        residual is visible and named: the only false positive in the whole ``PROBABLE``
        gold slice is ``TMG-0427``, ``surya ivopadrk`` "like the sun in appearance", where
        the recorded ``VOCATIVE`` is a reduced nominative -- the exact failure this
        docstring predicts, on the exact form it predicts it on.
    ``R3`` The matched form is a dative, the recipient of an offering. Measured 1.0000
        (9/9).

    **Signals considered and refused**, with the measurement that refused them, because a
    reader should see what was rejected and not only what was kept. ``NOMINATIVE`` 0.8571
    (24/28) and ``SANDHI_FUSED`` 0.8000 (20/25) are respectable but are not indications of
    *personhood* -- a nominative Soma is exactly the "the soma flows" case -- and admitting
    them would pull the tier below the 0.95 that makes a default worth having.
    ``extraction_path = 'rv-lemma-annotation'`` was expected to be the strongest signal
    here and **measures 0.5745 (27/47), the weakest of all of them**: the Rigvedic
    vocatives were already taken into ``CERTAIN`` by :func:`_grade`, so what is left on
    that path is pure oblique-case homonym residue. Promoting the annotated path as a class
    would have been the intuitive move, and the measurement says it is wrong.

    Returns the tier and the basis. ``CERTAIN`` passes through untouched: this function
    never demotes a row :func:`_grade` settled, because that would relitigate the
    morphology that settled it.
    """
    if certainty == CERTAIN:
        return CERTAIN, BASIS_CERTAIN
    role_set = set(roles)
    if role_set & _COMPOUND_ROLES:
        return AMBIGUOUS, BASIS_COMPOUND_HOLD
    if attribution_support:
        return PROBABLE, BASIS_ANUKRAMANI
    if role_set & _ADDRESS_ROLES:
        return PROBABLE, BASIS_ADDRESS
    if role_set & _DEDICATION_ROLES:
        return PROBABLE, BASIS_DEDICATION
    return AMBIGUOUS, BASIS_IDENTITY_ONLY


#: The three states a deity-presence answer may return. ``ATTESTED`` and ``NOT_IN_LAYER``
#: are ordinary; ``INSUFFICIENT_EVIDENCE`` is the one that had to be added, and
#: :func:`mention_verdict` explains why.
VERDICT_ATTESTED: Final = "ATTESTED"
VERDICT_INSUFFICIENT: Final = "INSUFFICIENT_EVIDENCE"
VERDICT_ABSENT: Final = "NOT_IN_LAYER"


def mention_verdict(certain: int, probable: int, ambiguous: int) -> str:
    """What a deity-presence answer is allowed to say, given the three tier counts.

    **The defect this closes is a zero that reads as an absence, and it is measured.**
    Before the three-way split, ``referent_certainty`` was in practice a function of
    *extraction path* rather than of context: :func:`_grade` returns ``CERTAIN`` outside the
    Rigveda only when the deity's name is not also a common noun, and only the Rigveda has
    the Zurich annotation that can settle a homonym. The consequence is exact and was
    verified per deity, not per aggregate: of the 2,440 non-Rigvedic ``DEITY_CERTAIN``
    edges, **zero** belong to Agni, Soma, Sūrya, Mitra, Savitṛ, Uṣas, Vāyu, Āpaḥ, Pṛthivī
    or Vāc; they belong entirely to the seventeen deities whose names are not common nouns
    (Indra 1,261, Bṛhaspati 197, Varuṇa 197, ...). So an analyst who applied the cautious
    filter got **a worse answer than one who applied none**: "Agni: Yajurveda 0" for a
    deity named on 276 Yajurvedic verses.

    The ``PROBABLE`` tier removes that for eight of those ten deities in all three
    unannotated corpora -- Agni SV 82 / YV 97 / AV 170, Soma 97 / 36 / 26, Sūrya 14 / 21 /
    51, Mitra 5 / 5 / 10, Savitṛ 1 / 14 / 13, Vāyu 7 / 15 / 10, Pṛthivī 0 / 18 / 19, Uṣas
    2 / 0 / 3 -- all of which were zero before. It does **not** remove it for Āpaḥ or Vāc,
    and 21 (deity, Veda) cells corpus-wide still have mentions and nothing in the default
    scope.

    Widening ``CERTAIN`` to make those cells non-empty was available and is refused: it
    would make the numbers look better by making the tier mean less, and for Āpaḥ (gold
    precision 0.2500) and Vāc (0.0000 on ten rows) a zero in the default scope is the
    *correct* result. What is wrong is not the zero, it is a zero **typed as a count**. So
    the residual is typed instead:

    ``ATTESTED``
        The default scope has evidence. Return the count.
    ``INSUFFICIENT_EVIDENCE``
        The deity is named in this slice, and no mention reaches the default scope. This is
        a statement about the *evidence*, not about the text, and it must never be rendered
        as ``0``. The ambiguous count is reported beside it so the caller can see how much
        is being withheld and can ask for exploratory mode.
    ``NOT_IN_LAYER``
        No mention at any tier. Still not "absent from the corpus" -- the mention layer's
        measured recall is 0.8857 -- but it is the strongest absence this layer can state.
    """
    if certain + probable > 0:
        return VERDICT_ATTESTED
    if ambiguous > 0:
        return VERDICT_INSUFFICIENT
    return VERDICT_ABSENT


def referent_tiers_for_mode(mode: str) -> frozenset[str]:
    """The tiers a caller in ``mode`` may read. This is the stated product contract.

    ``"default"`` is ``CERTAIN`` + ``PROBABLE``, ``"strict"`` is ``CERTAIN`` alone and
    ``"exploratory"`` is everything. An unknown mode raises rather than falling back to the
    widest set, because a typo silently widening a filter is how an ambiguous row reaches a
    user as a fact.
    """
    modes = {
        "default": DEFAULT_REFERENT_TIERS,
        "strict": STRICT_REFERENT_TIERS,
        "exploratory": EXPLORATORY_REFERENT_TIERS,
    }
    if mode not in modes:
        raise TheonymRegistryError(
            f"unknown referent-certainty mode {mode!r}; expected one of {sorted(modes)}"
        )
    return modes[mode]


@dataclass(frozen=True)
class TheonymForm:
    """One adjudicated surface form of one deity's name."""

    devata_id: str
    surface: str
    normalized: str
    source: str
    morphological_role: str
    ambiguity: str
    referent_certainty: str
    decision: str
    precision_estimate: float
    examples_read: int
    #: Vedas this form's **substring** pass is licensed for. Per form, not global, because
    #: the licence is a property of the word rather than of the edition's typography.
    #: ``pavamāna`` means Soma in the Rigveda and Samaveda and does *not* in the
    #: Atharvaveda -- wind at AVS 15.2.1-4, breath at 15.15.6, an abstract purifier at
    #: 6.19.1-2 -- so an unguarded Atharvavedic substring pass would assert that deity on
    #: roughly eleven mantras about wind and breath against two about Soma, taking the
    #: form's precision from 1.00 to about 0.2. A single global switch cannot express that.
    sandhi_vedas: frozenset[str] = frozenset({"SV"})
    #: True for a spelling this module generated rather than an adjudicator accepting it;
    #: see :func:`anusvara_variants`.
    generated: bool = False
    examples: tuple[str, ...] = ()
    counterexamples: tuple[str, ...] = ()
    notes: str = ""

    @property
    def admits_token(self) -> bool:
        return self.decision in _ADMITS_TOKEN

    @property
    def admits_sandhi(self) -> bool:
        return self.decision in _ADMITS_SANDHI and len(self.normalized) >= MIN_SANDHI_ALIAS_CHARS

    @property
    def is_vocative(self) -> bool:
        return self.morphological_role == ROLE_VOCATIVE


#: The folded surface's sentinel for every spelling of the anusvara. ``fold_alias``
#: collapses the various Devanagari and IAST anusvara spellings onto this one code point
#: and leaves a plain word-final ``m`` alone, so the two remain different strings.
_ANUSVARA_SENTINEL: Final = ""


def anusvara_variants(normalized: str) -> tuple[str, ...]:
    """The word-final anusvara/``-m`` counterpart of a folded form, if it has one.

    This is the single largest recall lever in the layer, and it exists because of an
    orthographic asymmetry between the annotation and the corpus.

    Word-final ``-m`` and the anusvara are in **complementary distribution** in Sanskrit,
    not lexical contrast: the same morpheme, written anusvara before a consonant and
    ``-m`` before a vowel or at a pause. The choice is settled by the *next* sound and
    never by the word, so no minimal pair exists and generating one spelling from the
    other cannot change which word is matched. ``sarasvatīṃ`` and ``sarasvatīm`` are the
    same accusative, split across Vedas.

    The asymmetry is what makes it necessary. The Zurich annotation writes word-final
    ``-m`` **27,285 times and the anusvara not once**, while the share of m-final tokens
    written with anusvara is **99.2% in the Samaveda, 87.4% in the Yajurveda and 60.0% in
    the Atharvaveda** against 48.4% in the Rigveda. So every form taken from the
    annotation and ending in ``-m`` fails in precisely the three Vedas this layer exists
    to reach.

    **Word-final only, deliberately.** Blanket substitution was measured against the same
    103 accepted aliases: final-only generates 21 new strings, blanket generates 81, and
    both land on the same single additional corpus token -- so blanket buys a four-times
    larger alias surface for zero measured gain. It also fabricates non-Sanskrit, because
    this corpus's Yajurvedic transcription carries a doubled-anusvara artefact
    (``sarasvatīṃṃ``, ``dyāvāpṛthivībhyāṃṃ``) which blanket substitution turns into
    ``-mm`` strings.
    """
    if normalized.endswith(_ANUSVARA_SENTINEL):
        return (normalized[: -len(_ANUSVARA_SENTINEL)] + "m",)
    if normalized.endswith("m"):
        return (normalized[:-1] + _ANUSVARA_SENTINEL,)
    return ()


@dataclass(frozen=True)
class TheonymDeity:
    """One deity's adjudicated theonym entry."""

    devata_id: str
    group: str
    ambiguity_class: str
    verdict: str
    rv_lemma: str
    rv_path: str
    forms: tuple[TheonymForm, ...]
    homonym_sense: str = ""
    structural_blocker: str = ""
    mislabelled_passages_avoided: int = 0
    belongs_in_layer: str = ""
    notes: str = ""
    adjudicator: str = "MODEL_ADJUDICATED"
    adjudicator_model: str = ""

    @property
    def accepted(self) -> bool:
        return self.verdict in _ACCEPTING_VERDICTS

    @property
    def is_homonym(self) -> bool:
        return self.ambiguity_class in _HOMONYM_CLASSES

    @property
    def vocative_only(self) -> bool:
        return self.verdict == "ACCEPTED_VOCATIVE_ONLY"

    def certainty_for(self, role: str) -> str:
        """Whether an occurrence in this role certainly denotes the deity.

        A vocative is an address, so it settles the reading whatever the name also means.
        Otherwise a name that is also an ordinary noun leaves the reading genuinely open,
        and the layer says so instead of choosing.
        """
        if role == ROLE_VOCATIVE:
            return CERTAIN
        return AMBIGUOUS if self.is_homonym else CERTAIN


@dataclass(frozen=True)
class TheonymIndex:
    """The registry inverted for matching."""

    deities: dict[str, TheonymDeity]
    #: folded RV lemma -> devata id. The annotation path.
    rv_lemma: dict[str, str]
    #: folded surface -> every (devata id, form) that claims it. The SV/YV/AV token path.
    #:
    #: **List-valued, and that is a corpus fact rather than a convenience.** The Samaveda
    #: and Yajurveda print several words as one token, so a single string genuinely names
    #: several gods: ``sarasvatīmaśvināvindramagnim`` names Sarasvatī, the Aśvins, Indra
    #: and Agni, and ``agniryasmintsomamindraḥ`` names Agni, Soma and Indra. 32 accepted
    #: forms are claimed by more than one deity and all 32 are correct. A one-deity index
    #: would have to discard three of those four gods, and which three would depend on the
    #: order the adjudicated fragments happened to be merged in.
    token: dict[str, tuple[tuple[str, TheonymForm], ...]]
    #: (folded surface, devata id, form), sorted. The Samavedic sandhi path.
    sandhi: tuple[tuple[str, str, TheonymForm], ...]

    @property
    def counts(self) -> dict[str, int]:
        return {
            "deities_in_registry": len(self.deities),
            "deities_accepted": sum(1 for d in self.deities.values() if d.accepted),
            "rv_lemmas": len(self.rv_lemma),
            "token_forms": len(self.token),
            "sandhi_forms": len(self.sandhi),
        }


def _as_float(value: Any, *, where: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TheonymRegistryError(
            f"{where}: precision_estimate {value!r} is not a number"
        ) from exc
    if not 0.0 <= number <= 1.0:
        raise TheonymRegistryError(f"{where}: precision_estimate {number} outside [0, 1]")
    return number


def load_theonyms(project_root: pathlib.Path) -> TheonymIndex:
    """Read and validate the adjudicated theonym registry.

    Validation refuses three things outright rather than resolving them, because each
    would produce a graph that loads and lies:

    * **A folded form claimed by two deities.** ``mitra`` cannot be both Mitra and the
      Mitra half of Mitravaruna on the token path; whichever won would depend on file
      order.
    * **An accepted form with no read evidence.** A precision estimate with
      ``examples_read: 0`` is admitted only for a form the annotation itself attests and
      whose deity is unambiguous, which is the one case where reading a verse adds nothing.
    * **A vocative-only deity with an accepted non-vocative form.** That combination means
      the deity-level verdict and the form-level decisions disagree, and silently
      following either would misreport the other.
    """
    path = project_root / REGISTRY_PATH
    if not path.exists():
        raise TheonymRegistryError(f"theonym registry not found: {path}")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or "deities" not in document:
        raise TheonymRegistryError(f"{path}: expected a mapping with a 'deities' key")

    deities: dict[str, TheonymDeity] = {}
    rv_lemma: dict[str, str] = {}
    token: dict[str, tuple[tuple[str, TheonymForm], ...]] = {}
    sandhi: list[tuple[str, str, TheonymForm]] = []

    for entry in document["deities"]:
        devata_id = str(entry["devata_id"])
        if devata_id in deities:
            raise TheonymRegistryError(f"{devata_id}: listed twice in the registry")
        verdict = str(entry.get("verdict", "ACCEPTED"))
        forms: list[TheonymForm] = []
        for raw in entry.get("forms") or ():
            where = f"{devata_id}/{raw.get('surface')}"
            normalized = fold_alias(str(raw.get("normalized") or raw.get("surface") or ""))
            if not normalized:
                raise TheonymRegistryError(f"{where}: form folds to the empty string")
            form = TheonymForm(
                devata_id=devata_id,
                surface=str(raw.get("surface") or ""),
                normalized=normalized,
                source=str(raw.get("source") or "UNKNOWN"),
                morphological_role=str(raw.get("morphological_role") or "UNKNOWN"),
                ambiguity=str(raw.get("ambiguity") or "UNAMBIGUOUS"),
                referent_certainty=str(raw.get("referent_certainty") or AMBIGUOUS),
                decision=str(raw.get("decision") or "REJECTED"),
                precision_estimate=_as_float(raw.get("precision_estimate", 0.0), where=where),
                examples_read=int(raw.get("examples_read") or 0),
                sandhi_vedas=frozenset(str(item) for item in (raw.get("sandhi_vedas") or ("SV",))),
                examples=tuple(str(item) for item in (raw.get("examples") or ())),
                counterexamples=tuple(str(item) for item in (raw.get("counterexamples") or ())),
                notes=str(raw.get("notes") or ""),
            )
            forms.append(form)

        deity = TheonymDeity(
            devata_id=devata_id,
            group=str(entry.get("group") or "UNSPECIFIED"),
            ambiguity_class=str(entry.get("ambiguity_class") or "UNAMBIGUOUS"),
            verdict=verdict,
            rv_lemma=fold_alias(str(entry.get("rv_lemma") or entry.get("lemma_stem") or "")),
            rv_path=str(entry.get("rv_path") or "LEMMA_ANNOTATION"),
            forms=tuple(forms),
            homonym_sense=str(entry.get("homonym_sense") or ""),
            structural_blocker=str(entry.get("structural_blocker") or ""),
            mislabelled_passages_avoided=int(entry.get("mislabelled_passages_avoided") or 0),
            belongs_in_layer=str(entry.get("belongs_in_layer") or ""),
            notes=str(entry.get("notes") or ""),
            adjudicator=str(entry.get("adjudicator") or "MODEL_ADJUDICATED"),
            adjudicator_model=str(entry.get("adjudicator_model") or ""),
        )
        deities[devata_id] = deity
        if not deity.accepted:
            continue

        if deity.rv_path == "LEMMA_ANNOTATION" and deity.rv_lemma:
            claimed = rv_lemma.get(deity.rv_lemma)
            if claimed and claimed != devata_id:
                raise TheonymRegistryError(
                    f"lemma {deity.rv_lemma!r} claimed by both {claimed} and {devata_id}"
                )
            rv_lemma[deity.rv_lemma] = devata_id

        for form in deity.forms:
            if deity.vocative_only and form.admits_token and not form.is_vocative:
                raise TheonymRegistryError(
                    f"{devata_id} is ACCEPTED_VOCATIVE_ONLY but accepts non-vocative "
                    f"{form.surface!r} on the token path"
                )
            if form.admits_token:
                if form.examples_read == 0 and not (
                    form.source == "RV_ANNOTATION" and form.ambiguity == "UNAMBIGUOUS"
                ):
                    raise TheonymRegistryError(
                        f"{devata_id}/{form.surface}: accepted with examples_read=0 and "
                        f"source={form.source} ambiguity={form.ambiguity}"
                    )
                spellings: list[tuple[str, bool]] = [
                    (form.normalized, False),
                    *((variant, True) for variant in anusvara_variants(form.normalized)),
                ]
                for spelling, is_generated in spellings:
                    claimants = token.get(spelling, ())
                    if any(claimed == devata_id for claimed, _ in claimants):
                        continue
                    # A generated spelling is not added where an adjudicated form already
                    # occupies the string for another deity: the adjudicated decision is
                    # the better evidence and the generated one adds nothing.
                    if is_generated and claimants:
                        continue
                    claimed_form = (
                        form
                        if not is_generated
                        else replace(form, normalized=spelling, generated=True)
                    )
                    token[spelling] = (*claimants, (devata_id, claimed_form))
            if form.admits_sandhi:
                sandhi.append((form.normalized, devata_id, form))

    return TheonymIndex(
        deities=deities,
        rv_lemma=rv_lemma,
        token=token,
        sandhi=tuple(sorted(sandhi, key=lambda item: (item[0], item[1]))),
    )


@dataclass
class TheonymMentionRow:
    """One (passage, deity) naming, with the evidence and the reading it supports."""

    passage_key: str
    veda: str
    devata_id: str
    path: str
    morphological_roles: tuple[str, ...]
    matched_forms: tuple[str, ...]
    occurrences: int
    referent_certainty: str
    #: Which rule in :func:`refine_referent_certainty` settled the tier. Stored so the
    #: bucket can be audited one rule at a time instead of as an average.
    referent_basis: str
    attribution_support: bool
    quality_tier: QualityTier
    provenance: Provenance
    grade_basis: str

    @property
    def mention_id(self) -> str:
        return stable_id("THEONYM-MENTION", self.passage_key, self.devata_id)

    def as_row(self) -> dict[str, Any]:
        return {
            "mention_id": self.mention_id,
            "passage_key": self.passage_key,
            "veda": self.veda,
            "devata_id": self.devata_id,
            "extraction_path": self.path,
            "morphological_roles": list(self.morphological_roles),
            "matched_forms": list(self.matched_forms),
            "occurrences": self.occurrences,
            "referent_certainty": self.referent_certainty,
            "referent_basis": self.referent_basis,
            "attribution_support": self.attribution_support,
            "attribution_precision": "TEXTUAL_MENTION",
            "evidence_basis": "SANSKRIT",
            "quality_tier": str(self.quality_tier),
            "grade_basis": self.grade_basis,
            "domain_model_version": DOMAIN_MODEL_VERSION,
            **self.provenance.as_edge_properties(),
        }


@dataclass
class _Occurrence:
    """Accumulated evidence for one deity in one passage."""

    roles: set[str] = field(default_factory=set)
    forms: set[str] = field(default_factory=set)
    count: int = 0
    quote: str = ""
    surface: str = ""
    locator: str = ""

    def add(self, role: str, form: str, *, quote: str, surface: str, locator: str) -> None:
        self.roles.add(role)
        self.forms.add(form)
        self.count += 1
        # Keep the first *vocative* quote in preference to any other, because that is the
        # occurrence a reader checking the deity reading needs to see.
        if not self.quote or (role == ROLE_VOCATIVE and ROLE_VOCATIVE not in self.roles - {role}):
            self.quote = quote
            self.surface = surface
            self.locator = locator


def _annotation_hits(
    tokens: Sequence[AnnotatedToken], index: TheonymIndex
) -> dict[str, _Occurrence]:
    """Deity namings in one Rigvedic passage, from the annotation's own lemma field."""
    found: dict[str, _Occurrence] = {}
    for token in tokens:
        devata_id = index.rv_lemma.get(token.folded_lemma)
        if devata_id is None or not token.is_nominal:
            continue
        role = ROLE_VOCATIVE if token.is_vocative else (token.case or "UNKNOWN")
        found.setdefault(devata_id, _Occurrence()).add(
            role,
            token.surface_form,
            quote=token.as_evidence_quote(),
            surface="vedaweb-zurich-annotation",
            locator=token.token_key or token.passage_key,
        )
    return found


def _surface_hits(mantra: MantraRecord, index: TheonymIndex) -> dict[str, _Occurrence]:
    """Deity namings in one non-Rigvedic passage, by whole-token surface match."""
    found: dict[str, _Occurrence] = {}
    tokens = mantra.surfaces.tokens
    for position, token in enumerate(tokens):
        for devata_id, form in index.token.get(token, ()):
            window = " ".join(tokens[max(0, position - 2) : position + 3])
            found.setdefault(devata_id, _Occurrence()).add(
                form.morphological_role,
                form.surface,
                quote=render_for_display(window),
                surface="script_folded",
                locator=mantra.passage_key,
            )
    return found


def _sandhi_hits(
    mantra: MantraRecord, index: TheonymIndex, already: Iterable[str]
) -> dict[str, _Occurrence]:
    """Substring pass, restricted to deities the token pass did not reach.

    A deity reached by both paths is reported on the stronger one. Recording the weaker
    alongside it would describe the evidence as worse than it is.

    Licensing is **per form**, from :attr:`TheonymForm.sandhi_vedas`, not per Veda from a
    module constant. The constant was the first design and it is not expressible enough:
    lifting a global Samaveda-only switch to include the Atharvaveda would take
    ``pavamāna`` from precision 1.00 to about 0.2, because that word means Soma in the
    Rigveda and Samaveda and means wind or breath in the Atharvaveda. The licence belongs
    to the word.
    """
    seen = set(already)
    text = mantra.surfaces.sandhi_insensitive
    found: dict[str, _Occurrence] = {}
    for normalized, devata_id, form in index.sandhi:
        if devata_id in seen or mantra.veda not in form.sandhi_vedas:
            continue
        position = text.find(normalized)
        if position < 0:
            continue
        quote = text[max(0, position - 25) : position + len(normalized) + 25]
        found.setdefault(devata_id, _Occurrence()).add(
            form.morphological_role,
            form.surface,
            quote=render_for_display(quote),
            surface="sandhi_insensitive",
            locator=mantra.passage_key,
        )
    return found


def _grade(deity: TheonymDeity, path: str, roles: Iterable[str]) -> tuple[QualityTier, str, str]:
    """Tier, grade basis and referent certainty for one mention.

    Two rules, and the second one is the subtler and was got wrong first.

    **On the Rigvedic path, tier follows what the source actually states.** A manual
    scholarly annotation saying that this token's lemma is ``indra-`` *is* the statement
    "this passage names Indra", because Indra is not also an ordinary noun: ``TIER_A``. For
    a name that is also an ordinary noun the same annotation does not state the deity
    reading -- ``agním`` is "fire" or "Agni" and the annotation assigns one lemma to both --
    and only the **vocative** settles it, because a vocative is an address to the named
    being. So a vocative of a homonym is ``TIER_A`` and every other case of one is
    ``TIER_B`` with the ambiguity recorded.

    **On the surface paths, a vocative is not observable, so it earns nothing.** This is
    the correction. For a thematic a-stem the vocative singular and the sandhi-reduced
    nominative singular are the *same Saṃhitā string*: RV 6.29.4 reads ``sá soma
    ā́miślatamaḥ``, "that Soma when effused hath best consistence", where the annotation
    records ``sómaḥ`` NOM/SG and the printed text spells it ``soma`` -- character for
    character the vocative. Measured across the group, the share of a form's tokens that
    are pre-consonantal, and therefore certainly vocative rather than a reduced
    nominative, runs from effectively 100% for ``agne`` down to **47% for ``sūrya``**.

    The annotation is not wrong about this and never was; the Samaveda, Yajurveda and
    Atharvaveda simply have no annotation, so on those three the case that would settle
    the reading is not there to be read. A form the adjudicators labelled ``VOCATIVE``
    carries a role taken from the *Rigvedic* paradigm, not from the token in front of us.
    Honouring that label as certainty would manufacture exactly the confidence this layer
    exists to refuse -- so outside the Rigveda a homonymous name is ``DEITY_AMBIGUOUS``
    however vocative it looks, and only a name that is not also an ordinary noun is
    certain.
    """
    role_set = set(roles)
    if path == PATH_ANNOTATION:
        if not deity.is_homonym:
            return (
                QualityTier.TIER_A,
                f"{ANNOTATION_SOURCE_ID} {ANNOTATION_METHOD}: lemma identity, "
                "name is not a common noun",
                CERTAIN,
            )
        if ROLE_VOCATIVE in role_set:
            return (
                QualityTier.TIER_A,
                f"{ANNOTATION_SOURCE_ID} {ANNOTATION_METHOD}: vocative address, "
                "which settles the deity reading of a homonymous name",
                CERTAIN,
            )
        return (
            QualityTier.TIER_B,
            f"{ANNOTATION_SOURCE_ID} {ANNOTATION_METHOD}: lemma identity only; "
            f"the name also means {deity.homonym_sense or 'an ordinary noun'}",
            AMBIGUOUS,
        )

    if path == PATH_TOKEN:
        basis = "whole-token match over stored Sanskrit, form attested in the Rigvedic annotation"
    else:
        basis = "substring match over the boundary-free Samavedic surface"
    if deity.is_homonym:
        return (
            QualityTier.TIER_B,
            (
                f"{basis}; the name also means "
                f"{deity.homonym_sense or 'an ordinary noun'}, and this Veda carries no "
                "morphological annotation, so the case that would settle the reading is "
                "not observable"
            ),
            AMBIGUOUS,
        )
    return QualityTier.TIER_B, basis, CERTAIN


def extract_theonym_mentions(
    corpus: Corpus,
    annotation: Annotation,
    index: TheonymIndex,
) -> tuple[list[TheonymMentionRow], RunReport]:
    """Find every deity each mantra names, on the strongest evidence each Veda affords.

    The Rigveda is read from the annotation and never string-matched; the other three are
    string-matched and never claimed as annotated. The report separates them at every
    level, because a single combined precision figure for this layer would be the most
    misleading number in the graph.
    """
    identity = run_id(
        _STAGE,
        len(corpus.mantras),
        len(annotation.tokens),
        len(index.rv_lemma),
        len(index.token),
        len(index.sandhi),
    )
    report = RunReport(stage=_STAGE)
    rows: list[TheonymMentionRow] = []
    per_veda: dict[str, int] = {}
    covered: dict[str, set[str]] = {}
    path_counts: dict[str, int] = {PATH_ANNOTATION: 0, PATH_TOKEN: 0, PATH_SANDHI: 0}
    certainty_counts: dict[str, int] = dict.fromkeys(REFERENT_TIERS, 0)
    basis_counts: dict[str, int] = {}
    support_counts: dict[str, int] = {"supported": 0, "unsupported": 0}

    for mantra in corpus.mantras:
        per_veda[mantra.veda] = per_veda.get(mantra.veda, 0) + 1
        if mantra.veda == "RV":
            hits = {
                key: (PATH_ANNOTATION, occurrence)
                for key, occurrence in _annotation_hits(
                    annotation.by_passage.get(mantra.passage_key, ()), index
                ).items()
            }
            if not annotation.by_passage.get(mantra.passage_key):
                report.reject("rv_passage_not_annotated")
        else:
            token_hits = _surface_hits(mantra, index)
            hits = {key: (PATH_TOKEN, value) for key, value in token_hits.items()}
            for key, value in _sandhi_hits(mantra, index, token_hits).items():
                hits[key] = (PATH_SANDHI, value)

        for devata_id, (path, occurrence) in sorted(hits.items()):
            deity = index.deities[devata_id]
            roles = tuple(sorted(occurrence.roles))
            tier, basis, base_certainty = _grade(deity, path, roles)
            support = devata_id in mantra.devatas
            certainty, referent_basis = refine_referent_certainty(base_certainty, roles, support)
            provenance = Provenance(
                trust=(
                    TrustClass.SOURCE_EXPLICIT
                    if path == PATH_ANNOTATION and tier is QualityTier.TIER_A
                    else TrustClass.DETERMINISTIC_DERIVED
                ),
                method=f"{_METHOD_ROOT}:{path}",
                score=(
                    _SCORE_ANNOTATION
                    if path == PATH_ANNOTATION
                    else (_SCORE_TOKEN if path == PATH_TOKEN else _SCORE_SANDHI)
                ),
                evidence=(
                    EvidenceSpan(
                        locator=occurrence.locator,
                        surface=occurrence.surface,
                        quote=occurrence.quote,
                    ),
                ),
                state=AssertionState.ACCEPTED,
                run_id=identity,
                notes=(
                    "forms: " + ", ".join(sorted(occurrence.forms)) + f"; roles: {'/'.join(roles)}"
                ),
            )
            rows.append(
                TheonymMentionRow(
                    passage_key=mantra.passage_key,
                    veda=mantra.veda,
                    devata_id=devata_id,
                    path=path,
                    morphological_roles=roles,
                    matched_forms=tuple(sorted(occurrence.forms)),
                    occurrences=occurrence.count,
                    referent_certainty=certainty,
                    referent_basis=referent_basis,
                    attribution_support=support,
                    quality_tier=tier,
                    provenance=provenance,
                    grade_basis=basis,
                )
            )
            covered.setdefault(mantra.veda, set()).add(mantra.passage_key)
            path_counts[path] += 1
            certainty_counts[certainty] += 1
            basis_counts[referent_basis] = basis_counts.get(referent_basis, 0) + 1
            support_counts["supported" if support else "unsupported"] += 1

    rows.sort(key=lambda row: (row.passage_key, row.devata_id))
    report.produced = len(rows)
    report.notes = {
        "registry": index.counts,
        "mentions_by_path": dict(sorted(path_counts.items())),
        "referent_certainty": dict(sorted(certainty_counts.items())),
        "referent_basis": dict(sorted(basis_counts.items())),
        "anukramani_attribution_support": dict(sorted(support_counts.items())),
        "tier": {
            str(tier): sum(1 for row in rows if row.quality_tier is tier)
            for tier in (QualityTier.TIER_A, QualityTier.TIER_B)
        },
        "coverage_by_veda": {
            veda: {
                "mantras": per_veda[veda],
                "with_theonym": len(covered.get(veda, set())),
                "coverage": round(len(covered.get(veda, set())) / per_veda[veda], 4),
            }
            for veda in sorted(per_veda)
        },
        "distinct_deities_used": len({row.devata_id for row in rows}),
        "deities_accepted_but_unused": sorted(
            devata_id
            for devata_id, deity in index.deities.items()
            if deity.accepted and devata_id not in {row.devata_id for row in rows}
        ),
    }
    return rows, report
