"""Test that _trunc() preserves multi-line content (regression of v3.0 → v3.1)."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path


PLUGIN_SOURCE = Path(__file__).resolve().parent.parent / "plugin" / "__init__.py"


def _load(tmp_path, monkeypatch):
    for k in list(os.environ.keys()):
        if k.startswith("HERMES_") or k.startswith("HMK_") or k == "AGENT_MEMORY_BASE":
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HERMES_HANDOFF_PATH", str(tmp_path / "h.md"))
    monkeypatch.setenv("HERMES_ALWAYS_CONTEXT_PATH", str(tmp_path / "a.md"))
    monkeypatch.setenv("HERMES_SESSIONS_DIR", str(tmp_path / "s"))
    (tmp_path / "s").mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location("cp_trunc", PLUGIN_SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_trunc_preserves_newlines_under_budget(tmp_path, monkeypatch):
    """When content is shorter than the budget, newlines must remain."""
    m = _load(tmp_path, monkeypatch)
    multi_line = "line one\nline two\nline three"
    out = m._trunc(multi_line, 1000)
    assert out == multi_line  # under budget, no change


def test_trunc_preserves_newlines_when_truncated(tmp_path, monkeypatch):
    """When content exceeds budget, truncation must keep newlines (not collapse to first line)."""
    m = _load(tmp_path, monkeypatch)
    multi_line = "line one\n" + ("line two contents " * 30) + "\nline three"
    out = m._trunc(multi_line, 100)
    # Should NOT be just "line one" (the v3.0 bug). It should contain at least
    # part of "line one\nline two..." preserving the newline.
    assert "\n" in out, f"truncated output collapsed multi-line: {out!r}"


def test_trunc_short_input_unchanged(tmp_path, monkeypatch):
    m = _load(tmp_path, monkeypatch)
    assert m._trunc("hello", 100) == "hello"
    assert m._trunc("", 100) == ""


def test_trunc_full_post_llm_call_preserves_markdown(tmp_path, monkeypatch):
    """End-to-end: a markdown response with bullets/code should appear in
    the Recent Exchanges tail with structure intact."""
    m = _load(tmp_path, monkeypatch)
    asst_md = """Here are three options:

1. **Option A**: do this thing.
2. **Option B**: do another thing.
3. **Option C**: do yet another thing.

```python
print("hello")
```

My recommendation is Option B.
"""
    m._on_post_llm_call(
        session_id="md-test",
        user_message="What are the options? " * 20,
        assistant_response=asst_md,
        conversation_history=[],
        model="test",
        platform="cli",
    )
    content = (tmp_path / "h.md").read_text()
    tail = content.split("## Recent Exchanges", 1)[1]
    # Multi-line markdown structure should be preserved in the tail
    assert "Option A" in tail
    assert "Option B" in tail
    assert "Option C" in tail
    assert "```python" in tail
    # Should not have been collapsed to first line
    assert tail.count("\n") > 5, "expected preserved multi-line structure in tail"
