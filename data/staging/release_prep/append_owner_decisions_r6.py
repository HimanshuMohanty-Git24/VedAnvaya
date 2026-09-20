"""Append owner round eight (release prep) to docs/reports/data-completeness/OWNER_DECISIONS.md.

Same mechanics as ``release_blocker_r5/append_owner_decisions.py``, and for the same reason:
the file is pure LF, so the append is written in binary with explicit ``\n``. Text mode on
this platform would rewrite all 1,024 line endings and bury a two-section addition inside a
whole-file diff.

Both sections are ``OWNER-SUPPLIED``. The attestation is the release-prep instruction, which
introduces them with "These decisions are explicitly supplied by the repository owner" and
"Record them in OWNER_DECISIONS.md as OWNER-SUPPLIED". Per the §37 provenance table that is
the strongest attestation available here, and it is what licenses a closure to cite them.
"""

# ruff: noqa: E501, RUF001 -- the appended text is markdown: its table rows do not wrap
# at 100 columns without ceasing to be a table, and it prints real en dashes.
from __future__ import annotations

import pathlib

DOC = (
    pathlib.Path(__file__).resolve().parents[3]
    / "docs"
    / "reports"
    / "data-completeness"
    / "OWNER_DECISIONS.md"
)

ADDITION = """
# Owner round eight — Release prep

Two decisions the registry had been holding its last two entries open for, both against
`OWNER_DECISION_E_AUDIO_GATE`. Both were supplied directly in the release-prep instruction,
which states "These decisions are explicitly supplied by the repository owner" and directs
that they be recorded "as OWNER-SUPPLIED". Both are therefore `OWNER-SUPPLIED` under the §37
provenance table.

`OWNER_DECISION_E_AUDIO_GATE` is not lifted by either. §14 stands unchanged: the 1,021-row
audible queue remains mandatory, no automated check may relabel a row, and the audio domains
stay blocked behind it. What these two decisions establish is the gate's **extent** — what it
was ever about — and what Product V1 requires of the object side of the melodic layer.

## 40. `OWNER_DECISION_F_NOTATION_IS_NOT_AUDIO` — the audible gate covers audio, not notation

**Decision, as given:**

> The audible-review gate applies to AUDIO only.
>
> It does NOT gate textual/musical notation.
>
> Therefore source-explicit Samavedic notation may be released when:
>
>     recension is compatible with the canonical Kauthuma Arcika corpus;
>     canonical coordinate alignment is verified;
>     notation is actually supplied by the source rather than inferred;
>     existing validation gates pass.
>
> No human listening is required for notation.
>
> Uncertain or unaligned notation remains withheld.
>
> Apply this decision to: GAP-SAMAVEDA_MUSIC-002.
>
> Do not pretend notation is audio.

**What this corrects.** `data/staging/integration/wave3_eligibility.json` has the
`samaveda_music` domain `BLOCKED` by `OWNER_DECISION_E_AUDIO_GATE` — the same gate as
`audio_rv`, `audio_av` and `audio_yv`. But 1,136 of that domain's 1,471 rows are
`ARCIKA_NOTATION`: combining Devanagari tone marks printed on verse text. Nothing in them is
a recording, and no amount of listening could verify or refute one. The domain was standing
behind a gate that could never have been the right gate for most of its rows.

**This decision is a permission, not a closure, and the four conditions are measured here
rather than assumed.** Three hold and one does not.

| condition | verdict | measurement |
| --- | --- | --- |
| recension compatible with the canonical Kauthuma arcika | **MET** | `proofs/recension.md`: source page-title prefix `samavedah/kauthumiya/samhita/`; the accented witness's own headers run `purvarcikah/chanda arcikah` through `uttararcikah/navamaprapathakah`, which is the Kauthuma arrangement and not Benfey's six-book Ranayaniya; 1,136 verses byte-identical under the declared normalisation to the text already held at `VG:WORK:SV:KAU`. `recension.no_foreign_recension_inside_kauthuma` evaluated 1,132 records for eight foreign-recension markers, 0 hits. |
| canonical coordinate alignment verified | **MET for 1,136, and only those** | `arcika_notation.text_redderives` 1,136 evaluated / 0 failures, stratified CHANDA 471, ARANYA 31, MAHANAMNYA 3, UTTARA 631; pairing order-consistent under an LCS alignment, not merely set-equal. `identity.uuid_recomputes_from_urn` 1,136/0 and `identity.keys_and_urns_unique` 1,132/0. The other **708** arcika verses are staged `UNRESOLVED` because the accented witness disagrees with our text there; they are what this decision's own "uncertain or unaligned notation remains withheld" clause withholds. |
| notation supplied by the source, not inferred | **MET** | `arcika_notation.tone_mark_present` 1,136/0 — every released row carries a real mark. `arcika_notation.no_pua_no_u0301` 1,136/0 refuses both the private-use-area font hack and the U+0301 acute, the second of which is the fold trap that makes an IAST śa indistinguishable from an udātta. `proofs/notation-codepoint-census.json` counts 108,160 cantillation marks over 1,750,419 characters, 98.09% of them real combining Devanagari Extended U+A8E1–U+A8F1. The notation is recorded as codepoints and never interpreted into pitch: the Kauthuma decipherment authority (van der Hoogt 1929) is not held, and Howard 1988 is Jaiminiya and was deliberately not applied. |
| existing validation gates pass | **NOT MET** | Gate A is `PASS` — the structural validator at full evaluation coverage with `--graph` — and the domain's own QA report is 12 checks, 11,193 records, 0 defects. But `wave3_eligibility.json` records Gate B `UNKNOWN` ("no semantic review recorded") and Gate C `NOT_RUN` ("adversarial test not yet performed"), against a stated eligibility rule of **A and B and C all PASS**. |

**The fourth condition is not a technicality and it is not being read conveniently.** Gate C
is an *independent* falsification attempt, and this campaign's own rule records why that
matters: "Four of four domains adversarially tested so far have failed C, and two of those
four had every aggregate count survive." The adversarial sample inside the artifact — the 40
shortest arcika verses carrying a gana rendering, 0 defects — is the agent's own check on its
own work, which is the thing Gate C exists because it is not. Reading "existing validation
gates" as Gate A alone would clear the board by narrowing a word.

**Consequence.** The notation is **authorised and not yet released**. The audio gate no longer
stands in front of it, so `GAP-SAMAVEDA_MUSIC-002` leaves `BLOCKED_OWNER_DECISION_REQUIRED`;
but nothing was imported, the graph still holds no melodic layer of any kind, and a staged and
unimported domain is not closed — this ledger has recorded that once already, when 944
Atharvavedic translations were described as "closed via the Wayback Machine" against a graph
holding none of them. The entry therefore reads `STILL_IMPLEMENTATION_FIXABLE`, with the
remaining work named exactly: run Gate B and Gate C for `samaveda_music`, then import the
1,136 aligned `ARCIKA_NOTATION` rows and leave the 708 unresolved ones withheld.

**If the owner intended "existing validation gates" to mean the structural validator alone**,
that is a one-line change to the ruling for this entry in
`scripts/wave4_registry_closure_audit.py` and the release-prep report says so plainly rather
than making the choice quietly. It is recorded as unmet because the conservative reading is
the one that cannot manufacture a closure.

## 41. `OWNER_DECISION_G_GANA_OBJECT_OUT_OF_V1` — no object side, no `MUSICALIZED_AS`

**Decision, as given:**

> For Product V1, MUSICALIZED_AS relationships are NOT required unless the object-side Gana
> identity is independently established and canonical.
>
> Current state:
>
>     no canonical Gana nodes exist;
>     four proposed Gana Works remain PROPOSED_FOR_LEAD_ADJUDICATION.
>
> Do NOT mint Gana nodes or MUSICALIZED_AS edges merely to satisfy a denominator.
>
> The missing object-side Gana model is outside the Product V1 bounded corpus and is future
> enrichment once a Gana corpus/object identity and reliable alignment are established.
>
> This is:
>
>     CLOSED_SCOPE_DECISION
>
> not:
>
>     BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE
>     missing engineering
>     verified zero

**Readback, measured 2026-09-18 against the live store rather than taken from a receipt.**
Every factual premise the decision states is true as given. `MUSICALIZED_AS` carries 0 edges
and the relationship type is absent from `db.relationshipTypes()` entirely. No label matching
`saman|gana|stobha|melod` exists. 0 nodes carry any property whose key contains `gana`. There
are 4 `:Work` nodes and exactly one is Samavedic, `VG:WORK:SV:KAU`; the four gana Works in
`data/staging/samaveda_music/gana_works.jsonl` all read
`identity_status: PROPOSED_FOR_LEAD_ADJUDICATION` and none is in the graph.

**The exclusion is already declared, which is what makes this a scope decision rather than a
convenient one.** `VG:WORK:SV:KAU` carries an `excluded_corpora` list naming
`SAMAVEDA_GRAMAGEYA_GANA`, `SAMAVEDA_ARANYAKAGEYA_GANA`, `SAMAVEDA_UHAGANA` and
`SAMAVEDA_UHYAGANA`, and a `scope` property that states the gana collections "require their
own work_id". `GAP-SAMAVEDA_MUSIC-001` already closed `CLOSED_SCOPE_DECISION` on precisely
that citation. This decision extends the same boundary to the *predicate* that would have
crossed it.

**Applied to `GAP-SAMAVEDA_MUSIC-003` clause 2, which is the whole of what that entry was
blocked on.** Clause 1 closed at R5 and is unmoved: all 1,844 Samavedic mantras carry the
source's own printed running Samhita number, 1,844 distinct values, 0 null. Clause 2 asked
that re-deriving the 495 `MUSICALIZED_AS` edges from the graph alone reproduce all 495; under
this decision those edges are not required for Product V1, the object side they would point at
is outside the bounded corpus, and minting them to reach 495 is the exact act the decision
forbids. **`GAP-SAMAVEDA_MUSIC-003` closes `CLOSED_SCOPE_DECISION`** citing this section. No
gana node was minted and no edge was created.

**The 495 edges are not deleted, denied or forgotten.** They remain staged in
`data/staging/samaveda_music/`, re-verified 495/495 against the graph's own stored arcika
text, and they become importable the moment a gana corpus carries a canonical object identity.
That is future enrichment, which is what the decision says it is.
"""


def main() -> None:
    raw = DOC.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("refusing to append: the file now contains CRLF and this script assumes LF")
    marker = b"# Owner round eight"
    if marker in raw:
        raise SystemExit("owner round eight is already present; refusing to duplicate it")
    if not raw.endswith(b"\n"):
        raw += b"\n"
    DOC.write_bytes(raw + ADDITION.encode("utf-8"))
    after = DOC.read_bytes()
    print(f"appended {len(after) - len(raw)} bytes; CRLF in file: {after.count(chr(13).encode())}")
    print(f"sections now: 40={'## 40.' in ADDITION} 41={'## 41.' in ADDITION}")


if __name__ == "__main__":
    raise SystemExit(main())
