import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import decrypt_json, encrypt_json
from app.database import Base, get_db
from app.main import app
from app.services.calc_engine import apply_rounding, calculate_activity_points


@pytest.fixture()
def client():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = create_engine(f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()
    Path(tmp.name).unlink(missing_ok=True)


def test_rounding_rules():
    assert apply_rounding(8.34, "decimal_1") == 8.3
    assert apply_rounding(8.36, "decimal_1") == 8.4
    assert apply_rounding(8.24, "half_point") == 8.0
    assert apply_rounding(8.26, "half_point") == 8.5
    assert apply_rounding(8.74, "half_point") == 8.5
    assert apply_rounding(8.76, "half_point") == 9.0
    assert apply_rounding(8.6, "integer") == 9.0


def test_proportional_activity_points():
    assert calculate_activity_points(80.0, 100.0, 5.0) == 4.0
    assert calculate_activity_points(7.5, 10.0, 2.0) == 1.5
    assert calculate_activity_points(None, 100.0, 5.0) == 0.0
    assert calculate_activity_points(50.0, 0.0, 5.0) == 0.0


def test_fernet_encryption_roundtrip():
    payload = {"username": "prof.sauer", "cookies": [{"name": "sid", "value": "abc123"}]}
    token = encrypt_json(payload)
    assert b"prof.sauer" not in token
    assert decrypt_json(token) == payload


def test_health_and_demo_seed_all_reports_and_exports(client: TestClient):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    seed_res = client.post("/api/sync/demo-seed")
    assert seed_res.status_code == 200
    assert seed_res.json()["courses_count"] == 2

    courses_res = client.get("/api/courses")
    assert courses_res.status_code == 200
    courses = courses_res.json()
    assert len(courses) == 2
    course_id = courses[0]["id"]

    gb_res = client.get(f"/api/courses/{course_id}/gradebook")
    assert gb_res.status_code == 200
    gb = gb_res.json()
    assert len(gb["themes"]) > 0
    assert len(gb["activities"]) > 0
    assert len(gb["students"]) > 0

    # Valida atualização de regras (RF08)
    first_act = gb["activities"][0]
    rules_res = client.put(
        f"/api/courses/{course_id}/rules",
        json={
            "min_passing_grade": 65.0,
            "use_draft_grades": True,
            "themes": [],
            "activities": [
                {
                    "id": first_act["id"],
                    "theme_id": first_act["theme_id"],
                    "custom_points_weight": 5.0,
                    "include_in_calc": True,
                }
            ],
        },
    )
    assert rules_res.status_code == 200
    assert rules_res.json()["course"]["min_passing_grade"] == 65.0

    # Valida todos os 18 relatórios (R01 a R18)
    for num in range(1, 19):
        code = f"R{num:02d}"
        rep_res = client.get(f"/api/reports/{code}?course_map_id={course_id}")
        assert rep_res.status_code == 200, f"Falha no relatório {code}: {rep_res.text}"
        data = rep_res.json()
        assert data["code"] == code
        assert len(data["columns"]) > 0

    # Valida exportações reais CSV, XLSX e PDF
    for fmt, expected_ct in [
        ("csv", "text/csv"),
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("pdf", "application/pdf"),
    ]:
        exp_res = client.get(f"/api/reports/R01/export?format={fmt}&course_map_id={course_id}")
        assert exp_res.status_code == 200
        assert expected_ct in exp_res.headers["content-type"]
        assert len(exp_res.content) > 50

