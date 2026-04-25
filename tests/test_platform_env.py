"""Test HERMES_PLATFORM env-var fallback for hermes-continuity-plugin v1.1.1.

Setups:
  H. platform kwarg empty + HERMES_PLATFORM="minecraft" → resolves to "minecraft"
     and writes/reads from DIALOGUE-HANDOFF.minecraft.md.
  I. platform kwarg "telegram" + HERMES_PLATFORM="minecraft" → kwarg wins, telegram.
  J. platform kwarg empty + HERMES_PLATFORM unset → resolves to "" (legacy file).
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest


PLUGIN_SOURCE = Path(__file__).resolve().parent.parent / "plugin" / "__init__.py"


def _load(tmp_path, monkeypatch):
    for k in list(os.environ.keys()):
        if k.startswith("HERMES_") or k.startswith("HMK_") or k == "AGENT_MEMORY_BASE":
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HERMES_HANDOFF_PATH", str(tmp_path / "DIALOGUE-HANDOFF.md"))
    monkeypatch.setenv("HERMES_ALWAYS_CONTEXT_PATH", str(tmp_path / "ALWAYS-CONTEXT.md"))
    monkeypatch.setenv("HERMES_SESSIONS_DIR", str(tmp_path / "sessions"))
    (tmp_path / "sessions").mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location("cp_platform_env", PLUGIN_SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _substantive(prefix, n=30):
    return {
        "user_message": f"{prefix}_USER " * n,
        "assistant_response": f"{prefix}_ASST " * n,
        "conversation_history": [],
        "model": "test",
    }


def test_setup_H_env_var_used_when_kwarg_empty(tmp_path, monkeypatch):
    """H: empty kwarg + HERMES_PLATFORM=minecraft → writes to .minecraft.md."""
    m = _load(tmp_path, monkeypatch)
    monkeypatch.setenv("HERMES_PLATFORM", "minecraft")
    m._on_post_llm_call(session_id="env-h", **_substantive("H"))  # NO platform kwarg
    legacy = tmp_path / "DIALOGUE-HANDOFF.md"
    minecraft = tmp_path / "DIALOGUE-HANDOFF.minecraft.md"
    assert minecraft.exists(), "should write to minecraft file via HERMES_PLATFORM env"
    assert not legacy.exists(), "should NOT write to legacy when env says minecraft"


def test_setup_I_kwarg_wins_over_env(tmp_path, monkeypatch):
    """I: kwarg=telegram + HERMES_PLATFORM=minecraft → telegram wins."""
    m = _load(tmp_path, monkeypatch)
    monkeypatch.setenv("HERMES_PLATFORM", "minecraft")
    m._on_post_llm_call(session_id="env-i", platform="telegram", **_substantive("I"))
    telegram = tmp_path / "DIALOGUE-HANDOFF.telegram.md"
    minecraft = tmp_path / "DIALOGUE-HANDOFF.minecraft.md"
    legacy = tmp_path / "DIALOGUE-HANDOFF.md"
    assert telegram.exists(), "kwarg should win — telegram file expected"
    assert not minecraft.exists()
    assert not legacy.exists()


def test_setup_J_no_kwarg_no_env_uses_legacy(tmp_path, monkeypatch):
    """J: empty kwarg + HERMES_PLATFORM unset → legacy file (back-compat)."""
    m = _load(tmp_path, monkeypatch)
    monkeypatch.delenv("HERMES_PLATFORM", raising=False)
    m._on_post_llm_call(session_id="env-j", **_substantive("J"))
    legacy = tmp_path / "DIALOGUE-HANDOFF.md"
    assert legacy.exists(), "should write to legacy when no kwarg and no env"


def test_setup_K_pre_llm_call_uses_env(tmp_path, monkeypatch):
    """K: pre_llm_call honors HERMES_PLATFORM env when kwarg empty."""
    m = _load(tmp_path, monkeypatch)
    # First, seed minecraft handoff via env override
    monkeypatch.setenv("HERMES_PLATFORM", "minecraft")
    m._on_post_llm_call(session_id="seed", **_substantive("MC_SEED"))

    # Read with no kwarg + env=minecraft → should see MC_SEED
    result_mc = m._on_pre_llm_call(
        session_id="read-mc", user_message="hola", conversation_history=[],
        is_first_turn=True,  # NO platform kwarg, but env=minecraft
    )
    ctx_mc = (result_mc or {}).get("context", "")
    assert "MC_SEED_USER" in ctx_mc, "pre_llm_call should honor HERMES_PLATFORM env"

    # Read with env unset → should NOT see MC_SEED (resolves to legacy, which is empty)
    monkeypatch.delenv("HERMES_PLATFORM", raising=False)
    result_legacy = m._on_pre_llm_call(
        session_id="read-legacy", user_message="hola", conversation_history=[],
        is_first_turn=True,
    )
    ctx_legacy = (result_legacy or {}).get("context", "")
    assert "MC_SEED_USER" not in ctx_legacy, "without env, should not contaminate legacy"
