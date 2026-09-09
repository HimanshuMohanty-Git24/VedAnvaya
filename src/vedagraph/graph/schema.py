"""Graph schema: node labels, relationship types, constraints, and indexes."""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Node labels
# ---------------------------------------------------------------------------

LABEL_WORK: Final = "Work"
LABEL_PASSAGE: Final = "Passage"
LABEL_MANTRA: Final = "Mantra"         # sublabel for leaf MANTRA passages
LABEL_TEXT_VERSION: Final = "TextVersion"
LABEL_TRANSLATION: Final = "Translation"
LABEL_SOURCE: Final = "Source"
LABEL_SOURCE_ARTIFACT: Final = "SourceArtifact"
LABEL_RISHI: Final = "Rishi"
LABEL_DEVATA: Final = "Devata"
LABEL_CHANDAS: Final = "Chandas"
LABEL_LEMMA: Final = "Lemma"
LABEL_QA_ISSUE: Final = "QAIssue"

# ---------------------------------------------------------------------------
# Relationship types
# ---------------------------------------------------------------------------

REL_CONTAINS: Final = "CONTAINS"
REL_HAS_TEXT_VERSION: Final = "HAS_TEXT_VERSION"
REL_HAS_TRANSLATION: Final = "HAS_TRANSLATION"
REL_HAS_RISHI: Final = "HAS_RISHI"
REL_HAS_DEVATA: Final = "HAS_DEVATA"
REL_HAS_CHANDAS: Final = "HAS_CHANDAS"
REL_MENTIONS_LEMMA: Final = "MENTIONS_LEMMA"
REL_MENTIONS_ENTITY: Final = "MENTIONS_ENTITY"
REL_EXACT_PARALLEL_OF: Final = "EXACT_PARALLEL_OF"
REL_PARALLEL_TO: Final = "PARALLEL_TO"
REL_EXTRACTED_FROM_CONTAINER: Final = "EXTRACTED_FROM_CONTAINER"
REL_ASSERTED_BY_SOURCE: Final = "ASSERTED_BY_SOURCE"
REL_HAS_QA_ISSUE: Final = "HAS_QA_ISSUE"


# ---------------------------------------------------------------------------
# Uniqueness constraints (one constraint per entity identity field)
# ---------------------------------------------------------------------------

CONSTRAINTS: Final[list[str]] = [
    # Work
    "CREATE CONSTRAINT work_id_unique IF NOT EXISTS FOR (n:Work) REQUIRE n.work_id IS UNIQUE",
    # Passage
    "CREATE CONSTRAINT passage_canonical_key_unique IF NOT EXISTS FOR (n:Passage) REQUIRE n.canonical_key IS UNIQUE",  # noqa: E501
    "CREATE CONSTRAINT passage_entity_id_unique IF NOT EXISTS FOR (n:Passage) REQUIRE n.entity_id IS UNIQUE",  # noqa: E501
    "CREATE CONSTRAINT passage_canonical_urn_unique IF NOT EXISTS FOR (n:Passage) REQUIRE n.canonical_urn IS UNIQUE",  # noqa: E501
    # TextVersion
    "CREATE CONSTRAINT text_version_id_unique IF NOT EXISTS FOR (n:TextVersion) REQUIRE n.text_id IS UNIQUE",  # noqa: E501
    # Translation
    "CREATE CONSTRAINT translation_id_unique IF NOT EXISTS FOR (n:Translation) REQUIRE n.translation_id IS UNIQUE",  # noqa: E501
    # Source
    "CREATE CONSTRAINT source_id_unique IF NOT EXISTS FOR (n:Source) REQUIRE n.source_id IS UNIQUE",
    # SourceArtifact
    "CREATE CONSTRAINT source_artifact_id_unique IF NOT EXISTS FOR (n:SourceArtifact) REQUIRE n.artifact_id IS UNIQUE",  # noqa: E501
    # Rishi
    "CREATE CONSTRAINT rishi_entity_key_unique IF NOT EXISTS FOR (n:Rishi) REQUIRE n.entity_key IS UNIQUE",  # noqa: E501
    # Devata
    "CREATE CONSTRAINT devata_entity_key_unique IF NOT EXISTS FOR (n:Devata) REQUIRE n.entity_key IS UNIQUE",  # noqa: E501
    # Chandas
    "CREATE CONSTRAINT chandas_entity_key_unique IF NOT EXISTS FOR (n:Chandas) REQUIRE n.entity_key IS UNIQUE",  # noqa: E501
    # Lemma — the accented citation form is the identity. normalized_lemma is NOT unique:
    # 243 groups collide (e.g. atrá- / ā́tra / ā́tra- all normalize to "atra"), so
    # constraining on it would silently collapse 246 distinct lemmas.
    "CREATE CONSTRAINT lemma_unique IF NOT EXISTS FOR (n:Lemma) REQUIRE n.lemma IS UNIQUE",
    # QAIssue - the corpus's own caveats, so a query can see them without reading a file
    "CREATE CONSTRAINT qa_issue_id_unique IF NOT EXISTS FOR (n:QAIssue) REQUIRE n.issue_id IS UNIQUE",  # noqa: E501
]


# ---------------------------------------------------------------------------
# Range / lookup indexes
# ---------------------------------------------------------------------------

INDEXES: Final[list[str]] = [
    # Filter passages by veda
    "CREATE INDEX passage_work_id IF NOT EXISTS FOR (n:Passage) ON (n.work_id)",
    # Filter passages by entity_type (MANTRA / HYMN / SECTION / etc.)
    "CREATE INDEX passage_entity_type IF NOT EXISTS FOR (n:Passage) ON (n.entity_type)",
    # Full-text search targets (text stored on TextVersion)
    "CREATE INDEX text_version_language IF NOT EXISTS FOR (n:TextVersion) ON (n.language)",
    "CREATE INDEX text_version_text_form IF NOT EXISTS FOR (n:TextVersion) ON (n.text_form)",
    # Translation lookup
    "CREATE INDEX translation_language IF NOT EXISTS FOR (n:Translation) ON (n.language)",
    "CREATE INDEX translation_translator IF NOT EXISTS FOR (n:Translation) ON (n.translator)",
    # Entity classification
    "CREATE INDEX devata_subtype IF NOT EXISTS FOR (n:Devata) ON (n.devata_subtype)",
    # Passage hierarchy navigation
    "CREATE INDEX passage_parent_key IF NOT EXISTS FOR (n:Passage) ON (n.parent_key)",
    # Lemma search: many-to-one, so this is an index rather than a constraint
    "CREATE INDEX lemma_normalized IF NOT EXISTS FOR (n:Lemma) ON (n.normalized_lemma)",
    # QA triage by severity and by which corpus raised it
    "CREATE INDEX qa_issue_severity IF NOT EXISTS FOR (n:QAIssue) ON (n.severity)",
    "CREATE INDEX qa_issue_veda IF NOT EXISTS FOR (n:QAIssue) ON (n.veda)",
]


def all_schema_cypher() -> list[str]:
    """Return all constraint and index Cypher statements in application order."""
    return CONSTRAINTS + INDEXES
