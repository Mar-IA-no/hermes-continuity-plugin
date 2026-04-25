"""Test the rolling tail of Recent Exchanges: keep last N=4 substantive turns."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path


PLUGIN_SOURCE = Path(__file__).resolve().parent.parent / "plugin" / "__init__.py"


def _load_plugin_with_paths(tmp_path, monkeypatch):
    for k in list(os.environ.keys()):
        if k.startswith("HERMES_") or k.startswith("HMK_") or k == "AGENT_MEMORY_BASE":
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HERMES_HANDOFF_PATH", str(tmp_path / "DIALOGUE-HANDOFF.md"))
    monkeypatch.setenv("HERMES_ALWAYS_CONTEXT_PATH", str(tmp_path / "ALWAYS-CONTEXT.md"))
    monkeypatch.setenv("HERMES_SESSIONS_DIR", str(tmp_path / "sessions"))
    (tmp_path / "sessions").mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location("cp_recent", PLUGIN_SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rolling_tail_caps_at_n(tmp_path, monkeypatch):
    """After 6 substantive turns, only the last 4 should remain in Recent Exchanges."""
    m = _load_plugin_with_paths(tmp_path, monkeypatch)
    assert m._TAIL_EXCHANGES == 4

    for i in range(6):
        m._on_post_llm_call(
            session_id=f"s{i}",
            user_message=f"USER_TURN_{i}_MARKER " * 30,  # >= 300 chars combined
            assistant_response=f"ASST_TURN_{i}_MARKER " * 30,
            conversation_history=[],
            model="test",
            platform="cli",
        )

    content = (tmp_path / "DIALOGUE-HANDOFF.md").read_text()
    tail = content.split("## Recent Exchanges", 1)[1]
    # Turns 2,3,4,5 should be in the tail; turns 0,1 should have rolled out.
    assert "USER_TURN_5_MARKER" in tail
    assert "USER_TURN_4_MARKER" in tail
    assert "USER_TURN_3_MARKER" in tail
    assert "USER_TURN_2_MARKER" in tail
    assert "USER_TURN_1_MARKER" not in tail
    assert "USER_TURN_0_MARKER" not in tail


def test_newest_first_in_tail(tmp_path, monkeypatch):
    """Most recent substantive turn appears first in the tail (newest-first ordering)."""
    m = _load_plugin_with_paths(tmp_path, monkeypatch)

    m._on_post_llm_call(
        session_id="first",
        user_message="FIRST_USER_MARKER " * 30,
        assistant_response="FIRST_ASST " * 30,
        conversation_history=[],
        model="test",
        platform="cli",
    )
    m._on_post_llm_call(
        session_id="second",
        user_message="SECOND_USER_MARKER " * 30,
        assistant_response="SECOND_ASST " * 30,
        conversation_history=[],
        model="test",
        platform="cli",
    )

    content = (tmp_path / "DIALOGUE-HANDOFF.md").read_text()
    tail = content.split("## Recent Exchanges", 1)[1]
    second_idx = tail.find("SECOND_USER_MARKER")
    first_idx = tail.find("FIRST_USER_MARKER")
    assert second_idx >= 0 and first_idx >= 0
    assert second_idx < first_idx, "newest exchange should appear first in the tail"
