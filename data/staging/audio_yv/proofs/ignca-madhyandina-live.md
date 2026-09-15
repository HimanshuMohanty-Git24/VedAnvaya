# Proof: IGNCA Mādhyandina audio is live today — reconnaissance's verdict is wrong

Probed 2026-09-15 from this machine. Agent 6, Wave 1.

## What reconnaissance concluded

`source-reconnaissance.md` §2.2 and `WAVE_0_CLOSURE.md` blocker 2:

> **IGNCA's 40 `SYMS_CHAP_*.mp3` remain 404**, re-verified 17 months on. YV Mādhyandina
> audio would have to be commissioned. This is a genuine external unavailability.
> **Do not re-probe.**

The brief instructed me to re-probe anyway. I did, and the instruction was right.

## The probe of the path reconnaissance used — it is correct

```
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_01.mp3 -> 404  179454b  text/html
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_01.mp4 -> 404  179454b  text/html
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_07.mp3 -> 404  179454b  text/html
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_07.mp4 -> 404  179454b  text/html
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_12.mp3 -> 404  179454b  text/html
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_12.mp4 -> 404  179454b  text/html
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_20.mp3 -> 404  179454b  text/html
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_20.mp4 -> 404  179454b  text/html
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_40.mp3 -> 404  179454b  text/html
https://vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_40.mp4 -> 404  179454b  text/html
```

All ten 404, with the portal's 179,454-byte HTML error page. The `/Yajurveda_MP3/` generation
is genuinely gone. Reconnaissance measured this correctly.

## The probe of the path reconnaissance did not use — it is live

`docs/FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md` §4.4 recorded a *different* directory, and
reconnaissance did not carry it forward. It answers today:

```
Shukla_Yajurveda_Madhyandin_MP3/SYMS_CHAP_01.mp4       -> 206  video/mp4
Shukla_Yajurveda_Madhyandin_MP3/SYMS_CHAP_20.mp4       -> 206  video/mp4
Shukla_Yajurveda_Madhyandin_MP3/SYMS_CHAP_40.mp4       -> 206  video/mp4
Shukla_Yajurveda_Madhyandin_MP3/SYMS_CHAP_41.mp4       -> 404  text/html
Shukla_Yajurveda_Madhyandin_MP3/SYMS_INTRO_CHAP_06.mp4 -> 206  video/mp4
Shukla_Yajurveda_Madhyandin_MP3/SYMS_CHAP_01.mp3       -> 404  text/html
```

`HEAD`, showing these are real media of substantial size and not redirect stubs:

| file | status | Content-Length | Content-Type | Last-Modified |
|---|---|--:|---|---|
| `SYMS_CHAP_01.mp4` | 200 | 42,989,877 | video/mp4 | Wed, 28 Feb 2024 12:18:41 GMT |
| `SYMS_CHAP_02.mp4` | 200 | 39,296,671 | video/mp4 | Wed, 28 Feb 2024 12:18:41 GMT |
| `SYMS_CHAP_08.mp4` | 200 | 48,470,612 | video/mp4 | Wed, 28 Feb 2024 12:18:42 GMT |
| `SYMS_CHAP_26.mp4` | 200 | 20,369,487 | video/mp4 | Wed, 28 Feb 2024 12:18:44 GMT |
| `SYMS_CHAP_35.mp4` | 200 | 13,993,056 | video/mp4 | Wed, 28 Feb 2024 12:18:45 GMT |

`Accept-Ranges: bytes` on all of them. `CHAP_41` → 404, so the set's boundary is exactly 40
adhyāyas — the Mādhyandina count, not Kāṇva's division.

## Why this is nonetheless rejected

Two independent grounds, and neither is availability.

**1. Rights.** IGNCA's stated position is `PERMISSION_REQUIRED`.
`docs/FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md` §4.3 additionally records that the portal's player
sets `disablepictureinpicture` — a deliberate technical step against download. Publicly
playable does not imply permitted, and this project already removed the Vedic Heritage route
once on exactly that basis. No mirroring, and direct linking is contested.

**2. Granularity.** One file per adhyāya, 14–48 MB, with no timestamp file, no cue index and no
per-mantra marker. The gap is 198 individual mantras. Section 10 permits `VERIFIED_SEGMENT` only
where a boundary is established by real evidence; here there is none, so any per-mantra
attachment would be a guessed boundary. `vedicheritage.gov.in/yajurveda-madhyandina-samhita-adhyaya-01/`
does enumerate mantras 1–31 individually, which is useful *text* apparatus, but it carries no
time offsets.

## The consequence for the gap's classification

The residual 198 must **not** be filed as `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE`. The recording
exists, it is the right recension, it is online today, and a named institution holds it. The
honest label is **blocked on rights and on granularity**, which is a materially different
problem with a materially different remedy: one permission request to IGNCA plus a verified
segmentation pass, rather than commissioning a reciter.

## One incidental corroboration

IGNCA's own page is titled "Yajurveda, Madhyandina Samhita, Adhyaya 01" and enumerates mantras
**1–31**. This corpus's adhyāya 1 holds exactly **31** mantras. That is one of the three
structural facts used as `recension_evidence` on every staged row.
