from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, CaseModel
from app.main import app
from app.api import cases
from app.services.documents import ParsedDocument, TextSpan


def make_client(tmp_path, monkeypatch, parser=None):
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=__import__("sqlalchemy").pool.StaticPool)
    Base.metadata.create_all(engine)
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[cases.get_session] = session
    monkeypatch.setattr(cases, "UPLOAD_DIR", tmp_path)
    if parser:
        app.dependency_overrides[cases.get_parser] = lambda: parser
    return TestClient(app), engine


def test_create_case_persists_kind_and_goal(tmp_path, monkeypatch):
    client, engine = make_client(tmp_path, monkeypatch)
    try:
        response = client.post("/cases", json={"kind": "contract_review", "goal": "检查合同"})
        assert response.status_code == 201
        with Session(engine) as db:
            assert db.get(CaseModel, response.json()["id"]).goal == "检查合同"
    finally:
        app.dependency_overrides.clear()


class StubParser:
    def parse(self, path):
        return ParsedDocument(text="签订日期 2026-09-13", page_count=1,
                              spans=[TextSpan(text="2026-09-13", page=1, confidence=.7, critical_kind="date")])


def test_upload_returns_spans_and_deletes_temp_file(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path, monkeypatch, StubParser())
    try:
        case_id = client.post("/cases", json={"kind": "contract_review", "goal": "检查合同"}).json()["id"]
        response = client.post(f"/cases/{case_id}/documents", files={"file": ("scan.pdf", b"%PDF", "application/pdf")})
        assert response.status_code == 200
        assert response.json()["spans"][0]["confidence"] == .7
        assert list(tmp_path.glob("upload-*")) == []
    finally:
        app.dependency_overrides.clear()


def test_failed_parse_keeps_case_and_cleans_temp(tmp_path, monkeypatch):
    class FailingParser:
        def parse(self, path):
            raise RuntimeError("OCR unavailable")
    client, engine = make_client(tmp_path, monkeypatch, FailingParser())
    try:
        case_id = client.post("/cases", json={"kind": "contract_review", "goal": "检查合同"}).json()["id"]
        response = client.post(f"/cases/{case_id}/documents", files={"file": ("scan.pdf", b"%PDF", "application/pdf")})
        assert response.status_code == 503
        with Session(engine) as db:
            assert db.get(CaseModel, case_id).status == "parse_failed"
        assert list(tmp_path.glob("upload-*")) == []
    finally:
        app.dependency_overrides.clear()


def test_invalid_type_is_rejected_before_storage(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path, monkeypatch, StubParser())
    try:
        case_id = client.post("/cases", json={"kind": "contract_review", "goal": "检查合同"}).json()["id"]
        response = client.post(f"/cases/{case_id}/documents", files={"file": ("evil.txt", b"hello", "text/plain")})
        assert response.status_code == 415
        assert list(tmp_path.glob("upload-*")) == []
    finally:
        app.dependency_overrides.clear()
