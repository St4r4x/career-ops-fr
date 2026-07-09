from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-32-chars-minimum-ok!")
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

import scan_state

USER_A = "user-a-test"
USER_B = "user-b-test"


def _reset() -> None:
    scan_state._status.clear()
    scan_state._result.clear()


def test_get_scan_state_defaults_to_idle() -> None:
    _reset()
    state = scan_state.get_scan_state(USER_A)
    assert state["status"] == "idle"
    assert state["result"]["inserted"] == 0


def test_start_scan_sets_running(monkeypatch) -> None:
    _reset()
    monkeypatch.setattr(asyncio, "create_task", lambda coro: coro.close())
    scan_state.start_scan(USER_A)
    assert scan_state.get_scan_state(USER_A)["status"] == "running"


def test_start_scan_already_running_does_not_spawn_second_task(monkeypatch) -> None:
    _reset()
    created = []
    monkeypatch.setattr(
        asyncio,
        "create_task",
        lambda coro: created.append(coro) or coro.close(),
    )
    scan_state.start_scan(USER_A)
    scan_state.start_scan(USER_A)
    assert len(created) == 1


def test_scan_state_isolated_per_user(monkeypatch) -> None:
    _reset()
    monkeypatch.setattr(asyncio, "create_task", lambda coro: coro.close())
    scan_state.start_scan(USER_A)
    assert scan_state.get_scan_state(USER_A)["status"] == "running"
    assert scan_state.get_scan_state(USER_B)["status"] == "idle"


def test_run_scan_success_updates_result(monkeypatch) -> None:
    _reset()

    async def fake_run_pipeline(_settings, *, skip_descriptions=False, user_id=None):
        return [1, 2, 3]

    def fake_import_offers(_offers, user_id):
        return (2, 1)

    def fake_expire_stale(user_id=None):
        return 0

    def fake_load_settings(user_id=None):
        return {}

    monkeypatch.setattr("scripts.import_offers._run_pipeline", fake_run_pipeline)
    monkeypatch.setattr("scripts.import_offers.import_offers", fake_import_offers)
    monkeypatch.setattr("scripts.import_offers.expire_stale_offers", fake_expire_stale)
    monkeypatch.setattr("scripts.pre_filter.load_settings", fake_load_settings)

    asyncio.run(scan_state._run_scan(USER_A))

    state = scan_state.get_scan_state(USER_A)
    assert state["status"] == "done"
    assert state["result"]["inserted"] == 2
    assert state["result"]["skipped"] == 1
    assert state["result"]["found"] == 3
    assert state["result"]["scored"] == 3


def test_run_scan_exception_sets_error_status(monkeypatch) -> None:
    _reset()

    async def fake_run_pipeline(_settings, *, skip_descriptions=False, user_id=None):
        raise RuntimeError("Connection refused")

    def fake_load_settings(user_id=None):
        return {}

    monkeypatch.setattr("scripts.import_offers._run_pipeline", fake_run_pipeline)
    monkeypatch.setattr("scripts.pre_filter.load_settings", fake_load_settings)

    asyncio.run(scan_state._run_scan(USER_A))

    state = scan_state.get_scan_state(USER_A)
    assert state["status"] == "error"
    assert "Connection refused" in state["result"]["error"]
