"""Test the substantive-turn gate: trivial turns don't overwrite Recent Exchanges."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest


PLUGIN_SOURCE = Path(__file__).resolve().parent.parent / "plugin" / "__init__.py"


def _load_plugin_with_paths(tmp_path, monkeypatch):
    """Load the plugin fresh against env pointing into tmp_path."""
    for k in list(os.environ.keys()):
        if k.startswith("HERMES_") or k.startswith("HMK_") or k == "AGENT_MEMORY_BASE":
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HERMES_HANDOFF_PATH", str(tmp_path / "DIALOGUE-HANDOFF.md"))
    monkeypatch.setenv("HERMES_ALWAYS_CONTEXT_PATH", str(tmp_path / "ALWAYS-CONTEXT.md"))
    monkeypatch.setenv("HERMES_SESSIONS_DIR", str(tmp_path / "sessions"))
    (tmp_path / "sessions").mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location("cp_substantive", PLUGIN_SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_substantive_turn_writes_recent_exchanges(tmp_path, monkeypatch):
    """A turn with combined chars >= 300 should append to ## Recent Exchanges."""
    m = _load_plugin_with_paths(tmp_path, monkeypatch)
    user_msg = "What is the capital of France? " * 10  # ~300 chars
    asst_resp = "The capital of France is Paris. " * 10  # ~320 chars
    m._on_post_llm_call(
        session_id="test-1",
        user_message=user_msg,
        assistant_response=asst_resp,
        conversation_history=[],
        model="test",
        platform="cli",
    )
    content = (tmp_path / "DIALOGUE-HANDOFF.md").read_text()
    assert "## Recent Exchanges" in content
    assert "Paris" in content
    assert "capital of France" in content


def test_trivial_turn_does_not_overwrite_recent_exchanges(tmp_path, monkeypatch):
    """A turn with <300 chars combined should leave ## Recent Exchanges intact."""
    m = _load_plugin_with_paths(tmp_path, monkeypatch)
    # First, seed with a substantive turn
    m._on_post_llm_call(
        session_id="seed",
        user_message="A" * 200,
        assistant_response="B" * 200,
        conversation_history=[],
        model="test",
        platform="cli",
    )
    content_after_seed = (tmp_path / "DIALOGUE-HANDOFF.md").read_text()
    assert "AAAA" in content_after_seed and "BBBB" in content_after_seed

    # Now, trivial turn
    m._on_post_llm_call(
        session_id="trivial",
        user_message="ok",
        assistant_response="bien",
        conversation_history=[],
        model="test",
        platform="cli",
    )
    content_after_trivial = (tmp_path / "DIALOGUE-HANDOFF.md").read_text()
    # Tail should still contain the substantive content
    assert "AAAA" in content_after_trivial and "BBBB" in content_after_trivial
    # The trivial echo "ok" / "bien" should NOT have hijacked the tail
    # (it's allowed to appear in Last Turn metadata, but NOT in the tail)
    tail_section = content_after_trivial.split("## Recent Exchanges", 1)[1]
    assert "ok" not in tail_section.lower().split("aaaa")[0] or "bien" not in tail_section.lower().split("aaaa")[0], \
        "trivial echo should not appear in Recent Exchanges tail"
