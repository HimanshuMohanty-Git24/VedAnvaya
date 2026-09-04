"""Choose the pilot mantras: deterministically, and not the famous ones.

The pilot exists to find out where extraction breaks, so it is selected to *contain* the
hard cases rather than to look representative. Strata are computed from the deterministic
layers only — a mantra is "ritual-heavy" or "cosmological" nowhere in this module,
because deciding that is exactly the judgement being tested.

Two properties matter more than the strata themselves:

**Deterministic.** Given the same corpus the same mantras come out, in the same order.
Selection is by a hash of the passage key, so the config is reproducible from the code
and a diff of it is meaningful.

**Not front-loaded.** Ordering within a stratum is by hash, not by citation. Taking the
first *n* by citation would fill the pilot with RV 1.1-1.20 and Maṇḍala 10's opening
hymns: the most translated, most discussed, most memorised verses in the corpus, and
therefore the ones a model is most likely to reproduce from training rather than read
from the packet. Measuring precision there would flatter the extractor and tell us
nothing about the other ten thousand.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass

from vedagraph.semantic.packet import PacketSources

PILOT_CONFIG_VERSION = "rigveda-semantic-pilot-v1"
SELECTION_RULE_VERSION = "rigveda-semantic-pilot-selection-v1"

#: A Devatā, Ṛṣi or metre with at most this many mantras is "rare" for stratification.
#: The common ones select themselves through the Maṇḍala quota; the rare ones are where
#: registry coverage is thinnest and are otherwise invisible in a 5% sample.
RARE_THRESHOLD = 12
SHORT_SUKTA = 3
LONG_SUKTA = 30


@dataclass(frozen=True)
class Stratum:
    """One reason a mantra is worth including, and how many of them to take."""

    name: str
    quota: int
    reason: str


#: Order matters: a mantra is credited to the first stratum that claims it, so the
#: scarce and awkward strata are listed before the broad ones and are not starved by
#: them. Quotas sum to roughly 500, inside the 400-600 target.
STRATA: tuple[Stratum, ...] = (
    Stratum(
        "TRANSLATION_MISSING",
        60,
        "no Griffith verse exists: the packet carries Sanskrit and morphology only, and "
        "the model must decline rather than translate",
    ),
    Stratum(
        "LEXICALLY_AMBIGUOUS",
        45,
        "the lexical layer deliberately refused to resolve a token here; a model that "
        "resolves it anyway is doing so without evidence",
    ),
    Stratum(
        "EXACT_PARALLEL",
        45,
        "the mantra recurs verbatim elsewhere, so its extraction can be compared with "
        "that of its twin",
    ),
    Stratum(
        "NEAR_PARALLEL",
        30,
        "a near-parallel: similar wording, possibly different claims",
    ),
    Stratum("RARE_DEVATA", 40, f"assigned a Devatā with at most {RARE_THRESHOLD} mantras"),
    Stratum("RARE_CHANDAS", 25, f"assigned a metre with at most {RARE_THRESHOLD} mantras"),
    Stratum("RARE_RISHI", 25, f"assigned a Ṛṣi with at most {RARE_THRESHOLD} mantras"),
    Stratum("MULTI_DEVATA", 25, "tradition assigns more than one Devatā"),
    Stratum(
        "NO_LEXICAL_MENTION",
        40,
        "no deterministic mention was found, so the model has metadata and text but no "
        "pre-established entity to lean on",
    ),
    Stratum("SHORT_SUKTA", 25, f"a Sūkta of at most {SHORT_SUKTA} mantras: little context"),
    Stratum("LONG_SUKTA", 25, f"a Sūkta of at least {LONG_SUKTA} mantras: a narrow window"),
    Stratum(
        "MANDALA_09_SOMA",
        40,
        "Maṇḍala 9 is almost entirely Soma Pavamāna: highly repetitive ritual language",
    ),
    Stratum(
        "MANDALA_10",
        40,
        "Maṇḍala 10 carries the cosmological and philosophical material, where the "
        "temptation to interpret is strongest",
    ),
    Stratum(
        "MANDALA_SPREAD",
        70,
        "an even draw across all ten Maṇḍalas so no book is represented only by its "
        "difficult cases",
    ),
)


def _order_key(passage_key: str) -> str:
    """A stable, citation-independent ordering. Same corpus, same pilot, every time."""
    return hashlib.sha256(f"{SELECTION_RULE_VERSION}|{passage_key}".encode()).hexdigest()


def _mandala(passage_key: str) -> int:
    return int(passage_key.split(":")[3][1:])


def _sukta_key(passage_key: str) -> str:
    return passage_key.rsplit(":", 1)[0]


@dataclass(frozen=True)
class PilotSelection:
    """The chosen mantras with the stratum each was credited to."""

    passage_keys: tuple[str, ...]
    reasons: dict[str, str]
    counts: dict[str, int]

    def __len__(self) -> int:
        return len(self.passage_keys)


def select_pilot(
    sources: PacketSources,
    *,
    ambiguous_passage_keys: frozenset[str] = frozenset(),
    strata: tuple[Stratum, ...] = STRATA,
) -> PilotSelection:
    """Pick the pilot set. Reads only deterministic layers; makes no textual judgement."""
    all_keys = sources.mantra_keys
    sukta_sizes = sources.sukta_sizes

    devata_freq = Counter(key for keys in sources.devatas.values() for key in keys)
    chandas_freq = Counter(key for keys in sources.chandas.values() for key in keys)
    rishi_freq = Counter(key for keys in sources.rishis.values() for key in keys)

    def rare(passage_key: str, assigned: dict[str, list[str]], freq: Counter[str]) -> bool:
        values = assigned.get(passage_key, [])
        return bool(values) and all(freq[value] <= RARE_THRESHOLD for value in values)

    members: dict[str, list[str]] = defaultdict(list)
    for key in all_keys:
        sukta_size = sukta_sizes[_sukta_key(key)]
        if key not in sources.translations:
            members["TRANSLATION_MISSING"].append(key)
        if key in ambiguous_passage_keys:
            members["LEXICALLY_AMBIGUOUS"].append(key)
        if sources.exact_parallels.get(key):
            members["EXACT_PARALLEL"].append(key)
        if sources.near_parallels.get(key):
            members["NEAR_PARALLEL"].append(key)
        if rare(key, sources.devatas, devata_freq):
            members["RARE_DEVATA"].append(key)
        if rare(key, sources.chandas, chandas_freq):
            members["RARE_CHANDAS"].append(key)
        if rare(key, sources.rishis, rishi_freq):
            members["RARE_RISHI"].append(key)
        if len(sources.devatas.get(key, [])) > 1:
            members["MULTI_DEVATA"].append(key)
        if not sources.mentions.get(key):
            members["NO_LEXICAL_MENTION"].append(key)
        if sukta_size <= SHORT_SUKTA:
            members["SHORT_SUKTA"].append(key)
        if sukta_size >= LONG_SUKTA:
            members["LONG_SUKTA"].append(key)
        if _mandala(key) == 9:
            members["MANDALA_09_SOMA"].append(key)
        if _mandala(key) == 10:
            members["MANDALA_10"].append(key)

    chosen: dict[str, str] = {}
    counts: dict[str, int] = {}
    for stratum in strata:
        if stratum.name == "MANDALA_SPREAD":
            continue
        pool = sorted(
            (key for key in members.get(stratum.name, ()) if key not in chosen), key=_order_key
        )
        taken = pool[: stratum.quota]
        counts[stratum.name] = len(taken)
        for key in taken:
            chosen[key] = stratum.name

    spread = next((item for item in strata if item.name == "MANDALA_SPREAD"), None)
    if spread is not None:
        per_mandala, remainder = divmod(spread.quota, 10)
        taken_total = 0
        for mandala in range(1, 11):
            quota = per_mandala + (1 if mandala <= remainder else 0)
            pool = sorted(
                (key for key in all_keys if _mandala(key) == mandala and key not in chosen),
                key=_order_key,
            )
            for key in pool[:quota]:
                chosen[key] = spread.name
                taken_total += 1
        counts[spread.name] = taken_total

    reasons = {name: stratum.reason for stratum in strata for name in (stratum.name,)}
    ordered = tuple(sorted(chosen))
    return PilotSelection(
        passage_keys=ordered,
        reasons={key: chosen[key] for key in ordered}
        | {f"_stratum:{k}": v for k, v in reasons.items()},
        counts=counts,
    )


def gold_subset(selection: PilotSelection, *, size: int = 120) -> tuple[str, ...]:
    """The mantras to annotate by hand, drawn from the pilot by the same stable order.

    Drawn across the pilot rather than from one stratum, so a precision figure measured
    here is a figure about the pipeline and not about its easiest slice.
    """
    return tuple(sorted(sorted(selection.passage_keys, key=_order_key)[:size]))
