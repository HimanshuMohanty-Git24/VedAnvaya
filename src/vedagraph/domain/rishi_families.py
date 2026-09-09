"""Derive the ``RishiFamily`` layer from the patronymic the Anukramaṇī actually states.

**No gotra data file exists in this repository, and none is invented here.** The evidence
is in the seer labels themselves. The Ṛgvedic Sarvānukramaṇī does not give a bare personal
name; it gives *patronymic + personal name* -- ``bhāradvājaḥ pāyuḥ``, ``bhārgavaḥ kaviḥ``,
``aucathyo dīrghatamāḥ`` -- and the first element is a **vṛddhi derivative**, the Sanskrit
grammatical marker of descent (``bhṛgu`` → ``bhārgava``, ``atri`` → ``ātreya``,
``aṅgiras`` → ``āṅgirasa``, ``kaṇva`` → ``kāṇva``). So a membership derived from that
element rests on a statement the source made, not on two names looking alike.

The distinction matters enough to be a hard rule of this module:

**A shared prefix is never descent.** ``bharadvāja`` and ``bhāradvāja`` differ by one
vowel length and that vowel length *is* the whole claim; ``bhārgava`` and ``bhaga`` share
four characters and are unrelated. Nothing here matches on similarity, edit distance or
prefix. Every membership requires the label's token to equal one of the finitely many
inflected surfaces of a patronymic listed by hand in :data:`GOTRA_PATRONYMICS`, where each
entry records its eponym and its vṛddhi derivation. The table is the evidence audit; the
code only applies it.

Four consequences that are deliberate, and each is a *smaller* layer than a reader might
expect:

1. **The eponym is not a member of his own family.** ``vasiṣṭha``, ``bharadvāja``,
   ``atri``, ``kaṇva`` and ``gṛtsamada`` appear in the Yajurvedic index as bare
   non-vṛddhi names. The Anukramaṇī states no patronymic for them, so this module states
   no family for them. They are reported unassigned under
   ``EPONYM_WITHOUT_STATED_PATRONYMIC``, and that is the honest reading: the source says
   "Vasiṣṭha", not "Vasiṣṭha son of anyone".
2. **Theonymic patronymics do not become families.** ``aindraḥ vasukraḥ``,
   ``prājāpatyo hiraṇyagarbhaḥ``, ``vaivasvato yamaḥ`` and ``vāruṇiḥ satyadhṛtiḥ`` all
   state descent -- from Indra, Prajāpati, Vivasvān, Varuṇa. That is divine parentage, not
   a gotra, and Q2/Q19/Q26 ask about seer families. They are declined by name in
   :data:`DECLINED_PATRONYMICS` with the reason recorded, not silently dropped, and the
   patronymic is still decomposed onto the ``Rishi`` node so the fact survives.
3. **Kinship that is not descent is declined.** ``agastyasvasā`` (Agastya's sister),
   ``vasukrapatnī`` (Vasukra's wife) and ``agastyāntevāsī brahmacārī`` (Agastya's resident
   student) each name a relation to a named man. None of them is patrilineal descent, and
   a gotra layer that swallowed a wife and a pupil would be asserting something the source
   does not.
4. **A non-human seer is never a family.** ``agniḥ``, ``aditiḥ``, ``devāḥ``,
   ``akṛṣṭā māṣāḥ`` ("the unploughed beans") and ``pṛśnayo ajāḥ`` ("the dappled goats")
   are attributed as seers by the tradition. They match no patronymic and so create
   nothing; they are separated out for the report by intersecting with the *existing*
   theonym registry rather than by a new hand-written list, so the classification cannot
   drift away from the deity layer.

Partial coverage, measured and labelled, is the intended outcome. Assigning a family to
every one of the 729 ṛṣis would require inventing evidence for the roughly half of them
the tradition gives as bare names.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from vedagraph.knowledge.normalize import ascii_key

# ---------------------------------------------------------------------------
# The patronymic tables. These are the evidence; everything below only applies them.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Patronymic:
    """One vṛddhi-derived gotra adjective, with the descent it encodes.

    ``eponym`` is the ancestor the derivative is built on and ``derivation`` states the
    vowel change in full, so a reader can check the grammar without trusting the table.
    ``variants`` holds spellings the *source* uses for the same stem -- never a spelling
    this module guessed.
    """

    stem: str
    eponym: str
    derivation: str
    variants: tuple[str, ...] = ()


def _p(stem: str, eponym: str, *variants: str) -> Patronymic:
    return Patronymic(
        stem=stem,
        eponym=eponym,
        derivation=f"vṛddhi patronymic: {eponym} → {stem}",
        variants=variants,
    )


#: Every patronymic this layer will turn into a family. One family per stated patronymic
#: stem: no two stems are merged, because merging ``kāṇva`` into ``kāṇvāyana`` (or the
#: reverse) would be a genealogical claim the Anukramaṇī does not make on the page.
GOTRA_PATRONYMICS: Final[tuple[Patronymic, ...]] = (
    _p("ailūṣa", "ilūṣa"),
    _p("airammada", "iramada"),
    _p("atharvaṇa", "atharvan", "ātharvaṇa"),
    _p("aucathya", "ucatha"),
    _p("aurava", "uru"),
    _p("auśija", "uśij"),
    _p("auśinara", "uśīnara"),
    _p("bhauma", "bhūmi"),
    _p("bhauvana", "bhuvana"),
    _p("bhālandana", "bhalandana"),
    _p("bhāmyaśva", "bhamyaśva"),
    _p("bhāradvāja", "bharadvāja"),
    _p("bhārata", "bharata"),
    _p("bhārgava", "bhṛgu"),
    _p("cākṣuṣa", "cakṣus"),
    _p("dairghatamasa", "dīrghatamas"),
    _p("daivodāsi", "divodāsa"),
    _p("dhānāka", "dhanaka"),
    _p("dārḻhacyuta", "dṛḻhacyuta"),
    _p("gaupāyana", "gopāyana"),
    _p("gautama", "gotama"),
    _p("ghaura", "ghora"),
    _p("ghauṣeya", "ghoṣa"),
    _p("gārgya", "garga"),
    _p("gārtsamada", "gṛtsamada"),
    _p("gāthina", "gāthin"),
    _p("hairaṇyastūpa", "hiraṇyastūpa"),
    _p("hārita", "harita"),
    _p("jāna", "jana"),
    _p("kautsa", "kutsa"),
    _p("kauśika", "kuśika"),
    _p("kākṣīvata", "kakṣīvān"),
    _p("kātya", "kati"),
    _p("kāvya", "kavi"),
    _p("kāśyapa", "kaśyapa"),
    _p("kāṇva", "kaṇva"),
    _p("kāṇvāyana", "kaṇva"),
    _p("mādhucchandasa", "madhucchandas"),
    _p("mānava", "manu"),
    _p("mārīca", "marīci"),
    _p("naudhasa", "nodhas"),
    _p("nāhuṣa", "nahuṣa"),
    _p("nārmedha", "nṛmedha"),
    _p("paijavana", "pijavana"),
    _p("paurukutsa", "purukutsa", "paurukutsya"),
    _p("plāta", "plata"),
    _p("praiyamedha", "priyamedha"),
    _p("prāgātha", "pragātha"),
    _p("pārucchepi", "parucchepa"),
    _p("rauhidaśva", "rohidaśva"),
    _p("rāhūgaṇa", "rahūgaṇa"),
    _p("saubhara", "sobhari"),
    _p("sauhotra", "suhotra"),
    _p("sāmmada", "sammada"),
    _p("sāṁvaraṇa", "saṁvaraṇa"),
    _p("sāṅkhya", "saṅkhya"),
    _p("sthaura", "sthūra"),
    _p("traivṛṣṇa", "trivṛṣṇa"),
    _p("tārkṣya", "tṛkṣi"),
    _p("vaidarbhi", "vidarbha"),
    _p("vaikhānasa", "vikhanas"),
    _p("vainya", "vena"),
    _p("vairūpa", "virūpa"),
    _p("vaitahavya", "vītahavya"),
    _p("vaiyaśva", "vyaśva"),
    _p("vaiśvāmitra", "viśvāmitra"),
    _p("vādhryaśva", "vadhryaśva"),
    _p("vāmadevya", "vāmadeva"),
    _p("vāndana", "vandana"),
    _p("vārṣāgira", "vṛṣāgir"),
    _p("vārṣṭihavya", "vṛṣṭihavya"),
    _p("vāsiṣṭha", "vasiṣṭha"),
    _p("vāsukra", "vasukra"),
    _p("yauvanāśva", "yuvanāśva"),
    _p("āgastya", "agastya"),
    _p("ājīgarti", "ajīgarta"),
    _p("āmahīyava", "mahīyava"),
    _p("āmbhṛṇī", "ambhṛṇa"),
    _p("āptya", "apti"),
    _p("ārṣṭiṣeṇa", "ṛṣṭiṣeṇa"),
    _p("āśvya", "aśva"),
    _p("ātreya", "atri", "atreya"),
    _p("āṅgirasa", "aṅgiras"),
    _p("śailūṣa", "śilūṣa"),
    _p("śairīṣi", "śiriṣa"),
    _p("śaunaka", "śunaka", "śāunaka"),
    _p("śyāvāśvi", "śyāvāśva"),
    _p("śāktya", "śakti"),
)

#: Patronymics the sources *do* state and this layer deliberately refuses to reify, with
#: the reason kept per stem. Declining by name rather than by omission is the point: the
#: report can then say how many ṛṣis were left unassigned *because of a policy* as opposed
#: to because their label carried no patronymic at all.
DECLINED_PATRONYMICS: Final[Mapping[str, tuple[str, str]]] = {
    "aindra": ("THEONYMIC_DESCENT", "descent from Indra, a deity, not a gotra"),
    "arbhava": ("THEONYMIC_DESCENT", "descent from the Ṛbhus, deities, not a gotra"),
    "brāhma": ("THEONYMIC_DESCENT", "descent from brahman, an abstraction"),
    "bārhaspatya": ("THEONYMIC_DESCENT", "descent from Bṛhaspati, a deity in this graph"),
    "gandharva": ("THEONYMIC_DESCENT", "a gandharva is a class of being, not an ancestor"),
    "kādraveya": ("MYTHIC_DESCENT", "descent from Kadrū, mother of serpents"),
    "kāmayānī": ("THEONYMIC_DESCENT", "descent from Kāma, a deity"),
    "maitrāvaruṇi": (
        "THEONYMIC_DESCENT",
        "descent from Mitra and Varuṇa, deities; the standard reading of Vasiṣṭha's and "
        "Agastya's birth, and not a gotra",
    ),
    "nairṛta": ("THEONYMIC_DESCENT", "descent from Nirṛti, a deity"),
    "paulomī": ("MYTHIC_DESCENT", "descent from Puloman, an asura"),
    "prājāpatya": ("THEONYMIC_DESCENT", "descent from Prajāpati, a deity"),
    # The Ṛgvedic registry prints both the long and the short first vowel.
    "prājapatya": ("THEONYMIC_DESCENT", "descent from Prajāpati, a deity"),
    "saumya": ("THEONYMIC_DESCENT", "descent from Soma, a deity"),
    "saurya": ("THEONYMIC_DESCENT", "descent from Sūrya, a deity"),
    "sārpa": ("MYTHIC_DESCENT", "a serpent lineage"),
    "sāvitrī": ("THEONYMIC_DESCENT", "descent from Savitṛ, a deity"),
    "tvāṣṭra": ("THEONYMIC_DESCENT", "descent from Tvaṣṭar, a deity"),
    "tāpasa": ("TITULAR_NOT_DESCENT", "'ascetic', a status word, not an ancestor"),
    "vaikuṇṭha": ("TITULAR_NOT_DESCENT", "an epithet of Indra, not a patronymic"),
    "vairāja": ("TITULAR_NOT_DESCENT", "derived from virāj, a metre and an abstraction"),
    "vaivasvata": ("THEONYMIC_DESCENT", "descent from Vivasvān, a deity"),
    "vātāyana": ("THEONYMIC_DESCENT", "descent from Vāta, a deity"),
    "vāruṇi": ("THEONYMIC_DESCENT", "descent from Varuṇa, a deity"),
    "yāmāyana": ("THEONYMIC_DESCENT", "descent from Yama, a deity"),
    "āditya": ("THEONYMIC_DESCENT", "descent from Aditi, a deity"),
    "āgneya": ("THEONYMIC_DESCENT", "descent from Agni, a deity"),
    "kāśirāja": ("TITULAR_NOT_DESCENT", "'king of Kāśi', a royal title and a toponym"),
    "parameṣṭhī": ("TITULAR_NOT_DESCENT", "'the highest', a title of Prajāpati"),
    # Stems that differ from a table entry by what looks like a misprint. Declined, and
    # declined *by name*, because deriving a family from them would mean emending the
    # source -- and "one vowel out" is precisely the distance between ``bharadvāja`` and
    # ``bhāradvāja``, which is a real difference. Correcting the printed string here would
    # license correcting it anywhere.
    "bhāgava": ("SOURCE_SPELLING_OUTSIDE_TABLE", "apparently bhārgava with r dropped"),
    "daivaodāsi": ("SOURCE_SPELLING_OUTSIDE_TABLE", "apparently daivodāsi with an extra a"),
    "vaivasvasta": ("SOURCE_SPELLING_OUTSIDE_TABLE", "apparently vaivasvata, itself declined"),
    "ātreyyapālā": (
        "SOURCE_SPELLING_OUTSIDE_TABLE",
        "ātreyī apālā printed as one token with the two names run together",
    ),
    "āṅgirhavirdhāna": (
        "SOURCE_SPELLING_OUTSIDE_TABLE",
        "the patronymic is truncated to āṅgir-, so the stem is not on the page",
    ),
    "cāpsava": (
        "ETYMON_UNCERTAIN",
        "in patronymic position and vṛddhi-shaped, but no eponym this layer can state "
        "from repository evidence -- c-āpsava is not a vṛddhi of apsu",
    ),
}

#: Labels stating descent *without* a vṛddhi derivative, by an explicit kinship compound.
#: Curated one by one and kept tiny on purpose -- ``-putra`` is unambiguous descent, while
#: ``-svasā`` (sister), ``-patnī`` (wife) and ``-antevāsī`` (resident pupil) are not, and
#: are declined in :data:`DECLINED_KINSHIP`.
EXPLICIT_DESCENT: Final[Mapping[str, tuple[str, str]]] = {
    "vasiṣṭhaputrāḥ": (
        "vāsiṣṭha",
        "the label is the compound vasiṣṭha-putrāḥ, 'the sons of Vasiṣṭha': descent "
        "stated in words rather than by vṛddhi",
    ),
}

#: Labels naming a relation to a man that is *not* patrilineal descent.
DECLINED_KINSHIP: Final[Mapping[str, str]] = {
    "agastyasvasā": "Agastya's sister: affinal, not descent from Agastya",
    "agastyāntevāsī brahmacārī": "Agastya's resident student: discipleship, not descent",
    "vasukrapatnī": "Vasukra's wife: marriage, not descent",
    "vasukrasya patnī": "Vasukra's wife: marriage, not descent",
}

#: Ṛṣi-registry entries that are not seers at all, listed one by one after reading every
#: label in the three registries.
#:
#: **Why this is a hand list and not an intersection with the deity registry.** The first
#: version of this classification took the ṛṣi labels that equal a label in
#: ``data/registry/devatas.yaml``. It found 18 -- and **3 of the 18 were human seers**:
#: ``purūravāḥ``, ``romaśā`` and ``svanayo bhāvayavyaḥ`` are each *also* named as the
#: devatā of the hymn they see, which is a normal thing for a dialogue hymn or a
#: dānastuti to do. A 17% error rate on the very question "is this a person?" is the
#: repository's recurring failure shape: the intersection measured *appears in the deity
#: registry*, not *is not a seer*. So the deity registry is not consulted at all now.
#:
#: The consequence for the layer is real and intended: an entry here creates **no**
#: family even if its label carries a patronymic. ``cākṣuṣo agniḥ``, ``saucīko agniḥ``,
#: ``sauvīko agniḥ`` and ``pāvako agniḥ`` are Agni under four epithets, and a Cākṣuṣa
#: gotra whose sole member is a god is worse than no Cākṣuṣa gotra.
#:
#: This matters outside the family layer, which is why it is written onto the ``Rishi``
#: node: the strict per-passage ṛṣi leaderboard was measured with ``devāḥ`` -- "the gods"
#: -- at rank 1, so a query that enumerates seers has been returning a deity group as the
#: most prolific poet of the Ṛgveda.
NON_SEER_ASCRIPTIONS: Final[Mapping[str, tuple[str, str]]] = {
    # -- Ṛgveda ---------------------------------------------------------------
    "aditiḥ": ("DEITY", "Aditi"),
    "agnivaruṇasomāḥ": ("DEITY_GROUP", "Agni, Varuṇa and Soma as a triad"),
    "agniḥ": ("DEITY", "Agni"),
    "akṛṣṭā māṣāḥ": ("PLANT_OR_ANIMAL", "'the unploughed beans'"),
    "brahma": ("ABSTRACTION", "brahman, the sacred formulation"),
    "cākṣuṣo agniḥ": ("DEITY", "Agni Cākṣuṣa"),
    "devajāmayaḥ indramātaraḥ": ("DEITY_GROUP", "'the divine kinswomen, Indra's mothers'"),
    "devāḥ": ("DEITY_GROUP", "'the gods'"),
    "garbhakartā tvaṣṭā": ("DEITY", "Tvaṣṭar the embryo-maker"),
    "godhā": ("PLANT_OR_ANIMAL", "the monitor lizard, or the bowstring-guard from its hide"),
    "indraḥ": ("DEITY", "Indra"),
    "indro labaḥ": ("DEITY", "Indra in the form of a quail"),
    "indrāṇī": ("DEITY", "Indrāṇī"),
    "juhūḥ": ("OBJECT", "the juhū offering-ladle, personified"),
    "marutaḥ": ("DEITY_GROUP", "the Maruts"),
    "muṣkavān indraḥ": ("DEITY", "Indra"),
    "nadyaḥ": ("DEITY_GROUP", "'the rivers'"),
    "nārāyaṇaḥ": ("DEITY", "Nārāyaṇa"),
    "paṇayaḥ asurāḥ": ("MYTHIC_BEING", "the Paṇis, called asuras"),
    "parameṣṭhī prajāpatiḥ": ("DEITY", "Prajāpati Parameṣṭhin"),
    "pāvako agniḥ": ("DEITY", "Agni Pāvaka"),
    "pṛśnayo ajāḥ": ("PLANT_OR_ANIMAL", "'the dappled goats'"),
    "saptarṣayaḥ": ("COLLECTIVE", "'the seven seers', a collective and not one of them"),
    "saramā": ("MYTHIC_BEING", "Saramā, Indra's messenger bitch"),
    "saucīko agniḥ": ("DEITY", "Agni Saucīka"),
    "saucīko vaiśvānaraḥ": ("DEITY", "Agni Vaiśvānara"),
    "sauvīko agniḥ": ("DEITY", "Agni Sauvīka"),
    "sikatā nivāvarī": ("OBJECT", "'the sands, flowing down'"),
    "sārparājñī": ("MYTHIC_BEING", "the queen of serpents"),
    "urvaśī": ("MYTHIC_BEING", "Urvaśī, an apsaras"),
    "vaikuṇṭha indraḥ": ("DEITY", "Indra Vaikuṇṭha"),
    "vācyaḥ prajāpatiḥ": ("DEITY", "Prajāpati"),
    "vaivasvato yamaḥ": ("DEITY", "Yama Vaivasvata"),
    "vaivasvatī yamī": ("DEITY", "Yamī Vaivasvatī"),
    "vātaśanāḥ": ("COLLECTIVE", "'the wind-eaters', a class of ascetics, unnamed"),
    "vṛṣākapiḥ": ("MYTHIC_BEING", "Vṛṣākapi, Indra's ape"),
    "śārṅgāḥ": ("PLANT_OR_ANIMAL", "the Śārṅga birds"),
    "ādityo vivasvān": ("DEITY", "Vivasvān Āditya"),
    "arbudaḥ sārpaḥ": ("MYTHIC_BEING", "Arbuda the serpent"),
    "kādraveyaḥ sarpaḥ arbudaḥ": ("MYTHIC_BEING", "Arbuda, serpent son of Kadrū"),
    "sārpa airāvato jaratkarṇaḥ": ("MYTHIC_BEING", "Jaratkarṇa, serpent of Airāvata"),
    "gandharvo viśvāvasuḥ": ("MYTHIC_BEING", "Viśvāvasu, a gandharva"),
    "sāvitrī sūryā": ("DEITY", "Sūryā, daughter of Savitṛ"),
    "prājapatyo yajña": ("ABSTRACTION", "the sacrifice personified"),
    "prājapatyo hiraṇyagarbhaḥ": ("ABSTRACTION", "Hiraṇyagarbha, the golden germ"),
    # -- Yajurveda ------------------------------------------------------------
    "agni": ("DEITY", "Agni"),
    "aśvi": ("DEITY", "an Aśvin"),
    "aśvinau": ("DEITY", "the two Aśvins"),
    "brahma(svayambhu-)": ("ABSTRACTION", "brahman, self-existent"),
    "bṛhaspati": ("DEITY", "Bṛhaspati"),
    "bṛhaspatī": ("DEITY", "Bṛhaspati"),
    "dadhikrāvā": ("DEITY", "Dadhikrāvan, the divine steed"),
    "dakṣa": ("DEITY", "Dakṣa"),
    "devā": ("DEITY_GROUP", "'the gods'"),
    "devā vā": ("DEITY_GROUP", "'or the gods', an alternative ascription to no person"),
    "hiraṇyagarbha": ("ABSTRACTION", "the golden germ"),
    "indra": ("DEITY", "Indra"),
    "indrābṛhaspatī": ("DEITY", "Indra and Bṛhaspati as a dual"),
    "indrāgnī": ("DEITY", "Indra and Agni as a dual"),
    "kadrūḥ(sarparājñī-)": ("MYTHIC_BEING", "Kadrū, queen of serpents"),
    "nārāyaṇa": ("DEITY", "Nārāyaṇa"),
    "nārāyaṇaḥ(uttara)": ("DEITY", "Nārāyaṇa, the latter portion"),
    "parameṣṭhī prajāpati": ("DEITY", "Prajāpati Parameṣṭhin"),
    "parameṣṭhī prajāpatirvā devā": ("DEITY", "Prajāpati Parameṣṭhin, or the gods"),
    "prajāpati": ("DEITY", "Prajāpati"),
    "prajāpatirvā devāḥ(parameṣṭhī-)": ("DEITY", "Prajāpati, or the gods"),
    "prajāpatiḥ(parameṣṭhī-)": ("DEITY", "Prajāpati Parameṣṭhin"),
    "prājāpatyo yajña": ("ABSTRACTION", "the sacrifice personified"),
    "sapta ṛṣaya": ("COLLECTIVE", "'the seven seers', a collective"),
    "sarasvatī": ("DEITY", "Sarasvatī"),
    "sarparājñī kadrū": ("MYTHIC_BEING", "Kadrū, queen of serpents"),
    "savitā": ("DEITY", "Savitṛ"),
    "saṅkalpaḥ(śiva-)": ("ABSTRACTION", "the auspicious resolve"),
    "svayambhu brahma": ("ABSTRACTION", "brahman, self-existent"),
    "uttaranārāyaṇa": ("DEITY", "Nārāyaṇa, the latter portion"),
    "varuṇa": ("DEITY", "Varuṇa"),
    "vivasvān": ("DEITY", "Vivasvān"),
    "viśvadeva": ("DEITY_GROUP", "the All-Gods"),
    "viśvakarmā": ("DEITY", "Viśvakarman"),
    "viśvakarmā(bhuvanaputro-)": ("DEITY", "Viśvakarman, son of Bhuvana"),
    "viśvedevā": ("DEITY_GROUP", "the All-Gods"),
    "viśvāvasu": ("MYTHIC_BEING", "Viśvāvasu, a gandharva"),
    "yajñapuruṣa": ("ABSTRACTION", "the sacrifice as person"),
    "yajñaḥ(prājāpatyo-)": ("ABSTRACTION", "the sacrifice personified"),
    "ādityā devā": ("DEITY_GROUP", "the Āditya gods"),
    "ādityā devā vā": ("DEITY_GROUP", "'or the Āditya gods'"),
    "śivasaṅkalpa": ("ABSTRACTION", "the auspicious resolve"),
    # -- Atharvaveda (Whitney's spellings, folded) -----------------------------
    "brahman": ("ABSTRACTION", "brahman; the AV's most frequent ascription, 83 rows"),
    "bhaga": ("DEITY", "Bhaga"),
    "draviṇodas": ("DEITY", "Draviṇodas, an epithet of Agni or Indra"),
    "garutman": ("MYTHIC_BEING", "Garutmān, the celestial bird"),
    "jagadbījampuruṣa": ("ABSTRACTION", "'the person who is the seed of the world'"),
    "savitar": ("DEITY", "Savitṛ"),
    "savitṛ": ("DEITY", "Savitṛ"),
    "tvaṣṭar": ("DEITY", "Tvaṣṭar"),
    "yama": ("DEITY", "Yama"),
    "ṛbhu": ("DEITY", "a Ṛbhu"),
    "cātana": ("ABSTRACTION", "cātana, the 'expelling' hymn class, not a person at all"),
    "kapiñjala": ("PLANT_OR_ANIMAL", "the francolin"),
}


#: Collective corpus-lineage compounds in the Atharvavedic index. ``bhṛgvaṅgiras`` and
#: ``atharvāṅgiras`` are dvandvas naming the *two* priestly stocks the Atharvaveda as a
#: whole is ascribed to. They are not vṛddhi derivatives and they are not a statement
#: about one seer's father, so they create no membership; there are enough of them
#: (roughly 40 Atharvavedic rows) that folding them in would have doubled the apparent
#: coverage of that namespace on evidence that does not support it.
COLLECTIVE_LINEAGE: Final[frozenset[str]] = frozenset(
    {
        "atharvaṅgiras",
        "atharvāṅgiras",
        "bhṛgaṅgiras",
        "bhṛgvaṅgiras",
        "bhṛgvāṅgiras",
        "pratyaṅgirasa",
        "bhṛvaṅgiras brahman",
    }
)

# ---------------------------------------------------------------------------
# Inflection. A closed set of surfaces per stem, generated -- never a fuzzy match.
# ---------------------------------------------------------------------------

#: Visarga sandhi: word-final ``-aḥ`` becomes ``-o`` before a voiced sound and assimilates
#: to a following sibilant or ``r``. That is why ``bhāradvājaḥ pāyuḥ`` and
#: ``bhāradvājo gargaḥ`` are the same word, and why ``kāṇvaḥ triśokaḥ`` is printed
#: ``kāṇvastriśokaḥ``. Enumerating the outcomes keeps the match an equality test.
_A_STEM_ENDINGS: Final[tuple[str, ...]] = ("", "ḥ", "s", "ś", "ṣ", "r")
_A_STEM_REPLACEMENTS: Final[tuple[str, ...]] = ("o", "au", "āḥ", "ā", "ī", "e")
_I_STEM_ENDINGS: Final[tuple[str, ...]] = ("", "ḥ", "r", "ṇ")


def surfaces(stem: str) -> frozenset[str]:
    """Every inflected surface of ``stem`` this module will accept as that patronymic.

    Nominative singular, dual, plural and feminine, plus the visarga-sandhi outcomes.
    Generated rather than listed so a new table entry cannot be half-inflected, and
    closed so that matching stays equality against a finite set.
    """
    forms = {stem}
    if stem.endswith("a"):
        base = stem[:-1]
        forms.update(stem + ending for ending in _A_STEM_ENDINGS)
        forms.update(base + replacement for replacement in _A_STEM_REPLACEMENTS)
    elif stem.endswith(("i", "ī")):
        base = stem.rstrip("iī")
        forms.update(base + "i" + ending for ending in _I_STEM_ENDINGS)
        forms.update({base + "ī", base + "yau", base + "iṇaḥ"})
    else:
        forms.update({stem + "ḥ", stem + "s"})
    return frozenset(forms)


_PUNCTUATION: Final = re.compile(r"[()\[\]{}:;,\-–—?!.·]+")  # noqa: RUF001
_PARENTHETICAL: Final = re.compile(r"[(⌊\[][^)⌋\]]*[)⌋\]]?")
_VERSE_PREFIX: Final = re.compile(r"^[\d\s,.–-]*\d[\s,.]*")  # noqa: RUF001
_WHITESPACE: Final = re.compile(r"\s+")

#: Whitney prints ``ç`` for ``ś``, ``n̄``/``n̈`` for ``ṅ``, and writes the diphthongs as
#: ``āu``/``āi``. Folding these is orthography, not emendation: it changes no phoneme.
#: It is applied only to the Atharvavedic namespace, whose registry stores Whitney's own
#: strings verbatim.
_WHITNEY_FOLD: Final[tuple[tuple[str, str], ...]] = (
    ("n̄", "ṅ"),
    ("n̈", "ṅ"),
    ("ç", "ś"),
    ("āu", "au"),
    ("āi", "ai"),
    ("’", ""),  # noqa: RUF001 - Whitney marks elided a- with a typographic apostrophe
    ("ʼ", ""),  # noqa: RUF001
)


def fold_whitney(label: str) -> str:
    """Whitney's orthography folded to the IAST the patronymic table is written in."""
    folded = unicodedata.normalize("NFC", label)
    for source, target in _WHITNEY_FOLD:
        folded = folded.replace(source, target)
    return unicodedata.normalize("NFC", folded)


def tokenize(label: str, *, drop_parentheticals: bool) -> list[str]:
    """The name tokens of a source label, lowercased, with nothing else changed.

    ``drop_parentheticals`` is per namespace and the two namespaces genuinely differ.
    In Whitney's Atharvavedic index a parenthesis holds a *wish annotation* -- what the
    seer wanted, ``Atharvan (svastyayanakāmaḥ)`` -- or an editorial ``(?)``/``(as above)``,
    none of which is a name. In the Yajurvedic ṛṣisūcī a parenthesis holds the **other
    half of the same name**: ``kāśyapaḥ(vatsāraḥ-)`` and ``vatsāraḥ kāśyapa`` are one
    entry printed two ways. Dropping Yajurvedic parentheticals would discard the
    patronymic in 30-odd rows; keeping Atharvavedic ones would tokenize ``yaśaskāmaḥ`` as
    a personal name.
    """
    text = unicodedata.normalize("NFC", label)
    if drop_parentheticals:
        text = _PARENTHETICAL.sub(" ", text)
    text = _VERSE_PREFIX.sub("", text)
    text = _PUNCTUATION.sub(" ", text)
    return [token for token in _WHITESPACE.sub(" ", text).strip().lower().split() if token]


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------

#: How a single membership was licensed. Recorded per edge, because the three are not
#: equally safe and a reader must be able to filter to the safest.
METHOD_TOKEN: Final = "patronymic-token-equality-v1"
METHOD_FUSED: Final = "patronymic-fused-token-split-v1"
METHOD_COMPOUND: Final = "explicit-descent-compound-v1"

#: A fused split must leave at least this many characters of personal name behind. Without
#: it, ``bhārgavaḥ`` itself would "split" into ``bhārgava`` + ``ḥ`` and every plain
#: patronymic would be reported as a fused two-name entry.
_MIN_FUSED_RESIDUE: Final = 3


@dataclass(frozen=True)
class Membership:
    """One ``Rishi`` → ``RishiFamily`` edge, carrying the string that licensed it."""

    entity_key: str
    family_key: str
    family_stem: str
    source_label: str
    source_token: str
    method: str
    derivation: str
    namespace: str


@dataclass(frozen=True)
class Decomposition:
    """The Q2 requirement: a seer label split into its patronymic and personal halves."""

    entity_key: str
    source_label: str
    namespace: str
    patronymics: tuple[str, ...]
    personal_names: tuple[str, ...]
    method: str
    #: ``None`` for a person. Set for the registry rows that are a deity, a deity group,
    #: an abstraction, a mythic being, an animal or an object rather than a seer.
    non_seer_kind: str | None = None


@dataclass
class Derivation:
    """Everything one pass over the registries produced, including what it refused."""

    families: dict[str, dict[str, object]] = field(default_factory=dict)
    memberships: list[Membership] = field(default_factory=list)
    decompositions: list[Decomposition] = field(default_factory=list)
    #: ``entity_key`` → (class, reason) for every ṛṣi left with no family.
    unassigned: dict[str, tuple[str, str]] = field(default_factory=dict)

    def counts_by_class(self) -> dict[str, int]:
        tally: dict[str, int] = {}
        for label, _ in self.unassigned.values():
            tally[label] = tally.get(label, 0) + 1
        return dict(sorted(tally.items()))


def family_key(stem: str) -> str:
    return f"VG:RISHI_FAMILY:{ascii_key(stem)}"


def _surface_index() -> dict[str, Patronymic]:
    """Surface → patronymic, with a hard collision check.

    Two table entries whose inflected surfaces overlap would make membership depend on
    table order, which is exactly the kind of silent arbitrariness this layer is supposed
    not to have. It raises instead.
    """
    index: dict[str, Patronymic] = {}
    for entry in GOTRA_PATRONYMICS:
        for stem in (entry.stem, *entry.variants):
            for surface in surfaces(stem):
                previous = index.get(surface)
                if previous is not None and previous.stem != entry.stem:
                    raise ValueError(
                        f"surface {surface!r} is claimed by both {previous.stem!r} and "
                        f"{entry.stem!r}; the patronymic table must stay unambiguous"
                    )
                index[surface] = entry
    return index


def _declined_index() -> dict[str, tuple[str, str]]:
    index: dict[str, tuple[str, str]] = {}
    for stem, verdict in DECLINED_PATRONYMICS.items():
        for surface in surfaces(stem):
            index[surface] = verdict
    return index


SURFACE_INDEX: Final[Mapping[str, Patronymic]] = _surface_index()
DECLINED_INDEX: Final[Mapping[str, tuple[str, str]]] = _declined_index()


def _split_fused[T](token: str, index: Mapping[str, T]) -> tuple[T, str] | None:
    """Split ``kāṇvastriśokaḥ`` into the patronymic ``kāṇva`` and the name ``triśokaḥ``.

    The Anukramaṇī is printed with sandhi applied *across* the two halves of a name, so a
    minority of entries arrive as a single token. Both positions are tried, because the
    patronymic may lead (``vāsiṣṭhaścitramahāḥ`` = vāsiṣṭhaḥ + citramahāḥ) or follow
    (``śaṃyubārhaspatya``, ``satyadhṛtirvāruṇi``, ``dadhyaṅṅātharvaṇa``); the trailing
    case also covers a printed compound whose final member *is* the gotra adjective, as
    in ``svastyātreya``.

    This is not prefix similarity. The match is equality against a closed surface index --
    the **whole** inflected patronymic has to be present, including the sandhi consonant --
    and the residue has to be long enough to be a name rather than a stray letter, which
    is what :data:`_MIN_FUSED_RESIDUE` enforces. Longest match wins, so a long stem is
    never split as a shorter one plus rubbish. All 16 splits this produced over the three
    registries were checked one by one against the Anukramaṇī reading; see the report.
    """
    best: tuple[T, str] | None = None
    best_length = 0
    for surface, entry in index.items():
        if len(surface) <= best_length:
            continue
        if token.startswith(surface) and len(token) - len(surface) >= _MIN_FUSED_RESIDUE:
            best, best_length = (entry, token[len(surface) :]), len(surface)
        elif token.endswith(surface) and len(token) - len(surface) >= _MIN_FUSED_RESIDUE:
            best, best_length = (entry, token[: -len(surface)]), len(surface)
    return best


@dataclass(frozen=True)
class RishiEntry:
    """One registry row, reduced to what the derivation needs."""

    entity_key: str
    label: str
    namespace: str


#: Namespaces attempted, and how each one's strings have to be read. The Atharvavedic
#: index needs both flags; the other two need neither.
NAMESPACE_READING: Final[Mapping[str, tuple[bool, bool]]] = {
    # namespace: (fold Whitney orthography, drop parentheticals)
    "RV_WSC2023_ANUKRAMANI": (False, False),
    "YV_VSM_RSISUCI": (False, False),
    "AV_WHITNEY_ANUKRAMANI": (True, True),
}


def derive(entries: Iterable[RishiEntry]) -> Derivation:
    """Apply the patronymic tables to every registry row and record both outcomes.

    Non-seer entries are settled first and unconditionally: see
    :data:`NON_SEER_ASCRIPTIONS` for why that list is hand-written and why an earlier
    version of it, derived by intersecting with the deity registry, was 17% wrong.
    """
    result = Derivation()
    for entry in entries:
        fold, drop = NAMESPACE_READING.get(entry.namespace, (False, False))
        label = fold_whitney(entry.label) if fold else unicodedata.normalize("NFC", entry.label)
        normalized = _WHITESPACE.sub(" ", label.strip()).lower()
        tokens = tokenize(label, drop_parentheticals=drop)

        matched: list[tuple[Patronymic, str, str]] = []
        personal: list[str] = []
        declined: tuple[str, str] | None = None

        # The Atharvavedic index prints editorial notes and wish annotations in
        # parentheses, so ``probe`` -- the tokens rejoined -- is the form that identifies
        # ``Brahman (?)`` and ``Cātana (sapatnakṣayakāmaḥ)`` with plain ``Brahman`` and
        # ``Cātana``. The Yajurvedic index puts a *name* in its parentheses, so its rows
        # match on ``normalized`` instead, and both forms are tried.
        probe = " ".join(tokens)
        non_seer = NON_SEER_ASCRIPTIONS.get(normalized) or NON_SEER_ASCRIPTIONS.get(probe)

        compound = EXPLICIT_DESCENT.get(normalized)
        if non_seer is not None:
            # Checked before every other branch, and it creates nothing. A patronymic in
            # the label of a deity does not make the deity a member of a gotra.
            kind, gloss = non_seer
            result.decompositions.append(
                Decomposition(
                    entity_key=entry.entity_key,
                    source_label=entry.label,
                    namespace=entry.namespace,
                    patronymics=(),
                    personal_names=(),
                    method="declined",
                    non_seer_kind=kind,
                )
            )
            result.unassigned[entry.entity_key] = (
                "NON_SEER_ASCRIPTION",
                f"not a seer: {gloss} ({kind}). The tradition ascribes the hymn to it; "
                f"it has no descent and must not appear in a leaderboard of poets",
            )
            continue
        if compound is not None:
            stem, reason = compound
            entry_p = next(p for p in GOTRA_PATRONYMICS if p.stem == stem)
            matched.append((entry_p, normalized, METHOD_COMPOUND))
            result.memberships.append(
                Membership(
                    entity_key=entry.entity_key,
                    family_key=family_key(stem),
                    family_stem=stem,
                    source_label=entry.label,
                    source_token=normalized,
                    method=METHOD_COMPOUND,
                    derivation=reason,
                    namespace=entry.namespace,
                )
            )
        elif normalized in DECLINED_KINSHIP:
            declined = ("KINSHIP_NOT_DESCENT", DECLINED_KINSHIP[normalized])
        elif normalized in COLLECTIVE_LINEAGE or (
            len(tokens) == 1 and tokens[0] in COLLECTIVE_LINEAGE
        ):
            declined = (
                "COLLECTIVE_LINEAGE_COMPOUND",
                "a dvandva naming two priestly stocks jointly, not one seer's descent",
            )
        else:
            for token in tokens:
                found = SURFACE_INDEX.get(token)
                if found is not None:
                    matched.append((found, token, METHOD_TOKEN))
                    continue
                refused = DECLINED_INDEX.get(token)
                if refused is not None:
                    declined = refused
                    personal.append(token)
                    continue
                fused = _split_fused(token, SURFACE_INDEX)
                if fused is not None:
                    found, residue = fused
                    matched.append((found, token, METHOD_FUSED))
                    personal.append(residue)
                    continue
                # A *declined* patronymic can be fused too -- `tvāṣṭrastriśirāḥ`,
                # `sauryaścakṣuḥ`, `maitrāvaruṇirvasiṣṭhaḥ`. Without this the row would be
                # reported as "no patronymic stated", which is false: one is stated and
                # this layer chose not to reify it. Getting the refusal class right is the
                # whole value of refusing by name.
                refused_fused = _split_fused(token, DECLINED_INDEX)
                if refused_fused is not None:
                    declined, residue = refused_fused
                    personal.append(residue)
                    continue
                personal.append(token)

            # One edge per (ṛṣi, family), not one per matching token. `ātreyaḥ
            # svastyātreyaḥ` states the same patronymic twice -- once bare and once inside
            # the compound personal name -- and two edges would double that family's
            # member count off a single label. Token equality is kept over a fused split
            # because it is the stronger evidence.
            seen: dict[str, tuple[Patronymic, str, str]] = {}
            for found, token, method in matched:
                previous = seen.get(found.stem)
                if previous is None or (previous[2] == METHOD_FUSED and method == METHOD_TOKEN):
                    seen[found.stem] = (found, token, method)
            matched = list(seen.values())

            for found, token, method in matched:
                result.memberships.append(
                    Membership(
                        entity_key=entry.entity_key,
                        family_key=family_key(found.stem),
                        family_stem=found.stem,
                        source_label=entry.label,
                        source_token=token,
                        method=method,
                        derivation=found.derivation,
                        namespace=entry.namespace,
                    )
                )

        for found, _token, _method in matched:
            record = result.families.setdefault(
                family_key(found.stem),
                {
                    "family_key": family_key(found.stem),
                    "display_label": found.stem,
                    "patronymic_iast": found.stem,
                    "eponym_iast": found.eponym,
                    "vrddhi_derivation": found.derivation,
                    "source_variants": list(found.variants),
                    "member_count": 0,
                    "namespaces": [],
                },
            )
            record["member_count"] = int(record["member_count"]) + 1  # type: ignore[call-overload]
            namespaces = record["namespaces"]
            assert isinstance(namespaces, list)
            if entry.namespace not in namespaces:
                namespaces.append(entry.namespace)

        result.decompositions.append(
            Decomposition(
                entity_key=entry.entity_key,
                source_label=entry.label,
                namespace=entry.namespace,
                patronymics=tuple(found.stem for found, _, _ in matched),
                personal_names=tuple(personal),
                method=(matched[0][2] if matched else ("declined" if declined else METHOD_TOKEN)),
            )
        )

        if matched:
            continue
        if declined is not None:
            result.unassigned[entry.entity_key] = declined
        elif any(token in {p.eponym for p in GOTRA_PATRONYMICS} for token in tokens):
            result.unassigned[entry.entity_key] = (
                "EPONYM_WITHOUT_STATED_PATRONYMIC",
                "the label is the non-vṛddhi eponym itself, so the source states no "
                "patronymic for him; the vowel length is the whole claim and it is absent",
            )
        else:
            result.unassigned[entry.entity_key] = (
                "NO_PATRONYMIC_STATED",
                "a bare personal name, or a string this layer cannot parse; left "
                "unassigned rather than guessed",
            )
    return result


def coverage(derivation: Derivation, entries: Sequence[RishiEntry]) -> dict[str, object]:
    """Assigned-over-total, overall and per namespace. Reported, never rounded up."""
    assigned = {m.entity_key for m in derivation.memberships}
    per_namespace: dict[str, dict[str, int]] = {}
    for entry in entries:
        bucket = per_namespace.setdefault(entry.namespace, {"total": 0, "assigned": 0})
        bucket["total"] += 1
        if entry.entity_key in assigned:
            bucket["assigned"] += 1
    non_seer = sum(1 for row in derivation.decompositions if row.non_seer_kind is not None)
    return {
        "total": len(entries),
        "assigned": len(assigned),
        # The honest denominator for any question about *poets*: registry rows minus the
        # rows that are not people. Reported alongside, never instead of, the raw total.
        "seer_rows": len(entries) - non_seer,
        "non_seer_rows": non_seer,
        "families": len(derivation.families),
        "memberships": len(derivation.memberships),
        "per_namespace": per_namespace,
        "unassigned_by_class": derivation.counts_by_class(),
    }
