import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["CUSTORA_DB"] = os.path.join(_tmp, "t.db")
os.environ["CUSTORA_MODEL_DIR"] = os.path.join(_tmp, "models")
os.environ["CUSTORA_DATA_DIR"] = os.path.join(_tmp, "data")

import io  # noqa: E402
import pytest  # noqa: E402
from backend.app import create_app  # noqa: E402
from ml.train import train  # noqa: E402

H = {"X-Client-Id": "test-client-0001"}
OTHER = {"X-Client-Id": "other-client-0002"}
LOYAL = {"recency": 10, "frequency": 14, "aov": 120, "tenure": 30, "sessions": 25, "email_click_rate": 55}
LAPSED = {"recency": 300, "frequency": 1, "aov": 40, "tenure": 30, "sessions": 1, "email_click_rate": 3}


@pytest.fixture(scope="module")
def client():
    train(n=2500, verbose=False)
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_health_and_model(client):
    assert client.get("/api/health").json["status"] == "ok"
    m = client.get("/api/model").json
    assert len(m["features"]) == 9 and m["regressors"] and m["importance"]


def test_prediction_is_sensible(client):
    a = client.post("/api/predict", json={"features": LOYAL, "margin": 35}).json
    b = client.post("/api/predict", json={"features": LAPSED, "margin": 35}).json
    assert a["retention_probability"] > b["retention_probability"]
    assert a["clv_12m"] > b["clv_12m"]
    assert a["segment"] in ("Champion", "Loyal regular") and a["actions"] and a["drivers"]


def test_missing_and_out_of_range_inputs_are_handled(client):
    r = client.post("/api/predict", json={"features": {"aov": 99999, "recency": "abc"}}).json
    assert r["features"]["aov"] == 500 and 1 <= r["features"]["recency"] <= 365


def test_customers_are_private_per_client(client):
    assert client.post("/api/customers", json={"name": "Asha", "features": LOYAL}, headers=H).status_code == 201
    assert len(client.get("/api/customers", headers=H).json) == 1
    assert client.get("/api/customers", headers=OTHER).json == []
    assert client.get("/api/customers").status_code == 400  # header required


def test_batch_upload_save_open_delete(client):
    csv = b"customer_id,recency,frequency,aov,sessions\nA,10,12,100,20\nB,250,1,30,1\nC,60,5,70,8\n"
    r = client.post("/api/predict/batch", data={"file": (io.BytesIO(csv), "x.csv"), "margin": "40"}, headers=H,
                    content_type="multipart/form-data").json
    assert r["summary"]["count"] == 3 and r["batch_id"]
    got = client.get(f"/api/batches/{r['batch_id']}", headers=H).json
    assert len(got["rows"]) == 3
    assert client.get(f"/api/batches/{r['batch_id']}", headers=OTHER).status_code == 404
    assert client.delete(f"/api/batches/{r['batch_id']}", headers=H).status_code == 200
    assert client.get("/api/batches", headers=H).json == []


def test_bad_csv_rejected(client):
    r = client.post("/api/predict/batch", data={"file": (io.BytesIO(b"foo,bar\n1,2\n"), "x.csv")}, headers=H,
                    content_type="multipart/form-data")
    assert r.status_code == 400


def test_planner_plans_export_and_wipe(client):
    p = client.post("/api/planner", json={"customers": 1000, "aov": 80, "orders_per_year": 4, "cac": 60,
                                          "retention": 60, "uplift": 5, "margin": 35}).json
    assert p["ltv_improved"] > p["ltv"] and len(p["series_today"]) == 6
    assert client.post("/api/plans", json={"aov": 80}, headers=H).status_code == 201
    exp = client.get("/api/export", headers=H).json
    assert len(exp["plans"]) == 1 and len(exp["customers"]) == 1
    client.delete("/api/data", headers=H)
    assert client.get("/api/plans", headers=H).json == []
