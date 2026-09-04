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
- Samaveda Kauthuma: intentionally unresolved until an edition and complete structural mapping
  are selected. A single running number is not an adequate identity.

Identity changes require a versioned migration and explicit mapping; silent reuse is forbidden.

