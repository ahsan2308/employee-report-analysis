"""Fakes for the external services the pipelines talk to.

Each fake records every call into a shared ``Recorder`` so a test can snapshot
exactly what the code under test sent to the outside world. Only external
boundaries are faked:

* ``FakeOllamaClient``      replaces ``ollama.Client`` (the HTTP client used by
                            ``OllamaProvider``), so the real provider -- including
                            its error handling -- stays under test.
* ``FakeEmbeddingProvider`` replaces the object returned by
                            ``embedding_service.get_embedding_provider``.
* ``FakeVectorStore``       replaces the Qdrant provider returned by
                            ``vector_store_service.get_vector_store``; it mimics
                            the real provider's contract (e.g. ``get_collection_info``
                            returns ``{}`` for a missing collection).
* ``FakeSQLServerConnector`` replaces ``create_sqlserver_connector()`` in the sync service.
"""
import copy
import hashlib
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional


def _describe(value: Any) -> Any:
    """Make a recorded argument JSON friendly while keeping business datetimes visible.

    ``repr`` is used for datetimes so ``tests.support.scrub`` does not blank them:
    these are source-data timestamps (e.g. the incremental-sync cutoff), not wall-clock noise.
    """
    if isinstance(value, datetime):
        return repr(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _describe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        items = sorted(value) if isinstance(value, set) else value
        return [_describe(v) for v in items]
    if isinstance(value, float):
        return round(value, 6)
    return value


def schema_digest(schema: Any) -> Any:
    """Short, stable fingerprint of a JSON schema passed to the LLM (full schema is large)."""
    if not isinstance(schema, dict):
        return schema
    text = json.dumps(schema, sort_keys=True, default=str)
    return {"title": schema.get("title"), "sha256": hashlib.sha256(text.encode()).hexdigest()[:16]}


class Recorder:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []

    def record(self, name: str, **data) -> None:
        self.calls.append({"call": name, **_describe(data)})

    def of(self, *names: str) -> List[Dict[str, Any]]:
        return [c for c in self.calls if c["call"] in names]


# --------------------------------------------------------------------------- LLM

class FakeOllamaClient:
    """Stand-in for ``ollama.Client``. Responses are consumed in order.

    A response may be a string (returned as ``{"response": text}``), ``None``
    (returned as ``{}``), or an Exception instance (raised, like a network error).
    When the queue is empty an empty string is returned.
    """

    def __init__(self, recorder: Recorder):
        self.recorder = recorder
        self.responses: List[Any] = []
        self.prompts: List[str] = []

    def queue(self, *responses: Any) -> None:
        self.responses.extend(responses)

    def __call__(self, host: Optional[str] = None, **kwargs):  # acts as the Client constructor
        self.recorder.record("llm.client", host=host)
        return self

    def generate(self, model=None, prompt=None, format=None, options=None, **kwargs):
        self.prompts.append(prompt)
        self.recorder.record(
            "llm.generate",
            model=model,
            prompt_index=len(self.prompts) - 1,
            prompt_chars=len(prompt or ""),
            format=schema_digest(format),
            options=options,
            extra=sorted(kwargs),
        )
        response = self.responses.pop(0) if self.responses else ""
        if isinstance(response, BaseException):
            raise response
        if response is None:
            return {}
        return {"response": response}


# --------------------------------------------------------------------------- embeddings

def fake_vector(text: str, dim: int) -> List[float]:
    digest = hashlib.sha256(str(text).encode("utf-8")).digest()
    return [round(digest[i] / 255.0, 4) for i in range(dim)]


class FakeEmbeddingProvider:
    model = "fake-embedding-model"

    def __init__(self, recorder: Recorder, dim: int = 4):
        self.recorder = recorder
        self.dim = dim
        self.fail = False  # True -> behave like the real provider after a swallowed error

    def get_embedding(self, text, is_query: bool = False):
        self.recorder.record("embed", input=text, is_query=is_query)
        if isinstance(text, list):
            if self.fail:
                return [[]]
            return [fake_vector(t, self.dim) for t in text]
        if self.fail:
            return []
        return fake_vector(text, self.dim)


# --------------------------------------------------------------------------- vector store

class FakeVectorStore:
    def __init__(self, recorder: Recorder, collections: Optional[Dict[str, int]] = None):
        self.recorder = recorder
        self.collections: Dict[str, int] = dict(collections or {})
        self.points: Dict[str, Dict[str, Any]] = {}
        self.search_hits: List[Dict[str, Any]] = []
        self.batch_failures = 0  # number of add_documents_batch calls that return False
        self.document_order: List[str] = []  # document ids in upsert order

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def _remember(self, document_id, vector, payload):
        if document_id not in self.document_order:
            self.document_order.append(document_id)
        self.points[document_id] = {"vector": vector, "payload": payload}

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        self.recorder.record("vs.get_collection_info", collection_name=collection_name)
        if collection_name not in self.collections:
            return {}  # real QdrantProvider swallows the error and returns {}
        return {"name": collection_name, "dimension": self.collections[collection_name],
                "points_count": len(self.points), "vectors_count": len(self.points)}

    def delete_collection(self, collection_name: str) -> bool:
        self.recorder.record("vs.delete_collection", collection_name=collection_name,
                             existed=collection_name in self.collections, points_lost=len(self.points))
        if collection_name in self.collections:
            del self.collections[collection_name]
            self.points.clear()
        return True

    def setup_collection(self, collection_name: str, vector_size: int) -> bool:
        self.recorder.record("vs.setup_collection", collection_name=collection_name, vector_size=vector_size)
        self.collections.setdefault(collection_name, vector_size)
        return True

    def add_documents_batch(self, collection_name: str, points: List[Dict[str, Any]]) -> bool:
        self.recorder.record("vs.add_documents_batch", collection_name=collection_name,
                             points=copy.deepcopy(points))
        if self.batch_failures > 0:
            self.batch_failures -= 1
            return False
        for point in points:
            self._remember(point["document_id"], point["vector"], point["payload"])
        return True

    def add_document(self, collection_name: str, document_id: str, vector, payload) -> bool:
        self.recorder.record("vs.add_document", collection_name=collection_name, document_id=document_id,
                             vector=vector, payload=copy.deepcopy(payload))
        self._remember(document_id, vector, payload)
        return True

    def search(self, **kwargs) -> List[Dict[str, Any]]:
        self.recorder.record("vs.search", **kwargs)
        return copy.deepcopy(self.search_hits)

    def retrieve_document(self, collection_name: str, document_id: str):
        self.recorder.record("vs.retrieve_document", collection_name=collection_name, document_id=document_id)
        point = self.points.get(document_id)
        if not point:
            return None
        return {**point["payload"], "id": document_id}


# --------------------------------------------------------------------------- SQL Server

class SQLServerDown(Exception):
    """Raised by the fake connector to simulate an unreachable SQL Server."""


DEFAULT_TABLES = ("EmployeeReports", "VisionEmployeeData", "EmployeeJobDescriptions", "SupervisorFeedback")
DEFAULT_TIMESTAMP_COLUMNS = {"LastModifiedDate", "ModifiedDate", "UpdatedAt"}


class FakeSQLServerConnector:
    """Serves fixed rows per table. ``rows[table]`` is a list of dicts; ``schemas[table]`` a column->type dict."""

    def __init__(self, recorder: Recorder, schemas: Dict[str, Dict[str, str]], rows: Dict[str, List[Dict]],
                 fetch_batch_size: int = 1000):
        self.recorder = recorder
        self.schemas = schemas
        self.rows = rows
        self.fetch_batch_size = fetch_batch_size
        self.fail_tables: Dict[str, str] = {}  # table -> "schema" | "fetch"

    def get_allowed_tables(self):
        return set(DEFAULT_TABLES)

    def get_allowed_timestamp_columns(self):
        return set(DEFAULT_TIMESTAMP_COLUMNS)

    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        self.recorder.record("sql.get_table_schema", table_name=table_name)
        if self.fail_tables.get(table_name) == "schema":
            raise SQLServerDown(f"Failed to get schema for table '{table_name}': connection refused")
        return dict(self.schemas.get(table_name, {}))

    def _batches(self, table_name: str, rows: List[Dict]):
        if self.fail_tables.get(table_name) == "fetch":
            raise SQLServerDown(f"Failed to fetch records from '{table_name}': connection reset")
        for i in range(0, len(rows), self.fetch_batch_size):
            yield [dict(r) for r in rows[i:i + self.fetch_batch_size]]

    def get_all_records(self, table_name: str, batch_size: int = 1000, order_by: Optional[str] = None):
        self.recorder.record("sql.get_all_records", table_name=table_name, batch_size=batch_size, order_by=order_by)
        return self._batches(table_name, list(self.rows.get(table_name, [])))

    def get_records_since(self, table_name: str, timestamp_column: str, since_timestamp, batch_size: int = 1000,
                          order_by: Optional[str] = None):
        self.recorder.record("sql.get_records_since", table_name=table_name, timestamp_column=timestamp_column,
                             since_timestamp=since_timestamp, batch_size=batch_size, order_by=order_by)
        rows = [r for r in self.rows.get(table_name, []) if r.get(timestamp_column) and r[timestamp_column] >= since_timestamp]
        return self._batches(table_name, rows)
