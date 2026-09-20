# License scope

VedAnvaya is **source-available for noncommercial use**. It is not OSI Open Source, and
this document explains exactly what the project license does and does not reach.

Read it together with [`LICENSE`](LICENSE),
[`RIGHTS_POLICY.md`](docs/architecture/RIGHTS_POLICY.md) and
[`SOURCE_POLICY.md`](docs/architecture/SOURCE_POLICY.md).

## What the project license covers

The [PolyForm Noncommercial License 1.0.0](LICENSE) covers the **original VedAnvaya
software and original project material for which the repository owner holds licensing
rights**. In practice that is:

- the Python package under [`src/`](src/) and the command-line tooling in [`scripts/`](scripts/)
- the Next.js application under [`frontend/`](frontend/) (excluding its third-party
  dependencies and bundled fonts, which carry their own licenses)
- the schemas in [`schemas/`](schemas/) and the prompt templates in [`prompts/`](prompts/)
- the tests in [`tests/`](tests/) and the infrastructure definitions in [`infra/`](infra/)
- the prose written for this project in [`docs/`](docs/) and in the repository root
- the ontology, vocabularies and editorial decisions recorded in
  [`data/registry/`](data/registry/)

Noncommercial use, study, modification and redistribution of that material are permitted
under the license terms. **Commercial use requires separate permission** from the
copyright holder.

## What the project license does NOT cover

VedAnvaya is built from Vedic texts, translations, scholarly editions, manuscript scans
and recitation recordings that **the repository owner did not create and does not own**.

**The PolyForm Noncommercial License does not apply to that material, and including or
referencing it here does not relicense it.** Each such item remains governed by the terms
of its own source — whether public domain, a Creative Commons license, an explicit
permission grant, or terms that have not yet been established.

This includes, without limitation:

- Saṃhitā texts and their digital editions
- translations and their transcriptions
- critical apparatus, accentuation and morphological analyses
- traditional metadata (Anukramaṇī ascriptions and comparable indices)
- manuscript and printed-book scans, and transcriptions derived from them
- recitation audio, and the catalogue metadata describing it
- any third-party dataset, font, image or software dependency vendored or referenced here

Derived artifacts do not escape this. Parsing, normalizing, re-keying and republishing a
source as JSONL or as graph records is, in copyright terms, both modification and
publication. A derived file inherits the constraints of the source it was derived from.

## Where the actual terms are recorded

Rights in this project attach to a **specific artifact**, not to a website, a publisher or
the corpus as a whole. No host-level license is assumed to cover every file, and website
accessibility is never treated as a grant of reuse.

| Registry | What it records |
| --- | --- |
| [`data/registry/rights.yaml`](data/registry/rights.yaml) | The 13 controlled rights statuses and, for each, what is operationally permitted: local copying, redistribution, redistribution of derived work, public mirroring, linking. |
| [`data/registry/sources.yaml`](data/registry/sources.yaml) | The 22 registered upstream sources. |
| [`data/registry/source_artifacts.yaml`](data/registry/source_artifacts.yaml) | The 53 pinned artifacts, each with a rights status and retrieval provenance. |
| [`data/registry/text_versions.yaml`](data/registry/text_versions.yaml) | Per-edition terms where one artifact carries several layers under different licenses, taken from the source header rather than retyped. |
| [`data/product/audio_catalog.jsonl`](data/product/audio_catalog.jsonl) | Per-recording attribution, source, and whether a local copy is permitted. |

Those files are the authoritative record. This document does not restate their contents
and does not make any new claim about the copyright status of third-party material.

## Consequences worth stating plainly

- **Some statuses are deliberately `UNKNOWN`.** That is a recorded finding, not an
  oversight, and the operational default for `UNKNOWN` is: do not redistribute.
- **Some material is reference-only.** Where a rights holder requires written permission,
  the repository stores metadata and links, not copied content.
- **Recitation audio is not redistributed.** The catalogue that describes each recording is
  committed; the media files are not, and most belong to a publisher who permits streaming
  rather than redistribution.
- **Raw, staged, canonical, derived and QA corpus artifacts are ignored by Git**, precisely
  because individual assets can carry different rights. They are reproducible from pinned
  sources by anyone entitled to fetch those sources.
- **A `CC_BY_NC_SA` source imposes its own conditions.** Where a derivative is built from
  share-alike material, that derivative must satisfy attribution and share-alike
  independently of this project's license.

If you intend to redistribute any part of this repository, or to use it commercially,
check the rights status of every artifact involved before you do — and obtain separate
permission from the copyright holder for commercial use of the original VedAnvaya
material.
