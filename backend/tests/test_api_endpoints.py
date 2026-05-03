from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api_test.db'}")

    from app.config import get_settings

    get_settings.cache_clear()

    import app.database as db_module
    from app.database import Base, get_db
    from app.models import CompilationJob, Story
    from main import app

    engine = create_engine(
        f"sqlite:///{tmp_path / 'api_test_runtime.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        client.testing_session_factory = TestingSessionLocal  # type: ignore[attr-defined]
        yield client
    app.dependency_overrides.clear()


def test_health(api_client: TestClient):
    res = api_client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
    assert "x-request-id" in res.headers
    assert "x-response-time-ms" in res.headers


def test_request_id_passthrough(api_client: TestClient):
    request_id = "test-request-id-123"
    res = api_client.get("/health", headers={"x-request-id": request_id})
    assert res.status_code == 200
    assert res.headers.get("x-request-id") == request_id


def test_story_end_to_end_all_primary_endpoints(api_client: TestClient):
    payload = {
        "title": "API End-to-End",
        "input": "A woman opens a letter and begins crying silently. Rain falls outside and she stares at a turned-down wedding photo.",
        "seed": 42,
        "input_type": "text",
        "use_llm": False,
    }
    create_res = api_client.post("/api/v1/stories", json=payload)
    assert create_res.status_code == 202
    story_id = create_res.json()["story_id"]
    job_id = create_res.json()["job_id"]

    job_res = api_client.get(f"/api/v1/jobs/{job_id}")
    assert job_res.status_code == 200
    assert job_res.json()["status"] == "completed"

    story_res = api_client.get(f"/api/v1/stories/{story_id}")
    assert story_res.status_code == 200
    story = story_res.json()
    assert story["status"] == "completed"
    assert story["parsed"] is not None

    scenes_res = api_client.get(f"/api/v1/stories/{story_id}/scenes")
    assert scenes_res.status_code == 200
    scenes = scenes_res.json()
    assert len(scenes) >= 3
    assert "metadata" in scenes[0]

    storyboard_res = api_client.get(f"/api/v1/stories/{story_id}/storyboard")
    assert storyboard_res.status_code == 200
    storyboard = storyboard_res.json()
    assert storyboard["story_id"] == story_id
    assert storyboard["scenes"]
    first_url = storyboard["scenes"][0]["frames"][0]["url"]
    assert first_url.startswith("/outputs/")

    video_gen = api_client.post(f"/api/v1/stories/{story_id}/video")
    assert video_gen.status_code == 200
    video_data = video_gen.json()
    assert video_data["video_url"].startswith("/outputs/")
    assert video_data["frames_written"] > 0

    video_state = api_client.get(f"/api/v1/stories/{story_id}/video")
    assert video_state.status_code == 200
    vs = video_state.json()
    assert vs["ready"] is True
    assert vs.get("video_kind") == "cinematic_scene_film"

    scene_id = scenes[0]["id"]
    clip_gen = api_client.post(f"/api/v1/stories/{story_id}/scenes/{scene_id}/video")
    assert clip_gen.status_code == 200
    clip_data = clip_gen.json()
    assert clip_data["video_url"].startswith("/outputs/")
    assert clip_data["frames_written"] > 0
    clip_state = api_client.get(f"/api/v1/stories/{story_id}/scenes/{scene_id}/video")
    assert clip_state.status_code == 200
    assert clip_state.json()["ready"] is True

    trace_res = api_client.get(f"/api/v1/stories/{story_id}/trace")
    assert trace_res.status_code == 200
    trace = trace_res.json()
    agent_names = [a["agent_name"] for a in trace["agents"]]
    for expected in (
        "narrative_parser",
        "scene_planner",
        "scriptwriter",
        "director",
        "continuity",
        "ambiguity",
        "evaluator",
        "storyboard_generation",
    ):
        assert expected in agent_names

    eval_res = api_client.get(f"/api/v1/stories/{story_id}/evaluation")
    assert eval_res.status_code == 200
    evaluation = eval_res.json()
    assert "overall_score" in evaluation
    assert "metrics" in evaluation
    assert 0 <= evaluation["overall_score"] <= 1

    graph_res = api_client.get(f"/api/v1/stories/{story_id}/narrative-graph")
    assert graph_res.status_code == 200
    graph = graph_res.json()
    assert graph["nodes"]
    assert graph["edges"] is not None

    jobs_res = api_client.get(f"/api/v1/stories/{story_id}/jobs")
    assert jobs_res.status_code == 200
    jobs = jobs_res.json()
    assert isinstance(jobs, list)
    assert any(j["id"] == job_id for j in jobs)


def test_regenerate_rebuilds_story_outputs(api_client: TestClient):
    payload = {
        "title": "Regenerate Test",
        "input": "A hacker infiltrates a floating cyberpunk city, dodges security, and escapes with a key.",
        "seed": 1,
        "input_type": "text",
        "use_llm": False,
    }
    create_res = api_client.post("/api/v1/stories", json=payload)
    story_id = create_res.json()["story_id"]

    before_storyboard = api_client.get(f"/api/v1/stories/{story_id}/storyboard").json()
    before_url = before_storyboard["scenes"][0]["frames"][0]["url"]

    regen_res = api_client.post(
        f"/api/v1/stories/{story_id}/regenerate",
        json={"seed": 999, "use_llm": False},
    )
    assert regen_res.status_code == 202
    regen_job_id = regen_res.json()["job_id"]
    regen_job = api_client.get(f"/api/v1/jobs/{regen_job_id}")
    assert regen_job.status_code == 200
    assert regen_job.json()["status"] == "completed"

    after_story = api_client.get(f"/api/v1/stories/{story_id}").json()
    assert after_story["status"] == "completed"
    assert after_story["seed"] == 999

    after_storyboard = api_client.get(f"/api/v1/stories/{story_id}/storyboard").json()
    after_url = after_storyboard["scenes"][0]["frames"][0]["url"]
    assert before_url == after_url  # file names are stable for deterministic overwrite

    trace = api_client.get(f"/api/v1/stories/{story_id}/trace").json()
    assert len(trace["agents"]) >= 7


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/stories/not-found",
        "/api/v1/stories/not-found/scenes",
        "/api/v1/stories/not-found/storyboard",
        "/api/v1/stories/not-found/video",
        "/api/v1/stories/not-found/scenes/not-a-scene/video",
        "/api/v1/stories/not-found/trace",
        "/api/v1/stories/not-found/evaluation",
        "/api/v1/stories/not-found/narrative-graph",
        "/api/v1/stories/not-found/jobs",
    ],
)
def test_not_found_paths(path: str, api_client: TestClient):
    res = api_client.get(path)
    assert res.status_code == 404
    assert res.json()["detail"] == "Story not found"


def test_regenerate_not_found(api_client: TestClient):
    res = api_client.post("/api/v1/stories/not-found/regenerate", json={"seed": 42, "use_llm": False})
    assert res.status_code == 404
    assert res.json()["detail"] == "Story not found"


def test_job_not_found(api_client: TestClient):
    res = api_client.get("/api/v1/jobs/not-found")
    assert res.status_code == 404
    assert res.json()["detail"] == "Job not found"


def test_cancel_completed_job_conflict(api_client: TestClient):
    payload = {
        "title": "Cancel conflict",
        "input": "A short but valid narrative about conflict and resolution over many moments.",
        "seed": 11,
        "input_type": "text",
        "use_llm": False,
    }
    created = api_client.post("/api/v1/stories", json=payload).json()
    job_id = created["job_id"]
    res = api_client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert res.status_code == 409


def test_cancel_queued_job(api_client: TestClient):
    from app.models import CompilationJob, Story

    SessionLocal = api_client.testing_session_factory  # type: ignore[attr-defined]
    db = SessionLocal()
    try:
        s = Story(title="Queued", raw_input="A valid narrative string for queued cancellation.", status="processing", seed=77)
        db.add(s)
        db.commit()
        db.refresh(s)
        j = CompilationJob(story_id=s.id, status="queued", attempts=0, max_attempts=2, use_llm=False)
        db.add(j)
        db.commit()
        db.refresh(j)
        job_id = j.id
    finally:
        db.close()

    res = api_client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"

    job_res = api_client.get(f"/api/v1/jobs/{job_id}")
    assert job_res.status_code == 200
    assert job_res.json()["status"] == "cancelled"


def test_job_retries_then_succeeds(api_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.api import routes as routes_module
    from app.models import CompilationJob, Story

    SessionLocal = api_client.testing_session_factory  # type: ignore[attr-defined]
    db = SessionLocal()
    try:
        s = Story(title="Retry", raw_input="A valid narrative string for retry test.", status="processing", seed=31)
        db.add(s)
        db.commit()
        db.refresh(s)
        j = CompilationJob(story_id=s.id, status="queued", attempts=0, max_attempts=2, use_llm=False)
        db.add(j)
        db.commit()
        db.refresh(j)
        job_id = j.id
    finally:
        db.close()

    real_run = routes_module.run_full_pipeline
    state = {"calls": 0}

    def flaky_run(db_session, story_id: str, use_llm: bool | None = None):
        state["calls"] += 1
        if state["calls"] == 1:
            raise RuntimeError("transient failure")
        return real_run(db_session, story_id, use_llm=use_llm)

    monkeypatch.setattr(routes_module, "run_full_pipeline", flaky_run)
    routes_module._run_compilation_job(job_id)

    job_res = api_client.get(f"/api/v1/jobs/{job_id}")
    assert job_res.status_code == 200
    body = job_res.json()
    assert body["status"] == "completed"
    assert body["attempts"] == 2


def test_create_story_validation(api_client: TestClient):
    bad_res = api_client.post(
        "/api/v1/stories",
        json={"title": "", "input": "short", "seed": -1, "input_type": "invalid", "use_llm": False},
    )
    assert bad_res.status_code == 422


def test_generate_video_without_scenes(api_client: TestClient):
    from app.models import Story

    SessionLocal = api_client.testing_session_factory  # type: ignore[attr-defined]
    db = SessionLocal()
    try:
        s = Story(
            title="No Scenes",
            raw_input="A valid narrative string but pipeline not executed yet.",
            status="processing",
            seed=55,
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        story_id = s.id
    finally:
        db.close()

    res = api_client.post(f"/api/v1/stories/{story_id}/video")
    assert res.status_code == 400
