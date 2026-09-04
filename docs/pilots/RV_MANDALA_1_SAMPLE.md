# RV Mandala 1 sample v2

The bounded sample contains Suktas 1, 22, 50, 164, and 191. They exercise short, medium, and long
hymns (9, 21, 13, 52, and 16 mantras), several Rishis and Devatas, simple and range-qualified
Chandas/Devata headings, early/middle/late Mandala positions, two Wikisource markup generations,
and one external VHP media reference per Sukta.

The selection optimizes parser and metadata-scope coverage rather than record volume. Complex VHP
range strings are preserved as source assertions and are not flattened into false hymn-wide
canonical metadata. No VHP text or media is redistributed; generated heterogeneous-rights output
remains ignored by Git.

Build with:

```bash
uv run vedagraph discover rigveda --mandala 1 --config data/builds/rv_mandala_1.yaml
uv run vedagraph ingest stage --config data/builds/rv_mandala_1.yaml
uv run vedagraph corpus build --config data/builds/rv_mandala_1.yaml
```

The generated report is `data/canonical/rv_mandala_1_sample_v2/REPORT.md`.

## Frozen Wikisource revisions

| Sukta | Page ID | Revision ID | Revision timestamp | Stanzas |
| --- | ---: | ---: | --- | ---: |
| RV 1.1 | 8692 | 14400993 | 2024-08-10T12:36:22Z | 9 |
| RV 1.22 | 15416 | 14396839 | 2024-08-08T09:33:39Z | 21 |
| RV 1.50 | 15444 | 14396868 | 2024-08-08T09:34:07Z | 13 |
| RV 1.164 | 15558 | 14396804 | 2024-08-08T09:33:06Z | 52 |
| RV 1.191 | 15584 | 14396835 | 2024-08-08T09:33:36Z | 16 |

All five pages expose a deterministic 1..N stanza sequence. Exact alignment means source-numbered
stanza-to-mantra alignment; it does not assert that Griffith's translation is philologically exact.
