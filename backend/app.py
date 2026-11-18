"""Flask application: REST API + static frontend.

Run:  python run.py        (development)
      gunicorn "backend.app:create_app()"   (production)
"""
import io
import re

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from ml.config import DATA_DIR, FRONTEND_DIR
from . import db, planner
from .predictor import Predictor

MAX_ROWS = 5000
CID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
TABLES = {"customers": "customers", "batches": "batches", "plans": "plans"}


def create_app():
    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
    db.init_db()
    app.teardown_appcontext(db.close)
    P = Predictor()
    app.config["PREDICTOR"] = P

    class ApiError(Exception):
        def __init__(self, msg, code=400):
            self.msg, self.code = msg, code

    @app.errorhandler(ApiError)
    def _api_err(e):
        return jsonify(error=e.msg), e.code

    @app.errorhandler(404)
    def _404(_e):
        return jsonify(error="Not found"), 404

    @app.errorhandler(413)
    def _413(_e):
        return jsonify(error="File too large (limit 8 MB)"), 413

    @app.errorhandler(Exception)
    def _500(e):
        app.logger.exception(e)
        return jsonify(error="Something went wrong on the server"), 500

    def client_id():
        c = request.headers.get("X-Client-Id", "")
        if not CID_RE.match(c):
            raise ApiError("Missing or invalid X-Client-Id header")
        return c

    def margin_of(v):
        try:
            return min(max(float(v), 1.0), 100.0)
        except (TypeError, ValueError):
            return 35.0

    # ---------- pages & meta ----------
    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", model_version=P.meta["version"], trained_at=P.meta["trained_at"])

    @app.get("/api/model")
    def model_info():
        return jsonify(P.meta)

    @app.get("/api/sample.csv")
    def sample():
        return send_from_directory(DATA_DIR, "customers_sample.csv", mimetype="text/csv")

    # ---------- prediction ----------
    @app.post("/api/predict")
    def predict():
        body = request.get_json(silent=True) or {}
        return jsonify(P.predict_one(body.get("features"), margin_of(body.get("margin"))))

    @app.post("/api/predict/batch")
    def predict_batch():
        cid = client_id()
        f = request.files.get("file")
        if not f:
            raise ApiError("Upload a CSV file in the 'file' field")
        m = margin_of(request.form.get("margin"))
        name = (request.form.get("name") or f.filename or "Uploaded list")[:120]
        try:
            df = pd.read_csv(io.BytesIO(f.read()), encoding="utf-8-sig", on_bad_lines="skip")
        except Exception:
            raise ApiError("Could not read the file as CSV")
        if df.empty:
            raise ApiError("The CSV has no rows")
        mapping, idcol = P.map_columns(df.columns)
        if len(mapping) < 2:
            raise ApiError("Could not find at least two known columns (recency, frequency, aov, sessions, ...)")
        truncated = len(df) > MAX_ROWS
        df = df.head(MAX_ROWS)
        rows = []
        for k, rec in enumerate(df.to_dict("records")):
            feats = P.clean({feat: rec.get(col) for feat, col in mapping.items()})
            cid_val = str(rec[idcol]) if idcol and pd.notna(rec.get(idcol)) else f"C-{k + 1}"
            rows.append((cid_val, feats))
        scored = P.score([f for _, f in rows], m)
        out = [{"id": i, "features": f, **s} for (i, f), s in zip(rows, scored)]
        segs = {}
        for r in out:
            segs[r["segment"]] = segs.get(r["segment"], 0) + 1
        total = sum(r["clv_12m"] for r in out)
        summary = {"count": len(out), "total_clv": round(total, 2), "avg_clv": round(total / len(out), 2),
                   "at_risk_clv": round(sum(r["clv_12m"] for r in out if r["segment"] == "At risk"), 2),
                   "segments": segs}
        saved = None
        if request.form.get("save", "1") != "0":
            saved = db.add_batch(cid, name, out, summary, m, truncated)
        return jsonify(batch_id=saved, name=name, summary=summary, truncated=truncated,
                       columns_used=mapping, rows=out)

    # ---------- saved customers ----------
    @app.post("/api/customers")
    def save_customer():
        cid, body = client_id(), request.get_json(silent=True) or {}
        m = margin_of(body.get("margin"))
        res = P.predict_one(body.get("features"), m)
        name = (str(body.get("name") or "Customer"))[:80]
        i = db.add_customer(cid, name, res["features"], {k: res[k] for k in
                            ("revenue_12m", "clv_12m", "retention_probability", "churn_risk", "segment")}, m)
        return jsonify(id=i, name=name), 201

    @app.get("/api/customers")
    def customers():
        return jsonify(db.list_customers(client_id()))

    # ---------- batches ----------
    @app.get("/api/batches")
    def batches():
        return jsonify(db.list_batches(client_id()))

    @app.get("/api/batches/<bid>")
    def batch(bid):
        b = db.get_batch(client_id(), bid)
        if not b:
            raise ApiError("Not found", 404)
        return jsonify(b)

    # ---------- planner & plans ----------
    @app.post("/api/planner")
    def planner_calc():
        return jsonify(planner.calc(request.get_json(silent=True) or {}))

    @app.post("/api/plans")
    def save_plan():
        cid = client_id()
        res = planner.calc(request.get_json(silent=True) or {})
        i = db.add_plan(cid, res["inputs"], {k: res[k] for k in ("ltv", "ratio", "verdict", "gain_total", "payback_months")})
        return jsonify(id=i), 201

    @app.get("/api/plans")
    def plans():
        return jsonify(db.list_plans(client_id()))

    # ---------- delete & export ----------
    @app.delete("/api/<kind>/<item_id>")
    def delete_item(kind, item_id):
        if kind not in TABLES:
            raise ApiError("Not found", 404)
        if not db.delete(client_id(), TABLES[kind], item_id):
            raise ApiError("Not found", 404)
        return jsonify(deleted=item_id)

    @app.get("/api/export")
    def export():
        cid = client_id()
        return jsonify(customers=db.list_customers(cid), plans=db.list_plans(cid),
                       batches=[db.get_batch(cid, b["id"]) for b in db.list_batches(cid)])

    @app.delete("/api/data")
    def wipe():
        db.wipe(client_id())
        return jsonify(deleted="all")

    return app
