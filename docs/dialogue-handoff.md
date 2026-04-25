# dialogue-handoff plugin

The plugin packaged in this repo. Auto-injects conversational continuity into Hermes Agent at the start of every new session.

## What it does

Two hooks registered in Hermes Agent's plugin system:

### `post_llm_call` — writes the handoff

After every substantive user turn (default threshold: `user + assistant >= 300 chars combined`), the plugin updates `DIALOGUE-HANDOFF.md` with:

- Last Turn metadata (platform, session_id, timestamp, model, substantive)
- Session Path (pointer to the full session JSON)
- Last User/Assistant messages (headlines)
- Last Working Set — paths extracted from `read_file`, `write_file`, `patch`, `terminal`, `execute_code` tool calls
- Resume Hint (one-liner)
- **`## Recent Exchanges` block** — verbatim multi-line tail of the last N substantive turns (default N=4, 2000 chars/msg)

Trivial turns (below the gate) update only the metadata; the `## Recent Exchanges` tail is left intact so noise doesn't overwrite the real conversation context.

### `pre_llm_call` — injects the handoff

On the **first turn of every new session** (`is_first_turn=True`), the plugin reads `## Recent Exchanges` directly from `DIALOGUE-HANDOFF.md` and injects it as `<previous_session_context>` into the user message. The model picks up the thread without having to grep through session JSONs.

For handoffs in older format (no `## Recent Exchanges` block), a legacy tiered-JSON fallback path is preserved.

## Tunables

```python
_SUBSTANTIVE_MIN_CHARS = 300
_TAIL_EXCHANGES        = 4
_TAIL_CHARS_PER_MSG    = 2000
```

## Configuration

See [README.md](../README.md) for the full env var cascade. Quick reference:

```bash
# Direct paths (canonical)
HERMES_HANDOFF_PATH         (||  HMK_DIALOGUE_HANDOFF_PATH legacy)
HERMES_ALWAYS_CONTEXT_PATH  (||  HMK_ALWAYS_CONTEXT_PATH legacy)
HERMES_SESSIONS_DIR         (||  HMK_SESSIONS_DIR legacy)

# Or bases (derive direct paths from these)
HERMES_HOME                 (||  HMK_HERMES_HOME legacy)
HERMES_AGENT_MEMORY_BASE    (||  HMK_AGENT_MEMORY_BASE legacy)
```

## Install

Standalone: `./install.sh` (see README for modes).

Inside `hermes-memory-kit`: vendored. `bootstrap_agent.py` copies it into `$HERMES_HOME/plugins/dialogue-handoff/` and resolves env vars from `.env`.

## Verify

```bash
hermes plugins list | grep dialogue-handoff
# → dialogue-handoff   enabled   1.0.0   Working memory plugin ...
```

After a substantive turn:

```bash
ls -la $HERMES_HANDOFF_PATH
# → file with current timestamp + content with ## Recent Exchanges block
```

After re-entry (start a new Hermes session):

```bash
hermes chat -q "en qué estábamos?"
# → response cites concrete details from the previous session's tail
```

## Architecture

See [architecture.md](architecture.md) for how this plugin sits relative to long-term memory layers.
