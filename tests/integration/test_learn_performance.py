import os
import time
import pytest

from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.learn.events import LearningEvent, Session
from framework_cli.learn.store import LearnStore
from framework_cli.learn.handoff import export_package
from framework_cli.quiz.sync import sync_quiz


@pytest.mark.skipif(not os.environ.get("FRAMEWORK_PERFORMANCE"), reason="performance suite is opt-in")
def test_store_handles_ten_thousand_events(tmp_path):
    config = ProjectConfig.default(tmp_path); config.learn["enabled"] = True; save_config(tmp_path, config)
    store = LearnStore(tmp_path); session = Session("performance", local_date="2026-07-30")
    store.save_session(session)
    for index in range(10_000):
        store.append_event(LearningEvent.create(session, "checkpoint", observations=[f"event-{index}"]))
    assert len(store.events("performance")) == 10_000
    started = time.monotonic(); exported = export_package(tmp_path, session_id="performance")
    assert exported.status == "passed" and time.monotonic() - started < 30
    assert sync_quiz(tmp_path).exit_code == 0
