# Stable identity specification

Every canonical entity has a human-readable key, canonical URN, and deterministic UUIDv5.

The permanent VedaGraph namespace UUID is:

```text
7c8cde94-2bc0-50e2-8819-568ae65a3ec4
```

It was established for protocol version 1 and is stored as a literal in
`src/vedagraph/identity.py`. It must never be regenerated or changed. Entity UUIDs are
`UUIDv5(VEDAGRAPH_NAMESPACE_UUID, canonical_urn)`.

Example:

```text
key:  VG:RV:SAK:M01:S001:V001
URN:  urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:1
UUID: deterministically derived from the URN
```

Keys use padded components for lexical sorting; URNs use unpadded integers. Presentation labels
such as `RV 1.1.1` are citations and do not participate in identity.

Supported key families:

- Rigveda Shakala: `VG:RV:SAK:M{02}:S{03}:V{03}`
- Vajasaneyi Madhyandina: `VG:YV:VSM:A{02}:V{03}`
- Atharvaveda Shaunaka: `VG:AV:SAU:K{02}:S{03}:V{03}`
- Samaveda Kauthuma: **key not frozen — but the hierarchy IS resolved.** These are two different
  things and an earlier version of this line collapsed them, implying the structure was still
  open. It is not. The hierarchy is `[Arcika, Prapathaka, Ardha, Dasati, Verse]` — five levels,
  variable depth (1–5 by arcika), absent levels encoded as a literal `0` — established from the
  selected source's own declared reference system and corroborated by two independent textual
  witnesses plus one independent addressing scheme. See `data/registry/works.yaml`.
  What remains open is the **key**, which is a permanent commitment rather than an observation,
  and the reason is narrower than "an edition and complete structural mapping are selected":
  no witness yet combines an **identified printed edition** with **redistribution rights**.
  Rights are solved (Sanskrit Wikisource, CC BY-SA, textually proven independent of the Pandey
  lineage); edition identity is not. Current state is `identity_status: RESEARCH_REQUIRED`,
  `key_pattern: null`.
  The **candidate** key, recorded so freezing later is a purely additive change and so the
  research is not lost, is implemented in `identity.sv_mantra_identity` as
  `VG:SV:KAU:A{arcika}:P{prapathaka:02d}:R{ardha}:D{dasati:02d}:V{verse:02d}`. It is a candidate,
  not a declaration, and nothing may treat it as canonical.
  The original claim that a single running number is not an adequate identity stands, and is
  reinforced: the edition does print a running verse number 1..1875, but it is defective (five
  values absent, one duplicated), so it is carried only as a non-canonical Citation.

Identity changes require a versioned migration and explicit mapping; silent reuse is forbidden.

