"""Shared read-only Neo4j helper for the R5 pass."""
from __future__ import annotations
import json, sys
from typing import Any
from neo4j import GraphDatabase, Query

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"
T = 300.0

def driver():
    return GraphDatabase.driver(URI, auth=AUTH)

def one(session, cypher: str, **params: Any):
    rec = session.run(Query(cypher, timeout=T), **params).single()
    return None if rec is None else rec[0]

def rows(session, cypher: str, **params: Any):
    return [r.data() for r in session.run(Query(cypher, timeout=T), **params)]

def run(fn):
    d = driver()
    try:
        with d.session(database=DB) as s:
            out = fn(s)
    finally:
        d.close()
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return out
