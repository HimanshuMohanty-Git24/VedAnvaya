# ADR-007: TEI editorial alternatives are selected, never concatenated

Status: Accepted

TEI text extraction is policy-driven. `ORIGINAL` selects `orig` (or `sic`) within `choice` and
retains standalone `orig` nodes. `REGULARIZED` selects `reg` (or `corr`) within `choice` and omits
standalone `orig` nodes.

This distinction is required by the reviewed GRETIL Rigveda file: contrary to the generic prose in
its header, the file contains no `choice/reg` pairs and stores every Vedic accent mark in a standalone
`orig` node. Concatenating descendants would duplicate real alternatives; ignoring standalone
`orig` would erase accents. Alternative readings remain separate staging/text-version data.

The Mandala 1 sample uses `ORIGINAL`. Unicode NFC is applied only after branch selection.
