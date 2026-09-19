"""Tests for the certified /completeness endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository, build_client

COMPLETENESS = "/api/v1/completeness"
STATS_COMPLETENESS = "/api/v1/stats/completeness"


def test_completeness_endpoint_returns_certified_state():
    app, client = build_client(FakeRepository())
    with client:
        resp = client.get(COMPLETENESS)
        assert resp.status_code == 200
        data = resp.json()

        assert data["data_status"] == "SUPPORTED"
        assert data["certified_release_commit"] == "50a40429103fa32a5667ee58c72c029cfbeb0f74"

        # Corpora invariants
        corpora = {c["veda"]: c for c in data["corpora"]}
        assert len(corpora) == 4
        assert corpora["RV"]["canonical_mantras"] == 10552
        assert corpora["SV"]["canonical_mantras"] == 1844
        assert corpora["YV"]["canonical_mantras"] == 1975
        assert corpora["AV"]["canonical_mantras"] == 5839
        total_mantras = sum(c["canonical_mantras"] for c in corpora.values())
        assert total_mantras == 20210

        # Translations typed breakdown
        trans = data["translations"]
        assert trans["total_mantras"] == 20210
        assert trans["total_dedicated_english"] == 18145
        assert trans["total_range_covered"] == 128
        assert trans["total_reused_rendering"] == 194
        assert trans["total_non_english"] == 24
        assert trans["total_uncovered"] == 1719
        # Sum check
        assert (
            trans["total_dedicated_english"]
            + trans["total_range_covered"]
            + trans["total_reused_rendering"]
            + trans["total_non_english"]
            + trans["total_uncovered"]
        ) == 20210

        # Samaveda translation truth
        sv_trans = trans["by_veda"]["SV"]
        assert sv_trans["dedicated_english"] == 0
        assert sv_trans["reused_rendering"] == 173
        assert sv_trans["uncovered"] == 1671

        # Samaveda notation
        sv_not = data["samaveda_notation"]
        assert sv_not["canonical_corpus_mantras"] == 1844
        assert sv_not["validated_notation_witnesses"] == 1136
        assert sv_not["unaligned_withheld_verses"] == 708
        assert sv_not["musicalized_as_edges"] == 0
        assert sv_not["gana_works_modeled"] == 0
        assert "Gate A: PASS" in sv_not["gates_passed"]
        assert "Gate B: PASS" in sv_not["gates_passed"]
        assert "Gate C: SURVIVED" in sv_not["gates_passed"]

        # Audio released and review queue
        audio = data["audio"]
        assert audio["released_catalogue_records"] == 16834
        assert audio["released_by_veda"]["SV"] == 0
        assert audio["owner_audible_sample_status"] == "ACCEPTED"
        assert audio["owner_sample_reviewed"] == 20
        assert audio["owner_sample_verified"] == 20
        assert audio["owner_sample_rejected"] == 0
        assert audio["not_individually_heard"] == 1001
        assert audio["queue_rows_promoted"] == 0

        # Ask 60 benchmark
        ask = data["ask_benchmark"]
        assert ask["total_questions"] == 60
        assert ask["effective_acceptable"] == "60/60"
        assert ask["misleading"] == 0
        assert ask["hallucinated"] == 0

        # Alias check
        alias_resp = client.get(STATS_COMPLETENESS)
        assert alias_resp.status_code == 200
        assert alias_resp.json() == data

