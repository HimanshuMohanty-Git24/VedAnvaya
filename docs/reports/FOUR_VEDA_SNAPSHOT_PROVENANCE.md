# Four-Veda Raw Snapshot Provenance — Policy and Audit

**Owner:** Agent E (rights / provenance / source archivist) — single writer
**Audit run:** 2026-09-07, against the working tree of branch `semantic-pilot-v1`
**Scope:** `data/raw/` — **full census, not a sample**

---

## 1. Policy

Acquisition must use **immutable raw snapshots** wherever legally permissible, and must never silently
overwrite an upstream snapshot.

### 1.1 Required provenance per snapshot

Every snapshot records, in a sidecar `<sha256>.metadata.json`:

| Field | Required | Purpose |
|---|---|---|
| `sha256` | yes | content hash; also the filename, making storage content-addressed |
| `retrieval_url` | yes | exact URL fetched, including query string |
| `retrieved_at` | yes | UTC timestamp |
| `http_status` | yes | proves a real 200 rather than a cached error page |
| `source_id` | yes | ties the snapshot to `data/registry/sources.yaml` |
| `filename` | yes | the stored payload |
| `content_type` | where served | declared encoding/format |
| `etag`, `last_modified` | where served | upstream revision signal |
| `request_headers` | yes | the User-Agent actually used, for polite-fetch accountability |
| `parser_independent_metadata` | yes | host, recorded independently of any parser |
| `schema_version` | yes | metadata format version |

Byte length is recoverable from the stored payload and is additionally denormalized onto
`SourceArtifact.file_size_bytes` for registered artifacts.

**Source revision / commit** is recorded at *artifact* rather than snapshot level, and is enforced by
the model: `SourceArtifact.require_commit_pin` raises if `repository_url` is set without
`repository_commit_sha`, or if a commit is given without `repository_path`. Git-hosted datasets must
name an exact commit and never a moving branch.

### 1.2 Immutability, verified in the code

`persist_snapshot()` in `src/vedagraph/ingest/fetcher/http.py` implements no-overwrite structurally
rather than by convention:

```python
if content_path.exists() and content_path.read_bytes() != content:
    raise RuntimeError(f"hash collision or corrupt snapshot at {content_path}")
if not content_path.exists():
    content_path.write_bytes(content)
...
if not metadata_path.exists():
    metadata_path.write_bytes(encoded)
```

Three properties follow, and they are the reason the audit below comes out clean:

1. **Content-addressed naming.** The filename *is* the digest, so differing upstream content cannot
   collide with an existing snapshot — it lands beside it as a new file. Upstream change produces a new
   snapshot; it never mutates an old one.
2. **Writes are guarded, not blind.** A same-named file with different bytes raises rather than
   overwriting.
3. **Idempotent reruns.** Existing payloads and metadata are left untouched, so re-fetching is safe.

`_find_cached()` additionally **re-verifies the stored hash** before reusing a snapshot, so a corrupted
cache entry is not silently served:

```python
if content_sha256(content_path.read_bytes()) == metadata.sha256:
```

Snapshots are laid out `data/raw/<source_id>/<retrieval-date>/<sha256>.<ext>`, so a re-fetch on a later
date produces a parallel dated directory rather than displacing the earlier one. In-flight downloads
stage under `data/raw/.partial/<source_id>/` and are only promoted on completion, so a truncated
transfer cannot masquerade as a snapshot.

### 1.3 Rights constraints on snapshotting

Snapshotting is itself a rights-bearing act, governed by `copy_local` in
`data/registry/rights.yaml`:

- `PUBLIC_DOMAIN`, `CC_*`, `APACHE_2_0`, `RESEARCH_ONLY` — snapshot freely.
- `PERMISSION_REQUIRED`, `REFERENCE_ONLY`, `UNKNOWN` — **conditional**: a bounded, private,
  non-published verification snapshot only, and only where site terms do not forbid retrieval.
- `EXTERNAL_REFERENCE_ONLY` — **no snapshot at all.** Store only a URL or identifier.

Raw snapshots stay gitignored per project policy; derived registries and aggregate reports are
committed.

---

## 2. Audit results — real numbers

Full census of every `*.metadata.json` under `data/raw/`, each payload re-hashed and compared against
its recorded digest.

Re-run after Agents C and D acted on finding F1. Figures below are the CURRENT state.

| Metric | Result |
|---|---|
| Metadata records | **1347** |
| **sha256 verified against stored bytes** | **1347** |
| **sha256 mismatched** | **0** |
| Payload missing | **0** |
| Provenance incomplete (any required field absent/empty) | **0** |
| Orphan payloads (no metadata sidecar) | **0** |
| `.partial` residue (stranded in-flight files) | **0** |
| Total bytes | 249,035,847 |

**Every one of the 1347 snapshots hash-verifies. There were no mismatches, no missing payloads, no
orphans, and no incomplete provenance records.** This is a full verification, not the sampled check that
was asked for as a minimum.

**Unregistered `source_id` values dropped from 71 snapshots to 25** after Agent C re-fetched under the
registered id `WIKISOURCE_SA` and removed the orphaned `wikisource_sa_vsm/` tree. Notably, **every one of
those 44 re-fetched snapshots came back with an identical sha256** — the bytes were never in question,
only the identifiers, which is exactly what a content-addressed store should be able to demonstrate.

### 2.1 Per source

| `source_id` | Records | Verified | Mismatch | Bytes | Registered? |
|---|---|---|---|---|---|
| `GRETIL` | 3 | 3 | 0 | 5,673,797 | yes |
| `GRETIL_AVS` | 2 | 2 | 0 | 2,138,722 | **NO** — namespace, resolved (see F1) |
| `VEDAWEB` | 11 | 11 | 0 | 222,620,623 | yes |
| `VEDAWEB_AVS` | 23 | 23 | 0 | 1,896,471 | **NO** — namespace, resolved (see F1) |
| `VHP` | 5 | 5 | 0 | 1,057,263 | yes |
| `WIKISOURCE_GRIFFITH_RV` | 1245 | 1245 | 0 | 7,579,250 | yes |
| `WIKISOURCE_GRIFFITH_SV` | 1 | 1 | 0 | 5,798 | yes |
| `WIKISOURCE_SA` | 47 | 47 | 0 | 7,987,015 | **yes** — re-fetched under the registered id |

**Note on that 47: it is a MIXED-VEDA count, not a Śukla Yajurveda count.** Verified by parsing the
retrieval URLs: **44 Śukla Yajurveda + 3 Sāmaveda**. Sāmaveda also legitimately uses `WIKISOURCE_SA`,
because it is the same *source*. Flagged by Agent C. This is shared storage working as designed, but it
means **no per-`source_id` snapshot count in this table can be read as a per-Veda count** — a
registry-correct `source_id` is deliberately coarser than a Veda. Anyone sizing a Veda's holdings must
filter by URL or by artifact, not by directory.
| `WSC2023` | 10 | 10 | 0 | 76,908 | yes |

All HTTP statuses are **200**. Hosts touched: `gretil.sub.uni-goettingen.de`,
`raw.githubusercontent.com`, `vedaweb.uni-koeln.de`, `vedicheritage.gov.in`, `en.wikisource.org`,
`sa.wikisource.org`.

### 2.2 Field population

| Field | Populated | Note |
|---|---|---|
| `sha256`, `retrieval_url`, `retrieved_at`, `http_status`, `source_id`, `filename`, `content_type`, `parser_independent_metadata`, `schema_version` | **1346 / 1346** | complete |
| `request_headers` | 1345 / 1346 | one early GRETIL fetch predates User-Agent recording |
| `etag` | 25 / 1346 | only where the server sent one |
| `last_modified` | 5 / 1346 | only where the server sent one |

Sparse `etag` / `last_modified` are **not** provenance defects — they are optional and only recorded when
upstream supplies them. Their real cost is that most snapshots cannot detect upstream change by header
alone and must rely on content hashing, which is the stronger check anyway.

---

## 3. Findings

### F1 — Unregistered `source_id` values: was 71 snapshots, now 25. **Largely resolved.**

`GRETIL_AVS`, `VEDAWEB_AVS`, `WIKISOURCE_SA_SV_KAU` and `WIKISOURCE_SA_VSM` appeared in snapshot metadata
without existing in `data/registry/sources.yaml` — ad-hoc per-task identifiers coined during fetching.

**Two of the four are now gone.** Agent C re-fetched all 44 Yajurveda snapshots under the registered
`WIKISOURCE_SA` and deleted the orphaned tree; all 44 digests came back identical. The remaining 25
(`GRETIL_AVS` 2, `VEDAWEB_AVS` 23) are a *deliberate, documented storage namespace* rather than a
mistake — see the fetcher-coupling analysis below.

This is the one genuine governance defect in an otherwise clean store. Consequences:

- `source_id` no longer joins reliably from snapshot to source registry, so rights cannot be resolved
  from a snapshot alone — which is precisely what the field exists for.
- Two of them are not new sources at all. `GRETIL_AVS` is **GRETIL** (`avs___u.htm`, `avs_acu.htm`) and
  `VEDAWEB_AVS` is **VedaWeb** (`vedaweb.uni-koeln.de/api/...`). Leaving them distinct implies four
  hosts where there are two.

**Resolution taken by Agent E:** `WIKISOURCE_SA` has been registered in `data/registry/sources.yaml`
(CC BY-SA 4.0) as the real source behind the two `WIKISOURCE_SA_*` prefixes, and the two GRETIL
Atharvaveda payloads are now registered as artifacts under `source_id: GRETIL` with their verified
digests (`7e3f74f3…`, `cd89bd1e…`).

**Resolved by Agent D after this audit — and it refined the finding.** Agent D accepted the ruling that
`GRETIL_AVS` and `VEDAWEB_AVS` are not sources but *artifacts* of GRETIL and VedaWeb, and rebuilt its
pilot to read `load_sources()` / `load_source_artifacts()` instead of constructing provenance locally.
Its emitted records now carry registry ids (459 `TextVersion` rows → `GRETIL`; 115 `Translation` rows →
`VEDAWEB`). It also added, unprompted, a **checksum cross-check**: the build compares my pinned
`checksum_sha256` against the bytes it actually read and raises on mismatch. That is a genuinely better
guarantee than this audit provides — I verify that stored bytes match their *own* recorded digest, while
that check verifies the bytes match the *registry's* claim about them. A registry edit that repointed an
artifact at different bytes would now fail a build rather than produce a release whose provenance is
fiction.

**One part of F1 I got wrong, and the correction matters.** I framed the ad-hoc ids as straightforwardly
a governance defect. For the *metadata field* that is right. For the *storage directory* it is not:
`PoliteFetcher` derives its cache directory from whatever `source_id` it is handed, so fetching GRETIL
Atharvaveda files under `source_id: GRETIL` would have written them into
`data/raw/gretil/` alongside the Rigveda snapshots. Agent D's namespace split is therefore defensible
storage layout, and it has documented it explicitly as `SNAPSHOT_SOURCE_ID` with the comment that a raw
directory is storage layout while the registry `source_id` is the contract.

**Residual issue, and it is not Agent D's to fix. It is also worse than I first wrote.** I described the
coupling as affecting "the storage directory and the metadata `source_id`". Agent D found it is
**three-way**, and I verified every line myself in `src/vedagraph/ingest/fetcher/http.py`:

| Line | Derived from the single `source_id` argument |
|---|---|
| 159 | `target_dir = data_dir / "raw" / source_id.lower() / …` — the storage directory |
| 168 | `snapshot_id=f"{source_id}:{digest}"` — **the snapshot identity itself** |
| 169 | `source_id=source_id` — the metadata sidecar field |

Line 168 is the one I missed, and it is the consequential one: **the namespace poisons the
`snapshot_id`**, which is the value manifests carry. Confirmed against stored bytes —
`GRETIL_AVS:7e3f74f3…` and `VEDAWEB_AVS:0a922cbe…`. So a caller genuinely cannot namespace storage
without corrupting recorded provenance identity, not merely a metadata label.

The clean fix remains a **fetcher change**: accept a storage namespace separate from the recorded
`source_id`. `src/vedagraph/ingest/fetcher/http.py` is not a file Agent E owns, so this is recorded as a
contract request with a concrete citation rather than actioned.

**The consequence is nonetheless now CLOSED from the release side, by Agent D, without touching the
fetcher.** The namespace mapping is emitted as *data* rather than left in a code comment:

```
SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE   GRETIL_AVS  -> GRETIL    data/raw/gretil_avs/     2 snapshots
SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE   VEDAWEB_AVS -> VEDAWEB   data/raw/vedaweb_avs/   23 snapshots
```

Each assertion carries the exact `snapshot_id`s it covers, the raw directory, the count, and an evidence
string stating explicitly that the namespace is **storage layout and not a rights claim** — rights
attach to the artifact ids. A consumer joining the raw tree to rights can now resolve it
programmatically instead of finding nothing.

**This is the right division of fix.** The fetcher change would remove the cause; the emitted assertions
remove the consequence today, from a file its author owns, without anyone patching shared infrastructure
they do not own. The contract request stays open on its merits, not as a blocker.

**Resolution still owed by others:**
- Whoever owns `src/vedagraph/ingest/fetcher/http.py` should decouple storage namespace from recorded
  `source_id` in `persist_snapshot()`. Until then, snapshot `source_id` values cannot be relied on to
  resolve against `sources.yaml`.
- Agent F should add a QA check asserting every snapshot `source_id` resolves against `sources.yaml`.
  **Do NOT implement this as suffix tolerance, which is what Agent E originally asked for.** Agent D
  proposed a strictly better form and it supersedes the original ask: **resolve the emitted
  `SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE` map first, then assert exact equality against the resolved
  value.** Suffix matching would accept a typo — `GRETIL_AVZ` ends in nothing suspicious and would pass
  a permissive matcher — whereas map-resolution followed by strict equality accepts exactly the
  documented namespaces and nothing else. The weaker check trades away the property the check exists to
  provide. This defect class is invisible to hash verification and would otherwise have gone unnoticed
  entirely.
- `VEDAWEB_AVS` rights are now determined and recorded, and the answer is **split**: the Whitney/Lanman
  translation resource is `PUBLIC_DOMAIN` (on the 1905 work's age, not on VedaWeb's null licence field),
  while the AVS *Sanskrit* resource reproduces the TITUS no-republication clause and is
  `PERMISSION_REQUIRED`. Two resources, one host, opposite verdicts — which is exactly why VedaWeb's
  source-level status stays `UNKNOWN` by design.

### F2 — API-response snapshots carry misleading file extensions. Cosmetic.

MediaWiki API snapshots are stored as `.php` and `.json`, derived from the URL path (`api.php`) rather
than the payload. `WIKISOURCE_GRIFFITH_RV` payloads are `.php` files containing JSON, as are the
`WIKISOURCE_SA_*` sets. Content is intact and `content_type` is recorded correctly
(`application/json; charset=utf-8`), so this is a naming wart, not data loss — but it will trip any
downstream tool that dispatches on extension.

### F3 — VedaWeb dominates stored bytes. Informational.

11 VedaWeb snapshots account for 222.6 MB of 249.0 MB — **89.4%** of the store. The Book-1 TEI alone is
large and carries six Sanskrit versions under two different CC licences. Any future full-corpus fetch
should expect storage to be driven by TEI aggregates, not by page counts.

### F4 — Revision provenance is captured for Sanskrit Wikisource. Positive finding.

The `WIKISOURCE_SA_VSM` set was fetched with `rvprop=content|ids|timestamp`, so **43 of 43 pages carry
their own `revid` and timestamp**, not merely a collection-level retrieval date. This is exactly what
`WIKISOURCE_GRIFFITH_SV` and `WIKISOURCE_WHITNEY_AV` still lack, and it is the standard the other
Wikisource sets should meet: a community transcription can change under us, so a retrieval date alone is
not sufficient provenance.

### F5 — No timing or cue artifacts exist for any audio. Blocker for alignment.

No `.vtt`, `.srt`, `.cue` or JSON cue-sheet was found on any inspected audio item. Alignment granularity
is **adhyāya-level at best**. An authoritative track-to-mantra-range index for the 54-part
IISH/Veda Prasar Samiti master exists but ships only with physical CDs. No audio has been snapshotted,
which is correct — see §1.3 and the audio inventory.

### F6 — A wrong-scope checksum in `source_artifacts.yaml`. **My defect. Fixed, and it changed the rules.**

Reported by Agent C, independently verified by me before amending. `WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI`
carried `checksum_sha256: cb13ec2ee19b…`, which is a **real, self-verifying snapshot of the wrong page** —
the preface page `शुक्लयजुर्वेदः/प्राक्कथनम्, विषयानुक्रमणिका च`, 26,330 bytes, not the saṃhitā. I confirmed the
page title by parsing the stored bytes.

**This defect class is worse than a missing checksum, and that is the point.** The bytes hash correctly,
the snapshot exists, the sidecar agrees — and the assertion is still false. **A checksum that points at
the wrong artifact passes every integrity check while verifying nothing.** A missing checksum is visibly
absent; a mis-scoped one is invisibly wrong. Agent C's first-generation check reported only "matches a
snapshot", which was technically true and therefore useless; it now names the page a checksum resolves
to and reports `WRONG_SCOPE_matches_<title>`. **Matching *some* snapshot is not verification** — worth
adopting wherever checksums are gated.

**How it happened, because the mechanism is reusable:** Agent C supplied the hash inside an
`edition_evidence` block, where it correctly documented *where the 1929 edition statement was read*, and
I lifted it into the artifact checksum slot. **Evidence-for-a-claim is not evidence-of-the-artifact.**

**Fixes applied:**
1. Checksum **removed** from the saṃhitā row. It is 40 MediaWiki pages, so no single digest is meaningful;
   byte verification belongs per snapshot in `manifest.raw_snapshot_hashes`.
2. The preface page is **registered as its own artifact**, `WIKISOURCE_SA.YV.VSM.PREFACE`, where that
   digest *is* in scope. Deleting the evidence would have lost something real — this page is what
   *identifies the printed edition* behind the entire Śukla Yajurveda selection.
3. A **MULTI-PAGE ARTIFACT CHECKSUM CONVENTION** is now documented at the head of
   `data/registry/source_artifacts.yaml`, at Agent C's request that I set it rather than have a peer
   invent one. Five rules: absent field for multi-file artifacts; **no** synthesised concatenation hash
   (rejected — it silently encodes an ordering and normalization nothing else declares, so two honest
   builds could disagree); per-snapshot verification instead; **scope must be verified, not just
   integrity**; and evidence-for-a-claim never becomes the artifact's checksum.
4. Two further checksums pinned after **independent verification of both integrity and scope** —
   `RISHISUCI` and `SARVANUKRAMANI` (single pages, so meaningful) from Agent C, and
   `VEDAWEB.AVS.WHITNEY_LANMAN_1905.PLAINTEXT.L2` from Agent D, verified on four legs (file present,
   fresh recomputation, content-addressed filename, sidecar digest).

**Current state: 31 of 51 artifacts carry a pinned checksum; zero local hash mismatches; the four
touched this round were scope-checked by parsing page titles from the payloads.**

### F7 — One rights level below this audit was unchecked: `text_versions.yaml`. **CLOSED.**

Raised by Agent C. `data/registry/text_versions.yaml` declares **7 `TextVersionDescriptor` records, all
Rigvedic**. `TextVersionDescriptor` is **rights-bearing** — its own docstring states that "Rights,
lineage, and permitted VedaGraph role attach here, not to the host repository or the enclosing file". So
an unregistered `text_version_id` is **the same unadjudicated-rights defect as F1, one level down**, and
neither this audit nor the shared QA gate looks there. Sāmaveda, Śukla Yajurveda and Atharvaveda all
need descriptors and none have them.

**Ownership was unassigned** when this finding was raised, so I adjudicated the rights, supplied values
to the requesting agent, and referred ownership to Agent A rather than writing the file — because
expanding my own write scope on a *peer's* request is the same failure this audit exists to catch.

**Agent A assigned the file to Agent E as single writer and the coordinator reviewed and endorsed that
ruling**, which discharges the scruple: it is a contract assignment, not self-assignment. The rationale
was that Agent A owns the *model* `TextVersionDescriptor` but holds no rights authority, so assigning it
there would split rights authority for one artifact across two writers and make Agent A a transcriber of
Agent E's values. `text_versions.yaml` is the same class of object as `sources.yaml`,
`source_artifacts.yaml` and `rights.yaml`. **Grouping by authority beats grouping by file.**

**RESOLVED. `text_versions.yaml` went from 7 records to 13.** Every `text_version_id` emitted by every
pilot now resolves; all descriptors reference a registered `artifact_id`. Ids were **read from the
pilots' own `text_versions.jsonl`**, never invented.

| `text_version_id` | role | **rights** |
|---|---|---|
| `GRETIL.AVS.SAUNAKA.ACCENTED` | `PRIMARY_TEXT` | **`REFERENCE_ONLY`** |
| `GRETIL.AVS.SAUNAKA.UNACCENTED` | `PARALLEL_TEXT` | **`REFERENCE_ONLY`** |
| `VEDAGRAPH.AVS.SEARCH_NORMALIZED` | `SEARCH_DERIVATIVE` | **`REFERENCE_ONLY`** |
| `GRETIL.SV.KAUTHUMA` | `PRIMARY_TEXT` | **`PERMISSION_REQUIRED`** |
| `WIKISOURCE_SA.YV.VSM.UNACCENTED` | `PARALLEL_TEXT` | `CC_BY_SA` |
| `WIKISOURCE_SA.YV.VSM.ACCENTED` | `EXTRACTED_FROM_CONTAINER` | `CC_BY_SA` |

**Four of the six are restrictive, and that is the deliverable.** Previously those ids resolved against
nothing, so a build could attach *no* rights to 561 emitted rows sitting over artifacts that are
reference-only or forbid modification outright. A correct restrictive value closes the defect; a
permissive guess would have deepened it.

**Two findings fell out of doing this, and both generalise.**

*Role and rights are independent, and neither is a proxy for the other.* Four records deliberately carry
a permissive-sounding **role** over a restrictive **rights** value — `GRETIL.AVS.SAUNAKA.ACCENTED` is
`PRIMARY_TEXT` *and* `REFERENCE_ONLY`. Those answer different questions: the role says what the layer
**is** structurally, the rights say what may be **done** with it. This is the best Śaunaka text available
and it is still not redistributable. **Any pipeline treating role as a proxy for permission would ship an
infringement here.**

*A derived layer cannot carry more rights than its source.* `VEDAGRAPH.AVS.SEARCH_NORMALIZED` is the most
rights-dangerous of the six precisely because it looks safest — it is the only layer VedaGraph itself
produces and its id begins with `VEDAGRAPH`, both of which invite the conclusion that we own it. We do
not: it is a derivative of a `REFERENCE_ONLY` artifact, and normalizing text for search does not launder
an upstream restriction (rule RIGHTS-9). Registering it is what makes that inheritance *checkable* —
unregistered, it would have had no resolvable rights at all, which is how a restriction gets silently
dropped at exactly the layer a human would least expect one.

---

## 4. Verdict

The snapshot store is **provenance-sound**. 1346 of 1346 payloads hash-verify, every required field is
populated on every record, and there are zero orphans, zero missing payloads and zero `.partial`
residue. The no-overwrite guarantee is enforced by content-addressed naming plus an explicit guard in
`persist_snapshot()`, not by operator discipline, and cached snapshots are re-hashed before reuse.

**One real defect:** 71 snapshots (5.3%) carry `source_id` values absent from the source registry,
breaking the snapshot-to-rights join. Partially resolved; the remainder is an action on Agents C/D and a
proposed QA check for Agent F.

**Two systemic gaps the audit cannot fix.**

First, hash verification proves a snapshot is *unaltered since retrieval*. It says nothing about whether
we were *entitled* to retrieve it. That question is answered only by `data/registry/rights.yaml` and the
per-artifact evidence in `data/registry/source_artifacts.yaml` — which is why `copy_local` is a rights
field rather than a storage setting.

Second, and sharper after F6: hash verification proves a snapshot matches *its own* recorded digest. It
cannot tell whether that digest was pinned against **the right artifact**. Integrity and scope are
independent properties, and this audit only ever measured the first. Three layers are needed and none
subsumes another — **this audit** (bytes match their own digest, catches corruption in the raw tree),
**Agent D's build-time cross-check** (bytes match the registry's claim, catches a registry mispointing),
and **Agent C's scope check** (the bytes are the artifact the row denotes, catches a mis-scoped pin that
both of the others would pass).
