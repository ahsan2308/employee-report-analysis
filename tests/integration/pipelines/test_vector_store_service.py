"""Characterization of app/services/vector_store_service.py with Qdrant and embeddings faked.

Outcome = return values + every vector-store / embedding call + qdrant_mappings rows.
"""
from datetime import date, datetime

import pytest

import app.services.vector_store_service as vss
from tests.integration.pipelines.conftest import COLLECTION
from tests.integration.pipelines.seed import (
    EMP_ID,
    FIXED_UUIDS,
    REPORT_IDS,
    dump_mappings,
    seed_employees,
    seed_reports,
)
from tests.support.scrub import scrub

LONG_TEXT = (
    "Reviewed twelve case files for the regional desk and reconciled every entry against the archive ledger. "
    "Prepared a consolidated digest for the wing head covering the backlog and the pending field reports. "
    "Coordinated with the operations section to schedule the archive scanner for the next fortnight. "
    "Drafted three analytical notes on recurring discrepancies in the district submissions. "
    "Trained two new desk officers on the reporting template and checked their first submissions. "
    "Closed the long standing request from the provincial office after verifying the supporting documents. "
    "A final sentence without any full stop that keeps going past the chunk limit so the splitter has to cut it "
    + "x" * 520
)

R1, R2, R3 = (REPORT_IDS[date(2025, 3, 7)], REPORT_IDS[date(2025, 3, 14)], REPORT_IDS[date(2025, 3, 21)])


@pytest.fixture
def reports(db_session):
    seed_employees(db_session)
    seed_reports(db_session)
    return db_session


def _snap(snapshot, name, db_session, ext, outcome):
    snapshot(name, scrub({
        "outcome": outcome,
        "qdrant_mappings": dump_mappings(db_session, ext.vector_store.document_order),
        "collections": ext.vector_store.collections,
        "external_calls": ext.calls,
    }, keep_uuids=FIXED_UUIDS))


def test_chunk_text_boundaries(snapshot):
    snapshot("vector__chunk_text", {
        "long": vss.chunk_text(LONG_TEXT),
        "exactly_500": [len(c) for c in vss.chunk_text("a" * 500)],
        "501_no_period": [len(c) for c in vss.chunk_text("a" * 501)],
        "empty": vss.chunk_text(""),
        "not_a_string": vss.chunk_text(None),
    })


# --------------------------------------------------------------------------- add_report_to_vector_store

def test_add_single_report_batch_mode(reports, ext, snapshot):
    outcome = vss.add_report_to_vector_store(report_id=str(R1), employee_id=EMP_ID, report_date="2025-03-07",
                                             report_text=LONG_TEXT)
    _snap(snapshot, "vector__add_single_batch_mode", reports, ext, outcome)


def test_add_single_report_bad_date_and_empty_text(reports, ext, snapshot):
    outcomes = {
        "empty_text": vss.add_report_to_vector_store(report_id=str(R1), employee_id=EMP_ID,
                                                     report_date="2025-03-07", report_text=""),
        # Day-first dates are read as the rest of the app reads them (14/03/2025 is 14 March)
        "day_first_date": vss.add_report_to_vector_store(report_id=str(R2), employee_id=EMP_ID,
                                                         report_date="14/03/2025", report_text="Short report."),
        # An unreadable date fails the call instead of being stored as "now"
        "bad_date": vss.add_report_to_vector_store(report_id=str(R3), employee_id=EMP_ID,
                                                   report_date="soon", report_text="Short report."),
    }
    _snap(snapshot, "vector__add_single_edge_cases", reports, ext, outcomes)


def test_add_reports_batch_list_with_small_upsert_batches(reports, ext, snapshot, monkeypatch):
    monkeypatch.setattr(vss, "VECTOR_UPSERT_BATCH_SIZE", 2)
    outcome = vss.add_report_to_vector_store(reports=[
        {"report_id": R1, "employee_id": EMP_ID, "report_date": "2025-03-07", "report_text": LONG_TEXT},
        {"report_id": R2, "employee_id": EMP_ID, "report_date": date(2025, 3, 14), "report_text": ""},
        {"report_id": R3, "employee_id": EMP_ID, "report_date": "2025-03-21", "report_text": "Short report."},
    ])
    _snap(snapshot, "vector__add_batch_list", reports, ext, outcome)


def test_add_reports_batch_list_all_empty(reports, ext, snapshot):
    outcome = vss.add_report_to_vector_store(reports=[
        {"report_id": R1, "employee_id": EMP_ID, "report_date": "2025-03-07", "report_text": ""},
    ])
    _snap(snapshot, "vector__add_batch_all_empty", reports, ext, outcome)


def test_add_report_upsert_fails_every_retry(reports, ext, snapshot):
    ext.vector_store.batch_failures = 99
    outcome = vss.add_report_to_vector_store(report_id=str(R1), employee_id=EMP_ID, report_date="2025-03-07",
                                             report_text="Short report.")
    _snap(snapshot, "vector__add_upsert_fails", reports, ext, outcome)


def test_add_report_upsert_recovers_on_retry(reports, ext, snapshot):
    ext.vector_store.batch_failures = 2
    outcome = vss.add_report_to_vector_store(report_id=str(R1), employee_id=EMP_ID, report_date="2025-03-07",
                                             report_text="Short report.")
    _snap(snapshot, "vector__add_upsert_recovers", reports, ext, outcome)


def test_add_report_mapping_insert_fails_for_unknown_report(reports, ext, snapshot):
    """Report id not in Postgres: points are upserted, then the mapping insert hits the FK and returns False."""
    outcome = vss.add_report_to_vector_store(report_id="00000000-0000-4000-8000-00000000beef", employee_id=EMP_ID,
                                             report_date="2025-03-07", report_text="Short report.")
    _snap(snapshot, "vector__add_mapping_fk_violation", reports, ext, outcome)


def test_add_report_when_embeddings_fail(reports, ext, snapshot):
    """Embedding provider fails: setup refuses to touch the collection, so nothing is upserted (B7 fixed)."""
    ext.embedder.fail = True
    outcome = vss.add_report_to_vector_store(report_id=str(R1), employee_id=EMP_ID, report_date="2025-03-07",
                                             report_text="Short report.")
    _snap(snapshot, "vector__add_embeddings_fail", reports, ext, outcome)


# --------------------------------------------------------------------------- setup_collection

def test_setup_collection_existing_matching_dimension(ext, snapshot):
    _snap_calls(snapshot, "vector__setup_existing_ok", ext, vss.setup_collection())


def test_setup_collection_missing(ext, snapshot):
    ext.vector_store.collections.clear()
    _snap_calls(snapshot, "vector__setup_missing", ext, vss.setup_collection())


def test_setup_collection_keeps_collection_when_embedding_probe_fails(ext, snapshot):
    ext.vector_store.points["existing-point"] = {"vector": [0.1] * 4, "payload": {"report_id": "x"}}
    ext.embedder.fail = True
    _snap_calls(snapshot, "vector__setup_probe_fails_keeps_collection", ext, vss.setup_collection())


def test_setup_collection_missing_and_embedding_probe_fails(ext, snapshot):
    ext.vector_store.collections.clear()
    ext.embedder.fail = True
    _snap_calls(snapshot, "vector__setup_missing_probe_fails", ext, vss.setup_collection())


def test_setup_collection_keeps_collection_qdrant_cannot_describe(ext, monkeypatch, snapshot):
    """The provider returns {} for any error, so an existing collection can look missing."""
    ext.vector_store.points["existing-point"] = {"vector": [0.1] * 4, "payload": {"report_id": "x"}}
    monkeypatch.setattr(ext.vector_store, "get_collection_info", lambda collection_name: {})
    _snap_calls(snapshot, "vector__setup_undescribed_keeps_collection", ext, vss.setup_collection())


def test_setup_collection_refuses_dimension_mismatch(ext, snapshot):
    ext.vector_store.collections[COLLECTION] = 8
    ext.vector_store.points["existing-point"] = {"vector": [0.1] * 8, "payload": {"report_id": "x"}}
    _snap_calls(snapshot, "vector__setup_dimension_mismatch_keeps_collection", ext, vss.setup_collection())


def _snap_calls(snapshot, name, ext, outcome):
    snapshot(name, scrub({"outcome": outcome, "collections": ext.vector_store.collections,
                          "points_left": len(ext.vector_store.points), "external_calls": ext.calls}))


# --------------------------------------------------------------------------- search_reports

def _hits():
    def hit(rid, day, score, chunk=0):
        return {"report_id": rid, "employee_id": EMP_ID, "chunk_index": chunk, "report_date": day,
                "report_date_ts": 0.0, "text": f"chunk of {day}", "score": score, "id": f"pt-{day}-{chunk}"}
    return [hit("r-a", "2025-02-07", 0.55), hit("r-b", "2025-02-21", 0.95), hit("r-c", "2025-01-10", 0.29),
            hit("r-d", "2025-02-14", 0.30, chunk=2)]


def test_search_reports_with_cutoff_grouping_and_threshold(ext, snapshot):
    ext.vector_store.search_hits = _hits()
    outcome = vss.search_reports("backlog audit", employee_id=EMP_ID, top_k=3, group_by_report=True,
                                 cutoff_date=date(2025, 3, 7), search_params={"hnsw_ef": 64})
    _snap_calls(snapshot, "vector__search_cutoff_grouped", ext, outcome)


def test_search_reports_bypass_threshold_datetime_cutoff(ext, snapshot):
    ext.vector_store.search_hits = _hits()
    outcome = vss.search_reports("backlog audit", employee_id=EMP_ID, bypass_threshold=True,
                                 cutoff_date=datetime(2025, 3, 7, 15, 30))
    _snap_calls(snapshot, "vector__search_bypass_threshold", ext, outcome)


def test_search_reports_unsortable_dates_fall_back_to_store_order(ext, snapshot):
    ext.vector_store.search_hits = _hits() + [{"report_id": "r-e", "report_date": "07/03/2025", "score": 0.9}]
    outcome = vss.search_reports("backlog audit", employee_id=EMP_ID)
    _snap_calls(snapshot, "vector__search_unsortable_dates", ext, outcome)


def test_search_reports_empty_query_embedding(ext, snapshot):
    ext.embedder.fail = True
    ext.vector_store.search_hits = _hits()
    outcome = vss.search_reports("backlog audit", employee_id=EMP_ID)
    _snap_calls(snapshot, "vector__search_embedding_fails", ext, outcome)


# --------------------------------------------------------------------------- get_report_chunks

def test_get_report_chunks_round_trip(reports, ext, snapshot):
    vss.add_report_to_vector_store(report_id=str(R1), employee_id=EMP_ID, report_date="2025-03-07",
                                   report_text=LONG_TEXT)
    chunks = vss.get_report_chunks(str(R1))
    snapshot("vector__get_report_chunks", {"chunks": chunks, "rejoined_equals_chunk_text": chunks == vss.chunk_text(LONG_TEXT)})
