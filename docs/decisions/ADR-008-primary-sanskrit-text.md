# ADR-008: The primary Sanskrit text is a build decision, not a parser constant

Status: Accepted

`GRETIL.RV.AUFRECHT` is the primary displayed Rigveda Saṃhitā representation for v1. The
evidence and the alternatives are in
[`RIGVEDA_BASE_EDITION.md`](../architecture/RIGVEDA_BASE_EDITION.md).

The selection is expressed in build configuration (`primary_sanskrit`, `parallel_sanskrit`,
`candidate_text_versions`), never in adapter or parser code. A build may also set
`primary_sanskrit: null` and list `candidate_text_versions` while a choice is still open;
comparison and QA keep working in that state.

Passage identity is derived from the citation hierarchy alone. `VG:RV:SAK:M01:S001:V001` and
its UUIDv5 are the same whichever version is primary, so changing the base edition changes
which text is displayed and nothing else. This is enforced by test, not by convention.

Every Sanskrit representation carries a `text_role` alongside its existing `text_form`.
`text_form` says what the textual object is (Saṃhitā, Padapāṭha); `text_role` says how
VedaGraph is allowed to use it. One passage can hold a transmitted Saṃhitā, another
scholarly edition, a metrically restored representation, a Padapāṭha and derived
transliteration or search forms without any of them being mistaken for another.

A metrically restored text is never the primary displayed Saṃhitā. Restoration is an
editorial reconstruction of the poetic form, and presenting it as the received text would
misrepresent both.
