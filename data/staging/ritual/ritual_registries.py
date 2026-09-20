"""Candidate registries for the ritual expansion: rites, roles, implements, materials,
offerings, actions, and the deity dative forms.

Every list here is a CANDIDATE SPACE, not a result. The build measures each candidate
against the acquired corpora and against the four Samhitas separately, and a candidate that
is not attested is written to rejected.jsonl with the reason. That is why the lists include
entries expected to fail: a candidate space that only contains winners cannot close
campaign section 32, because it cannot say what was looked for and not found.

Alias discipline. A prefix alias shorter than MIN_PREFIX_ALIAS_LEN is refused rather than
matched, because short prefixes collide: `darsa` reaches `darsanat` (from "seeing") and
`darsayati` as readily as `darsapurnamasau`, and `asvina` reaches 28 hits of which all 28
are `asvinau`, the Asvin deity pair, and none is the Asvina rite. Both were measured.

The floor is FIVE, not the six the material-culture lexicon used, and the difference is
deliberate. That audit's six-character floor governed a SUBSTRING pass over the Samaveda,
where a short needle can land anywhere inside a word. This module matches word-initially,
which is a much narrower opening, and a six-character floor here silently refused `sruva`,
`sphya`, `kapal`, `musal`, `barhi`, `nestr` and twenty more -- and the first run then
reported their absence as a VERIFIED ZERO over an assessed population, which is the one
thing the ingestion contract forbids outright. A refused alias is now NOT ASSESSED and says
so.

Where a five-character prefix still collides the collision is named in
`NEGATIVE_PREFIXES` rather than assumed away, and every accepted alias's host-form
distribution is written to proofs/alias-host-forms.json so a reader can check the
collisions instead of trusting this docstring.
"""

from __future__ import annotations

MIN_PREFIX_ALIAS_LEN = 5

# Measured collisions: a prefix long enough to pass the floor that nonetheless reaches a
# different word. Each was found by printing the host forms, not by guessing.
NEGATIVE_PREFIXES = {
    "grāva": ("grāvastut",),                      # the priest named after the stone
    "madhu": ("madhupark", "madhumat", "madhumant", "madhumatt"),
    "śyāma": ("śyāmāk",),                          # syamaka millet, not the dark metal
    "dakṣiṇā": ("dakṣiṇāgn", "dakṣiṇāvṛt", "dakṣiṇārdh", "dakṣiṇāgr", "dakṣiṇāt",
                "dakṣiṇāhi", "dakṣiṇāmukh"),      # daksina is also `south` and `right`
}

# Four-character prefixes admitted by name, each because its host forms were printed and
# checked. `yupa` is the case that forced this: the sacrificial post is written yupena,
# yupo, yupad, yupeva, yupavraska and asvayupaya, and a five-character floor with a
# whole-token list reached six of the ten attesting mantras and neither of the two
# Yajurvedic ones -- which is precisely the alias shortfall GAP-RITUAL-003 records.
# `yupitam` at AVS 4.25.2 is a different root and does not carry the macron, so it does
# not collide.
ALLOWED_SHORT_PREFIXES = {
    "yūpa": (
        "Host forms measured across the four Samhitas and the eighteen supplementary "
        "works: every one is the sacrificial post or a compound of it. The homograph "
        "`yupita` has no long u and therefore never matches."
    ),
}

# Sequence words. A step whose sutra carries one of these has its position stated by the
# text and not merely by the printing. Measured frequencies are in
# proofs/sequence-marker-census.json.
SEQUENCE_MARKERS_EXACT = (
    "atha", "athātaḥ", "athāto", "tataḥ", "anantaram", "paścāt", "pūrvam", "ūrdhvam",
    "agre", "upariṣṭāt", "punar", "prathamam", "prathamaṃ", "prathamam", "dvitīyam",
    "dvitīyaṃ", "tṛtīyam", "tṛtīyaṃ", "caturtham", "caturthaṃ", "pañcamam", "pañcamaṃ",
    "ṣaṣṭham", "ṣaṣṭhaṃ", "saptamam", "saptamaṃ", "aṣṭamam", "aṣṭamaṃ", "navamam",
    "navamaṃ", "daśamam", "daśamaṃ", "uttamam", "uttamaṃ", "athaitat", "athāta",
)

# ---------------------------------------------------------------------------------------
# RITES. `key` follows the existing VG:CONCEPT: convention. `existing` names the eight
# rites already in the graph, so the build proposes no duplicate.
# ---------------------------------------------------------------------------------------

# (key, label_en, label_sa, rite_class, aliases, exact_tokens, basis_note)
RITE_CANDIDATES: tuple[tuple[str, str, str, str, tuple[str, ...], tuple[str, ...], str], ...] = (
    # --- already modelled: measured, never re-minted -----------------------------------
    ("YAJNA-SACRIFICE", "sacrifice", "yajña", "SRAUTA_GENERIC",
     ("yajñakratu",), ("yajñaḥ", "yajñam", "yajñaṃ", "yajñena", "yajñasya", "yajñe"),
     "EXISTING. Measured for its supplementary attestation only."),
    ("SOMA-PRESSING", "soma pressing", "savana", "SRAUTA_SOMA",
     ("somayāga", "abhiṣava"), ("savanam", "savanaṃ", "savane", "savanāni", "sutyā"),
     "EXISTING. Measured for its supplementary attestation only."),
    ("AGNIHOTRA", "fire oblation", "agnihotra", "SRAUTA_HAVIRYAJNA",
     ("agnihotra",), (),
     "EXISTING, and the Samhita basis was one passage. The apparatus describes it."),
    ("DIKSA-CONSECRATION", "consecration", "dīkṣā", "SRAUTA_SOMA",
     ("dīkṣā", "dīkṣit", "dīkṣay", "dīkṣaṇīy"), (),
     "EXISTING. The apparatus supplies the procedure the Samhitas do not."),
    ("AGNI-CITI-FIRE-PILING", "fire altar piling", "citi", "SRAUTA_SOMA",
     ("agnicit", "agniciti", "agnicayana", "agnicayan"), ("citiḥ", "citim", "citiṃ", "citayaḥ"),
     "EXISTING. `agnicayana` is ZERO in this corpus; `agnicit` is the attested form."),
    ("ASVAMEDHA-HORSE-SACRIFICE", "horse sacrifice", "aśvamedha", "SRAUTA_GREAT",
     ("aśvamedha",), (),
     "EXISTING. GAP-RITUAL-007 is stale: this rite is present and is measured here."),
    ("GRAHA-SOMA-DRAWING", "soma cup drawing", "graha", "SRAUTA_SOMA",
     ("atigrāhya", "grahaṇ"), ("grahaḥ", "graham", "grahaṃ", "grahān", "grahāṇām"),
     "EXISTING."),
    ("SAUTRAMANI", "sautramani rite", "sautrāmaṇī", "SRAUTA_HAVIRYAJNA",
     ("sautrāmaṇ",), (),
     "EXISTING."),

    # --- the four rites GAP-RITUAL-001 names as absent ---------------------------------
    ("VAJAPEYA", "vajapeya", "vājapeya", "SRAUTA_GREAT",
     ("vājapeya",), (),
     "GAP-RITUAL-001 names this rite as absent. Attested across nine of the eighteen "
     "acquired works."),
    ("RAJASUYA", "royal consecration", "rājasūya", "SRAUTA_GREAT",
     ("rājasūya",), (),
     "GAP-RITUAL-001 names this rite as absent."),
    ("DARSAPURNAMASA", "new and full moon sacrifices", "darśapūrṇamāsa",
     "SRAUTA_HAVIRYAJNA",
     ("darśapūrṇamās", "paurṇamās", "darśeṣṭi"), (),
     "GAP-RITUAL-001 names this rite as absent. The bare alias `darśa` is REJECTED and "
     "recorded: 49 host forms, of which `darśanāt` and `darśayati` are the verb 'to see'."),
    ("CATURMASYA", "four-monthly sacrifices", "cāturmāsya", "SRAUTA_HAVIRYAJNA",
     ("cāturmāsy",), (),
     "GAP-RITUAL-001 names this rite as absent."),

    # --- srauta, soma and the sacrificial days -----------------------------------------
    ("AGNISTOMA", "agnistoma", "agniṣṭoma", "SRAUTA_SOMA", ("agniṣṭom",), (), ""),
    ("ATYAGNISTOMA", "atyagnistoma", "atyagniṣṭoma", "SRAUTA_SOMA", ("atyagniṣṭom",), (), ""),
    ("UKTHYA", "ukthya", "ukthya", "SRAUTA_SOMA", ("ukthya",), (), ""),
    ("SODASIN", "sodasin", "ṣoḍaśin", "SRAUTA_SOMA", ("ṣoḍaśin", "ṣoḍaśī"), (), ""),
    ("ATIRATRA", "overnight rite", "atirātra", "SRAUTA_SOMA", ("atirātr",), (), ""),
    ("APTORYAMA", "aptoryama", "aptoryāma", "SRAUTA_SOMA", ("aptoryām",), (), ""),
    ("JYOTISTOMA", "jyotistoma", "jyotiṣṭoma", "SRAUTA_SOMA", ("jyotiṣṭom",), (), ""),
    ("AGNISTUT", "agnistut", "agniṣṭut", "SRAUTA_SOMA", ("agniṣṭut",), (), ""),
    ("SARVASVARA", "sarvasvara", "sarvasvāra", "SRAUTA_SOMA", ("sarvasvār",), (), ""),
    ("GOSAVA", "gosava", "gosava", "SRAUTA_SOMA", ("gosava",), (), ""),
    ("BRHASPATISAVA", "brhaspatisava", "bṛhaspatisava", "SRAUTA_SOMA",
     ("bṛhaspatisava",), (), ""),
    ("UPAHAVYA", "upahavya", "upahavya", "SRAUTA_SOMA", ("upahavya",), (), ""),
    ("VISVAJIT", "visvajit", "viśvajit", "SRAUTA_SOMA", ("viśvajit",), (), ""),
    ("GAVAMAYANA", "the cows' year-long session", "gavāmayana", "SRAUTA_SATTRA",
     ("gavāmayan",), (), ""),
    ("SATTRA", "sacrificial session", "sattra", "SRAUTA_SATTRA",
     ("sattrāyaṇ",), ("sattram", "sattraṃ", "sattrasya", "sattre", "sattrāṇi", "sattrāṇāṃ"),
     "The generic session. `sattra` is six letters so it also matches as a prefix, but "
     "`baliṣṭha`-style adjective collisions were checked: 14 host forms, all the session."),
    ("DVADASAHA", "twelve-day rite", "dvādaśāha", "SRAUTA_SOMA", ("dvādaśāh",), (), ""),
    ("EKAHA", "one-day rite", "ekāha", "SRAUTA_SOMA", ("ekāha",), (), ""),
    ("AHINA", "multi-day rite", "ahīna", "SRAUTA_SOMA", ("ahīna",), (), ""),
    ("TRIRATRA", "three-night rite", "trirātra", "SRAUTA_SOMA", ("trirātr",), (), ""),
    ("SADAHA", "six-day rite", "ṣaḍaha", "SRAUTA_SOMA", ("ṣaḍaha",), (), ""),
    ("ABHIPLAVA", "abhiplava six-day rite", "abhiplava", "SRAUTA_SOMA", ("abhiplav",), (), ""),
    ("PRSTHYA", "prsthya six-day rite", "pṛṣṭhya", "SRAUTA_SOMA", ("pṛṣṭhya",), (), ""),
    ("PRAYANIYA", "opening isti", "prāyaṇīya", "SRAUTA_SOMA", ("prāyaṇīy",), (), ""),
    ("UDAYANIYA", "concluding isti", "udayanīya", "SRAUTA_SOMA", ("udayanīy",), (), ""),
    ("TANUNAPTRA", "tanunaptra covenant", "tānūnaptra", "SRAUTA_SOMA", ("tānūnaptr",), (), ""),
    ("UPASAD", "upasad days", "upasad", "SRAUTA_SOMA", ("upasad",), (), ""),
    ("PRAVARGYA", "pravargya hot-milk rite", "pravargya", "SRAUTA_SOMA", ("pravargya",), (), ""),
    ("AVABHRTHA", "concluding bath", "avabhṛtha", "SRAUTA_SOMA", ("avabhṛth",), (), ""),
    ("AGNISOMIYA-PASU", "the Agni-Soma victim", "agnīṣomīya", "SRAUTA_PASU",
     ("agnīṣomīy",), (), ""),
    ("PASUBANDHA", "animal sacrifice", "paśubandha", "SRAUTA_PASU",
     ("paśubandh", "nirūḍhapaśubandh"), (), ""),
    ("VASATIVARI", "the vasativari waters", "vasatīvarī", "SRAUTA_SOMA", ("vasatīvar",), (), ""),
    ("BAHISPAVAMANA", "bahispavamana stotra", "bahiṣpavamāna", "SRAUTA_SOMA",
     ("bahiṣpavamān",), (), ""),
    ("HARIYOJANA", "hariyojana graha", "hāriyojana", "SRAUTA_SOMA", ("hāriyojan",), (), ""),
    ("APYAYANA", "the soma's swelling", "āpyāyana", "SRAUTA_SOMA", ("āpyāyan",), (), ""),
    ("PURUSAMEDHA", "human sacrifice", "puruṣamedha", "SRAUTA_GREAT", ("puruṣamedh",), (), ""),
    ("SARVAMEDHA", "sarvamedha", "sarvamedha", "SRAUTA_GREAT", ("sarvamedh",), (), ""),

    # --- srauta, haviryajna ------------------------------------------------------------
    ("AGNYADHEYA", "establishing the fires", "agnyādheya", "SRAUTA_HAVIRYAJNA",
     ("agnyādhey", "agnyādhān", "agnyupasthān"), (), ""),
    ("PUNARADHEYA", "re-establishing the fires", "punarādheya", "SRAUTA_HAVIRYAJNA",
     ("punarādhey",), (), ""),
    ("AGRAYANA", "first-fruits offering", "āgrayaṇa", "SRAUTA_HAVIRYAJNA",
     ("āgrayaṇ",), (), ""),
    ("PINDAPITRYAJNA", "the ancestral rice-ball offering", "piṇḍapitṛyajña",
     "SRAUTA_HAVIRYAJNA", ("piṇḍapitṛyajñ",), (), ""),
    ("DAKSAYANA", "daksayana isti", "dākṣāyaṇa", "SRAUTA_HAVIRYAJNA", ("dākṣāyaṇ",), (), ""),
    ("SAMNAYYA", "the milk mixture offering", "sāṃnāyya", "SRAUTA_HAVIRYAJNA",
     ("sāṃnāyy", "sāṃnāyy"), (), ""),
    ("VAISVANARA-ISTI", "the Vaisvanara isti", "vaiśvānara", "SRAUTA_HAVIRYAJNA",
     ("vaiśvānar",), (),
     "Ambiguous by construction: `vaisvanara` is also an epithet of Agni. Accepted as a "
     "rite only where the citing line is in a sutra work, and flagged."),
    ("VAISVAKARMANA", "the Vaisvakarmana isti", "vaiśvakarmaṇa", "SRAUTA_HAVIRYAJNA",
     ("vaiśvakarmaṇ",), (), ""),
    ("AINDRAGNA", "the Indra-Agni offering", "aindrāgna", "SRAUTA_HAVIRYAJNA",
     ("aindrāgn",), (), ""),
    ("ISTI", "isti", "iṣṭi", "SRAUTA_HAVIRYAJNA",
     ("iṣṭikṛt",), ("iṣṭiḥ", "iṣṭim", "iṣṭiṃ", "iṣṭir", "iṣṭyā", "iṣṭibhiḥ", "iṣṭiṣu",
                    "iṣṭīnām", "iṣṭyām"),
     "The generic haviryajna. Whole-token only: `isti` is four letters."),
    ("PRAYASCITTI", "expiation", "prāyaścitti", "SRAUTA_OTHER",
     ("prāyaścitt",), (), ""),
    ("KARIRI", "the kariri rain rite", "kārīrī", "SRAUTA_HAVIRYAJNA", ("kārīr",), (), ""),

    # --- caturmasya parvans ------------------------------------------------------------
    ("VAISVADEVA-PARVAN", "the Vaisvadeva parvan", "vaiśvadeva", "SRAUTA_HAVIRYAJNA",
     ("vaiśvadev",), (),
     "Ambiguous by construction: `vaisvadeva` is also the deity group. Flagged."),
    ("VARUNAPRAGHASA", "the Varunapraghasa parvan", "varuṇapraghāsa", "SRAUTA_HAVIRYAJNA",
     ("varuṇapraghās",), (), ""),
    ("SAKAMEDHA", "the Sakamedha parvan", "sākamedha", "SRAUTA_HAVIRYAJNA",
     ("sākamedh",), (), ""),
    ("SUNASIRIYA", "the Sunasiriya parvan", "śunāsīrīya", "SRAUTA_HAVIRYAJNA",
     ("śunāsīr",), (), ""),

    # --- grhya samskaras ---------------------------------------------------------------
    ("VIVAHA-MARRIAGE", "marriage", "vivāha", "GRHYA_SAMSKARA",
     ("vivāha", "pāṇigrahaṇ"), (),
     "EXISTING as a SocialRite with 168 USED_FOR_RITE edges; measured, not re-minted."),
    ("PUMSAVANA", "rite for a male child", "puṃsavana", "GRHYA_SAMSKARA",
     ("puṃsavan",), (), ""),
    ("SIMANTONNAYANA", "parting of the hair", "sīmantonnayana", "GRHYA_SAMSKARA",
     ("sīmantonnayan", "sīmantakaraṇ"), (), ""),
    ("GARBHALAMBHANA", "rite for conception", "garbhalambhana", "GRHYA_SAMSKARA",
     ("garbhalambhan", "garbhādhān"), (), ""),
    ("ANNAPRASANA", "first feeding", "annaprāśana", "GRHYA_SAMSKARA",
     ("annaprāśan",), (), ""),
    ("CUDAKARANA", "tonsure", "cūḍākaraṇa", "GRHYA_SAMSKARA",
     ("cūḍākaraṇ", "cūḍākarm", "caulakarm"), (), ""),
    ("GODANA", "the hair-cutting at sixteen", "godāna", "GRHYA_SAMSKARA",
     ("godāna", "godānik"), (), ""),
    ("KESANTA", "the beard-cutting", "keśānta", "GRHYA_SAMSKARA", ("keśānta",), (), ""),
    ("KARNAVEDHA", "ear-piercing", "karṇavedha", "GRHYA_SAMSKARA", ("karṇavedh",), (), ""),
    ("NAMADHEYA", "name-giving", "nāmadheya", "GRHYA_SAMSKARA",
     ("nāmadhey", "nāmakaraṇ"), (), ""),
    ("NISKRAMANA", "first outing", "niṣkramaṇa", "GRHYA_SAMSKARA", ("niṣkramaṇ",), (), ""),
    ("UPANAYANA", "initiation", "upanayana", "GRHYA_SAMSKARA",
     ("upanayan", "brahmacary", "vratopanayan"), (), ""),
    ("SAMAVARTANA", "return from studentship", "samāvartana", "GRHYA_SAMSKARA",
     ("samāvartan", "samavartan"), (), ""),
    ("UPAKARMA", "beginning the Veda study", "upākarma", "GRHYA_OTHER",
     ("upākarm", "upākaraṇ"), (), ""),
    ("UTSARJANA", "closing the Veda study", "utsarjana", "GRHYA_OTHER",
     ("utsarjan", "utsarga"), (), ""),
    ("PITRMEDHA", "funeral rites", "pitṛmedha", "GRHYA_SAMSKARA",
     ("pitṛmedh", "antyeṣṭi", "śmaśān"), (),
     "EXISTING as SocialRite PITRYANA-FUNERARY-RITE. `antyesti` is ZERO in this corpus; "
     "`pitrmedha` and `smasana` are the attested forms."),
    ("SRADDHA", "offering to the ancestors", "śrāddha", "GRHYA_PAKAYAJNA",
     ("śrāddh",), (), ""),
    ("ASTAKA", "the astaka offerings", "aṣṭakā", "GRHYA_PAKAYAJNA",
     ("aṣṭakā", "anvaṣṭaky"), (), ""),
    ("MADHUPARKA", "the honey-mixture reception", "madhuparka", "GRHYA_OTHER",
     ("madhuparka",), (), ""),
    ("STHALIPAKA", "the cooked-food offering", "sthālīpāka", "GRHYA_PAKAYAJNA",
     ("sthālīpāk", "pākayajñ"), (), ""),
    ("BALIHARANA", "the bali offerings", "balīharaṇa", "GRHYA_PAKAYAJNA",
     ("balihar", "balīhar"), ("baliṃ", "balim", "balir", "balis", "baliḥ", "balayaḥ"),
     "The bare prefix `bali` is REJECTED and recorded: it reaches `balistha`, an "
     "adjective meaning strongest. Exact tokens only, plus the compound `balihara`."),
    ("SULAGAVA", "the spit-ox offering to Rudra", "śūlagava", "GRHYA_PAKAYAJNA",
     ("śūlagav",), (), ""),
    ("SVASTYAYANA", "the rite for a safe journey", "svastyayana", "GRHYA_OTHER",
     ("svastyayan",), (), ""),
    ("VRSOTSARGA", "releasing the bull", "vṛṣotsarga", "GRHYA_OTHER", ("vṛṣotsarg",), (), ""),
    ("GRHAPRAVESA", "entering a new house", "gṛhapraveśa", "GRHYA_OTHER",
     ("gṛhapraveś", "vāstoṣpat", "śālākarm"), (),
     "EXISTING as SocialRite SALA-HOUSE-BUILDING with 322 USED_FOR_RITE edges."),
    ("SNANA", "the ritual bath", "snāna", "GRHYA_OTHER", ("snānaprabhṛt",),
     ("snānam", "snānaṃ", "snāne", "snānena"), ""),
    ("ABHICARA", "hostile rite", "abhicāra", "ATHARVAN_MAGICAL", ("abhicār",), (), ""),
    ("PRAYASCITTA-GRHYA", "expiation, grhya", "prāyaścitta", "GRHYA_OTHER",
     ("prāyaścitta",), (), ""),
    ("CAITRI", "the Caitri offering", "caitrī", "GRHYA_PAKAYAJNA", ("caitrī",), (), ""),
    ("ASVAYUJI", "the Asvayuji offering", "āśvayujī", "GRHYA_PAKAYAJNA", ("āśvayuj",), (), ""),
    ("SRAVANA", "the Sravana offering", "śrāvaṇa", "GRHYA_PAKAYAJNA",
     ("śrāvaṇ", "śrāvaṇī"), (), ""),
    ("AGRAHAYANI", "the Agrahayani offering", "āgrahāyaṇī", "GRHYA_PAKAYAJNA",
     ("āgrahāyaṇ",), (), ""),

    # --- candidates expected to fail, kept so the negative is recorded ------------------
    ("SARPABALI", "the serpent offering", "sarpabali", "GRHYA_PAKAYAJNA",
     ("sarpabali",), (), "Expected absent; kept so the zero is recorded."),
    ("NAKSATRAKALPA", "the naksatra rites", "nakṣatrakalpa", "ATHARVAN_MAGICAL",
     ("nakṣatrakalp",), (), "Expected absent; kept so the zero is recorded."),
    ("PUSTIKARMAN", "prosperity rite", "puṣṭikarman", "ATHARVAN_MAGICAL",
     ("puṣṭikarm",), (), "Expected absent; kept so the zero is recorded."),
    ("SANTIKARMAN", "appeasement rite", "śāntikarman", "ATHARVAN_MAGICAL",
     ("śāntikarm",), (), "Expected absent; kept so the zero is recorded."),
    ("MANIBANDHANA", "binding on an amulet", "maṇibandhana", "ATHARVAN_MAGICAL",
     ("maṇibandhan", "maṇibandh"), (),
     "The compound is absent; the act is present as `manim badhnati`, which the implement "
     "layer picks up instead. Kept so the compound's zero is recorded."),
    ("VRATYASTOMA", "the vratyastoma", "vrātyastoma", "SRAUTA_SOMA",
     ("vrātyastom", "vratyastom"), (), "Expected absent; kept so the zero is recorded."),
    ("RTUPEYA", "the rtupeya", "ṛtupeya", "SRAUTA_SOMA",
     ("ṛtupey",), (), "Expected absent; kept so the zero is recorded."),
    ("ATITHYESTI", "the guest offering", "atithyeṣṭi", "SRAUTA_SOMA",
     ("atithyeṣṭ", "ātithyeṣṭ", "ātithy"), (), ""),
    ("SATARUDRIYA", "the Satarudriya", "śatarudrīya", "SRAUTA_OTHER",
     ("śatarudr",), (), "Expected absent; kept so the zero is recorded."),
    ("TRAIDHATAVI", "the traidhatavi isti", "traidhātavī", "SRAUTA_HAVIRYAJNA",
     ("traidhātav",), (), "Expected absent; kept so the zero is recorded."),
    ("PANCAYAJNA", "the five great sacrifices", "pañcayajña", "GRHYA_PAKAYAJNA",
     ("pañcayajñ", "pañcamahāyajñ"), (), "Expected absent; kept so the zero is recorded."),
    ("INDRADHVAJA", "raising Indra's banner", "indradhvaja", "GRHYA_OTHER",
     ("indradhvaj",), (), "Expected absent; kept so the zero is recorded."),
)

# Rites already carrying a node, so the build measures and never re-mints them.
EXISTING_RITUAL_KEYS = frozenset({
    "VG:CONCEPT:YAJNA-SACRIFICE", "VG:CONCEPT:SOMA-PRESSING", "VG:CONCEPT:AGNIHOTRA",
    "VG:CONCEPT:DIKSA-CONSECRATION", "VG:CONCEPT:AGNI-CITI-FIRE-PILING",
    "VG:CONCEPT:ASVAMEDHA-HORSE-SACRIFICE", "VG:CONCEPT:GRAHA-SOMA-DRAWING",
    "VG:CONCEPT:SAUTRAMANI",
})
EXISTING_SOCIAL_RITE_KEYS = frozenset({
    "VG:CONCEPT:VIVAHA-MARRIAGE", "VG:CONCEPT:PITRYANA-FUNERARY-RITE",
    "VG:CONCEPT:SALA-HOUSE-BUILDING", "VG:CONCEPT:SABHA-ASSEMBLY",
    "VG:CONCEPT:PRASUTI-CHILDBIRTH",
})
# Rite candidates whose concept already exists under another key.
RITE_ALREADY_MODELLED_AS = {
    "VIVAHA-MARRIAGE": "VG:CONCEPT:VIVAHA-MARRIAGE",
    "PITRMEDHA": "VG:CONCEPT:PITRYANA-FUNERARY-RITE",
    "GRHAPRAVESA": "VG:CONCEPT:SALA-HOUSE-BUILDING",
}

# Sub-rite relations, each one read in its own witness rather than inferred from
# co-occurrence. `locator` is the line that states the relation.
SUB_RITE_CLAIMS = (
    ("VAISVADEVA-PARVAN", "CATURMASYA", "PART_OF_RITE",
     "The first of the four caturmasya parvans."),
    ("VARUNAPRAGHASA", "CATURMASYA", "PART_OF_RITE",
     "The second of the four caturmasya parvans."),
    ("SAKAMEDHA", "CATURMASYA", "PART_OF_RITE",
     "The third of the four caturmasya parvans."),
    ("SUNASIRIYA", "CATURMASYA", "PART_OF_RITE",
     "The fourth of the four caturmasya parvans."),
    ("AGNISTOMA", "JYOTISTOMA", "FORM_OF_RITE",
     "The first of the jyotistoma's samsthas."),
    ("UKTHYA", "JYOTISTOMA", "FORM_OF_RITE", "A jyotistoma samstha."),
    ("SODASIN", "JYOTISTOMA", "FORM_OF_RITE", "A jyotistoma samstha."),
    ("ATIRATRA", "JYOTISTOMA", "FORM_OF_RITE", "A jyotistoma samstha."),
    ("APTORYAMA", "JYOTISTOMA", "FORM_OF_RITE", "A jyotistoma samstha."),
    ("DIKSA-CONSECRATION", "SOMA-PRESSING", "PART_OF_RITE",
     "The consecration that opens a soma sacrifice."),
    ("UPASAD", "SOMA-PRESSING", "PART_OF_RITE", "The upasad days of a soma sacrifice."),
    ("PRAVARGYA", "SOMA-PRESSING", "PART_OF_RITE", "Performed on the upasad days."),
    ("TANUNAPTRA", "SOMA-PRESSING", "PART_OF_RITE", "Part of the soma sacrifice."),
    ("AVABHRTHA", "SOMA-PRESSING", "PART_OF_RITE", "The bath that closes it."),
    ("PRAYANIYA", "SOMA-PRESSING", "PART_OF_RITE", "The opening isti."),
    ("UDAYANIYA", "SOMA-PRESSING", "PART_OF_RITE", "The closing isti."),
    ("AGNISOMIYA-PASU", "SOMA-PRESSING", "PART_OF_RITE",
     "The Agni-Soma victim offered on the day before the pressing."),
    ("VASATIVARI", "SOMA-PRESSING", "PART_OF_RITE", "The waters drawn for the pressing."),
    ("BAHISPAVAMANA", "SOMA-PRESSING", "PART_OF_RITE", "The first stotra of the pressing day."),
    ("HARIYOJANA", "SOMA-PRESSING", "PART_OF_RITE", "The last graha of the pressing day."),
    ("APYAYANA", "SOMA-PRESSING", "PART_OF_RITE", "The swelling of the soma."),
    ("ABHIPLAVA", "GAVAMAYANA", "PART_OF_RITE", "A six-day period of the year-long session."),
    ("PRSTHYA", "GAVAMAYANA", "PART_OF_RITE", "A six-day period of the year-long session."),
)

# ---------------------------------------------------------------------------------------
# RITUAL ROLES. The sixteen officiants are a Srautasutra schema, not a Samhita one; the
# denominator is labelled as such wherever it is reported, which is what GAP-RITUAL-004
# asks for.
# ---------------------------------------------------------------------------------------

# (key, label_en, label_sa, group, aliases, exact_tokens, in_classical_sixteen)
ROLE_CANDIDATES = (
    ("HOTR-PRIEST", "hotr", "hotṛ", "HOTR", ("hotṛṣ", "hotrak"),
     ("hotā", "hotāram", "hotāraṃ", "hotāraḥ", "hotuḥ", "hotre", "hotrā", "hotṛn"), True),
    ("MAITRAVARUNA-PRIEST", "maitravaruna", "maitrāvaruṇa", "HOTR",
     ("maitrāvaruṇ",), (), True),
    ("ACCHAVAKA-PRIEST", "acchavaka", "acchāvāka", "HOTR",
     ("acchāvāk", "achāvāk"), (), True),
    ("GRAVASTUT-PRIEST", "gravastut", "grāvastut", "HOTR", ("grāvastut",), (), True),
    ("ADHVARYU-PRIEST", "adhvaryu", "adhvaryu", "ADHVARYU", ("adhvaryu",), (), True),
    ("PRATIPRASTHATR-PRIEST", "pratiprasthatr", "pratiprasthātṛ", "ADHVARYU",
     ("pratiprasthāt",), (), True),
    ("NESTR-LEADER", "nestr", "neṣṭṛ", "ADHVARYU", ("neṣṭṛ", "neṣṭā", "neṣṭr"), (), True),
    ("UNNETR-PRIEST", "unnetr", "unnetṛ", "ADHVARYU",
     ("unnetṛ", "unnetā", "unnetr"), (), True),
    ("UDGATR-CHANTER", "udgatr", "udgātṛ", "UDGATR",
     ("udgātṛ", "udgātā", "udgātr"), (), True),
    ("PRASTOTR-PRIEST", "prastotr", "prastotṛ", "UDGATR",
     ("prastotṛ", "prastotā", "prastotr"), (), True),
    ("PRATIHARTR-PRIEST", "pratihartr", "pratihartṛ", "UDGATR",
     ("pratihartṛ", "pratihartā", "pratihartr"), (), True),
    ("SUBRAHMANYA-PRIEST", "subrahmanya", "subrahmaṇya", "UDGATR",
     ("subrahmaṇy",), (), True),
    ("BRAHMAN-PRIEST", "brahman priest", "brahman", "BRAHMAN",
     (), ("brahmā", "brahman", "brahmaṇ", "brahmaṇā", "brahmāṇam"), True),
    ("BRAHMANACCHAMSIN-PRIEST", "brahmanacchamsin", "brāhmaṇācchaṃsin", "BRAHMAN",
     ("brāhmaṇācchaṃs", "brāhmaṇāchaṃs"), (), True),
    ("AGNIDH-FIRE-KINDLER", "agnidh", "agnīdh", "BRAHMAN",
     ("agnīdh", "agnīt"), (), True),
    ("POTR-PURIFIER", "potr", "potṛ", "BRAHMAN", ("potṛt",),
     ("potā", "potaḥ", "potre", "potuḥ", "potur", "potrā", "potāram", "potāraṃ"), True),
    # outside the sixteen
    ("PRASASTR-DIRECTOR", "prasastr", "praśāstṛ", "HOTR",
     ("praśāstṛ", "praśāstā", "praśāstr", "prāśāstr"), (), False),
    ("YAJAMANA-SACRIFICER", "sacrificer", "yajamāna", "PATRON", ("yajamān",), (), False),
    ("PUROHITA-CHAPLAIN", "household priest", "purohita", "PATRON", ("purohit",), (), False),
    ("BRAHMACARIN-STUDENT", "vedic student", "brahmacārin", "OTHER",
     ("brahmacāri",), (), False),
    ("RTVIJ-OFFICIANT", "officiant", "ṛtvij", "GENERIC", ("ṛtvij", "ārtvijy"), (), False),
    ("SADASYA-PRIEST", "sadasya", "sadasya", "OTHER", ("sadasya",), (), False),
    ("GRHAPATI-HOUSEHOLDER", "session householder", "gṛhapati", "PATRON",
     ("gṛhapati",), (), False),
    ("DIKSITA-CONSECRATED", "the consecrated sacrificer", "dīkṣita", "PATRON",
     ("dīkṣit",), (), False),
    ("ACARYA-TEACHER", "teacher", "ācārya", "OTHER", ("ācārya",), (), False),
    ("PATNI-SACRIFICERS-WIFE", "the sacrificer's wife", "patnī", "PATRON",
     ("patnīsaṃnahan",), ("patnī", "patnīm", "patnīṃ", "patnyā", "patnyai"), False),
    ("SAMITR-BUTCHER", "samitr", "śamitṛ", "OTHER",
     ("śamitṛ", "śamitā", "śamitr"), (), False),
)
EXISTING_ROLE_KEYS = frozenset({
    "VG:CONCEPT:ADHVARYU-PRIEST", "VG:CONCEPT:AGNIDH-FIRE-KINDLER",
    "VG:CONCEPT:BRAHMACARIN-STUDENT", "VG:CONCEPT:BRAHMAN-PRIEST",
    "VG:CONCEPT:HOTR-PRIEST", "VG:CONCEPT:NESTR-LEADER", "VG:CONCEPT:POTR-PURIFIER",
    "VG:CONCEPT:PRASASTR-DIRECTOR", "VG:CONCEPT:PUROHITA-CHAPLAIN",
    "VG:CONCEPT:UDGATR-CHANTER", "VG:CONCEPT:YAJAMANA-SACRIFICER",
})

# ---------------------------------------------------------------------------------------
# IMPLEMENTS. The three GAP-RITUAL-003 names as missing come first.
# ---------------------------------------------------------------------------------------
IMPLEMENT_CANDIDATES = (
    ("MANI-AMULET", "amulet", "maṇi", ("maṇibandh",),
     ("maṇiḥ", "maṇim", "maṇiṃ", "maṇinā", "maṇayaḥ", "maṇīn"), True),
    ("DUNDUBHI-DRUM", "drum", "dundubhi", ("dundubh",), (), True),
    ("AUDUMBARA-AMULET", "udumbara amulet", "audumbara", ("audumbar",), (), True),
    ("YUPA-SACRIFICIAL-POST", "sacrificial post", "yūpa",
     ("yūpa", "aśvayūpa"),
     ("yūpaḥ", "yūpam", "yūpaṃ", "yūpe", "yūpasya", "yūpān", "yūpau"), True),
    ("VEDI-ALTAR", "altar", "vedi", ("vedikṛ",),
     ("vediḥ", "vedim", "vediṃ", "vedyā", "vedyām", "vedeḥ", "vedīm"), True),
    ("BARHIS-SACRED-GRASS", "sacred grass", "barhis", ("barhi",), (), True),
    ("SRUC-LADLE", "offering ladle", "sruc", (), ("sruk", "srucaḥ", "srucā", "srucam",
                                                   "srucaṃ", "srucau", "srucāṃ"), True),
    ("SRUVA-DIPPING-SPOON", "dipping spoon", "sruva", ("sruva",), (), False),
    ("JUHU-SPOON", "juhu spoon", "juhū", ("juhūp",),
     ("juhū", "juhūm", "juhūṃ", "juhvā", "juhvām", "juhūś", "juhūḥ"), False),
    ("UPABHRT-SPOON", "upabhrt spoon", "upabhṛt", ("upabhṛt",), (), False),
    ("DHRUVA-SPOON", "dhruva spoon", "dhruvā", ("dhruvāy",),
     ("dhruvā", "dhruvām", "dhruvāṃ", "dhruvayā"), False),
    ("SPHYA-WOODEN-SWORD", "wooden sword", "sphya", ("sphya",), (), False),
    ("KAPALA-POTSHERD", "potsherd", "kapāla", ("kapāl",), (), False),
    ("ULUKHALA-MORTAR", "mortar", "ulūkhala", ("ulūkhal",), (), True),
    ("MUSALA-PESTLE", "pestle", "musala", ("musal",), (), False),
    ("DRSAD-GRINDING-STONE", "grinding stone", "dṛṣad", ("dṛṣad",), (), False),
    ("UPALA-UPPER-STONE", "upper grinding stone", "upalā", ("upalā",), (), False),
    ("SURPA-WINNOWING-BASKET", "winnowing basket", "śūrpa", ("śūrpa",), (), False),
    ("KRSNAJINA-BLACK-ANTELOPE-SKIN", "black antelope skin", "kṛṣṇājina",
     ("kṛṣṇājin",), (), False),
    ("SAMYA-YOKE-PIN", "yoke-pin", "śamyā", ("śamyā",), (), False),
    ("ASMAN-PRESSING-STONE", "pressing stone", "grāvan", ("grāva",), (), True),
    ("CAMASA-CUP", "cup", "camasa", ("camas",), (), True),
    ("KALASA-JAR", "jar", "kalaśa", ("kalaś",), (), True),
    ("DRONAKALASA-WOODEN-TUB", "wooden soma tub", "droṇakalaśa", ("droṇakalaś",), (), True),
    ("PAVITRA-STRAINER", "strainer", "pavitra", ("pavitr",), (), True),
    ("VAYAVYA-VAYU-CUP", "vayu cup", "vāyavya", ("vāyavy",), (), True),
    ("ISTAKA-BRICK", "ritual brick", "iṣṭakā", ("iṣṭak",), (), True),
    ("SAMIDH-FUEL", "kindling", "samidh", ("samidh", "samidhy"), (), True),
    ("IDHMA-FIREWOOD", "firewood", "idhma", ("idhma",), (), False),
    ("VEDA-GRASS-BUNDLE", "grass bundle", "veda", (),
     ("vedaḥ", "vedena", "vedam"), False),
    ("PRANITA-WATER", "the pranita waters", "praṇītā", ("praṇītā", "praṇayan"), (), False),
    ("AGNIHOTRAHAVANI-LADLE", "agnihotra ladle", "agnihotrahavaṇī",
     ("agnihotrahavaṇ",), (), False),
    ("PRASITRAHARANA-DISH", "prasitra dish", "prāśitraharaṇa", ("prāśitraharaṇ",), (), False),
    ("PATRI-DISH", "dish", "pātrī", ("pātrī",), (), False),
    ("SAKATA-CART", "cart", "śakaṭa", ("śakaṭ",), (), False),
    ("YOKTRA-GIRDLE", "girdle", "yoktra", ("yoktr",), (), False),
    ("MEKHALA-GIRDLE", "student's girdle", "mekhalā", ("mekhal",), (), False),
    ("AJINA-SKIN", "skin garment", "ajina", ("ajina",), (), False),
    ("DANDA-STAFF", "staff", "daṇḍa", ("daṇḍa",), (), False),
    ("RATHA-CHARIOT", "chariot", "ratha", (),
     ("rathaḥ", "ratham", "rathaṃ", "rathena", "rathe", "rathasya"), True),
    ("SVADHITI-AXE", "axe", "svadhiti", ("svadhit",), (), True),
    ("AYUDHA-WEAPON", "weapon", "āyudha", ("āyudh",), (), True),
    ("JYA-BOWSTRING", "bowstring", "jyā", (), ("jyā", "jyām", "jyāṃ", "jyayā"), True),
    ("PASA-NOOSE", "noose", "pāśa", (), ("pāśaḥ", "pāśam", "pāśaṃ", "pāśena", "pāśān"), True),
    ("VARMAN-ARMOUR", "armour", "varman", ("varmaṇ",), ("varma",), True),
    ("VAJRA-THUNDERBOLT", "thunderbolt", "vajra", ("vajra",), (), True),
    ("ANJANA-OINTMENT-BOX", "ointment", "añjana", ("añjan",), (), True),
)
EXISTING_OBJECT_KEYS = frozenset({
    "VG:CONCEPT:ASMAN-PRESSING-STONE", "VG:CONCEPT:AUDUMBARA-AMULET",
    "VG:CONCEPT:AYUDHA-WEAPON", "VG:CONCEPT:BARHIS-SACRED-GRASS", "VG:CONCEPT:CAMASA-CUP",
    "VG:CONCEPT:DRONAKALASA-WOODEN-TUB", "VG:CONCEPT:DUNDUBHI-DRUM",
    "VG:CONCEPT:ISTAKA-BRICK", "VG:CONCEPT:JYA-BOWSTRING", "VG:CONCEPT:KALASA-JAR",
    "VG:CONCEPT:MANI-AMULET", "VG:CONCEPT:PASA-NOOSE", "VG:CONCEPT:PAVITRA-STRAINER",
    "VG:CONCEPT:RATHA-CHARIOT", "VG:CONCEPT:SAMIDH-FUEL", "VG:CONCEPT:SRUC-LADLE",
    "VG:CONCEPT:SVADHITI-AXE", "VG:CONCEPT:ULUKHALA-MORTAR", "VG:CONCEPT:VAJRA-THUNDERBOLT",
    "VG:CONCEPT:VARMAN-ARMOUR", "VG:CONCEPT:VAYAVYA-VAYU-CUP", "VG:CONCEPT:VEDI-ALTAR",
    "VG:CONCEPT:YUPA-SACRIFICIAL-POST",
})

# ---------------------------------------------------------------------------------------
# OFFERINGS and MATERIALS
# ---------------------------------------------------------------------------------------
OFFERING_CANDIDATES = (
    ("HAVIS-OBLATION", "oblation", "havis", ("haviṣ", "havīṃ"), ("havis", "haviḥ"), True),
    ("PURODASA-CAKE", "sacrificial cake", "puroḍāśa", ("puroḍāś", "puroḍās"), (), False),
    ("CARU-GRUEL", "gruel oblation", "caru", (), ("caruḥ", "carum", "caruṃ", "caruṇā",
                                                   "caroḥ", "carūn"), False),
    ("AJYA-MELTED-BUTTER", "melted butter", "ājya", ("ājyabh",),
     ("ājyam", "ājyaṃ", "ājyena", "ājyasya", "ājye", "ājyāni", "ājyaiḥ"), False),
    ("AMIKSA-CURDLED-MILK", "curdled milk offering", "āmikṣā", ("āmikṣ",), (), False),
    ("DADHI-SOUR-MILK", "sour milk", "dadhi", (), ("dadhi", "dadhnā", "dadhyā"), False),
    ("PAYAS-MILK", "milk", "payas", ("payas",), (), True),
    ("GHRTA-CLARIFIED-BUTTER", "clarified butter", "ghṛta", ("ghṛta",), (), True),
    ("SOMA-DRINK", "soma juice", "soma", ("somapān",),
     ("somaḥ", "somam", "somaṃ", "somena", "somasya", "some", "somān"), True),
    ("PASU-LIVESTOCK", "livestock victim", "paśu", (),
     ("paśuḥ", "paśum", "paśuṃ", "paśunā", "paśavaḥ", "paśūn", "paśoḥ"), True),
    ("ASVA-HORSE", "horse", "aśva", (), ("aśvaḥ", "aśvam", "aśvaṃ", "aśvena", "aśvāḥ",
                                          "aśvān", "aśvasya"), True),
    ("GO-CATTLE", "cattle", "go", (), ("gauḥ", "gām", "gāṃ", "gāvaḥ", "gavām", "gobhiḥ"), True),
    ("AJA-GOAT", "goat", "aja", (), ("ajaḥ", "ajam", "ajaṃ", "ajena", "ajāḥ", "ajān"), False),
    ("ANNA-FOOD", "food", "anna", ("annād",), ("annam", "annaṃ", "annena", "annasya"), True),
    ("DAKSINA-PRIESTLY-GIFT", "priestly fee", "dakṣiṇā", ("dakṣiṇā",), (), True),
    ("VAPA-OMENTUM", "omentum", "vapā", ("vapāś", "vapāh"),
     ("vapā", "vapām", "vapāṃ", "vapayā", "vapāyāṃ", "vapāyām"), False),
    ("PRAJAPATI-PURODASA", "cake to Prajapati", "prājāpatya", ("prājāpaty",), (), False),
    ("SURA-SPIRITUOUS-LIQUOR", "spirituous liquor", "surā", ("surāg", "surāk"),
     ("surā", "surām", "surāṃ", "surayā", "surāyāḥ"), True),
    ("PARISRUT-FERMENTED-DRAUGHT", "fermented draught", "parisrut", ("parisru",), (), True),
    ("MADHU-HONEY", "honey", "madhu", ("madhu",), (), True),
    ("PURODASA-ASTAKAPALA", "cake on eight potsherds", "aṣṭākapāla",
     ("aṣṭākapāl",), (), False),
)
EXISTING_OFFERING_KEYS = frozenset({
    "VG:CONCEPT:ANNA-FOOD", "VG:CONCEPT:ASVA-HORSE", "VG:CONCEPT:DAKSINA-PRIESTLY-GIFT",
    "VG:CONCEPT:GHRTA-CLARIFIED-BUTTER", "VG:CONCEPT:GO-CATTLE", "VG:CONCEPT:HAVIS-OBLATION",
    "VG:CONCEPT:PASU-LIVESTOCK", "VG:CONCEPT:SOMA-DRINK",
})

MATERIAL_CANDIDATES = (
    ("VRIHI-RICE", "rice", "vrīhi", "PLANT", ("vrīhi",), (), False),
    ("YAVA-BARLEY", "barley", "yava", "PLANT", (), ("yavaḥ", "yavam", "yavaṃ", "yavān",
                                                     "yavaiḥ", "yavasya"), True),
    ("TILA-SESAME", "sesame", "tila", "PLANT", (), ("tilaḥ", "tilam", "tilaṃ", "tilān",
                                                     "tilaiḥ"), False),
    ("MASA-BEAN", "bean", "māṣa", "PLANT", ("māṣat",),
     ("māṣaḥ", "māṣam", "māṣaṃ", "māṣān", "māṣaiḥ", "māṣā"), False),
    ("PRIYANGU-MILLET", "millet", "priyaṅgu", "PLANT", ("priyaṅgu",), (), False),
    ("GAVIDHUKA-GRAIN", "gavidhuka grain", "gavīdhukā", "PLANT", ("gavīdhuk",), (), False),
    ("NIVARA-WILD-RICE", "wild rice", "nīvāra", "PLANT", ("nīvār",), (), False),
    ("SYAMAKA-MILLET", "syamaka millet", "śyāmāka", "PLANT", ("śyāmāk",), (), False),
    ("TANDULA-HUSKED-GRAIN", "husked grain", "taṇḍula", "PLANT", ("taṇḍul",), (), False),
    ("DARBHA-GRASS", "darbha grass", "darbha", "PLANT", ("darbh",), (), True),
    ("KUSA-GRASS", "kusa grass", "kuśa", "PLANT", ("kuśām", "kuśai"),
     ("kuśaḥ", "kuśam", "kuśaṃ", "kuśān", "kuśena", "kuśāḥ"), False),
    ("PALASA-WOOD", "palasa wood", "palāśa", "PLANT", ("palāś",), (), False),
    ("KHADIRA-WOOD", "khadira wood", "khadira", "PLANT", ("khadir",), (), True),
    ("BILVA-WOOD", "bilva wood", "bilva", "PLANT", ("bilva",), (), False),
    ("UDUMBARA-WOOD", "udumbara wood", "udumbara", "PLANT", ("udumbar",), (), False),
    ("ASVATTHA-WOOD", "asvattha wood", "aśvattha", "PLANT", ("aśvatth",), (), True),
    ("NYAGRODHA-WOOD", "nyagrodha wood", "nyagrodha", "PLANT", ("nyagrodh",), (), False),
    ("VIKANKATA-WOOD", "vikankata wood", "vikaṅkata", "PLANT", ("vikaṅkat",), (), False),
    ("PLAKSA-WOOD", "plaksa wood", "plakṣa", "PLANT", ("plakṣa",), (), False),
    ("SAMI-WOOD", "sami wood", "śamī", "PLANT", ("śamīgarbh",), ("śamī", "śamīm"), False),
    ("KARSMARYA-WOOD", "karsmarya wood", "kārṣmarya", "PLANT", ("kārṣmary",), (), False),
    ("DEVADARU-WOOD", "devadaru wood", "devadāru", "PLANT", ("devadār",), (), False),
    ("HIRANYA-GOLD", "gold", "hiraṇya", "SUBSTANCE", ("hiraṇy",), (), True),
    ("RAJATA-SILVER", "silver", "rajata", "SUBSTANCE", ("rajat",), (), True),
    ("LOHA-COPPER", "copper", "loha", "SUBSTANCE", (),
     ("lohaḥ", "loham", "lohaṃ", "lohena", "lohasya"), True),
    ("TRAPU-TIN", "tin", "trapu", "SUBSTANCE", ("trapu",), (), True),
    ("SISA-LEAD", "lead", "sīsa", "SUBSTANCE", ("sīsen", "sīsam"),
     ("sīsam", "sīsaṃ", "sīsena", "sīsaḥ"), True),
    ("AYAS-METAL", "metal", "ayas", "SUBSTANCE", (),
     ("ayaḥ", "ayasā", "ayasaḥ", "ayasi"), True),
    ("SYAMA-DARK-METAL", "dark metal", "śyāma", "SUBSTANCE", ("śyāma",), (), True),
    ("KRSNALA-GOLD-BEAD", "krsnala gold bead", "kṛṣṇala", "SUBSTANCE", ("kṛṣṇal",), (), False),
    ("LAVANA-SALT", "salt", "lavaṇa", "SUBSTANCE", ("lavaṇ",), (), False),
    ("MRTTIKA-CLAY", "clay", "mṛttikā", "SUBSTANCE", ("mṛttik",), (), False),
    ("BHASMA-ASH", "ash", "bhasma", "SUBSTANCE", ("bhasma",), (), False),
    ("GOMAYA-COWDUNG", "cowdung", "gomaya", "SUBSTANCE", ("gomay",), (), False),
    ("URNA-WOOL", "wool", "ūrṇā", "SUBSTANCE", ("ūrṇās", "ūrṇāv", "ūrṇam"),
     ("ūrṇā", "ūrṇām", "ūrṇāṃ", "ūrṇayā", "ūrṇāyāḥ"), False),
)

# ---------------------------------------------------------------------------------------
# RITUAL ACTIONS
# ---------------------------------------------------------------------------------------
ACTION_CANDIDATES = (
    ("NIRVAPA-TAKING-OUT", "taking out the grain", "nirvāpa", ("nirvap", "nirvāp"), ()),
    ("PROKSANA-SPRINKLING", "sprinkling", "prokṣaṇa", ("prokṣ",), ()),
    ("AVADANA-CUTTING-PORTIONS", "cutting the portions", "avadāna",
     ("avadā", "avadān", "avadya"), ()),
    ("HOMA-POURING-INTO-FIRE", "pouring into the fire", "homa",
     ("homa",), ("hutam", "hutaṃ", "juhoti", "juhuyāt")),
    ("ABHIGHARANA-BASTING", "basting with butter", "abhighāraṇa",
     ("abhighār",), ()),
    ("UPASTARANA-UNDERLAYING", "underlaying with butter", "upastaraṇa", ("upastar",), ()),
    ("PRANAYANA-CARRYING-FORWARD", "carrying the fire forward", "praṇayana",
     ("praṇay", "praṇīy"), ()),
    ("ADHISRAYANA-PUTTING-ON-FIRE", "putting on the fire", "adhiśrayaṇa",
     ("adhiśray", "adhiśrit"), ()),
    ("UTPAVANA-STRAINING", "straining", "utpavana", ("utpav", "utpūt"), ()),
    ("SAMNAYANA-MIXING", "mixing the milk", "saṃnayana", ("saṃnay",), ()),
    ("VYUHANA-SPREADING-OUT", "spreading out", "vyūhana",
     ("vyūhan", "vyūhat", "vyūhya", "vyūḍh"), ()),
    ("PARISAMUHANA-SWEEPING", "sweeping together", "parisamūhana", ("parisamūh",), ()),
    ("ULLEKHANA-DRAWING-LINES", "drawing the lines", "ullekhana", ("ullikh", "ullekh"), ()),
    ("AVAHANANA-HUSKING", "husking", "avahanana", ("avahan",), ()),
    ("SRAPANA-COOKING", "cooking", "śrapaṇa", ("śrap", "śrapaṇ", "śṛt"), ()),
    ("ANVADHANA-PUTTING-ON-FUEL", "putting on the fuel", "anvādhāna", ("anvādh",), ()),
    ("SAMIDADHANA-KINDLING", "laying on the kindling", "samidādhāna",
     ("samidādh", "samidhādh"), ()),
    ("AGHARA-BUTTER-STREAM", "the butter stream", "āghāra", ("āghār",), ()),
    ("IDA-THE-IDA-PORTION", "the ida portion", "iḍā", ("iḍopahvay",),
     ("iḍā", "iḍām", "iḍāṃ", "iḍāyai")),
    ("PRASITRA-THE-BRAHMANS-PORTION", "the brahman's portion", "prāśitra",
     ("prāśitr",), ()),
    ("SVAHAKARA-OFFERING-CALL", "the svaha call", "svāhākāra", ("svāhākār",), ()),
    ("VASATKARA-VASAT-CALL", "the vasat call", "vaṣaṭkāra", ("vaṣaṭkār", "vauṣaṭ"), ()),
    ("PRAYAJA-FORE-OFFERINGS", "the fore-offerings", "prayāja", ("prayāj",), ()),
    ("ANUYAJA-AFTER-OFFERINGS", "the after-offerings", "anuyāja", ("anuyāj",), ()),
    ("PATNISAMYAJA-WIVES-OFFERINGS", "the wives' offerings", "patnīsaṃyāja",
     ("patnīsaṃyāj",), ()),
    ("SVISTAKRT-OFFERING", "the Svistakrt offering", "sviṣṭakṛt", ("sviṣṭakṛt",), ()),
    ("SAMISTAYAJUS-CLOSING-FORMULA", "the closing formula", "samiṣṭayajus",
     ("samiṣṭayaju",), ()),
    ("JAPA-MUTTERING", "muttering", "japa", ("japat", "japan", "japit"),
     ("japati", "japet", "japam", "japaṃ", "japtvā", "japaḥ")),
    ("UPAMSUYAJA-INAUDIBLE-OFFERING", "the inaudible offering", "upāṃśuyāja",
     ("upāṃśuyāj", "upāṃśu"), ()),
    ("STOMA-PRAISE", "praise", "stoma", ("stoma",), ()),
    ("NAMAS-HOMAGE", "homage", "namas", ("namas", "namaḥ"), ()),
    ("GRAHANA-RITUAL-TAKING-UP", "ritual taking up", "grahaṇa", ("grahaṇ",), ()),
    ("DANA-LIBERALITY", "liberality", "dāna", (),
     ("dānam", "dānaṃ", "dānena", "dānasya", "dānāni")),
    ("PRATAHSAVANA-MORNING-PRESSING", "morning pressing", "prātaḥsavana",
     ("prātaḥsavan", "prātaḥsāv", "prātaḥsav"), ()),
    ("MADHYANDINA-SAVANA-MIDDAY-PRESSING", "midday pressing", "mādhyandina savana",
     ("mādhyaṃdin", "mādhyandin"), ()),
    ("TRTIYA-SAVANA-THIRD-PRESSING", "third pressing", "tṛtīya savana",
     ("tṛtīyasavan",), ()),
)
EXISTING_ACTION_KEYS = frozenset({
    "VG:CONCEPT:AVABHRTHA-CONCLUDING-BATH", "VG:CONCEPT:DANA-LIBERALITY",
    "VG:CONCEPT:GRAHANA-RITUAL-TAKING-UP", "VG:CONCEPT:HOMA-POURING-INTO-FIRE",
    "VG:CONCEPT:JANMAN-BIRTH", "VG:CONCEPT:MADHYANDINA-SAVANA-MIDDAY-PRESSING",
    "VG:CONCEPT:NAMAS-HOMAGE", "VG:CONCEPT:PRATAHSAVANA-MORNING-PRESSING",
    "VG:CONCEPT:STOMA-PRAISE", "VG:CONCEPT:SVAHAKARA-OFFERING-CALL",
    "VG:CONCEPT:TRTIYA-SAVANA-THIRD-PRESSING", "VG:CONCEPT:YUDH-BATTLE",
})

# ---------------------------------------------------------------------------------------
# DEITY DATIVES. The dative case is the statement of recipiency, so a dative theonym
# beside an offering word is the source saying who receives what. These forms are
# lexically unambiguous -- no parser needed -- which is why the deity-to-offering predicate
# GAP-RITUAL-005 asks for can be derived deterministically rather than from co-occurrence.
# ---------------------------------------------------------------------------------------
DEITY_DATIVES = {
    "VG:DEVATA:AGNIH": ("agnaye",),
    "VG:DEVATA:INDRAH": ("indrāya",),
    "VG:DEVATA:SOMAH": ("somāya",),
    "VG:DEVATA:SURYAH": ("sūryāya",),
    "VG:DEVATA:VAYUH": ("vāyave",),
    "VG:DEVATA:MITRAH": ("mitrāya",),
    "VG:DEVATA:VARUNAH": ("varuṇāya",),
    "VG:DEVATA:SAVITA": ("savitre",),
    "VG:DEVATA:PUSA": ("pūṣṇe",),
    "VG:DEVATA:BRHASPATIH": ("bṛhaspataye", "brahmaṇaspataye"),
    
    "VG:DEVATA:VISNUH": ("viṣṇave",),
    "VG:DEVATA:RUDRAH": ("rudrāya",),
    "VG:DEVATA:MARUTAH": ("marudbhyaḥ", "marutbhyaḥ", "marudbhyo", "marutbhyo"),
    "VG:DEVATA:ASVINAU": ("aśvibhyām",),
    "VG:DEVATA:SARASVATI": ("sarasvatyai",),
    "VG:DEVATA:USAH": ("uṣase",),
    "VG:DEVATA:ADITYAH": ("ādityāya", "ādityebhyaḥ", "ādityebhyo"),
    "VG:DEVATA:VISVE-DEVAH": ("viśvebhyo", "viśvebhyaḥ"),
    "VG:DEVATA:PITARAH": ("pitṛbhyaḥ", "pitṛbhyo"),
    "VG:DEVATA:TVASTA": ("tvaṣṭre",),
    "VG:DEVATA:DHATA": ("dhātre",),
    
    "VG:DEVATA:SINIVALI": ("sinīvālyai",),
    
    "VG:DEVATA:YAMAH": ("yamāya",),
    
    "VG:DEVATA:SOMARUDRAU": ("somārudrābhyām",),
    "VG:DEVATA:INDRAGNI": ("indrāgnibhyām",),
    "VG:DEVATA:AGNISOMAU": ("agnīṣomābhyām",),
    "VG:DEVATA:MITRAVARUNAU": ("mitrāvaruṇābhyām",),
    "VG:DEVATA:INDRAVARUNAU": ("indrāvaruṇābhyām",),
    "VG:DEVATA:VISVAKARMA": ("viśvakarmaṇe",),
    "VG:DEVATA:APAH": ("apbhyaḥ", "abbhyaḥ", "apsu"),
}

# Four dative theonyms the ritual literature uses that the Devata layer has NO node for.
# They are recorded here rather than dropped, and rather than minted: the Devata class is
# derived from Samhita dedication, and a Brahmana's recipient is not thereby a Samhita
# dedicatee. Prajapati is the significant one -- he is the central deity of the Brahmana
# sacrificial system and has no Devata node at all.
DEITY_DATIVES_WITH_NO_GRAPH_NODE = {
    "prajāpataye": (
        "Prajapati. No :Devata node exists under any key containing PRAJA. He is the "
        "presiding deity of the Brahmana sacrificial system, so his absence from the "
        "Devata layer is a real finding about that layer's Samhita-derived scope, not a "
        "defect in this artifact."
    ),
    "vaiśvānarāya": (
        "Vaisvanara. No :Devata node contains VAISV. Ordinarily read as an epithet of "
        "Agni, and the graph has JATAVEDA-AGNIH but no vaisvanara form."
    ),
    "anumatyai": ("Anumati. No node. Named in the Yajurvedic isti literature."),
    "aryamṇe": ("Aryaman. No node, although the Aditya group is present."),
}

OFFERING_WORDS_FOR_DEITY_LINK = (
    "puroḍāś", "puroḍās", "caru", "havi", "ājya", "āmikṣ", "payas", "ghṛta", "dadhi",
    "paśu", "soma", "sthālīpāk", "aṣṭākapāl", "nirvap", "nirvāp", "juhoti", "juhuyāt",
    "yajati", "yajeta", "ālabhate", "ālabheta", "hutam",
)
