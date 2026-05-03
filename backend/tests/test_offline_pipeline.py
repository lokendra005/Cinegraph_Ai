from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.pipeline_runner import clear_generated, run_full_pipeline
from app.config import get_settings
from app.database import Base
from app.models import Scene, Story


@pytest.fixture
def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    get_settings.cache_clear()
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_offline_pipeline_completes(db_session, tmp_path: Path):
    story = Story(
        title="Test",
        raw_input="A woman opens a letter and begins crying silently. Rain taps the window.",
        seed=7,
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    run_full_pipeline(db_session, story.id, use_llm=False)

    db_session.refresh(story)
    assert story.status == "completed"
    scenes = db_session.query(Scene).filter(Scene.story_id == story.id).all()
    assert len(scenes) >= 3
    out = get_settings().outputs_dir / story.id
    assert out.exists()
    assert any(out.glob("*.png"))


def test_regenerate_is_deterministic_for_titles(db_session, tmp_path: Path):
    text = "A hacker infiltrates a floating cyberpunk city. Neon reflects on wet metal walkways."
    story = Story(title="Cyber", raw_input=text, seed=99)
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    run_full_pipeline(db_session, story.id, use_llm=False)
    t1 = [s.title for s in db_session.query(Scene).filter(Scene.story_id == story.id).order_by(Scene.scene_number).all()]

    clear_generated(db_session, story.id)
    run_full_pipeline(db_session, story.id, use_llm=False)
    t2 = [s.title for s in db_session.query(Scene).filter(Scene.story_id == story.id).order_by(Scene.scene_number).all()]

    assert t1 == t2
