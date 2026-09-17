"""Generate the ontology reference from the contract and the live graph.

Written by a script rather than by hand for one reason: a hand-written ontology reference
is a document that was true once. Every count here is measured against the running
database and every declaration is read from
:mod:`vedagraph.domain.ontology`, so re-running this is the only way the reference stays
honest -- and if a predicate is added without a definition, the generator says so instead
of quietly omitting it.

The brief asks that this be understandable to someone who did not write the code. So each
relationship type gets a definition, its declared domain and range, what evidence it
requires, how much of it exists, and -- the part usually missing -- an **example and a
counterexample**: a case it does cover and a case it deliberately does not. The
counterexamples are where the real information is, because a predicate's boundary is what
tells a reader what it will not answer.

Usage::

    python scripts/generate_ontology_reference.py
    python scripts/generate_ontology_reference.py --check   # verify, write nothing
"""

from __future__ import annotations

import argparse
import io
import pathlib
import sys
from typing import Any, Final

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.domain.ontology import (  # noqa: E402
    DOMAIN_RELATIONSHIP_TYPES,
    INTERNAL_LABELS,
    PRODUCT_LABELS,
    all_declared_relationship_types,
    all_endpoint_signatures,
)
from vedagraph.domain.ontology import (  # noqa: E402
    UNPOPULATED_BY_DESIGN as _DOMAIN_UNPOPULATED,
)
from vedagraph.enrich.predicates import (  # noqa: E402
    UNPOPULATED_BY_DESIGN as _ENRICH_UNPOPULATED,
)

#: Both layers' deliberately-empty predicates, in one lookup. Each layer declares its own
#: -- a domain constant asserting a reason for an enrichment predicate would be a
#: cross-layer reach -- but a reader enumerating the live relationship types sees one flat
#: list and needs one answer per name.
UNPOPULATED_BY_DESIGN: Final[dict[str, str]] = {
    **_DOMAIN_UNPOPULATED,
    **_ENRICH_UNPOPULATED,
}

BOLT_URI: Final = "bolt://localhost:7687"
BOLT_AUTH: Final = ("neo4j", "vedagraph_dev")
OUT: Final = PROJECT_ROOT / "docs" / "reports" / "VEDAGRAPH_ONTOLOGY_REFERENCE_V3.md"

#: What each predicate asserts, what it requires as evidence, and a case it refuses.
#:
#: The refusals are load-bearing. A reader who knows only what a predicate covers will
#: over-read it; the counterexample is what stops "this passage mentions Indra" being read
#: as "this hymn is dedicated to Indra", which are different edges with different tiers.
DEFINITIONS: Final[dict[str, dict[str, str]]] = {
    "MENTIONS_DEVATA": {
        "asserts": "This passage names this god, in its own Sanskrit.",
        "evidence": (
            "Rigveda: a manual scholarly morphological annotation states the token's "
            "lemma, and its case. The other three Vedas: a whole-token or (Samaveda and "
            "Yajurveda) substring match against an individually adjudicated surface form."
        ),
        "trust": (
            "TIER_A where the source states the claim the edge makes -- lemma identity for "
            "a name that is not also a common noun, or a vocative, which is an address and "
            "so settles the deity reading. TIER_B otherwise, with referent_certainty = "
            "DEITY_AMBIGUOUS. Outside the Rigveda a vocative earns nothing, because the "
            "vocative singular and the sandhi-reduced nominative are the same printed "
            "string and no annotation is there to tell them apart."
        ),
        "example": (
            "AVS 1.7.3 contains `índraś`, so the Atharvavedic passage names Indra -- a fact "
            "no attribution layer could supply, since the Atharvaveda's index ascribes "
            "descriptors rather than deities."
        ),
        "counterexample": (
            "It does NOT mean the hymn is dedicated to this deity. That is HAS_DEVATA, it "
            "exists only for the Rigveda, and 78.9% of it is inherited from the sukta "
            "rather than stated of the verse. The two disagree often and are meant to."
        ),
    },
    "HAS_DEVATA": {
        "asserts": "A traditional index ascribes this passage to this deity.",
        "evidence": "The Anukramani, via the commit-pinned WSC2023 artifacts.",
        "trust": (
            "TIER_A with attribution_precision = PER_PASSAGE where the index names the "
            "verse or a range containing it; TIER_B with CONTAINER_INHERITED where the "
            "claim is the sukta's and has been projected onto its verses."
        ),
        "example": "RV 1.1.1 is ascribed to Agni by the Anukramani.",
        "counterexample": (
            "The Atharvaveda has none of these and that is not a gap: Whitney's excerpts "
            "ascribe an adjectival descriptor (`agneyam`, 'belonging to Agni'), carried by "
            "HAS_DEVATA_ASCRIPTION. The Samaveda and Yajurveda have none either, for "
            "source reasons recorded in the coverage report."
        ),
    },
    "HAS_DEVATA_ASCRIPTION": {
        "asserts": "A traditional index ascribes this passage using a deity *descriptor*.",
        "evidence": "Whitney's printed Brhatsarvanukramani excerpts, per hymn.",
        "trust": "TIER_B, CONTAINER_INHERITED: the ascription is the hymn's, not the verse's.",
        "example": (
            "AVS 1.1 is ascribed `mantroktadevatyam`, 'having the deity named in the mantra'."
        ),
        "counterexample": (
            "The object is NOT a deity and must never be unioned with :Devata. There are "
            "356 of these descriptors; counting them as gods would add 356 spurious "
            "deities to every census."
        ),
    },
    "HAS_SEMANTIC_ASSERTION": {
        "asserts": "This assertion was read off this passage.",
        "evidence": "Structural: the spine of the reified assertion layer.",
        "trust": "TIER_B, STRUCTURAL. It asserts nothing about the corpus itself.",
        "example": "RV 1.32.4 has an assertion that Indra slew the firstborn.",
        "counterexample": (
            "It carries no claim of its own. The claim, its grade and its evidence live on "
            "the SemanticAssertion node, whose `derivation` says whether a rule derived it "
            "from the annotation or a model extracted it from a translation."
        ),
    },
    "ASSERTION_AGENT": {
        "asserts": "This being is the agent of this assertion -- it acts, or is asked to.",
        "evidence": (
            "Rule-derived: within one metrical line containing exactly one finite verb, a "
            "third-person verb with exactly one agreeing nominative deity, or a "
            "second-person verb with exactly one vocative deity."
        ),
        "trust": "TIER_B, SANSKRIT. As good as the assertion it belongs to, and no better.",
        "example": "RV 1.51.4: Indra is the agent of a slaying, with `savasa` as instrument.",
        "counterexample": (
            "This is co-location plus agreement, NOT a parse. The annotation has no "
            "dependency structure, so in a line packing two clauses the agreement may be "
            "with a verb this rule did not pick. `agent_incomplete` marks the 23 cases "
            "where a dual or plural verb has more agents than the assertion names."
        ),
    },
    "ASSERTION_PREDICATE": {
        "asserts": "This assertion predicates this member of the closed action vocabulary.",
        "evidence": "The verb's root, mapped through data/registry/action_root_map.yaml.",
        "trust": "TIER_B, STRUCTURAL.",
        "example": "The root `han-` maps to SLAYS.",
        "counterexample": (
            "A predicate is a verb *class*, not a verb. The mapping loses information "
            "deliberately and sometimes heavily: `kr-` ('do, make', 1,207 tokens) maps to "
            "CREATES and carries almost no content, which is why the registry recommends "
            "excluding it from action profiles alongside IS_OR_BECOMES."
        ),
    },
    "ASSERTION_TARGET": {
        "asserts": "This assertion is about this entity, in the role the edge names.",
        "evidence": "The same source as its assertion; `role` distinguishes patient from referent.",
        "trust": "TIER_B for rule-derived assertions, TIER_D for the sealed model run.",
        "example": "An assertion at RV 1.51.4 targets Vrtra in the PATIENT role.",
        "counterexample": (
            "An accusative in a metrical line is not necessarily the verb's object. "
            "Several accusatives per line are normal and all are recorded as candidates."
        ),
    },
    "PERFORMS_ACTION": {
        "asserts": "The corpus states that this deity does this, aggregated over passages.",
        "evidence": "Rebuilt from the assertion nodes on every load; never authored beside them.",
        "trust": "TIER_B, SANSKRIT, with assertion_count and passage_count on the edge.",
        "example": "Indra PERFORMS_ACTION SLAYS, with the assertions as the evidence trail.",
        "counterexample": (
            "It is not a mythological statement and does not mean the deity is "
            "characteristically associated with the act. It means the rule fired this many "
            "times. And it is Rigveda-only, because the annotation it derives from is."
        ),
    },
    "IS_ASKED_TO": {
        "asserts": "The corpus asks this deity to do this.",
        "evidence": (
            "A second-person imperative, optative, subjunctive, injunctive or precative "
            "addressed to a vocative deity. A grammatical fact about the verse, not a "
            "reading of it."
        ),
        "trust": "TIER_B, SANSKRIT.",
        "example": "RV 1.3.4 `indra a yahi` -- Indra is asked to come.",
        "counterexample": (
            "Distinct from PERFORMS_ACTION on purpose. 'Indra slays Vrtra' and 'Indra, "
            "slay Vrtra!' are different claims about the corpus, and the commonest thing "
            "said to a Vedic god is a request rather than a description."
        ),
    },
    "MENTIONS_ENTITY": {
        "asserts": "This passage names this domain entity, on Sanskrit evidence.",
        "evidence": "A probed alias matched as a whole token, or as a substring in the Samaveda.",
        "trust": "TIER_B, SANSKRIT. Uncapped: a passage naming four things names four things.",
        "example": "A passage containing `yava` names barley.",
        "counterexample": (
            "It no longer reaches :Devata. Those 9,000 Rigveda-only edges duplicated "
            "MENTIONS_LEMMA fact for fact and are superseded by the four-Veda "
            "MENTIONS_DEVATA layer."
        ),
    },
    "ABOUT_CONCEPT": {
        "asserts": (
            "Of the entities this passage names, this is one of the (at most four) it is "
            "substantively about."
        ),
        "evidence": "The same Sanskrit evidence as the mention it ranks.",
        "trust": "TIER_B.",
        "example": "A hymn to the waters is about water as well as naming it.",
        "counterexample": (
            "It is NOT an independent layer and must not be quoted against the mention "
            "layer as a second opinion. V3 retired the 21,539 translation-only edges that "
            "made it look independent -- an aboutness claim resting on one keyword in "
            "Griffith's 1896 English measures his word choice, not the passage -- leaving "
            "26,437 edges of which 24,947 (94.4%) are corroborated by a MENTIONS_ENTITY "
            "edge to the same entity. The 1,490 that are not are ~97% sanskrit-token, "
            "aimed mostly at NaturalPhenomenon and Substance: they are Sanskrit-grounded, "
            "and what they lack is agreement from the other lexicon, because aboutness "
            "reads the 91 entities of concepts.yaml while mentions read the 227-entity "
            "merged domain registry with its stricter suppression list. An earlier pass "
            "reported this residue as 0; it is not 0, and the per-method breakdown is in "
            "the about_concept_reconciliation load report."
        ),
    },
    # ---- V2 domain predicates ---------------------------------------------------
    "ADDRESSES_CONCERN": {
        "asserts": "This passage names a human concern, so it is about wanting it.",
        "evidence": "A probed Sanskrit alias for the concern, matched in the passage.",
        "trust": (
            "TIER_B: naming what you want is wanting it, so the edge asserts no more than "
            "the mention it derives from."
        ),
        "example": "A charm naming progeny addresses the concern of offspring.",
        "counterexample": (
            "It does not assert that the passage *treats* or achieves the concern. TREATS "
            "is the stronger claim and is graded TIER_D for exactly that reason."
        ),
    },
    "TREATS": {
        "asserts": "This passage acts on this affliction -- it is a remedy for it.",
        "evidence": "A probed Sanskrit alias for the condition, plus a curated whitelist.",
        "trust": (
            "TIER_D, interpretive. It asserts a *function* beyond naming: that the charm "
            "works on the affliction rather than merely mentioning it. That is a reading."
        ),
        "example": "The Atharvavedic takman hymns treat fever.",
        "counterexample": (
            "Naming a disease is not treating it. A verse listing afflictions to be "
            "avoided names them without being a remedy."
        ),
    },
    "PROTECTS_FROM": {
        "asserts": "This passage seeks protection from this thing.",
        "evidence": "A probed alias plus a curated whitelist.",
        "trust": "TIER_D, interpretive, for the same reason as TREATS: it asserts a function.",
        "example": "A protective charm naming demons seeks protection from them.",
        "counterexample": "A narrative mentioning an enemy is not asking to be protected from it.",
    },
    "USED_FOR_RITE": {
        "asserts": "This passage belongs to this social rite.",
        "evidence": "A probed alias whose vocabulary occurs nowhere but the occasion.",
        "trust": "TIER_B: the rite vocabulary is specific enough that naming it is using it.",
        "example": "AV 14 is used for marriage, and so are the Rigvedic verses it redacts.",
        "counterexample": (
            "The Rigvedic appearances are correct rather than errors -- AV 14 redacts RV "
            "10.85 -- so a rite edge is not evidence of a Veda distinctive character."
        ),
    },
    "COMPOSED_OF": {
        "asserts": "This dual or collective deity label decomposes into these deities.",
        "evidence": "The morphology of the label itself, from a curated component registry.",
        "trust": "TIER_B, SOURCE_METADATA: it follows from the form of the label.",
        "example": "Mitravarunau is composed of Mitra and Varuna.",
        "counterexample": (
            "A mention of the dual is NOT a mention of either component, and the theonym "
            "layer deliberately does not propagate it. Indra alone and Indra jointly are "
            "different questions, and propagation would destroy the second."
        ),
    },
    "HAS_AXIS": {
        "asserts": "The corpus uses this deity in this functional role.",
        "evidence": "A curated multi-axis taxonomy, authored per deity with a stated reason.",
        "trust": "TIER_D: a reading of what the corpus does, not a source statement.",
        "example": "Agni holds FIRE_MEDIUM, PRIESTLY and TERRESTRIAL at once.",
        "counterexample": (
            "Not a source classification. 101 of 214 deities are deliberately UNSPECIFIED, "
            "each with a recorded reason -- an absent axis is a refusal to guess."
        ),
    },
    "HAS_EPITHET": {
        "asserts": "This deity is called by this epithet.",
        "evidence": "Curated, from attested corpus forms.",
        "trust": "TIER_D: curated.",
        "example": "Agni is called jatavedas.",
        "counterexample": (
            "An epithet is a name, so it belongs to the deity and not to the impersonal "
            "concept of the same word. The jatavedas forms were removed from the fire "
            "concept in V3 for this reason."
        ),
    },
    "MEMBER_OF": {
        "asserts": "This deity belongs to this named group.",
        "evidence": "Curated.",
        "trust": "TIER_D.",
        "example": "The Adityas as a group.",
        "counterexample": "Group membership is not co-occurrence; CO_OCCURS_WITH measures that.",
    },
    "USES_OFFERING": {
        "asserts": "This rite uses this offering.",
        "evidence": "Curated from verses naming the rite and the item together.",
        "trust": "TIER_D: curated ritual structure.",
        "example": "The yajna uses the havis oblation, cited to VS 19.17 and RV 1.84.18.",
        "counterexample": (
            "Absence is not evidence of absence. Fields fillable only from Brahmana or "
            "Sutra systematisation are left EMPTY on purpose, with the omission stated in "
            "each rite basis field rather than filled plausibly."
        ),
    },
    "USES_SUBSTANCE": {
        "asserts": "This rite uses this substance.",
        "evidence": "Curated from co-naming verses.",
        "trust": "TIER_D.",
        "example": "The soma pressing uses soma.",
        "counterexample": "Same Brahmana caveat as USES_OFFERING.",
    },
    "USES_OBJECT": {
        "asserts": "This rite manipulates this object.",
        "evidence": "Curated from co-naming verses.",
        "trust": "TIER_D.",
        "example": "The soma pressing uses the pressing stones, mortar, strainer, jar and cup.",
        "counterexample": "Same Brahmana caveat as USES_OFFERING.",
    },
    "INVOKES_DEVATA": {
        "asserts": "This rite invokes this deity.",
        "evidence": "Curated.",
        "trust": "TIER_D.",
        "example": "The yajna invokes Agni, the deity every oblation passes through by definition.",
        "counterexample": (
            "Not a list of every deity a rite ever addresses. Which deity a passage invokes "
            "is the attribution and mention layers question, not this one."
        ),
    },
    "PERFORMED_BY": {
        "asserts": "This rite is performed by this priestly role.",
        "evidence": "Curated.",
        "trust": "TIER_D.",
        "example": "The soma pressing is performed by the adhvaryu.",
        "counterexample": (
            "A recorded modelling limitation: this predicate carries both officiates-at "
            "and is-the-patron-of, because there is no COMMISSIONED_BY. The yajamana "
            "appears here for that reason, not because the corpus says the patron works."
        ),
    },
    "PERFORMED_FOR": {
        "asserts": "This rite is performed for this outcome or concern.",
        "evidence": "Curated from what the corpus asks for in the same breath as the rite.",
        "trust": "TIER_D.",
        "example": "The yajna is performed for wealth, offspring, wellbeing and long life.",
        "counterexample": "Not an exhaustive purpose list; it is the four asked for oftenest.",
    },
    "MEASURES": {
        "asserts": "This derived metric is about this entity.",
        "evidence": "Structural: the metric own subject field.",
        "trust": "TIER_B, STRUCTURAL.",
        "example": "DEVATA_ACTION_DISTRIBUTION measures Indra.",
        "counterexample": (
            "A metric carries no interpretation. Reading a trend in one is an "
            "InterpretiveClaim, which is why every metric node carries interpretation: NONE."
        ),
    },
    "SUPPORTED_BY": {
        "asserts": "This interpretive claim cites this passage as evidence.",
        "evidence": "Structural; the loader refuses a claim citing neither passage nor metric.",
        "trust": "TIER_D: the claim it supports is a reading.",
        "example": "A claim about deity prominence citing the verses it rests on.",
        "counterexample": "Citation is not proof; two claims may cite one passage and contradict.",
    },
    "SUPPORTED_BY_STATISTIC": {
        "asserts": "This interpretive claim cites this derived metric.",
        "evidence": "Structural; the loader refuses a claim citing a metric nothing computes.",
        "trust": "TIER_D.",
        "example": "A claim about ritual complexity citing RITUAL_ENTITY_DENSITY.",
        "counterexample": "A metric supporting a claim does not make the claim deterministic.",
    },
    "CONCERNS": {
        "asserts": "This interpretive claim is about this entity.",
        "evidence": "Structural.",
        "trust": "TIER_D.",
        "example": "A claim about Rudra concerns Rudra.",
        "counterexample": (
            "One bogus-edge lesson lives here: an unlabelled MATCH filtering on work_id "
            "once produced 39,461 of these, because every Passage carries a work_id. Two "
            "live tests now guard it."
        ),
    },
    "CONTRADICTS": {
        "asserts": "These two interpretive claims are in conflict.",
        "evidence": "Structural, authored.",
        "trust": "TIER_D.",
        "example": "Two claims about changing deity prominence that cannot both hold.",
        "counterexample": (
            "The graph does not pick a winner and must not be read as endorsing either. A "
            "live contradiction is a feature of the interpretive layer."
        ),
    },
    "ASSERTED_BY": {
        "asserts": "This interpretive claim is held by this named source.",
        "evidence": "Structural.",
        "trust": "TIER_D.",
        "example": "None. Unpopulated.",
        "counterexample": (
            "Every current claim is this project own synthesis rather than a commentator "
            "position, so attributing one to a source would be false."
        ),
    },
    # ---- declared and deliberately unpopulated ----------------------------------
    "PERSONIFIES": {
        "asserts": "This deity is the personification of this phenomenon or concept.",
        "evidence": "Would require a source stating the identification.",
        "trust": "Would be TIER_D.",
        "example": "None. Unpopulated.",
        "counterexample": (
            "Deliberately empty. Agni is fire is a commentarial reading, not a fact the "
            "corpus states, and the frozen semantic ontology refuses REPRESENTS and "
            "IS_GOD_OF by name for the same reason. DEVATA_ASSOCIATED_WITH records the "
            "association without asserting the identity."
        ),
    },
    "WIELDS": {
        "asserts": "This deity wields this object.",
        "evidence": "Would require an agentive layer resolving instruments to entities.",
        "trust": "Would be TIER_B.",
        "example": "None. Unpopulated.",
        "counterexample": (
            "The agentive layer records instruments as surface forms on the assertion "
            "rather than as resolved entities, so Indra wields the vajra is reachable "
            "through an assertion instrument field but is not asserted as an edge."
        ),
    },
    "RECEIVES_OFFERING": {
        "asserts": "This deity receives this offering.",
        "evidence": "Would require resolving an offering to a recipient deity per passage.",
        "trust": "Would be TIER_B.",
        "example": "None. Unpopulated.",
        "counterexample": (
            "RECEIVES_OFFERING also exists as an action predicate in the closed verb "
            "vocabulary and is populated there, which is a different claim: that a verse "
            "says a god accepted something, not that a god is a standing recipient."
        ),
    },
    "HAS_STEP": {
        "asserts": "This rite has this act as a step, in a stated order.",
        "evidence": "The source must state the ordinal in words.",
        "trust": "TIER_B where populated, with order_basis on the edge.",
        "example": (
            "The three soma pressings: RV 10.112.1 calls the morning one the first "
            "(purvapiti), AVS 6.47.2 says at the second pressing, AVS 6.47.3 the third."
        ),
        "counterexample": (
            "Adjacency was refused outright. Order in the Vajasaneyi adhyayas is a real "
            "citable fact and is not a stated step relation; populating from it would "
            "present a text order as a ritual procedure."
        ),
    },
    "DESCRIBED_IN": {
        "asserts": "This rite is described in this passage.",
        "evidence": "Per-rite passage curation, each citation read.",
        "trust": "TIER_D: curated.",
        "example": "The graha soma-drawing is described in 15 Yajurvedic passages.",
        "counterexample": (
            "It does not mean the passage is *only* about the rite, and one passage is "
            "deliberately excluded: VG:YV:VSM:A07:V003 carries Uvata and Mahidhara "
            "commentary inline in its stored text, so a match there would import a "
            "Brahmana sentence into the Samhita layer through a corpus defect."
        ),
    },
    "BELONGS_TO_FAMILY": {
        "asserts": "This rsi belongs to this family.",
        "evidence": "Would require a source stating descent.",
        "trust": "Would be TIER_B.",
        "example": "None. Unpopulated; there are 0 RishiFamily nodes.",
        "counterexample": (
            "Family membership must never be inferred from a similar name. The Rigvedic "
            "registry stores patronymic compounds while the Yajurvedic and Atharvavedic "
            "indices give bare names, so cross-index name similarity is exactly the signal "
            "that must not be trusted."
        ),
    },
    "ASSOCIATED_WITH_TRIBE": {
        "asserts": "This deity or rsi is associated with this tribe.",
        "evidence": "Would require curation.",
        "trust": "Would be TIER_D.",
        "example": "None. Unpopulated.",
        "counterexample": "Unpopulated rather than guessed.",
    },
    "ASSOCIATED_WITH_CONCEPT": {
        "asserts": "This deity is associated with this concept.",
        "evidence": "Curated; superseded in practice by DEVATA_ASSOCIATED_WITH.",
        "trust": "Would be TIER_D.",
        "example": "None. Unpopulated.",
        "counterexample": (
            "DEVATA_ASSOCIATED_WITH already carries this, generated from the concept "
            "lexicon related_devatas field, so a second predicate would double-count."
        ),
    },
    "ASSOCIATED_WITH_PHENOMENON": {
        "asserts": "This deity is associated with this natural phenomenon.",
        "evidence": "Curated.",
        "trust": "Would be TIER_D.",
        "example": "None. Unpopulated.",
        "counterexample": "Association is not personification; see PERSONIFIES.",
    },
    "ASSOCIATED_WITH_SUBSTANCE": {
        "asserts": "This deity is associated with this substance.",
        "evidence": "Curated.",
        "trust": "Would be TIER_D.",
        "example": "None. Unpopulated.",
        "counterexample": (
            "The Soma deity and the Soma substance are deliberately NOT joined by this "
            "edge. They are separate entities and their overlap is measured rather than "
            "asserted -- 467 mantras do both, and saying so is more informative than an "
            "edge claiming the two are related."
        ),
    },
    "TEXTUALLY_REUSED_AS": {
        "asserts": "This passage is reused as that one, directionally.",
        "evidence": "Would require a directional claim beyond textual identity.",
        "trust": "Would be TIER_B.",
        "example": "None. Unpopulated.",
        "counterexample": (
            "REUSES_TEXT_FROM carries 1,684 reuse edges already. Asserting a direction "
            "requires a chronology this graph does not have and must not imply."
        ),
    },
    "MUSICALIZED_AS": {
        "asserts": "This Rigvedic verse is sung as this Samavedic melody.",
        "evidence": "Would require a gana corpus.",
        "trust": "Would be TIER_A.",
        "example": "None. Unpopulated.",
        "counterexample": (
            "No gana or saman melodic corpus is ingested. The type exists so that adding "
            "one later does not require reinterpreting existing textual-reuse edges."
        ),
    },
    "ASCRIBES_TO_DEVATA": {
        "asserts": "This Atharvavedic ascription descriptor derives from this deity name.",
        "evidence": (
            "Would require a curated per-descriptor derivation table, NOT a morphological "
            "rule. Measured over all 324 descriptors after the apparatus filter: 78 are "
            "multi-word compounds and 42 begin mantrokta- ('the deity named in the "
            "mantra'), which names no deity at all. Of the 246 single-word descriptors, "
            "106 have a vrddhi-shaped first syllable, and a mechanical reverse-vrddhi "
            "against data/registry/devatas.yaml finds a candidate stem for only 23 of "
            "them. The other 83 fail for a systematic reason: that registry stores "
            "sandhi'd nominative singulars -- candramah for the stem candramas, savita "
            "for savitr, pusa for pusan, 'jataveda agnih' as one label -- so the "
            "derivation needs reverse nominative sandhi as well as reverse vrddhi."
        ),
        "trust": "Would be TIER_B, SOURCE_METADATA: the derivation is morphological.",
        "example": "None. Unpopulated in V3, and deliberately so.",
        "counterexample": (
            "Declared and not populated, because the blocking step is not morphological "
            "at all. A vrddhi shape does not distinguish 'belonging to deity X' from 'for "
            "purpose Y': bhaisajyam is healing, laksikam is the lac plant, yajnikam is the "
            "sacrifice, sammanasyam is concord, chandasam is the metres, parsnisuktam is "
            "the heel-hymn. Each needs a human decision on whether its base is a deity "
            "before an edge can exist. Worse, two bases the Atharvavedic index does treat "
            "as deities -- kama and vac -- are absent from devatas.yaml entirely, so a "
            "complete edge would have to mint new Devata nodes out of the Atharvaveda, "
            "reintroducing in subtler form the spurious-god hazard that the separate "
            "DevataAscription namespace exists to prevent. A conservative hand-curated "
            "table would reach roughly 23 descriptors and 138 of 571 hymn-scope rows "
            "(7.1% of descriptors), and its coverage would be a function of gaps in an "
            "unrelated registry rather than of the Atharvavedic index. So it is left as a "
            "documented gap. Meanwhile HAS_DEVATA_ASCRIPTION answers the ascription "
            "question directly, and 'which passages does the index ascribe to Agni' is "
            "answerable through the descriptor: agneyam carries 33 hymn-scope rows."
        ),
    },
    "CO_OCCURS_WITH": {
        "asserts": "These two deities are named in the same mantra, this many times.",
        "evidence": "The four-Veda theonym mention layer; minimum five shared mantras.",
        "trust": (
            "TIER_B, SANSKRIT, TEXTUAL_MENTION. `lift` is joint frequency against the "
            "product of the marginals, so 1.0 means 'no more than chance predicts'."
        ),
        "example": (
            "Mitra and Varuna share 271 mantras at lift 13.21 across all four Vedas -- the "
            "canonical pair, and now a measured one."
        ),
        "counterexample": (
            "Frequency is not association. Agni and Indra share 126 mantras and co-occur "
            "at lift 0.18, roughly one fifth of chance: the two commonest gods in the "
            "corpus are systematically *not* named together. A reader taking the raw count "
            "would conclude the opposite."
        ),
    },
}


def _measure(session: Any) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for record in session.run(
        "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS n, "
        "collect(DISTINCT r.quality_tier)[0..4] AS tiers, "
        "collect(DISTINCT r.evidence_basis)[0..4] AS bases, "
        "collect(DISTINCT r.attribution_precision)[0..4] AS precisions ORDER BY n DESC"
    ):
        rows[str(record["t"])] = {
            "count": record["n"],
            "tiers": sorted(x for x in record["tiers"] if x),
            "bases": sorted(x for x in record["bases"] if x),
            "precisions": sorted(x for x in record["precisions"] if x),
        }
    return rows


def _endpoints(name: str) -> str:
    """The declared endpoints, read from the COMPOSED declaration.

    ``RELATIONSHIP_SIGNATURES`` alone is the domain layer's slice. Reading it as though it
    were the whole contract printed "not declared" beside HAS_DEVATA, CONTAINS,
    EXACT_PARALLEL_OF and 36 others in a published reference, while the composed declaration
    covered every one of them and the scorecard's gate read 0. Same blind spot the scorecard
    had, still live in the document a reader consults to learn what the contract is.
    """
    signature = all_endpoint_signatures().get(name)
    if signature is None:
        return "— *(not declared)*"
    domain, target = signature
    return f"`{' \\| '.join(sorted(domain))}` → `{' \\| '.join(sorted(target))}`"


def build(session: Any) -> str:
    live = _measure(session)
    node_counts = {
        str(record["l"]): record["n"]
        for record in session.run(
            "MATCH (n) UNWIND labels(n) AS l RETURN l, count(*) AS n ORDER BY n DESC"
        )
    }
    total_nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    total_rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]

    # Every layer's declaration, composed. See _endpoints above for what reading one slice
    # of it cost: a self-audit section asserting 39 live predicates were undeclared.
    declared = all_declared_relationship_types()
    live_types = set(live)
    # Prose definitions are written for the domain contract, so the documentation gap is
    # still measured against that set rather than against all 90.
    undocumented = sorted(set(DOMAIN_RELATIONSHIP_TYPES) - set(DEFINITIONS))
    undeclared_live = sorted(live_types - declared)
    declared_empty = sorted(declared - live_types)

    out: list[str] = []
    add = out.append
    add("# VedaGraph Ontology Reference V3\n")
    add(
        "Generated by `scripts/generate_ontology_reference.py` from "
        "`vedagraph.domain.ontology` and the live database. Every count below is measured, "
        "not typed. Re-run it rather than editing it.\n"
    )
    add(
        f"**Live graph:** {total_nodes:,} nodes, {total_rels:,} relationships, "
        f"{len(live_types)} relationship types in use, {len(declared)} declared.\n"
    )

    add("\n## How to read a tier\n")
    add(
        "| tier | means |\n|---|---|\n"
        "| `TIER_A` | a source states this |\n"
        "| `TIER_B` | reproducibly derived from something a source states |\n"
        "| `TIER_C` | model-extracted and independently reviewed and accepted |\n"
        "| `TIER_D` | a candidate, an interpretation, or an unreviewed model proposal |\n"
    )
    add(
        "\n`evidence_basis` is an orthogonal axis and answers a different question — *which "
        "text* the evidence is in: `SANSKRIT`, `TRANSLATION`, `MIXED`, `STRUCTURAL` (the "
        "corpus as printed), `SOURCE_METADATA` (a traditional index), or "
        "`MODEL_INTERPRETATION`. A rule over a stored translation is exactly as "
        "reproducible as one over stored Sanskrit, which is why tier cannot carry this.\n"
    )
    add(
        "\n`attribution_precision` answers a third: `PER_PASSAGE` (the source names this "
        "verse), `CONTAINER_INHERITED` (the claim is the hymn's, projected onto its "
        "verses), or `TEXTUAL_MENTION` (the verse names the entity in its own words). "
        "These are three different questions and the graph refuses to collapse them.\n"
    )

    add("\n## Relationship types\n")
    for name in sorted(declared | live_types):
        if name == "QA_ISSUE_ON":
            continue
        info = DEFINITIONS.get(name)
        stats = live.get(name)
        add(f"\n### `{name}`\n")
        add(f"- **endpoints:** {_endpoints(name)}")
        if stats:
            add(f"- **edges:** {stats['count']:,}")
            add(f"- **tiers present:** {', '.join(stats['tiers']) or '—'}")
            add(f"- **evidence bases:** {', '.join(stats['bases']) or '—'}")
            add(f"- **precision values:** {', '.join(stats['precisions']) or '—'}")
        elif name in UNPOPULATED_BY_DESIGN:
            add(
                "- **edges:** 0 — *declared and unpopulated by design.* "
                + UNPOPULATED_BY_DESIGN[name]
            )
        else:
            add("- **edges:** 0 — declared, not populated, and not documented as deliberate.")
        if info:
            add(f"- **asserts:** {info['asserts']}")
            add(f"- **evidence required:** {info['evidence']}")
            add(f"- **trust rule:** {info['trust']}")
            add(f"- **example:** {info['example']}")
            add(f"- **counterexample — what it does NOT mean:** {info['counterexample']}")
        else:
            add(
                "- *No prose definition yet. This is a gap in this document, not in the "
                "contract: the endpoint signature above is enforced at build time.*"
            )

    add("\n## Product and internal labels\n")
    add(
        f"Product labels ({len(PRODUCT_LABELS)}): "
        + ", ".join(
            f"`{label}` ({node_counts.get(label, 0):,})" for label in sorted(PRODUCT_LABELS)
        )
    )
    add(
        f"\n\nInternal labels ({len(INTERNAL_LABELS)}), excluded from knowledge traversal by "
        "the single filter `vedagraph.domain.ontology.PRODUCT_NODE_FILTER`: "
        + ", ".join(
            f"`{label}` ({node_counts.get(label, 0):,})" for label in sorted(INTERNAL_LABELS)
        )
    )

    add("\n\n## Contract self-audit\n")
    add(
        f"- relationship types declared but **not populated**: {len(declared_empty)} "
        f"{'— ' + ', '.join(f'`{x}`' for x in declared_empty) if declared_empty else ''}"
    )
    add(
        f"- relationship types **live but not declared** by the V2/V3 contract: "
        f"{len(undeclared_live)} "
        f"{'— ' + ', '.join(f'`{x}`' for x in undeclared_live) if undeclared_live else ''}"
    )
    add(
        f"- declared types with **no prose definition** in this document: "
        f"{len(undocumented)} "
        f"{'— ' + ', '.join(f'`{x}`' for x in undocumented) if undocumented else ''}"
    )
    add(
        "\nThe declared set is composed from every layer that declares one — domain, corpus, "
        "campaign and enrichment — so a predicate introduced by any of them is inside the "
        "contract. This section used to report 39 live predicates as undeclared, including "
        "`HAS_DEVATA` and `CONTAINS`, because it read the domain layer's slice as though it "
        "were the whole contract."
    )
    if declared_empty:
        with_reason = len(set(declared_empty) & set(UNPOPULATED_BY_DESIGN))
        add(
            f"\nOf the {len(declared_empty)} declared-but-unpopulated types, "
            f"{with_reason} {'carries' if with_reason == 1 else 'carry'} a stated reason in "
            "`UNPOPULATED_BY_DESIGN`. The rest are declarations whose layer was built and "
            "whose population is zero, which is architecture without a rationale attached — "
            "recorded here rather than presented as intent."
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    with driver.session() as session:
        text = build(session)
    driver.close()
    if args.check:
        print(text[:2000])
        print(f"\n--check: {len(text.splitlines())} lines, nothing written")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
