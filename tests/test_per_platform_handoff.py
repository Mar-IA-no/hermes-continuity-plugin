"""Test per-platform handoff for hermes-continuity-plugin v1.1.0.

Setups:
  A. platform="" → writes to legacy DIALOGUE-HANDOFF.md.
  B. platform="cli" → writes to legacy DIALOGUE-HANDOFF.md (same as A).
  C. platform="minecraft" → writes to DIALOGUE-HANDOFF.minecraft.md.
  D. CLI and Minecraft turns in the same env → two separate files, no
     cross-contamination of Recent Exchanges.
  E. Read with platform="minecraft" only sees minecraft tail; read with
     platform="" only sees the legacy file.
  F. HERMES_HANDOFF_FALLBACK_LEGACY=true → if per-platform file is missing
     and legacy exists, falls back to legacy. With false (default), does not.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Iterator

import pytest


PLUGIN_SOURCE = Path(__file__).resolve().parent.parent / "plugin" / "__init__.py"


@pytest.fixture
def isolated_env(monkeypatch) -> Iterator[None]:
    for k in list(os.environ.keys()):
        if k.startswith("HERMES_") or k.startswith("HMK_") or k == "AGENT_MEMORY_BASE":
            monkeypatch.delenv(k, raising=False)
    yield


def _load(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HANDOFF_PATH", str(tmp_path / "DIALOGUE-HANDOFF.md"))
    monkeypatch.setenv("HERMES_ALWAYS_CONTEXT_PATH", str(tmp_path / "ALWAYS-CONTEXT.md"))
    monkeypatch.setenv("HERMES_SESSIONS_DIR", str(tmp_path / "sessions"))
    (tmp_path / "sessions").mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location("cp_per_platform", PLUGIN_SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _substantive_turn(prefix: str, n: int = 30) -> dict:
    """Build a kwargs dict for _on_post_llm_call that passes the substantive gate."""
    return {
        "user_message": f"{prefix}_USER " * n,
        "assistant_response": f"{prefix}_ASST " * n,
        "conversation_history": [],
        "model": "test",
    }


def test_setup_A_empty_platform_uses_legacy_file(isolated_env, tmp_path, monkeypatch):
    """A: platform="" → writes to DIALOGUE-HANDOFF.md (legacy)."""
    m = _load(tmp_path, monkeypatch)
    m._on_post_llm_call(session_id="t-A", platform="", **_substantive_turn("A"))
    legacy = tmp_path / "DIALOGUE-HANDOFF.md"
    minecraft = tmp_path / "DIALOGUE-HANDOFF.minecraft.md"
    assert legacy.exists(), "legacy file should be written for platform=''"
    assert not minecraft.exists(), "minecraft file should NOT exist"
    assert "A_USER" in legacy.read_text()


def test_setup_B_cli_platform_uses_legacy_file(isolated_env, tmp_path, monkeypatch):
    """B: platform="cli" → writes to DIALOGUE-HANDOFF.md (legacy, same as empty)."""
    m = _load(tmp_path, monkeypatch)
    m._on_post_llm_call(session_id="t-B", platform="cli", **_substantive_turn("B"))
    legacy = tmp_path / "DIALOGUE-HANDOFF.md"
    cli_suffix = tmp_path / "DIALOGUE-HANDOFF.cli.md"
    assert legacy.exists(), "legacy file should be written for platform='cli'"
    assert not cli_suffix.exists(), "DIALOGUE-HANDOFF.cli.md should NOT exist"
    assert "B_USER" in legacy.read_text()


def test_setup_C_minecraft_platform_uses_suffixed_file(isolated_env, tmp_path, monkeypatch):
    """C: platform="minecraft" → writes to DIALOGUE-HANDOFF.minecraft.md."""
    m = _load(tmp_path, monkeypatch)
    m._on_post_llm_call(session_id="t-C", platform="minecraft", **_substantive_turn("C"))
    legacy = tmp_path / "DIALOGUE-HANDOFF.md"
    minecraft = tmp_path / "DIALOGUE-HANDOFF.minecraft.md"
    assert minecraft.exists(), "minecraft file should be written"
    assert not legacy.exists(), "legacy file should NOT be written when platform=minecraft"
    assert "C_USER" in minecraft.read_text()


def test_setup_D_no_cross_contamination(isolated_env, tmp_path, monkeypatch):
    """D: CLI and minecraft turns in same env → two separate files, no overlap."""
    m = _load(tmp_path, monkeypatch)
    m._on_post_llm_call(session_id="cli-1", platform="cli", **_substantive_turn("CLI_TURN"))
    m._on_post_llm_call(session_id="mc-1", platform="minecraft", **_substantive_turn("MC_TURN"))
    legacy = tmp_path / "DIALOGUE-HANDOFF.md"
    minecraft = tmp_path / "DIALOGUE-HANDOFF.minecraft.md"
    legacy_text = legacy.read_text()
    minecraft_text = minecraft.read_text()
    # Each file should contain only its own platform's turn
    assert "CLI_TURN_USER" in legacy_text
    assert "MC_TURN_USER" not in legacy_text, "CLI handoff should NOT contain MC turn"
    assert "MC_TURN_USER" in minecraft_text
    assert "CLI_TURN_USER" not in minecraft_text, "MC handoff should NOT contain CLI turn"


def test_setup_E_pre_llm_reads_only_matching_platform(isolated_env, tmp_path, monkeypatch):
    """E: pre_llm_call with platform=minecraft only sees minecraft tail."""
    m = _load(tmp_path, monkeypatch)
    m._on_post_llm_call(session_id="cli-1", platform="cli", **_substantive_turn("CLI_TURN"))
    m._on_post_llm_call(session_id="mc-1", platform="minecraft", **_substantive_turn("MC_TURN"))

    # Reading with platform=minecraft → should see MC_TURN, not CLI_TURN
    result_mc = m._on_pre_llm_call(
        session_id="mc-2", user_message="hola", conversation_history=[],
        is_first_turn=True, platform="minecraft"
    )
    ctx_mc = (result_mc or {}).get("context", "")
    assert "MC_TURN_USER" in ctx_mc, "MC injection should contain MC turn"
    assert "CLI_TURN_USER" not in ctx_mc, "MC injection should NOT contain CLI turn"

    # Reading with platform=cli (or empty) → should see CLI_TURN, not MC_TURN
    result_cli = m._on_pre_llm_call(
        session_id="cli-2", user_message="hola", conversation_history=[],
        is_first_turn=True, platform="cli"
    )
    ctx_cli = (result_cli or {}).get("context", "")
    assert "CLI_TURN_USER" in ctx_cli, "CLI injection should contain CLI turn"
    assert "MC_TURN_USER" not in ctx_cli, "CLI injection should NOT contain MC turn"


def test_setup_F_legacy_fallback_when_enabled(isolated_env, tmp_path, monkeypatch):
    """F: HERMES_HANDOFF_FALLBACK_LEGACY=true → MC pre_llm reads legacy if MC file missing."""
    m = _load(tmp_path, monkeypatch)
    # Seed only legacy
    m._on_post_llm_call(session_id="cli-only", platform="cli", **_substantive_turn("LEGACY"))
    legacy = tmp_path / "DIALOGUE-HANDOFF.md"
    minecraft = tmp_path / "DIALOGUE-HANDOFF.minecraft.md"
    assert legacy.exists() and not minecraft.exists()

    # Without fallback → MC pre_llm sees nothing
    monkeypatch.delenv("HERMES_HANDOFF_FALLBACK_LEGACY", raising=False)
    result_strict = m._on_pre_llm_call(
        session_id="mc-strict", user_message="hola", conversation_history=[],
        is_first_turn=True, platform="minecraft"
    )
    ctx_strict = (result_strict or {}).get("context", "")
    assert "LEGACY_USER" not in ctx_strict, "without fallback, MC should NOT see legacy"

    # With fallback enabled → MC pre_llm sees legacy
    monkeypatch.setenv("HERMES_HANDOFF_FALLBACK_LEGACY", "true")
    result_fallback = m._on_pre_llm_call(
        session_id="mc-fallback", user_message="hola", conversation_history=[],
        is_first_turn=True, platform="minecraft"
    )
    ctx_fallback = (result_fallback or {}).get("context", "")
    assert "LEGACY_USER" in ctx_fallback, "with fallback, MC should see legacy"
