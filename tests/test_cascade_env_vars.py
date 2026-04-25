"""Test env var cascade for hermes-continuity-plugin v1.0.0.

Tests Setup A-G from the plan:
  A. only HERMES_HANDOFF_PATH → resolves to it, NO warning.
  B. only HMK_DIALOGUE_HANDOFF_PATH → resolves, logs warning once.
  C. both → canonical wins, NO warning.
  D. only HERMES_AGENT_MEMORY_BASE → derives, NO warning (canonical base).
  E. only HMK_AGENT_MEMORY_BASE → derives, logs warning.
  F. nothing → plugin disabled (_CONFIG_OK=False), logger.error.
  G. legacy hit N times → warning appears only ONCE (gate of _legacy_warned).
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import os
from pathlib import Path
from typing import Iterator

import pytest


PLUGIN_SOURCE = Path(__file__).resolve().parent.parent / "plugin" / "__init__.py"


@pytest.fixture
def isolated_env(monkeypatch) -> Iterator[None]:
    """Strip every HERMES_* and HMK_* var so each test starts clean."""
    for k in list(os.environ.keys()):
        if k.startswith("HERMES_") or k.startswith("HMK_") or k == "AGENT_MEMORY_BASE":
            monkeypatch.delenv(k, raising=False)
    yield


def _load_plugin_fresh():
    """Import the plugin module from source, fresh each time, so the
    module-level cascade re-runs against the current env."""
    spec = importlib.util.spec_from_file_location(
        "continuity_plugin_under_test", PLUGIN_SOURCE
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_setup_A_canonical_only(isolated_env, monkeypatch, tmp_path, caplog):
    """A: only HERMES_HANDOFF_PATH set → resolves to it, no warning."""
    handoff = tmp_path / "h.md"
    always = tmp_path / "a.md"
    sessions = tmp_path / "sessions"
    monkeypatch.setenv("HERMES_HANDOFF_PATH", str(handoff))
    monkeypatch.setenv("HERMES_ALWAYS_CONTEXT_PATH", str(always))
    monkeypatch.setenv("HERMES_SESSIONS_DIR", str(sessions))

    with caplog.at_level(logging.WARNING):
        m = _load_plugin_fresh()

    assert m._HANDOFF_PATH == handoff
    assert m._ALWAYS_CONTEXT_PATH == always
    assert m._SESSIONS_DIR == sessions
    assert m._CONFIG_OK is True
    legacy_warns = [r for r in caplog.records if "legacy env var" in r.message]
    assert legacy_warns == [], f"unexpected legacy warning: {legacy_warns}"


def test_setup_B_legacy_direct_only(isolated_env, monkeypatch, tmp_path, caplog):
    """B: only HMK_DIALOGUE_HANDOFF_PATH (and friends) → resolves + warns once."""
    handoff = tmp_path / "h.md"
    always = tmp_path / "a.md"
    sessions = tmp_path / "sessions"
    monkeypatch.setenv("HMK_DIALOGUE_HANDOFF_PATH", str(handoff))
    monkeypatch.setenv("HMK_ALWAYS_CONTEXT_PATH", str(always))
    monkeypatch.setenv("HMK_SESSIONS_DIR", str(sessions))

    with caplog.at_level(logging.WARNING):
        m = _load_plugin_fresh()

    assert m._HANDOFF_PATH == handoff
    assert m._ALWAYS_CONTEXT_PATH == always
    assert m._SESSIONS_DIR == sessions
    assert m._CONFIG_OK is True
    msgs = [r.message for r in caplog.records if "legacy env var" in r.message]
    assert any("HMK_DIALOGUE_HANDOFF_PATH" in m for m in msgs), msgs
    assert any("HMK_ALWAYS_CONTEXT_PATH" in m for m in msgs), msgs
    assert any("HMK_SESSIONS_DIR" in m for m in msgs), msgs


def test_setup_C_both_canonical_wins(isolated_env, monkeypatch, tmp_path, caplog):
    """C: canonical + legacy set → canonical wins, no warning."""
    canonical_handoff = tmp_path / "canon.md"
    legacy_handoff = tmp_path / "legacy.md"
    monkeypatch.setenv("HERMES_HANDOFF_PATH", str(canonical_handoff))
    monkeypatch.setenv("HMK_DIALOGUE_HANDOFF_PATH", str(legacy_handoff))
    # Set the other two from canonical too so plugin is enabled
    monkeypatch.setenv("HERMES_ALWAYS_CONTEXT_PATH", str(tmp_path / "a.md"))
    monkeypatch.setenv("HERMES_SESSIONS_DIR", str(tmp_path / "s"))

    with caplog.at_level(logging.WARNING):
        m = _load_plugin_fresh()

    assert m._HANDOFF_PATH == canonical_handoff
    legacy_warns = [r for r in caplog.records if "HMK_DIALOGUE_HANDOFF_PATH" in r.message]
    assert legacy_warns == [], "canonical match should NOT warn for HMK_*"


def test_setup_D_canonical_base_derives(isolated_env, monkeypatch, tmp_path, caplog):
    """D: only HERMES_AGENT_MEMORY_BASE + HERMES_HOME → derives, NO warning."""
    base = tmp_path / "agent-memory"
    home = tmp_path / "hermes-home"
    monkeypatch.setenv("HERMES_AGENT_MEMORY_BASE", str(base))
    monkeypatch.setenv("HERMES_HOME", str(home))

    with caplog.at_level(logging.WARNING):
        m = _load_plugin_fresh()

    assert m._HANDOFF_PATH == base / "state" / "DIALOGUE-HANDOFF.md"
    assert m._ALWAYS_CONTEXT_PATH == base / "state" / "ALWAYS-CONTEXT.md"
    assert m._SESSIONS_DIR == home / "sessions"
    assert m._CONFIG_OK is True
    legacy_warns = [r for r in caplog.records if "legacy env var" in r.message]
    assert legacy_warns == []


def test_setup_E_legacy_base_derives_with_warning(isolated_env, monkeypatch, tmp_path, caplog):
    """E: only HMK_AGENT_MEMORY_BASE + HMK_HERMES_HOME → derives, warns once each."""
    base = tmp_path / "agent-memory"
    home = tmp_path / "hermes-home"
    monkeypatch.setenv("HMK_AGENT_MEMORY_BASE", str(base))
    monkeypatch.setenv("HMK_HERMES_HOME", str(home))

    with caplog.at_level(logging.WARNING):
        m = _load_plugin_fresh()

    assert m._HANDOFF_PATH == base / "state" / "DIALOGUE-HANDOFF.md"
    assert m._SESSIONS_DIR == home / "sessions"
    assert m._CONFIG_OK is True
    msgs = [r.message for r in caplog.records if "legacy env var" in r.message]
    assert any("HMK_AGENT_MEMORY_BASE" in msg for msg in msgs), msgs
    assert any("HMK_HERMES_HOME" in msg for msg in msgs), msgs


def test_setup_F_nothing_disables(isolated_env, caplog):
    """F: nothing → plugin disabled, logger.error."""
    with caplog.at_level(logging.ERROR):
        m = _load_plugin_fresh()

    assert m._CONFIG_OK is False
    errors = [r for r in caplog.records if r.levelname == "ERROR" and "DISABLED" in r.message]
    assert errors, "expected logger.error about disabled plugin"


def test_setup_G_legacy_warning_only_once(isolated_env, monkeypatch, tmp_path, caplog):
    """G: same legacy var resolved N times → warning appears ONCE (gate)."""
    base = tmp_path / "agent-memory"
    home = tmp_path / "hermes-home"
    monkeypatch.setenv("HMK_AGENT_MEMORY_BASE", str(base))
    monkeypatch.setenv("HMK_HERMES_HOME", str(home))

    with caplog.at_level(logging.WARNING):
        m = _load_plugin_fresh()
        # Simulate further calls within the same process: re-call _resolve_path.
        # The gate (_legacy_warned set) should prevent additional warnings.
        m._resolve_path([
            "HERMES_AGENT_MEMORY_BASE",
            "AGENT_MEMORY_BASE",
            "HMK_AGENT_MEMORY_BASE",
            "HMK_BASE_DIR",
        ])
        m._resolve_path([
            "HERMES_AGENT_MEMORY_BASE",
            "AGENT_MEMORY_BASE",
            "HMK_AGENT_MEMORY_BASE",
            "HMK_BASE_DIR",
        ])

    base_warns = [r for r in caplog.records if "HMK_AGENT_MEMORY_BASE" in r.message]
    assert len(base_warns) == 1, f"expected exactly one warning, got {len(base_warns)}: {base_warns}"
