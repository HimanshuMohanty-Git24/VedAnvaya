"""Shared loading, normalisation and indexing for the ritual staging build.

Agent 13, Wave 2. Read-only with respect to the canonical graph.

Two facts about this module drive its shape.

First, the four core Samhita recensions and the supplementary ritual corpora are kept in
separate containers that never merge. `load_supplementary()` returns ritual prose; Samhita
text is only ever read through a separate reader against the live graph. No function
returns both in one structure, so a supplementary line cannot be counted into a Samhita
total by accident.

Second, every citation is preserved verbatim as the source prints it. The VPC convention is
one sentence per line prefixed by its own citation, so a locator is never reconstructed.
"""

from __future__ import annotations

import pathlib
import re
import unicodedata
from dataclasses import dataclass

EVIDENCE_SOURCE_TYPES = frozenset(
    {
        "SAMHITA",
        "BRAHMANA",
        "SRAUTASUTRA",
        "GRHYASUTRA",
        "OTHER_SUPPLEMENTARY_RITUAL_SOURCE",
        "DERIVED",
    }
)


@dataclass(frozen=True)
class SuppWork:
    abbr: str
    file: str
    title_iast: str
    slug: str
    evidence_source_type: str
    veda_school: str
    school_note: str
    edition: str
    citation_scheme: str
    citation_prefix: str


# The supplementary works, scoped to the ritual apparatus of the four recensions this
# project holds. `veda_school` is the recension whose apparatus the work is -- it is NOT a
# claim that the work belongs to that Samhita.
SUPP_WORKS: tuple[SuppWork, ...] = (
    # --- Yajurveda, Sukla, Madhyandina: the apparatus of our VSM spine ---------------
    SuppWork("SBM", "SBM.txt", "Satapathabrahmana (Madhyandina)",
             "satapathabrahmana-madhyandina", "BRAHMANA", "YV_VSM",
             "Madhyandina recension, the same school as our Vajasaneyi Samhita.",
             "Weber", "kanda.adhyaya.brahmana.kandika.sentence", "SBM"),
    SuppWork("KatySS", "KatySS.txt", "Katyayanasrautasutra", "katyayanasrautasutra",
             "SRAUTASUTRA", "YV_VSM",
             "The srautasutra of the Sukla Yajurveda, Madhyandina school.",
             "M. Fushimi (data entry)", "kanda.kandika.sutra", "KatySS"),
    SuppWork("ParGS", "ParGS.txt", "Paraskaragrhyasutra", "paraskaragrhyasutra",
             "GRHYASUTRA", "YV_VSM",
             "The grhyasutra of the Sukla Yajurveda, Madhyandina school.",
             "VPC", "kanda.kandika.sutra", "ParGS"),
    # --- Atharvaveda, Saunaka --------------------------------------------------------
    SuppWork("GB", "GB.txt", "Gopathabrahmana", "gopathabrahmana", "BRAHMANA", "AV_SAU",
             "The only surviving Atharvavedic brahmana.",
             "VPC", "part.prapathaka.kandika.sentence", "GB"),
    SuppWork("VaitS", "VaitS.txt", "Vaitanasutra", "vaitanasutra", "SRAUTASUTRA", "AV_SAU",
             "The Atharvavedic srautasutra.",
             "Vishva Bandhu", "adhyaya.kandika.sutra", "VaitS"),
    SuppWork("KausS", "KausS.txt", "Kausikasutra", "kausikasutra", "GRHYASUTRA", "AV_SAU",
             "The Atharvavedic ritual sutra: grhya plus the magical rites.",
             "VPC", "adhyaya.kandika.sutra", "KausS"),
    # --- Samaveda, Kauthuma ----------------------------------------------------------
    SuppWork("PB", "PB.txt", "Pancavimsabrahmana", "pancavimsabrahmana", "BRAHMANA",
             "SV_KAU",
             "The Tandya-Mahabrahmana of the Kauthuma-Ranayaniya branch; where samans get "
             "their ritual employment.",
             "VPC", "prapathaka.adhyaya.kandika", "PB"),
    SuppWork("SadvB", "SadvB.txt", "Sadvimsabrahmana", "sadvimsabrahmana", "BRAHMANA",
             "SV_KAU", "The twenty-sixth prapathaka, appended to the Pancavimsa.",
             "B.R. Sharma, Tirupati 1967", "prapathaka.kandika.sentence", "SadvB"),
    SuppWork("SVidhB", "SVidhB.txt", "Samavidhanabrahmana", "samavidhanabrahmana",
             "BRAHMANA", "SV_KAU", "Samavedic; the ritual application of samans.",
             "VPC", "prapathaka.kandika.sentence", "SVidhB"),
    SuppWork("LatSS", "LatSS.txt", "Latyayanasrautasutra", "latyayanasrautasutra",
             "SRAUTASUTRA", "SV_KAU",
             "The KAUTHUMA srautasutra. Wave 0 recorded this work as essentially absent "
             "from the reachable sources; it is present and complete here.",
             "Vedantavagisa, Bibliotheca Indica", "prapathaka.kandika.sutra", "LatSS"),
    SuppWork("GobhGS", "GobhGS.txt", "Gobhilagrhyasutra", "gobhilagrhyasutra", "GRHYASUTRA",
             "SV_KAU", "The Samavedic grhyasutra.",
             "VPC", "prapathaka.kandika.sutra", "GobhGS"),
    # --- Rigveda, Sakala -------------------------------------------------------------
    SuppWork("AB", "AB.txt", "Aitareyabrahmana", "aitareyabrahmana", "BRAHMANA", "RV_SAK",
             "Rigvedic, Aitareya school of the Sakala Samhita.",
             "VPC", "pancika.adhyaya.kandika", "AB"),
    SuppWork("KausB", "KausB.txt", "Kausitakibrahmana", "kausitakibrahmana", "BRAHMANA",
             "RV_SAK", "Rigvedic, Kausitaki-Sankhayana school.",
             "VPC", "adhyaya.kandika.sentence", "KausB"),
    SuppWork("AsvSS", "AsvSS.txt", "Asvalayanasrautasutra", "asvalayanasrautasutra",
             "SRAUTASUTRA", "RV_SAK", "Rigvedic, Aitareya school.",
             "VPC", "adhyaya.kandika.sutra", "AsvSS"),
    SuppWork("SankhSS", "SankhSS.txt", "Sankhayanasrautasutra", "sankhayanasrautasutra",
             "SRAUTASUTRA", "RV_SAK", "Rigvedic, Kausitaki-Sankhayana school.",
             "VPC", "adhyaya.kandika.sutra", "SankhSS"),
    SuppWork("AsvGS", "AsvGS.txt", "Asvalayanagrhyasutra", "asvalayanagrhyasutra",
             "GRHYASUTRA", "RV_SAK", "Rigvedic, Aitareya school.",
             "VPC", "adhyaya.kandika.sutra", "AsvGS"),
    SuppWork("SankhGS", "SankhGS.txt", "Sankhayanagrhyasutra", "sankhayanagrhyasutra",
             "GRHYASUTRA", "RV_SAK", "Rigvedic, Kausitaki-Sankhayana school.",
             "VPC", "adhyaya.kandika.sutra", "SankhGS"),
    SuppWork("KausGS", "KausGS.txt", "Kausitakagrhyasutra", "kausitakagrhyasutra",
             "GRHYASUTRA", "RV_SAK", "Rigvedic, Kausitaki-Sankhayana school.",
             "VPC", "adhyaya.kandika.sutra", "KausGS"),
)

WORKS_BY_ABBR = {w.abbr: w for w in SUPP_WORKS}

# Attributed translations, aligned line-for-line on the same citation scheme.
# A machine translation (`-mt.txt` in the source repository) is deliberately NOT here: the
# ingestion contract forbids attributing a model-assisted rendering to a translator, and an
# unattributed rendering is not evidence about a rite.
SUPP_TRANSLATIONS = {
    "VaitS": ("VaitS-Caland.txt", "Caland", "de",
              "W. Caland, Das Vaitanasutra des Atharvaveda, 1910"),
    "PB": ("PB-Caland.txt", "Caland", "en",
           "W. Caland, Pancavimsa-Brahmana, Bibliotheca Indica, 1931"),
    "SankhSS": ("SankhSS-Caland.txt", "Caland", "de",
                "W. Caland, Sankhayana-Srautasutra"),
    "SankhGS": ("SankhGS-Oldenberg.txt", "Oldenberg", "en",
                "H. Oldenberg, The Grihya-sutras, SBE 29"),
    "GobhGS": ("GobhGS-Oldenberg.txt", "Oldenberg", "en",
               "H. Oldenberg, The Grihya-sutras, SBE 30"),
    "ParGS": ("ParGS-Oldenberg.txt", "Oldenberg", "en",
              "H. Oldenberg, The Grihya-sutras, SBE 29"),
}

CITATION_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)*(?:-[0-9]+)?)[ \t]+(.+)$")

_PUNCT_RE = re.compile(
    r"[|/\\.,;:!?\"()\[\]{}0-9–—\-=+*&%$#@<>~`^_‘’“”]"
)


def norm_iast(s: str) -> str:
    """Lowercase, drop avagraha and punctuation, collapse whitespace. Diacritics kept.

    Diacritics are load-bearing in IAST -- a dental and a palatal sibilant are different
    letters -- so this deliberately does NOT fold them. What it drops is only what the
    editions vary on freely: case, avagraha, danda, verse numerals and punctuation.
    """
    s = unicodedata.normalize("NFC", s).lower()
    s = s.replace("’", "").replace("‘", "").replace("'", "")
    s = _PUNCT_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


# Accent handling, measured rather than assumed. A census of every combining mark in both
# corpora (proofs/combining-mark-census.json) shows the naive rule is wrong: U+0301 is the
# udatta when it sits on a vowel and the palatal sibilant when it sits on `s`, and U+0304
# is the long-vowel macron, not an accent. Stripping U+0304 as an accent -- the first
# version of this function did -- silently destroys vowel length, which turns `tva` and
# `tvaa` into the same string and makes every pratika match unfalsifiable.
#
# So: marks that never form a letter are always dropped; marks that are ambiguous are
# dropped only over a vowel; letter-forming marks are always kept.
_ALWAYS_STRIP = set(
    "̍"          # vertical line above: udatta in the GRETIL Vedic scheme
    "̭"          # circumflex below: the Wikisource VSM accent
    "॒॑"    # Devanagari udatta / anudatta, if any survive transliteration
    "᳔᳜᳝᳐᳑᳒᳚᳛᳠᳡᳭"  # Vedic signs
)
_STRIP_OVER_VOWEL = set("̱̀́̂")
_VOWELS = set("aeiou")


def strip_accents(s: str) -> str:
    decomposed = unicodedata.normalize("NFD", s.lower())
    kept: list[str] = []
    for char in decomposed:
        if char in _ALWAYS_STRIP:
            continue
        if char in _STRIP_OVER_VOWEL:
            base = next((c for c in reversed(kept) if not unicodedata.combining(c)), "")
            if base in _VOWELS:
                continue
        kept.append(char)
    return unicodedata.normalize("NFC", "".join(kept))


_NONLETTER_RE = re.compile(r"[^a-zÀ-ɏḀ-ỿĀ-ſ]")

# Cross-witness spelling equivalences, each one measured in the combining-mark census.
# Vocalic r is `r` plus a ring below in VedaWeb and GRETIL's Atharvaveda and `r` plus a dot
# below everywhere in the ritual prose (10,505 against 9 occurrences), and anusvara is
# m-dot-above in some witnesses and m-dot-below in others. Neither difference is a
# difference of text. Nothing else folds.
# Folds, each one measured: vocalic r is `r` plus a ring below in VedaWeb and GRETIL's
# Atharvaveda and `r` plus a dot below throughout the ritual prose (10,505 against 9
# occurrences); anusvara is m-dot-above in some witnesses and m-dot-below in others; and
# GRETIL's Rigveda writes the retroflex lateral with a macron below where VedaWeb writes it
# with a dot below. None of the three is a difference of text -- each was found by diffing
# the two independent witnesses of RV 1.1.1 against each other.
_FOLDS_NFD = (("r̥", "ṛ"), ("l̥", "ḷ"), ("ḻ", "ḷ"))
_FOLDS_NFC = (("ṁ", "ṃ"), ("ḻ", "ḷ"))


def letters_only(s: str) -> str:
    """Normalised letters with no spaces, for sandhi-tolerant substring comparison."""
    folded = unicodedata.normalize("NFD", norm_iast(strip_accents(s)))
    for src, dst in _FOLDS_NFD:
        folded = folded.replace(src, dst)
    folded = unicodedata.normalize("NFC", folded)
    for src, dst in _FOLDS_NFC:
        folded = folded.replace(src, dst)
    return _NONLETTER_RE.sub("", folded)


@dataclass(frozen=True)
class SuppLine:
    abbr: str
    citation: str          # verbatim, as the source prints it
    full_citation: str     # e.g. "KatySS 1.1.1"
    text: str              # verbatim
    norm: str              # normalised, spaces kept
    letters: str           # normalised, no spaces
    ordinal: int           # 1-based printed position within the work
    tokens: tuple[str, ...]


def load_supplementary(root: pathlib.Path) -> dict[str, list[SuppLine]]:
    """Load every supplementary work. Returns ritual prose ONLY -- never Samhita text."""
    out: dict[str, list[SuppLine]] = {}
    for work in SUPP_WORKS:
        lines: list[SuppLine] = []
        raw = (root / work.file).read_text(encoding="utf-8")
        ordinal = 0
        for line in raw.splitlines():
            if not line.strip() or line.startswith("#") or line.startswith("@"):
                continue
            match = CITATION_RE.match(line)
            if not match:
                continue
            ordinal += 1
            citation, text = match.group(1), match.group(2).strip()
            normed = norm_iast(text)
            lines.append(
                SuppLine(
                    abbr=work.abbr,
                    citation=citation,
                    full_citation=f"{work.citation_prefix} {citation}",
                    text=text,
                    norm=normed,
                    letters=letters_only(text),
                    ordinal=ordinal,
                    tokens=tuple(normed.split()),
                )
            )
        out[work.abbr] = lines
    return out


def load_translations(root: pathlib.Path) -> dict[str, dict[str, str]]:
    """Attributed translations, keyed by work abbreviation then by citation."""
    out: dict[str, dict[str, str]] = {}
    for abbr, (fname, _tr, _lang, _cite) in SUPP_TRANSLATIONS.items():
        path = root / fname
        if not path.exists():
            continue
        table: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#") or line.startswith("@"):
                continue
            match = CITATION_RE.match(line)
            if match:
                table[match.group(1)] = match.group(2).strip()
        out[abbr] = table
    return out


def alias_hits(lines: list[SuppLine], alias: str) -> list[SuppLine]:
    """Lines where `alias` begins a token.

    Word-initial rather than anywhere, so a compound's first member matches and a chance
    interior substring does not. Sanskrit ritual vocabulary is overwhelmingly
    compound-initial in exactly this way (`darsapurnamasa-` before a case ending, or
    `agnihotra-havani`), and an unanchored substring search on this corpus produces the
    containment errors the material-culture audit had to measure alias by alias.
    """
    needle = norm_iast(alias)
    return [ln for ln in lines if any(t.startswith(needle) for t in ln.tokens)]


def token_hits(lines: list[SuppLine], form: str) -> list[SuppLine]:
    """Lines carrying `form` as a whole token."""
    needle = norm_iast(form)
    return [ln for ln in lines if needle in ln.tokens]
