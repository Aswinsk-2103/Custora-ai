"""SQLite storage. Every row belongs to a client_id (a random id the browser keeps)."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone

from flask import g

from ml.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers(
  id TEXT PRIMARY KEY, client_id TEXT NOT NULL, name TEXT, features TEXT, result TEXT,
  margin REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS batches(
  id TEXT PRIMARY KEY, client_id TEXT NOT NULL, name TEXT, count INTEGER, total_clv REAL,
  avg_clv REAL, segments TEXT, margin REAL, truncated INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS batch_rows(
  batch_id TEXT NOT NULL REFERENCES batches(id) ON DELETE CASCADE, idx INTEGER, customer_id TEXT,
  features TEXT, clv REAL, retention REAL, segment TEXT, risk TEXT);
CREATE TABLE IF NOT EXISTS plans(
  id TEXT PRIMARY KEY, client_id TEXT NOT NULL, inputs TEXT, result TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS ix_c ON customers(client_id, created_at);
CREATE INDEX IF NOT EXISTS ix_b ON batches(client_id, created_at);
CREATE INDEX IF NOT EXISTS ix_r ON batch_rows(batch_id, idx);
CREATE INDEX IF NOT EXISTS ix_p ON plans(client_id, created_at);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id():
    return uuid.uuid4().hex[:12]


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    con.commit()
    con.close()


def conn():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _j(row, *keys):
    d = dict(row)
    for k in keys:
        d[k] = json.loads(d[k]) if d.get(k) else None
    d.pop("client_id", None)
    return d


# ---- customers ----
def add_customer(cid, name, features, result, margin):
    i = new_id()
    conn().execute("INSERT INTO customers VALUES(?,?,?,?,?,?,?)",
                   (i, cid, name, json.dumps(features), json.dumps(result), margin, now()))
    conn().commit()
    return i


def list_customers(cid, limit=200):
    rows = conn().execute("SELECT * FROM customers WHERE client_id=? ORDER BY created_at DESC, rowid DESC LIMIT ?",
                          (cid, limit)).fetchall()
    return [_j(r, "features", "result") for r in rows]


# ---- batches ----
def add_batch(cid, name, rows, summary, margin, truncated):
    i = new_id()
    db = conn()
    db.execute("INSERT INTO batches VALUES(?,?,?,?,?,?,?,?,?,?)",
               (i, cid, name, summary["count"], summary["total_clv"], summary["avg_clv"],
                json.dumps(summary["segments"]), margin, int(truncated), now()))
    db.executemany("INSERT INTO batch_rows VALUES(?,?,?,?,?,?,?,?)",
                   [(i, k, r["id"], json.dumps(r["features"]), r["clv_12m"], r["retention_probability"],
                     r["segment"], r["churn_risk"]) for k, r in enumerate(rows)])
    db.commit()
    return i


def list_batches(cid):
    rows = conn().execute("SELECT * FROM batches WHERE client_id=? ORDER BY created_at DESC, rowid DESC", (cid,)).fetchall()
    return [_j(r, "segments") for r in rows]


def get_batch(cid, bid, with_rows=True):
    r = conn().execute("SELECT * FROM batches WHERE id=? AND client_id=?", (bid, cid)).fetchone()
    if not r:
        return None
    b = _j(r, "segments")
    if with_rows:
        rs = conn().execute("SELECT * FROM batch_rows WHERE batch_id=? ORDER BY idx", (bid,)).fetchall()
        b["rows"] = [{"id": x["customer_id"], "features": json.loads(x["features"]), "clv_12m": x["clv"],
                      "retention_probability": x["retention"], "segment": x["segment"], "churn_risk": x["risk"]}
                     for x in rs]
    return b


# ---- plans ----
def add_plan(cid, inputs, result):
    i = new_id()
    conn().execute("INSERT INTO plans VALUES(?,?,?,?,?)", (i, cid, json.dumps(inputs), json.dumps(result), now()))
    conn().commit()
    return i


def list_plans(cid):
    rows = conn().execute("SELECT * FROM plans WHERE client_id=? ORDER BY created_at DESC, rowid DESC", (cid,)).fetchall()
    return [_j(r, "inputs", "result") for r in rows]


def delete(cid, table, item_id):
    cur = conn().execute(f"DELETE FROM {table} WHERE id=? AND client_id=?", (item_id, cid))
    conn().commit()
    return cur.rowcount > 0


def wipe(cid):
    db = conn()
    for t in ("customers", "batches", "plans"):
        db.execute(f"DELETE FROM {t} WHERE client_id=?", (cid,))
    db.commit()
