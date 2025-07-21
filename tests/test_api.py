import os
from fastapi.testclient import TestClient
from datetime import datetime

# Set up test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from api.main import app
from shared.database import Base, engine, SessionLocal
from shared.models import Job, JobStatus

# Ensure tables exist
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def cleanup_db():
    with engine.connect() as conn:
        conn.execute(Job.__table__.delete())
        conn.commit()


def test_root_and_health():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Judge0 API"

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] in {"healthy", "unhealthy"}


def test_submit_and_retrieve(monkeypatch):
    cleanup_db()

    def fake_execute(job_id, source_code, language, stdin=""):
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = JobStatus.COMPLETED
        job.stdout = "Hello\n"
        job.stderr = ""
        job.exit_code = 0
        job.execution_time = 5
        job.completed_at = datetime.utcnow()
        db.commit()
        db.close()

    monkeypatch.setattr(
        "shared.background_executor.background_executor.execute_code_job", fake_execute
    )

    payload = {"source_code": "print('Hello')", "language": "python3", "stdin": ""}
    resp = client.post("/submissions", json=payload)
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    resp = client.get(f"/submissions/{job_id}")
    assert resp.status_code == 200
    result = resp.json()
    assert result["status"] == "completed"
    assert result["result"]["stdout"] == "Hello\n"
