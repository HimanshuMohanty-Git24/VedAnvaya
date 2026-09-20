"""Turn a corpus's own traditional index into graph-ready attribution assertions.

Two Vedas acquired an attribution layer in V3 and neither of them needed a model:

*The Yajurveda* had one all along. ``data/canonical/yajurveda_vsm_v1/traditional_metadata.jsonl``
has carried **2,240 source-stated rsi assertions covering 1,960 of its 1,975 mantras**
since ingestion, lifted from the edition's own रिषिसूची with a per-line locator, and
nothing read them. Two places asserted in prose that they did not exist. So every report
in this repository that said attribution was Rigveda-only was measuring the reader.

*The Atharvaveda* was acquired in this pass from Whitney's printed Brhatsarvanukramani
excerpts: **3,270 assertions over 563 hymns**, gated against the stated verse count of each
hymn, with 17 hymns refused where the count disagreed with our text.

The two are shaped differently and the difference is the whole reason this script is
parameterised rather than copied. The Yajurvedic index states a **mantra range**
(``आभूतिः १९.४-९``), which the ingestion expanded, so its scope is ``MANTRA_RANGE`` and its
provenance ``SOURCE_EXPLICIT`` -- ``PER_PASSAGE`` attribution, the strictest class, and
strictly better than 95.5% of the Rigveda's own rsi attribution, which is sukta-inherited.
Whitney's brackets are stated for a **hymn**, so their scope is ``WHOLE_PASSAGE`` and a
projection onto mantras is ``CONTAINER_INHERITED``. Collapsing those two would undo the
distinction the V2 pass spent itself restoring.

**Identity stays in its own namespace, per corpus, deliberately.** Values are the index's
own strings and are not resolved against ``data/registry/rishis.yaml``. Measured, only
**8 of 228** Yajurvedic names equal a Rigvedic registry label, because that registry stores
Sarvanukramani patronymic compounds (``rāhūgaṇo gotamaḥ``) where these indices give bare
names (``गोतमः``). A further 64 appear as one word inside a Rigvedic compound, which is a
candidate identity signal and not identity -- one of them matches inside a Rigvedic entry
that is itself a *dual*. Merging on either signal is an alias-level error that per-row
sampling would not catch: ``प्रजापतिः`` alone carries 222 assertions.

**Atharvavedic devata values are not deity names and are not projected as Devata nodes.**
Whitney prints ``āgneyam``, ``mantroktadevatyam``, ``bhāiṣajyāyuṣyam uta
mantroktāuṣadhidevatākam`` -- adjectival ascription *descriptors*, 324 of them after the
apparatus filter below, meaning "belonging to Agni", "having the deity named in the
mantra". Unioning them with the Rigvedic deity set would add 324 spurious gods and make
any deity census meaningless.

**The descriptor set is filtered, and the filter is recorded.** The first harvest of
Whitney's brackets took the printed apparatus with the ascriptions, because the bracket
interleaves them in one period-delimited run with no field markers: the graph asserted
that the deity-ascription of AVS 18.4 was ``ekonanavati`` -- eighty-nine -- across 90
passages, that AVS 18.3's was ``saptatis tryadhikā`` -- seventy-three -- across 74, and
that AVS 19.38's was ``a-d``, a pāda address. ``scripts/build_atharvaveda_anukramani.py``
now classifies every head token and refuses the apparatus with a named reason; the
reasons are carried per hymn in ``traditional_metadata_provenance.jsonl`` and republished
in the generated registry's ``rejections`` block, so a later pass cannot re-add a value
believing it was never seen. Nine ascriptions that the scan had broken into siblings are
merged onto the spelling the page prints -- see :data:`AV_ASCRIPTION_OCR_SIBLINGS`.
They are kept as their own entity type with their own namespace and their own label, so
"which passages does the Atharvavedic index ascribe to Agni" stays answerable while
"how many deities are in this graph" stays true.

Usage::

    python scripts/build_anukramani_knowledge_layer.py            # every configured corpus
    python scripts/build_anukramani_knowledge_layer.py --veda AV
    python scripts/build_anukramani_knowledge_layer.py --check    # measure, write nothing
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import pathlib
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Final

import orjson
import yaml

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.transliteration import DevanagariToIAST  # noqa: E402

SCHEMA_VERSION: Final = "1.0.0"
RV_RISHI_REGISTRY: Final = PROJECT_ROOT / "data" / "registry" / "rishis.yaml"

#: ``scope_type`` in the canonical artifact -> the graph's ``scope_origin`` vocabulary.
#: ``WHOLE_PASSAGE`` on a hymn is a container statement and grades ``CONTAINER_INHERITED``;
#: the other two name the verse and grade ``PER_PASSAGE``.
SCOPE_ORIGIN: Final[dict[str, str]] = {
    "SINGLE_MANTRA": "SINGLE_MANTRA",
    "MANTRA_RANGE": "MANTRA_RANGE",
    "WHOLE_PASSAGE": "SUKTA_WIDE",
}

#: Provenance class per scope. A container statement is a source-derived *scope*, not a
#: source statement about the verse.
PROVENANCE_CLASS: Final[dict[str, str]] = {
    "SINGLE_MANTRA": "SOURCE_EXPLICIT",
    "MANTRA_RANGE": "SOURCE_EXPLICIT",
    "SUKTA_WIDE": "SOURCE_DERIVED_SCOPE",
}

_TRANSLITERATOR = DevanagariToIAST()


#: Values that are the SAME printed ascription broken into siblings by the scan, keyed
#: variant -> the spelling the page actually prints.
#:
#: Each entry below was read off the pinned ``Page:``-namespace snapshot, and each is kept
#: to two evidence tests, both of which must hold:
#:
#: 1. the variant is not a Sanskrit word and the target is (``bahti``/``baku`` for ``bahu``
#:    in *bahudevatya*, "many-deitied"; ``tn``/``vi`` for a broken final ``m``; ``h`` for
#:    ``k``; ``f`` for ``p``; ``dtvatyam`` for ``devatyam``); and
#: 2. the target already stands in this registry as an independently printed value, so the
#:    merge joins two readings of one string rather than inventing a correction.
#:
#: Test 2 is why this table is short. ``ādityadevatyatn`` (ii. 32) and ``balāsadevatyatn``
#: (vi. 14) are the same broken-``m`` defect, but neither has a correctly-spelled sibling
#: in the printed set, so correcting them would be an emendation and they are left as
#: printed. A variant that repeats consistently across several hymns is treated as printed
#: orthography and never merged: ``duḥsvapnanāçanadevatya`` stands at xvi. 5-7,
#: ``ādityadevatya`` at xvi. 3-4 -- book xvi drops the final ``m``, and that is the page,
#: not the scanner. Likewise ``agnīṣomīyam``/``āgnīṣomīyam`` (a vrddhi that the taddhita
#: does not require) and ``vārṣabham``/``ārṣabham`` (vṛṣabha vs ṛṣabha) are distinct
#: legitimate forms and are NOT merged. Nor is ``mantrokta drvatyāḥ`` (xiii. 4) merged onto
#: ``mantroktādevatyāḥ`` (xix. 69): reaching one from the other needs a word break closed
#: AND a linking vowel chosen, which is two independent decisions, so it stays as printed.
AV_ASCRIPTION_OCR_SIBLINGS: Final[dict[str, str]] = {
    # The three-way split named by the audit: AVS 18.1/18.3 print `bahu`, 18.4 `bahti`,
    # 18.2 `baku`. One ascription, one node.
    "yamadevatyam mantroktabahtidevatyaṁ ca": "yamadevatyam mantroktabahudevatyaṁ ca",
    "yamadevatyam mantroktabakudevatyaṁ ca": "yamadevatyam mantroktabahudevatyaṁ ca",
    # Broken final `m`, set as `tn` or `vi`.
    "mantroktadevatyatn": "mantroktadevatyam",
    "mantroktadevatyavi": "mantroktadevatyam",
    "vānaspatyatn": "vānaspatyam",
    "brahmagavīdevatyatn": "brahmagavīdevatyam",
    # `f` for `p`, `h` for `k`, `t` for `n`, `dtvatyam` for `devatyam`, and the `n` lost
    # from the `gn` conjunct (`āindrāga` is not a word; vi. 5 prints `āindrāgnam`).
    "vānasfatyam": "vānaspatyam",
    "smaradevatāham": "smaradevatākam",
    "yahṣmanāçanadāivatam": "yakṣmanāçanadāivatam",
    "āgteyam uta mantroktadevatyam": "āgneyam uta mantroktadevatyam",
    "āindrāgam": "āindrāgnam",
    "cāndramasam uta mantroktadtvatyam": "cāndramasam uta mantroktadevatyam",
}

#: The same defect class in the **Chandas** namespace, keyed variant -> printed spelling.
#:
#: Found by enumerating all 578 values rather than by eye: every pair at edit distance 1
#: was listed and classified (91 pairs), and only these pass three tests --
#:
#: 1. one mechanical change (a diacritic, a broken ligature, a dropped or spurious letter);
#: 2. the variant is not a form the tradition uses, and the target is independently
#:    attested in this same index; and
#: 3. **the variant occurs in exactly one hymn.** A spelling that recurs across independent
#:    brackets is the page's, not the scanner's, so `jagati` (iv. 30 and xiv. 1),
#:    `paroṣṇi` (vi. 2 and xi. 9) and `çin̄kumatī` are left alone -- ``METRE_STEM`` already
#:    admits `[cç][ai]n̄kumat`, so the second spelling was known to be printed.
#:
#: Refused, and named so the refusals are on record. **Different metres, not variants:**
#: `ārcī`/`ārṣī` (of the *ṛc* versus of the *ṛṣi*) at three pairs; `paroṣṇih`/`puroṣṇih`
#: and `parābṛhatī`/`purābṛhatī` (`parā-` and `puro-` are both real prefixes); and 22 pairs
#: differing only in a pāda or avasāna count (`3-p.`/`5-p.`, `3-av. 6-p.`/`3-av. 7-p.`),
#: which is the whole content of the specification. **Printed orthography, not corruption:**
#: 19 pairs differing only in whether a compound is set with a space -- `virāḍ jagatī` (9)
#: beside `virāḍjagatī` (15), `virāṭ prastārapan̄kti` (4) beside `virāṭprastārapan̄kti` (4);
#: both settings are well attested and neither is an error. **Two decisions at once:**
#: `3-p. sāmny bṛhatī` (either `sāmnī bṛhatī` or a vowel-initial metre mis-set),
#: `purauṣṇih`/`purāuṣṇih` (guṇa versus vrddhi), `parabṛhatī`/`parābṛhatī`,
#: `skandhogrīvābṛhatī`/`skandhogrīvībṛhatī`, and `upariṣṭādvirāḍbrṛatT`, which needs a
#: transposition, an inserted `h` and a `T`-for-`ī` before it reads `upariṣṭādvirāḍbṛhatī`.
AV_CHANDAS_OCR_SIBLINGS: Final[dict[str, str]] = {
    # Ligature break: `bh` followed by a spurious repeat of its own `h` (vii. 44). Note
    # this is NOT a general doubled-letter rule -- 59 values carry a legitimate sandhi
    # geminate (`kakummatī`, `uṣṇiggarbhā`, `triṣṭubbṛhatī`, `nicṛjjagatī`), and folding
    # those would destroy real metre names.
    "bhurik triṣṭubhh": "bhurik triṣṭubh",
    # Missing diacritic on a fixed metre name.
    "2-p. sāmni bṛhatī": "2-p. sāmnī bṛhatī",
    "3-p. prajāpatyā bṛhatī": "3-p. prājāpatyā bṛhatī",
    "3-p. virāḍgayatrī": "3-p. virāḍgāyatrī",
    "bhūrij": "bhurij",
    "brhatīgarbhā virāj": "bṛhatīgarbhā virāj",
    "dāivi pan̄kti": "dāivī pan̄kti",
    "gāyatri": "gāyatrī",
    "nicṛtpathypan̄kti": "nicṛtpathyāpan̄kti",
    "pathyapan̄kti": "pathyāpan̄kti",
    "pathyābṛhati": "pathyābṛhatī",
    "traiṣṭubham": "trāiṣṭubham",
    "trāiṣtubham": "trāiṣṭubham",
    "upariṣṭadbṛhatī": "upariṣṭādbṛhatī",
    "āsuri triṣṭubh": "āsurī triṣṭubh",
    # Letter substituted: `k` for `h`, `tk` for `th`, a spurious `j`, a comma for the
    # period in the pāda-count abbreviation.
    "bkuriktriṣṭubh": "bhuriktriṣṭubh",
    "patkyāpan̄kti": "pathyāpan̄kti",
    "3-p. virāḍ gājyatrī": "3-p. virāḍ gāyatrī",
    "3-p, yavamadhyā gāyatrī": "3-p. yavamadhyā gāyatrī",
    # Letter dropped: the `v` of the avasāna abbreviation (`3-a.` stands once against
    # `3-av.` 49 times), a final visarga, the `ṭ` of `anuṣṭubh`, the `d` of `upariṣṭād`.
    "3-a. 6-p. jagatī": "3-av. 6-p. jagatī",
    "4-p. uṣṇi": "4-p. uṣṇih",
    "anuṣubh": "anuṣṭubh",
    "purastājjyots": "purastājjyotis",
    "upariṣṭāvirāḍ bṛhatī": "upariṣṭādvirāḍ bṛhatī",
    "upariṣṭāvirāḍbṛhatī": "upariṣṭādvirāḍbṛhatī",
}

#: Rejection reasons from the corpus builder's ``rejected_from_devata_slot`` ledger that
#: name a value which USED to stand in this registry as a product-visible ascription node.
#: These are surfaced in the generated registry so the rejection is on the record next to
#: the entities, not only in the corpus provenance sidecar. ``verse_count_routed_to_
#: alignment_gate`` is deliberately excluded: it fires on every ordinary ``tṛcam`` and is
#: normal routing, not a rejection of something that was ever emitted.
PUBLISHED_REJECTION_REASONS: Final[frozenset[str]] = frozenset(
    {
        "head_token_is_verse_count",
        "head_token_is_verse_count_note",
        "head_token_is_pada_reference",
        "head_token_is_corrupt_metre",
        "head_token_is_metrical_apparatus",
        "head_token_without_separator_not_a_devata",
        "head_token_not_a_devata",
    }
)


@dataclass(frozen=True)
class CorpusConfig:
    """One corpus's index, and how its identity namespaces are named."""

    veda: str
    work_id: str
    corpus_dir: str
    knowledge_dir: str
    source_artifact_id: str
    #: predicate -> (registry filename, namespace tag, entity-key prefix)
    namespaces: dict[str, tuple[str, str, str]]
    #: True when the values are Devanagari and want transliterating for display.
    devanagari: bool
    #: Predicates whose values are ascription descriptors rather than entity names.
    descriptor_predicates: frozenset[str]
    notes: str
    #: predicate -> {scan variant: printed spelling}. Empty for a corpus with no scan.
    ocr_siblings: dict[str, dict[str, str]] = field(default_factory=dict)


CORPORA: Final[tuple[CorpusConfig, ...]] = (
    CorpusConfig(
        veda="YV",
        work_id="VG:WORK:YV:VSM",
        corpus_dir="yajurveda_vsm_v1",
        knowledge_dir="yajurveda_deterministic_v1",
        source_artifact_id="WIKISOURCE_SA.YV.VSM.RSISUCI",
        namespaces={
            "HAS_RISHI": ("rishis_yv.yaml", "YV_VSM_RSISUCI", "VG:RISHI:YV:"),
        },
        devanagari=True,
        descriptor_predicates=frozenset(),
        notes=(
            "Rsi only. The Madhyandina Sarvanukramana-sutra, which would give devata and "
            "chandas, is pratika-keyed sutra prose and is refused for machine resolution; "
            "Rigvedic practice does not transfer to the Yajurveda. The Yajurveda therefore "
            "keeps a source-stated ABSENCE of metre rather than a borrowed presence."
        ),
    ),
    CorpusConfig(
        veda="AV",
        work_id="VG:WORK:AV:SAU",
        corpus_dir="atharvaveda_saunaka_digital_working_v1",
        knowledge_dir="atharvaveda_deterministic_v1",
        source_artifact_id="WIKISOURCE_WHITNEY_AV.BRHATSARVANUKRAMANI",
        namespaces={
            "HAS_RISHI": ("rishis_av.yaml", "AV_WHITNEY_ANUKRAMANI", "VG:RISHI:AV:"),
            "HAS_DEVATA": (
                "devata_ascriptions_av.yaml",
                "AV_WHITNEY_ANUKRAMANI",
                "VG:ASCRIPTION:AV:",
            ),
            "HAS_CHANDAS": ("chandas_av.yaml", "AV_WHITNEY_ANUKRAMANI", "VG:CHANDAS:AV:"),
        },
        devanagari=False,
        # See the module docstring: `agneyam` is "belonging to Agni", not "Agni".
        descriptor_predicates=frozenset({"HAS_DEVATA"}),
        ocr_siblings={
            "HAS_DEVATA": AV_ASCRIPTION_OCR_SIBLINGS,
            "HAS_CHANDAS": AV_CHANDAS_OCR_SIBLINGS,
        },
        notes=(
            "Kanda 20 (143 hymns / 958 mantras) contributes nothing: Whitney excluded it. "
            "Kanda 15 yields no rsi and no devata at all -- Lanman states the Vratya book "
            "'is treated as a unit in that no seer is named for the whole nor for any "
            "part of it'. Any per-Veda coverage figure must carry the K20 gap explicitly "
            "or the Atharvaveda will look uniformly attributed when a sixth of it is "
            "untouched."
        ),
    ),
)


def fold_visarga(value: str) -> str:
    """Fold a trailing visarga, in Devanagari or in IAST.

    Applied on both sides -- to index values and to Rigvedic registry labels when
    measuring name overlap -- so it must handle both spellings. Folding only the
    Devanagari form once reported the overlap as 1 name instead of 8.
    """
    # The first character is DEVANAGARI SIGN VISARGA, not a colon; both
    # spellings are folded because this runs over Devanagari values and IAST labels.
    return value.rstrip("ः").rstrip("ḥ").strip()  # noqa: RUF001


def readable_slug(text: str) -> str:
    """The human-readable, diacritic-stripped part of a key. Not unique on its own."""
    decomposed = unicodedata.normalize("NFD", text)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    out: list[str] = []
    previous_hyphen = False
    for ch in ascii_only.upper():
        if ch.isalnum():
            out.append(ch)
            previous_hyphen = False
        elif not previous_hyphen:
            out.append("-")
            previous_hyphen = True
    return "".join(out).strip("-")


def entity_key(prefix: str, iast: str) -> str:
    """A stable, collision-proof key.

    The house convention strips diacritics -- ``vasiṣṭhaḥ`` becomes ``VASISTHAH`` -- and on
    these indices that convention silently merges **different referents**: bhāradvāja with
    bharadvāja, āgastya with agastya, āṅgirasa with aṅgirasa, each pair being a patronymic
    and the man it derives from. Two more collide on a palatal/retroflex and a vowel
    length. So a four-hex fingerprint of the full IAST string is appended to **every** key,
    not only to colliding ones: appending it selectively would mean that adding a new value
    later could change an existing key.
    """
    fingerprint = hashlib.blake2b(iast.encode("utf-8"), digest_size=2).hexdigest().upper()
    return f"{prefix}{readable_slug(iast)}-{fingerprint}"


def _read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [orjson.loads(raw) for raw in path.read_bytes().split(b"\n") if raw.strip()]


def passage_index(corpus_dir: pathlib.Path) -> dict[str, tuple[str, str, str]]:
    """passage uuid -> (canonical_key, citation, entity_type), for every passage.

    Every passage, not only mantras: an Atharvavedic hymn-scope assertion points at a
    HYMN, and an index restricted to mantras would silently drop 1,577 of 3,270 rows and
    report a clean partial load.
    """
    index: dict[str, tuple[str, str, str]] = {}
    for record in _read_jsonl(corpus_dir / "passages.jsonl"):
        index[record["entity_id"]] = (
            record["canonical_key"],
            record.get("canonical_citation", record["canonical_key"]),
            str(record.get("entity_type", "")),
        )
    return index


def child_index(
    passages: dict[str, tuple[str, str, str]],
) -> dict[str, tuple[tuple[str, str, str], ...]]:
    """container canonical_key -> its immediate leaf verses.

    Containment is read off the canonical key rather than a parent pointer, because these
    corpora carry no ``parent_id``: the key is hierarchical, so the hymn
    ``VG:AV:SAU:K01:S001`` contains exactly those mantras whose key is that string plus a
    verse segment. Deterministic, and it cannot attach a verse to the wrong hymn.
    """
    grouped: dict[str, list[tuple[str, str, str]]] = collections.defaultdict(list)
    for key, citation, kind in passages.values():
        if kind != "MANTRA":
            continue
        container = key.rsplit(":", 1)[0]
        grouped[container].append((key, citation, kind))
    return {key: tuple(sorted(value)) for key, value in grouped.items()}


def rv_registry_names() -> dict[str, str]:
    """Visarga-folded Rigvedic rsi label -> its key. Used to *measure* overlap only."""
    if not RV_RISHI_REGISTRY.exists():
        return {}
    document = yaml.safe_load(RV_RISHI_REGISTRY.read_text(encoding="utf-8"))
    return {
        fold_visarga(str(row.get("preferred_label", ""))): str(row["entity_key"])
        for row in document.get("entities", [])
    }


def rejection_ledger(corpus_dir: pathlib.Path) -> list[dict[str, Any]]:
    """Every value the corpus builder refused to call an ascription, with its reason.

    Read from ``traditional_metadata_provenance.jsonl`` and published into the generated
    registry so the rejection sits beside the entities it is not one of. Without it, a
    filter is indistinguishable from a parser that never met the value, and the next pass
    re-adds ``ekonanavati`` -- eighty-nine -- as the deity-ascription of AVS 18.4.
    """
    grouped: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for record in _read_jsonl(corpus_dir / "traditional_metadata_provenance.jsonl"):
        for rejection in record.get("rejected_from_devata_slot") or []:
            reason = str(rejection.get("reason", ""))
            if reason not in PUBLISHED_REJECTION_REASONS:
                continue
            grouped[(str(rejection.get("value", "")), reason)].append(str(record["citation"]))
    return [
        {
            "rejected_value": value,
            "reason": reason,
            "printed_at": sorted(set(citations)),
            "occurrences": len(citations),
        }
        for (value, reason), citations in sorted(grouped.items())
    ]


def build(config: CorpusConfig) -> dict[str, Any]:
    corpus_dir = PROJECT_ROOT / "data" / "canonical" / config.corpus_dir
    rows = _read_jsonl(corpus_dir / "traditional_metadata.jsonl")
    if not rows:
        return {"config": config, "skipped": "no traditional_metadata.jsonl rows"}
    passages = passage_index(corpus_dir)
    children = child_index(passages)
    rv_names = rv_registry_names()
    rejections = rejection_ledger(corpus_dir)

    # ---- entity pass, per predicate namespace ---------------------------------------
    variants: dict[str, dict[str, set[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(set)
    )
    occurrences: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    merged_siblings: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for row in rows:
        predicate = str(row["predicate"])
        if predicate not in config.namespaces:
            continue
        raw_value = str(row["value"]).strip()
        folded = fold_visarga(raw_value)
        # An OCR sibling is folded onto the spelling the page prints, and the variant is
        # kept in `source_variants`. It is a merge of two readings of ONE printed string,
        # not a normalisation across spellings: three nodes carrying 136, 90 and 61
        # passages were one ascription that the scan broke in the middle of `bahu`.
        canonical = config.ocr_siblings.get(predicate, {}).get(folded)
        if canonical is not None:
            merged_siblings[predicate][folded] = canonical
            folded = canonical
        variants[predicate][folded].add(raw_value)
        occurrences[predicate][folded] += 1

    registries: dict[str, list[dict[str, Any]]] = {}
    key_by_value: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for predicate, (_filename, namespace, prefix) in config.namespaces.items():
        entities: list[dict[str, Any]] = []
        for folded in sorted(variants[predicate]):
            iast = _TRANSLITERATOR.transliterate(folded) if config.devanagari else folded
            key = entity_key(prefix, iast)
            key_by_value[predicate][folded] = key
            entities.append(
                {
                    "entity_key": key,
                    "entity_type": (
                        "DEVATA_ASCRIPTION"
                        if predicate in config.descriptor_predicates
                        else predicate.removeprefix("HAS_")
                    ),
                    "registry_namespace": namespace,
                    "preferred_label": folded,
                    "label_iast": iast,
                    "normalized_name": fold_visarga(iast),
                    "occurrence_count": occurrences[predicate][folded],
                    "source_variants": sorted(variants[predicate][folded]),
                    "ocr_variants_merged": sorted(
                        variant
                        for variant, target in merged_siblings[predicate].items()
                        if target == folded
                    ),
                    "is_ascription_descriptor": predicate in config.descriptor_predicates,
                    "rv_registry_name_match": (
                        rv_names.get(folded, "") or rv_names.get(fold_visarga(iast), "")
                        if predicate == "HAS_RISHI"
                        else ""
                    ),
                }
            )
        duplicates = [
            key
            for key, count in collections.Counter(e["entity_key"] for e in entities).items()
            if count > 1
        ]
        if duplicates:
            raise SystemExit(f"{config.veda}/{predicate}: colliding entity keys {duplicates}")
        registries[predicate] = entities

    # ---- assertion pass --------------------------------------------------------------
    assertions: list[dict[str, Any]] = []
    unresolved = 0
    scope_counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        predicate = str(row["predicate"])
        if predicate not in config.namespaces:
            continue
        scope = row.get("scope") or {}
        identity = passages.get(str(scope.get("passage_id")))
        if identity is None:
            unresolved += 1
            continue
        canonical_key, citation, entity_type = identity
        scope_type = str(scope.get("scope_type", "SINGLE_MANTRA"))
        scope_origin = SCOPE_ORIGIN.get(scope_type, "SINGLE_MANTRA")
        folded = fold_visarga(str(row["value"]).strip())
        sibling_of = config.ocr_siblings.get(predicate, {}).get(folded)
        if sibling_of is not None:
            folded = sibling_of
        object_key = key_by_value[predicate][folded]
        scope_counts[f"{scope_origin}->{entity_type}"] += 1

        # A container-scoped ascription is emitted for the container *and* for each verse
        # inside it. Both are needed and neither substitutes for the other: without the
        # verse rows "which Atharvavedic mantras have a rsi" answers zero, and without the
        # container row the fact that one bracket covers fifty verses is lost. The verse
        # rows carry SUKTA_WIDE, which the graph grades CONTAINER_INHERITED, so a query
        # that must not overstate can still have the strict count.
        targets: list[tuple[str, str, str]] = [(canonical_key, citation, entity_type)]
        if scope_origin == "SUKTA_WIDE":
            targets += [
                (child_key, child_citation, child_type)
                for child_key, child_citation, child_type in children.get(canonical_key, ())
            ]

        for target_key, target_citation, target_type in targets:
            inherited = target_key != canonical_key
            assertions.append(
                {
                    "assertion_id": hashlib.blake2b(
                        f"{target_key}|{predicate}|{object_key}".encode(), digest_size=16
                    ).hexdigest(),
                    "citation": target_citation,
                    "confidence": 1.0,
                    "object_id": "",
                    "object_key": object_key,
                    # A descriptor predicate is renamed in the artifact, not only in the
                    # loader. `agneyam` is not a deity, so a row saying HAS_DEVATA about it
                    # is false in the artifact as well as in the graph -- and the shared
                    # attribution loader would try to match it against a `:Devata` node,
                    # find nothing, and report a clean load of 5,674 edges it never made.
                    "predicate": (
                        "HAS_DEVATA_ASCRIPTION"
                        if predicate in config.descriptor_predicates
                        else predicate
                    ),
                    "source_predicate": predicate,
                    "provenance_class": PROVENANCE_CLASS[scope_origin],
                    "resolution_method": (
                        "VERBATIM_SOURCE_STRING_VISARGA_FOLDED_OCR_SIBLING_MERGED"
                        if sibling_of is not None
                        else "VERBATIM_SOURCE_STRING_VISARGA_FOLDED"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "scope_origin": scope_origin,
                    "scope_container_key": canonical_key if inherited else "",
                    "source_artifact_id": config.source_artifact_id,
                    "source_assertion_id": str(row.get("assertion_id", "")),
                    "source_id": str(row.get("source_id", "")),
                    "source_label": str(row["value"]).strip(),
                    "source_locator": str(row.get("source_locator", "")),
                    "subject_id": str(scope.get("passage_id")) if not inherited else "",
                    "subject_key": target_key,
                    "subject_entity_type": target_type,
                    "work_id": config.work_id,
                }
            )

    pairs = {(a["subject_key"], a["predicate"], a["object_key"]) for a in assertions}
    mantras = {key for key, (_c, _t, kind) in passages.items() if kind == "MANTRA"}
    return {
        "config": config,
        "registries": registries,
        "assertions": assertions,
        "rejections": rejections,
        "stats": {
            "source_rows": len(rows),
            "assertions_written": len(assertions),
            "ocr_sibling_variants_merged": {
                predicate: len(mapping) for predicate, mapping in sorted(merged_siblings.items())
            },
            "rejected_values_published": len(rejections),
            "rejected_values_by_reason": dict(
                sorted(collections.Counter(r["reason"] for r in rejections).items())
            ),
            "distinct_triples": len(pairs),
            "duplicates_collapsed_by_merge": len(assertions) - len(pairs),
            "unresolved_passage_ids": unresolved,
            "scope_to_entity_type": dict(sorted(scope_counts.items())),
            "by_predicate": dict(
                collections.Counter(a["predicate"] for a in assertions).most_common()
            ),
            "mantras_in_corpus": len(mantras),
            "entities_by_predicate": {p: len(e) for p, e in registries.items()},
            "distinct_values_raw": len({str(r["value"]).strip() for r in rows}),
            "multi_variant_entities": {
                p: sum(1 for e in entities if len(e["source_variants"]) > 1)
                for p, entities in registries.items()
            },
            "rishi_names_also_in_rv_registry": sum(
                1 for e in registries.get("HAS_RISHI", []) if e["rv_registry_name_match"]
            ),
        },
    }


def write(result: dict[str, Any]) -> None:
    config: CorpusConfig = result["config"]
    out_dir = PROJECT_ROOT / "data" / "knowledge" / config.knowledge_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "knowledge_assertions.jsonl").write_text(
        "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) for row in result["assertions"]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for predicate, entities in result["registries"].items():
        filename, namespace, _prefix = config.namespaces[predicate]
        descriptor = predicate in config.descriptor_predicates
        header = (
            f"# {config.veda} {predicate.removeprefix('HAS_')} registry, generated by\n"
            "# scripts/build_anukramani_knowledge_layer.py from the corpus's own\n"
            f"# traditional index ({config.source_artifact_id}).\n"
            "#\n"
            f"# DELIBERATELY A SEPARATE NAMESPACE ({namespace}). Values are the index's own\n"
            "# strings and are not resolved against data/registry/. Measured: only 8 of 228\n"
            "# Yajurvedic rsi names equal a Rigvedic registry label, because that registry\n"
            "# stores Sarvanukramani patronymic compounds where these indices give bare\n"
            "# names. rv_registry_name_match records where a name coincides; it asserts\n"
            "# nothing about whether the two indices mean the same person.\n"
            "#\n"
            "# preferred_label is the source string with a trailing visarga folded and\n"
            "# nothing else changed; source_variants lists every spelling folded into it.\n"
        )
        document: dict[str, Any] = {"entities": entities}
        if descriptor:
            header += (
                "#\n"
                "# THESE ARE NOT DEITY NAMES. Whitney prints adjectival ascription\n"
                "# descriptors -- `agneyam` is 'belonging to Agni', `mantroktadevatyam` is\n"
                "# 'having the deity named in the mantra'. They are typed\n"
                "# DEVATA_ASCRIPTION and must never be unioned with the Rigvedic deity set:\n"
                "# doing so would add spurious gods and make a deity census meaningless.\n"
                "#\n"
                "# `rejections` is part of the contract, not commentary. Whitney's bracket\n"
                "# interleaves the ascription with the rest of the printed apparatus -- verse\n"
                "# counts, verse-count notes, pada addresses, metre names -- in one\n"
                "# period-delimited run with no field markers, and every value listed there\n"
                "# once stood in this file as a product-visible ascription node. The graph\n"
                "# asserted that the deity-ascription of AVS 18.4 was `ekonanavati`, the\n"
                "# number eighty-nine. They are recorded rather than silently dropped so that\n"
                "# a later pass cannot re-add them believing they were never seen.\n"
                "#\n"
                "# `ocr_variants_merged` on an entity lists the scan spellings folded into\n"
                "# its printed one. Only two-test merges are made: the variant is not a\n"
                "# Sanskrit word AND the target is independently printed elsewhere in this\n"
                "# same index. See AV_ASCRIPTION_OCR_SIBLINGS in the builder for the\n"
                "# near-pairs that are deliberately NOT merged.\n"
            )
            document["rejections"] = result["rejections"]
        (PROJECT_ROOT / "data" / "registry" / filename).write_text(
            header
            + yaml.safe_dump(
                document,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ),
            encoding="utf-8",
            newline="\n",
        )
    (out_dir / "manifest.json").write_text(
        json.dumps(
            {
                "artifact": config.knowledge_dir,
                "work_id": config.work_id,
                "veda": config.veda,
                "source_artifact_id": config.source_artifact_id,
                "predicates": sorted(config.namespaces),
                "descriptor_predicates": sorted(config.descriptor_predicates),
                "notes": config.notes,
                "stats": result["stats"],
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--veda", choices=[c.veda for c in CORPORA])
    parser.add_argument("--check", action="store_true", help="measure and write nothing")
    args = parser.parse_args()

    for config in CORPORA:
        if args.veda and config.veda != args.veda:
            continue
        result = build(config)
        print(f"\n=== {config.veda} ({config.work_id})")
        if result.get("skipped"):
            print(f"  skipped: {result['skipped']}")
            continue
        print(json.dumps(result["stats"], ensure_ascii=False, indent=1))
        if result["stats"]["unresolved_passage_ids"]:
            raise SystemExit(
                f"{config.veda}: {result['stats']['unresolved_passage_ids']} metadata rows "
                "name a passage this corpus does not contain. Refusing a partial join."
            )
        if args.check:
            print("  --check: nothing written")
            continue
        write(result)
        print(f"  wrote data/knowledge/{config.knowledge_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
