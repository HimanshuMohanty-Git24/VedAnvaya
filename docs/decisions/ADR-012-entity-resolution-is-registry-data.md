# ADR-012: Canonical entity identity is reviewed registry data, not a computed match

Status: Accepted

A raw source string never becomes a graph entity directly. The path is:

```text
raw source label → source assertion → normalized label → registry lookup
                 → canonical entity → deterministic relationship
```

## Registries are pinned data

`data/registry/{rishis,devatas,chandas}.yaml` carry an explicit `entity_key` for every
entity. The build reads those keys; it does not recompute them. A change to the
normalization rules therefore cannot silently re-identify an existing entity.

`scripts/build_anukramani_registries.py` generates the registries deterministically from
the pinned artifacts, but the result is reviewed and committed. Generation proposes;
the committed file decides.

## Normalization touches writing, never meaning

Only Unicode form, surrounding whitespace, internal whitespace runs and letter case are
folded. Hyphens, which the source uses as its own compositional marker, are preserved.
`Soma` and `Pavamāna Soma` stay distinct because the source distinguishes them.

## Similarity is never identity

Entity keys use a readable ASCII fold (`gāyatrī` → `GAYATRI`). That fold is lossy: `ś`,
`ṣ` and `s` all become `S`. A fold collision is treated as a *warning that two labels
look alike*, never as proof that they are the same thing. Colliding entities keep
separate identities and receive collision-broken keys derived from a longer,
length-preserving fold (`aśvaḥ` → `ASHVAH`, `aśvāḥ` → `ASHVAAH`).

Fuzzy comparison exists in exactly one function, `EntityResolver.candidates`, and its
output only ever appears in a review report.

## Resolution statuses

`EXACT`, `NORMALIZED_EXACT`, `KNOWN_ALIAS` and `COMPOSITE_PRESERVED` may attach a
canonical entity id. `NEEDS_REVIEW`, `AMBIGUOUS` and `REJECTED` may not, and the model
enforces this rather than trusting the caller.

## Aliases are typed and evidenced

An alias entry names its `alias_type` and the evidence that justified it. A source string
is not called an `EPITHET` because it looks like one; the six current aliases are five
`SOURCE_SPELLING` slips and one `ORTHOGRAPHIC_VARIANT`, each with the occurrence counts
that support it.

## Both sides are kept

A resolved assertion stores the canonical entity **and** the verbatim source label. The
source label is never rewritten to the canonical spelling, so the digitized Anukramaṇī
remains reconstructible from VedaGraph output.
