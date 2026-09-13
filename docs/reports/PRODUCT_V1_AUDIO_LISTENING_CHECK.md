# Product V1 — audio listening check (outstanding, human)

Every mapping in `data/product/audio_catalog.jsonl` is `EXACT`, `text_verified`, and
`MANTRA`-scoped. That verification is **textual**: it compares the text VedSearch states a
recording recites against this corpus's text for the same key. It does not establish that
the audio file at that URL contains that recitation.

Nothing in this repository has listened to a recording. The automated audit
(`scripts/audio/audit_mappings.py`) re-derives coordinates and re-reads text; a browser
run can confirm the `playing` event fires and bytes arrive. Neither is an auditory test,
and neither should be reported as one.

This check is therefore **open** and requires a human with working audio.

## Why this specific sample

The Rigveda rows are chosen at the one boundary where a mapping error would be silent
rather than loud. VedSearch numbers Mandala 8 in Griffith's order, which places the eleven
Vālakhilya hymns inside the sequence; this corpus follows inline Aufrecht ordering. The
transform is `vedagraph.editions.griffith_page`. Below the gap the two orders agree, so a
broken transform still sounds right. Above it they differ by eleven hymns, so a broken
transform plays a plausible Rigvedic verse that is simply the wrong one.

## What to listen to

Open each reader page, press play, and compare what you hear against the Sanskrit shown on
that same page. The stream URL is given so a failure can be attributed to the mapping or
to the upstream file.

| # | Reader page | VedSearch ref | Listen for |
|---|---|---|---|
| 1 | `/passage/VG%3ARV%3ASAK%3AM01%3AS001%3AV001` | `1.1.1` | `agnim īḷe purohitaṃ yajñasya devam ṛtvijam` — the control. If this is wrong, nothing below is interpretable. |
| 2 | `/passage/VG%3ARV%3ASAK%3AM08%3AS048%3AV001` | `8.48.1` | Below the Vālakhilya gap, so the reference is **unshifted**. Confirms the transform is not applied where it must not be. |
| 3 | `/passage/VG%3ARV%3ASAK%3AM08%3AS071%3AV001` | `8.60.1` | **The critical check.** Begins approximately `agna ā yāhy agnibhir hotāraṁ tvā vṛṇīmahe`. A recitation that is fluent but does not match the on-page Sanskrit means the permutation is wrong. |
| 4 | `/passage/VG%3AAV%3ASAU%3AK01%3AS001%3AV001` | `1.1.1` | Atharvaveda sample; no permutation applies. |
| 5 | `/passage/VG%3AYV%3AVSM%3AA01%3AV001` | `1.1.1` | Yajurveda sample; no permutation applies. |

Stream URLs, if needed directly:

```
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:RV:1.1.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:RV:8.48.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:RV:8.60.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:AV:1.1.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:YV:1.1.1/stream
```

## Recording the result

Row 3 decides the check. If the recitation matches the on-page Sanskrit, the Vālakhilya
permutation is confirmed in audio as well as in text, and the mapping may be described as
heard. If it does not match, **stop**: do not adjust the catalogue to fit what was heard.
Re-derive `griffith_page` first, because a single wrong transform moves all 55 hymns above
the gap, and a per-row correction would hide that.

Until a human records a result here, the honest statement is: the audio mapping is
verified textually and unverified auditorily.
