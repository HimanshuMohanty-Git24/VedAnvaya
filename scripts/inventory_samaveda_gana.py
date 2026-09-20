"""Inventory the Samaveda GANA corpus without ingesting it.

Scope note, and the reason this script exists at all: ``VG:WORK:SV:KAU`` covers the
Kauthuma **arcika** only - 1,844 canonical verses over 106 Wikisource pages. The **gana**
collections (gramageya, aranyakageya, uha, uhya/rahasya) are a parallel and larger body
that the arcika work does not cover and cannot address. They need their own ``work_id``.

This script measures that body and stops. It does NOT model gana identity, does NOT
snapshot or parse gana page content, and does NOT download audio bytes. It writes two
inventory files under ``data/source_registry/``:

* ``samaveda_gana_page_inventory.jsonl`` - one row per non-arcika page in the Kauthuma
  Samhita subtree on ``sa.wikisource.org``, with pageid, current revid, byte size and the
  gana book it belongs to.
* ``samaveda_gana_audio_inventory.jsonl`` - one row per distinct ``.ogg`` referenced from
  any page of that subtree, with the metadata the Commons ``imageinfo`` API reports.

Two digests are emitted for the audio collection so that the artifact record
``COMMONS.SV.KAU.SAMAN.AUDIO`` can finally carry one. Both are computed over API-reported
values, NOT over audio bytes:

* ``collection_digest_sha256`` - sha256 over ``f"{file_name}\\t{sha1}\\n"`` for every file,
  ordered by ``(file_name, sha1)``, UTF-8 encoded.
* the per-file ``sha1`` values it is built from are the MediaWiki API's own digests. They
  are **not** the sha256-of-bytes that ``checksum_sha256`` in the artifact registry means.
  Recording a sha1 in a sha256 field would be a category error; see the work packet.

Enumeration is reproducible from these two facts alone:

1. every page whose title begins ``सामवेदः/कौथुमीया/संहिता/`` on ``sa.wikisource.org``
   namespace 0, via ``list=allpages``;
2. every file transcluded on those pages, via ``prop=images``, filtered to ``.ogg``.

Usage::

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/inventory_samaveda_gana.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import httpx

USER_AGENT: Final = "VedaGraph/1.0 (research; +https://github.com/HimanshuMohanty-Git24/VedAnvaya)"
WIKISOURCE_HOST: Final = "sa.wikisource.org"
COMMONS_HOST: Final = "commons.wikimedia.org"

# The Kauthuma Samhita subtree. The parent page itself is excluded by the trailing slash;
# it carries no verse or gana content and is counted separately in the summary.
SAMHITA_PREFIX: Final = "सामवेदः/कौथुमीया/संहिता/"

# Segment 3 of the page title (0-based) names the collection. These are the values the
# selected witness actually uses; anything else is reported as UNCLASSIFIED rather than
# silently folded into a neighbouring book.
ARCIKA_SEGMENTS: Final[dict[str, str]] = {
    "पूर्वार्चिकः": "PURVARCIKA",
    "उत्तरार्चिकः": "UTTARARCIKA",
}
GANA_SEGMENTS: Final[dict[str, str]] = {
    "ग्रामगेयः": "GRAMAGEYA",
    "आरण्यकगेयः": "ARANYAKAGEYA",
    "ऊहगानम्": "UHAGANA",
    "ऊह्यगानम्": "UHYAGANA",
    "रहस्यगानम्": "RAHASYAGANA",
}
# Indexes, stobha and chandas word-lists, and the "saswara purna" page. Real pages of the
# subtree, but not gana units - kept in the inventory and flagged, never counted as gana.
ANCILLARY_SEGMENTS: Final[frozenset[str]] = frozenset(
    {
        "ग्रामगेयस्य सूची",
        "आरण्यकगानस्य सूची",
        "ऊहगानस्य सूची",
        "ऊह्यगानस्य सूची",
        "छन्दःपदम्",
        "स्तोभपदम्",
        "सस्वरा पूर्णा",
    }
)

# Commons categories queried only as a cross-check on the page-reference enumeration.
# They are NOT the enumeration basis: the page-reference route is, because it is the one
# that yields the PAGE_LEVEL alignment the artifact record claims.
CROSSCHECK_CATEGORIES: Final[tuple[str, ...]] = (
    "Category:Audio files of Samaveda",
    "Category:Gramageya",
    "Category:Uhaganam",
    "Category:Uhyaganam",
    "Category:Samaveda",
)

_TAG_RE: Final = re.compile(r"<[^>]+>")


def _strip_html(value: str) -> str:
    """Reduce a Commons extmetadata HTML fragment to its text, entities unescaped."""
    text = _TAG_RE.sub("", value)
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')):
        text = text.replace(entity, char)
    return " ".join(text.split())


class MediaWikiClient:
    """A deliberately slow MediaWiki API client.

    No writes, no bulk downloads, one request at a time with a fixed inter-request
    delay. The delay is not tuned for throughput; it exists so that a survey run is
    obviously polite to a donated public API.
    """

    def __init__(self, host: str, *, delay_seconds: float = 0.4, timeout: float = 60.0) -> None:
        self.host = host
        self.delay_seconds = delay_seconds
        self._client = httpx.Client(
            base_url=f"https://{host}/w/",
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=timeout,
            follow_redirects=True,
        )
        self.request_count = 0

    def __enter__(self) -> MediaWikiClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self._client.close()

    def get(self, params: Mapping[str, str]) -> dict[str, Any]:
        return self._request("GET", params)

    def post(self, params: Mapping[str, str]) -> dict[str, Any]:
        """POST a read query.

        Needed because Devanagari titles percent-encode to roughly nine bytes per
        character, so a 50-title ``titles=`` batch overruns the URI length limit and the
        server answers 414. POST is explicitly supported for read queries.
        """
        return self._request("POST", params)

    def _request(self, method: str, params: Mapping[str, str]) -> dict[str, Any]:
        merged: dict[str, str] = {"format": "json", "formatversion": "2", **params}
        last_error: Exception | None = None
        for attempt in range(4):
            if self.request_count:
                time.sleep(self.delay_seconds)
            self.request_count += 1
            try:
                if method == "POST":
                    response = self._client.post("api.php", data=merged)
                else:
                    response = self._client.get("api.php", params=merged)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - network path
                status = exc.response.status_code
                if status < 500 and status != 429:
                    raise RuntimeError(f"{self.host} refused the request: {status}") from exc
                last_error = exc
                time.sleep(2.0 * (attempt + 1))
                continue
            except (httpx.HTTPError, ValueError) as exc:  # pragma: no cover - network path
                last_error = exc
                time.sleep(2.0 * (attempt + 1))
                continue
            if "error" in payload:
                raise RuntimeError(f"{self.host} API error: {payload['error']}")
            return payload
        raise RuntimeError(f"{self.host} unreachable after 4 attempts: {last_error}")

    def query_pages(self, params: Mapping[str, str]) -> list[dict[str, Any]]:
        """Run a ``prop=`` query to exhaustion, merging continuations by pageid.

        MediaWiki may return the same page across several continuation rounds with
        different slices of a list-valued prop, so list values are extended rather than
        overwritten. Overwriting is the classic way to lose half a page's images.
        """
        merged: dict[int, dict[str, Any]] = {}
        continuation: dict[str, str] = {}
        while True:
            payload = self.get({**params, **continuation})
            for page in payload.get("query", {}).get("pages", []):
                pageid = int(page.get("pageid", -1))
                existing = merged.get(pageid)
                if existing is None:
                    merged[pageid] = dict(page)
                    continue
                for key, value in page.items():
                    if isinstance(value, list):
                        prior = existing.get(key)
                        existing[key] = (prior if isinstance(prior, list) else []) + value
                    else:
                        existing.setdefault(key, value)
            raw_continue = payload.get("continue")
            if not raw_continue:
                return list(merged.values())
            continuation = {k: str(v) for k, v in raw_continue.items()}

    def list_all(self, params: Mapping[str, str], list_name: str) -> list[dict[str, Any]]:
        """Run a ``list=`` query to exhaustion."""
        out: list[dict[str, Any]] = []
        continuation: dict[str, str] = {}
        while True:
            payload = self.get({**params, **continuation})
            out.extend(payload.get("query", {}).get(list_name, []))
            raw_continue = payload.get("continue")
            if not raw_continue:
                return out
            continuation = {k: str(v) for k, v in raw_continue.items()}


@dataclass(frozen=True, slots=True)
class SamhitaPage:
    """One page of the Kauthuma Samhita subtree, as the API reports it."""

    page_title: str
    page_id: int
    revid: int
    byte_size: int
    url: str
    is_redirect: bool
    section: str
    collection: str | None
    title_segment: str


def classify(title: str) -> tuple[str, str | None, str]:
    """Return ``(section, collection, title_segment)`` for a Samhita subtree page title.

    ``section`` is one of ARCIKA / GANA / ANCILLARY / UNCLASSIFIED and is what the
    106-versus-725 split is counted on. ``collection`` is the romanised book name, or
    ``None`` where the page belongs to no collection.
    """
    segments = title.split("/")
    key = segments[3].rstrip("/") if len(segments) > 3 else ""
    if key in ARCIKA_SEGMENTS:
        return "ARCIKA", ARCIKA_SEGMENTS[key], key
    if key in GANA_SEGMENTS:
        return "GANA", GANA_SEGMENTS[key], key
    if key in ANCILLARY_SEGMENTS:
        return "ANCILLARY", None, key
    return "UNCLASSIFIED", None, key


def fetch_samhita_pages(client: MediaWikiClient) -> list[SamhitaPage]:
    raw = client.query_pages(
        {
            "action": "query",
            "generator": "allpages",
            "gapnamespace": "0",
            "gaplimit": "500",
            "gapprefix": SAMHITA_PREFIX,
            "prop": "info",
            "inprop": "url",
        }
    )
    pages: list[SamhitaPage] = []
    for page in raw:
        title = str(page["title"])
        section, collection, segment = classify(title)
        pages.append(
            SamhitaPage(
                page_title=title,
                page_id=int(page["pageid"]),
                revid=int(page.get("lastrevid", 0)),
                byte_size=int(page.get("length", 0)),
                url=str(page.get("fullurl", "")),
                is_redirect=bool(page.get("redirect", False)),
                section=section,
                collection=collection,
                title_segment=segment,
            )
        )
    pages.sort(key=lambda p: p.page_title)
    return pages


def fetch_file_references(client: MediaWikiClient) -> dict[str, set[str]]:
    """Map each ``.ogg`` file title to the set of subtree pages that reference it.

    File titles are returned in the wiki's own namespace form (``सञ्चिका:``); they are
    normalised to the canonical ``File:`` form for the Commons query.
    """
    raw = client.query_pages(
        {
            "action": "query",
            "generator": "allpages",
            "gapnamespace": "0",
            "gaplimit": "100",
            "gapprefix": SAMHITA_PREFIX,
            "prop": "images",
            "imlimit": "max",
        }
    )
    references: dict[str, set[str]] = defaultdict(set)
    for page in raw:
        page_title = str(page["title"])
        for image in page.get("images", []):
            local_title = str(image["title"])
            _, _, bare = local_title.partition(":")
            if not bare.lower().endswith(".ogg"):
                continue
            references[f"File:{bare}"].add(page_title)
    return dict(references)


def fetch_commons_imageinfo(
    client: MediaWikiClient, titles: Sequence[str]
) -> dict[str, dict[str, Any]]:
    """Fetch imageinfo for every title, 50 at a time (the API's uncapped-user limit)."""
    out: dict[str, dict[str, Any]] = {}
    for batch in _chunks(titles, 50):
        payload = client.post(
            {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "imageinfo",
                "iiprop": "url|size|sha1|mime|extmetadata|user|timestamp|mediatype",
            }
        )
        query = payload.get("query", {})
        normalised = {str(entry["from"]): str(entry["to"]) for entry in query.get("normalized", [])}
        by_title: dict[str, dict[str, Any]] = {
            str(page["title"]): page for page in query.get("pages", [])
        }
        for requested in batch:
            resolved = normalised.get(requested, requested)
            page = by_title.get(resolved)
            if page is not None:
                out[requested] = page
    return out


def _chunks(items: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _ext(metadata: Mapping[str, Any], key: str) -> str:
    entry = metadata.get(key)
    if isinstance(entry, dict):
        return str(entry.get("value", ""))
    return ""


def build_audio_rows(
    references: Mapping[str, set[str]],
    imageinfo: Mapping[str, dict[str, Any]],
    page_collection: Mapping[str, str | None],
    page_section: Mapping[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for commons_title in sorted(references):
        pages = sorted(references[commons_title])
        collections = sorted({page_collection.get(page) or "UNCLASSIFIED" for page in pages})
        gana_aligned = any(page_section.get(page) == "GANA" for page in pages)
        page = imageinfo.get(commons_title)
        file_name = commons_title.removeprefix("File:")
        if page is None or "missing" in page or not page.get("imageinfo"):
            rows.append(
                {
                    "alignment_granularity": "PAGE_LEVEL",
                    "artist": None,
                    "artist_html": None,
                    "byte_size": None,
                    "commons_page_id": None,
                    "commons_title": commons_title,
                    "credit": None,
                    "descriptionurl": None,
                    "direct_url": None,
                    "duration_seconds": None,
                    "file_name": file_name,
                    "found_on_commons": False,
                    "gana_aligned": gana_aligned,
                    "licence_shortname": None,
                    "licence_url": None,
                    "mediatype": None,
                    "mime": None,
                    "referenced_from_collections": collections,
                    "referenced_from_wikisource_page_count": len(pages),
                    "referenced_from_wikisource_pages": pages,
                    "sha1": None,
                    "sha1_is_not_sha256": True,
                    "sha256_of_bytes": None,
                    "upload_timestamp": None,
                    "uploader": None,
                    "usage_terms": None,
                }
            )
            continue
        info = page["imageinfo"][0]
        meta = info.get("extmetadata", {})
        direct_url = str(info.get("url", "")).split("?", 1)[0]
        rows.append(
            {
                # Stated on every row: the source's own reference is from a PAGE, so no
                # mantra-level or timestamp-level alignment exists and none is invented.
                "alignment_granularity": "PAGE_LEVEL",
                "artist": _strip_html(_ext(meta, "Artist")) or None,
                "artist_html": _ext(meta, "Artist") or None,
                "byte_size": int(info.get("size", 0)),
                "commons_page_id": int(page["pageid"]),
                "commons_title": commons_title,
                "credit": _strip_html(_ext(meta, "Credit")) or None,
                "descriptionurl": str(info.get("descriptionurl", "")) or None,
                "direct_url": direct_url or None,
                "duration_seconds": (
                    float(info["duration"]) if info.get("duration") is not None else None
                ),
                "file_name": file_name,
                "found_on_commons": True,
                "gana_aligned": gana_aligned,
                "licence_shortname": _ext(meta, "LicenseShortName") or None,
                "licence_url": _ext(meta, "LicenseUrl") or None,
                "mediatype": str(info.get("mediatype", "")) or None,
                "mime": str(info.get("mime", "")) or None,
                "referenced_from_collections": collections,
                "referenced_from_wikisource_page_count": len(pages),
                "referenced_from_wikisource_pages": pages,
                "sha1": str(info.get("sha1", "")) or None,
                # Stated on every row so no downstream reader can mistake the MediaWiki
                # sha1 for the sha256-of-bytes the artifact registry asks for.
                "sha1_is_not_sha256": True,
                "sha256_of_bytes": None,
                "upload_timestamp": str(info.get("timestamp", "")) or None,
                "uploader": str(info.get("user", "")) or None,
                "usage_terms": _ext(meta, "UsageTerms") or None,
            }
        )
    return rows


def collection_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    """sha256 over ``file_name\\tsha1\\n`` pairs, ordered by ``(file_name, sha1)``.

    Deterministic and independent of row order, JSON formatting and key set. Files with
    no Commons sha1 contribute an empty digest field rather than being dropped, so a file
    disappearing from Commons changes the collection digest instead of hiding.
    """
    pairs = sorted((str(row["file_name"]), str(row["sha1"] or "")) for row in rows)
    blob = "".join(f"{name}\t{digest}\n" for name, digest in pairs)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def crosscheck_categories(client: MediaWikiClient) -> dict[str, int]:
    counts: dict[str, int] = {}
    for category in CROSSCHECK_CATEGORIES:
        members = client.list_all(
            {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmlimit": "500",
                "cmtype": "file",
            },
            "categorymembers",
        )
        counts[category] = sum(
            1 for member in members if str(member["title"]).lower().endswith(".ogg")
        )
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/source_registry"),
        help="directory the two JSONL inventories are written to",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.4,
        help="fixed pause between API requests",
    )
    parser.add_argument(
        "--skip-crosscheck",
        action="store_true",
        help="skip the Commons category cross-check",
    )
    args = parser.parse_args(argv)

    with MediaWikiClient(WIKISOURCE_HOST, delay_seconds=args.delay_seconds) as wikisource:
        pages = fetch_samhita_pages(wikisource)
        references = fetch_file_references(wikisource)
        wikisource_requests = wikisource.request_count

    page_collection = {page.page_title: page.collection for page in pages}
    page_section = {page.page_title: page.section for page in pages}
    referencing_pages = {page for pages_ in references.values() for page in pages_}

    with MediaWikiClient(COMMONS_HOST, delay_seconds=args.delay_seconds) as commons:
        imageinfo = fetch_commons_imageinfo(commons, sorted(references))
        category_counts = {} if args.skip_crosscheck else crosscheck_categories(commons)
        commons_requests = commons.request_count

    audio_rows = build_audio_rows(references, imageinfo, page_collection, page_section)
    digest = collection_digest(audio_rows)

    non_arcika = [page for page in pages if page.section != "ARCIKA"]
    ogg_per_page: Counter[str] = Counter()
    for pages_ in references.values():
        for page_title in pages_:
            ogg_per_page[page_title] += 1
    page_rows = [
        {
            "byte_size": page.byte_size,
            # Deliberately false everywhere: this run inventories, it does not snapshot.
            "content_snapshotted": False,
            "gana_book": page.collection,
            "is_redirect": page.is_redirect,
            "page_id": page.page_id,
            "page_title": page.page_title,
            "referenced_ogg_count": ogg_per_page.get(page.page_title, 0),
            "revid": page.revid,
            "section": page.section,
            "title_segment": page.title_segment,
            "url": page.url,
        }
        for page in non_arcika
    ]

    out_dir: Path = args.out_dir
    write_jsonl(out_dir / "samaveda_gana_page_inventory.jsonl", page_rows)
    write_jsonl(out_dir / "samaveda_gana_audio_inventory.jsonl", audio_rows)

    section_counts = Counter(page.section for page in pages)
    book_counts = Counter(
        page.collection or "UNCLASSIFIED" for page in pages if page.section == "GANA"
    )
    licence_counts = Counter(str(row["licence_shortname"]) for row in audio_rows)
    uploader_counts = Counter(str(row["uploader"]) for row in audio_rows)
    total_bytes = sum(int(row["byte_size"] or 0) for row in audio_rows)
    total_seconds = sum(float(row["duration_seconds"] or 0.0) for row in audio_rows)
    gana_aligned = sum(1 for row in audio_rows if row["gana_aligned"])
    gana_ref_pages = sum(1 for page in referencing_pages if page_section.get(page) == "GANA")

    print(f"wikisource API requests : {wikisource_requests}")
    print(f"commons API requests    : {commons_requests}")
    print(f"samhita subtree pages   : {len(pages)}")
    for section, count in sorted(section_counts.items()):
        print(f"  {section:<14}: {count}")
    print("gana pages per book:")
    for book, count in sorted(book_counts.items()):
        print(f"  {book:<14}: {count}")
    print(f"non-arcika rows written : {len(page_rows)}")
    print(f"distinct .ogg           : {len(audio_rows)}")
    print(f"  of which gana-aligned : {gana_aligned}")
    print(f"  arcika-page only      : {len(audio_rows) - gana_aligned}")
    print(f"pages referencing .ogg  : {len(referencing_pages)} ({gana_ref_pages} gana)")
    print(f"missing on commons      : {sum(1 for r in audio_rows if not r['found_on_commons'])}")
    print("licence split (measured):")
    for licence, count in sorted(licence_counts.items()):
        print(f"  {licence:<24}: {count}")
    print("uploaders:")
    for uploader, count in uploader_counts.most_common(10):
        print(f"  {uploader:<24}: {count}")
    print(f"total audio bytes       : {total_bytes}")
    print(f"total duration (hours)  : {total_seconds / 3600.0:.2f}")
    print(f"collection_digest_sha256: {digest}")
    print("  definition: sha256 of UTF-8 'file_name\\tsha1\\n' lines, sorted by")
    print("  (file_name, sha1). sha1 is the MediaWiki digest, NOT sha256-of-bytes.")
    if category_counts:
        print("commons category cross-check (.ogg members):")
        for category, count in sorted(category_counts.items()):
            print(f"  {category:<36}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
