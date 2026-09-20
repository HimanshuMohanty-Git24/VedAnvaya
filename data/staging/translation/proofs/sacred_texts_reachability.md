# sacred-texts.com reachability, re-probed 2026-09-15

Wave 0 recorded HTTP 403 from this host, direct and through its own `www` redirect, and made
a re-probe Wave 1's first step. The re-probe was run before any acquisition was attempted.

## Result: still 403, and now with the cause visible

| URL | Result |
|---|---|
| `https://sacred-texts.com/hin/av/av20001.htm` (research UA) | **403**, 5,525 bytes |
| `https://www.sacred-texts.com/hin/av/index.htm` (research UA, followed to apex) | **403**, 5,519 bytes |
| `https://sacred-texts.com/hin/sv/index.htm` (research UA) | **403**, 5,519 bytes |
| `https://sacred-texts.com/hin/av/av20001.htm` (full desktop browser UA + Accept) | **403** |

The body is not an error page. It is a Cloudflare interstitial:

```html
<!DOCTYPE html><html lang="en-US"><head><title>Just a moment...</title>
 ... script-src ... https://challenges.cloudflare.com ...
```

So the host is answering, and answering with a **bot challenge**. That matters for two reasons.

1. It is not a transient outage and not an IP block to wait out. It is a managed challenge
   that only a challenge solver clears.
2. Solving it is out of bounds. The brief forbids CAPTCHAs and bypasses, so no attempt was
   made, and none should be made later either: the route is closed by policy, not by luck.

## What was used instead

**The Internet Archive Wayback Machine**, which is a public archive, serves no challenge, and
returns the pre-JavaScript captures of the same pages with their per-verse anchors intact.

| Need | Route | Outcome |
|---|---|---|
| Griffith AV kanda 20, 143 hymns | `web.archive.org/web/20230325113203/.../hin/av/av20NNN.htm` | 144/144 pages HTTP 200 |
| Griffith AV kandas 3, 5, 10 (the 3 strays) | same capture | 3/3 HTTP 200 |
| Griffith Samaveda, whole work | `web.archive.org/web/20231227014835/.../hin/sv.htm` | HTTP 200, 284,759 bytes |
| Griffith Rigveda, 16 hymn pages | `web.archive.org/web/2023/.../hin/rigveda/rvMMSSS.htm` | 16/16 HTTP 200 |
| Griffith White Yajurveda | not fetched at all | the 2026-09-07 snapshot is already on disk |

Wayback URLs carry an explicit capture timestamp and are immutable, so a timestamped URL plus
the sha256 recorded in `proofs/source_pages.json` is replayable provenance in the same sense
the local content-addressed snapshots are.

## One path note worth keeping

Griffith's *Hymns of the Samaveda* is **not** under `/hin/sv/`. That path 404s on Wayback and
would read as "the archive does not have it". The work is a single page at `/hin/sv.htm`.
