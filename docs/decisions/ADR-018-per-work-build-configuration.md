# ADR-018: `CorpusBuildConfig` is Rigveda-specific and stays that way

Status: Accepted
Date: 2026-09-07
Corollary of [ADR-017](ADR-017-four-veda-structural-model.md).

## Context

`CorpusBuildConfig` is how a corpus build is declared and hashed into the manifest. It
requires two Rigveda-shaped fields:

```python
mandala: int = Field(ge=1)
selected_suktas: list[int] = Field(min_length=1)
```

Vajasaneyi Samhita has neither a Mandala nor a Sukta level, so no Yajurveda build can be
expressed as a `CorpusBuildConfig`, and `build_from_config` / `stage_from_config` are
unusable for it. The same is true for Samaveda. This was raised by the Yajurveda owner as
a blocker for shared ingestion, with a request either to generalize the model or to state
that per-work builders own their own config shape.

The obvious fix — make `mandala` and `selected_suktas` optional and add generic
equivalents — is not minimal. `config.mandala` is dereferenced as a plain `int` in roughly
twenty-five places in `src/vedagraph/build.py` (including key construction at lines 472,
484 and 689-773 and report text at 623, 961-1000), plus `compare/report.py` and
`cli/app.py`. Making it `int | None` propagates `None` through the entire sealed Rigveda
builder in exchange for reusing a model whose remaining fields are also RV-tuned. The
Rigveda corpus must stay byte-reproducible; that is the constraint the decision has to
respect.

## Decision

`CorpusBuildConfig` is **declared Rigveda-specific** and is not loosened. Its fields are
unchanged; only a docstring is added saying so. It is not renamed, because
`schemas/corpus_build_config.schema.json` is an existing published filename.

A new additive model, `WorkBuildConfig`, is the shared shape for every other work:

```python
work_id: str                      # ^VG:WORK:[A-Z]+:[A-Z]+$
section_level: str | None         # the container this build slices on, in the work's own
                                  # vocabulary: "Adhyaya", "Prapathaka", "Kanda"
selected_sections: list[int]      # empty means the whole work
mantra_level: str = "Mantra"      # "Verse" for Samaveda
```

plus the policy-version, source, text-selection and output fields mirroring
`CorpusBuildConfig`. It exports as `schemas/work_build_config.schema.json`. Slicing
requires `section_level` to be named, so a build cannot select sections without saying
what kind of section they are.

Correspondingly, `SectionDiscoveryRecord` is added as the work-agnostic form of
`SuktaDiscoveryRecord`, keyed on `(work_id, section_level, section_number)` with an
optional `parent_key`. `section_number` allows `0` because Samaveda encodes an absent
level as zero. `SuktaDiscoveryRecord` is left exactly as it is: the sealed Rigveda corpus
contains 2,247 of them.

The point of landing these now, rather than letting each Veda invent its own, is that
three owners were each about to define a build-config shape independently. One shared
additive model costs less than three divergent ones plus a later migration.

## Consequences

Rigveda and non-Rigveda builds are configured by two different models. That is real
duplication and is accepted deliberately: the alternative was threading `None` through a
sealed builder. Rigveda's eventual expression as a `WorkBuildConfig` is possible but is
a rebuild-scale change and is explicitly **not** attempted here.

Per-Veda pilot configs written before this decision do not validate against
`corpus_build_config.schema.json`. That divergence is disclosed rather than hidden, and
`work_build_config.schema.json` is what they should validate against going forward.

`SectionDiscoveryRecord` exists but no QA check consumes it yet. The count-reconciliation
path in `qa/checks.py` is keyed on `(mandala, sukta)` and is owned by the QA owner; until
it is generalized, non-Rigveda works report count reconciliation as data from their own
modules. Emitting `SectionDiscoveryRecord` is still strictly better than emitting nothing,
because the structural discovery becomes reviewable evidence rather than a gap.
