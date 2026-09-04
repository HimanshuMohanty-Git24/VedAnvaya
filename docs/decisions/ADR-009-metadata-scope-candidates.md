# ADR-009: Traditional-metadata scopes are extracted as candidates and fail closed

Status: Accepted

VHP writes Rishi, Devata and Chandas metadata as one free-text string per Sukta. Some
strings name a single entity for the whole hymn; others assign entities to numbered mantras,
to half-verses, or to alternatives, and mix all of these in one string.

`vedagraph.metadata.ranges` extracts a scope structure from such a string and returns a
**candidate** record with a status: `PARSED`, `PARTIALLY_PARSED`, `AMBIGUOUS`, `UNSUPPORTED`
or `INVALID`. It supports only forms observed in real VHP data, handles Devanagari and ASCII
digits alike, and reports anything else rather than interpreting it. An entity written
before its numbers is `AMBIGUOUS`; an inline parenthetical gloss containing the comma that
otherwise separates segments is `UNSUPPORTED`. Both keep the raw string.

Only `PARSED` records with no segment needing review are marked `safe_to_promote`, and even
those are not promoted automatically. Promotion requires a reader who knows the source
notation to confirm the reading, via
[`rv_m1_metadata_range_review.md`](../reports/rv_m1_metadata_range_review.md).

Candidates use `CandidateScopeType`, which admits `HALF_VERSE`, `PADA`, `PADA_RANGE`,
`MANTRA_SET` and `UNRESOLVED_SUBSPAN` in addition to the canonical scope types. The
canonical `ScopeType` and `MetadataScope` are deliberately untouched: sub-mantra scopes have
no reviewed canonical representation yet, and inventing one would either widen a half-verse
claim into a whole-mantra claim or destabilise records that are already correct. A
sub-mantra scope keeps `raw_scope_text` and stays flagged for review.

Qualifiers are detected by literal match, never by interpretation. Short function words such
as *vā* ("or") must match as whole words, because they also occur as syllables inside
ordinary names.

`vedagraph metadata review-ranges` writes two reports. The committed one withholds the
verbatim VHP strings, because VHP is a permission-required source and its content stays out
of Git; it keeps every parser output — status, scope type, mantra spans, qualifier presence
— so the shape of each reading is still reviewable. The full report, with the source
strings a reader needs in order to check the parser against the notation it was given, is
written under `data/derived/` and is not committed.

The parser extracts **scope**, not **entity identity**. `raw_entity` stays a source string;
resolving it to a canonical Vedic entity belongs to a future entity registry and is a
separate concern.
