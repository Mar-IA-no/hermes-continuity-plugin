# hermes-continuity-plugin

Working memory plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent). Anti-amnesia layer between sessions, crashes, model switches, and context compaction.

What it does: persists the last N substantive turns of conversation in a single markdown file (`DIALOGUE-HANDOFF.md`) and injects them into the first turn of every new session. The model picks up the thread without having to grep through session JSONs.

## Why this is separated from `hermes-memory-kit`

This plugin is **working memory** (per session, last few turns, immediate continuity). The [hermes-memory-kit](https://github.com/Mar-IA-no/hermes-memory-kit) handles **long-term memory** (durable facts, embeddings, hybrid retrieval).

The two layers are orthogonal: this plugin works fine without the kit, and the kit can use any continuity mechanism (or none). Splitting them into separate repos lets each evolve independently and lets you use just the part you need.

## Install

### Modes

The plugin needs to know **where** Hermes Agent is installed (`HERMES_HOME`) and **where** to write its state (handoff + always-context + sessions). The install script supports four configuration modes:

| Mode | Required env | Where state goes |
|---|---|---|
| **kit-integrated** | (handled by `hermes-memory-kit`) | `<workspace>/agent-memory/state/...` |
| **bases** | `HERMES_HOME`, `HERMES_AGENT_MEMORY_BASE` | derived: `<base>/state/DIALOGUE-HANDOFF.md`, etc |
| **direct** | `HERMES_HOME` + the 3 `HERMES_HANDOFF_PATH`/`HERMES_ALWAYS_CONTEXT_PATH`/`HERMES_SESSIONS_DIR` | exactly what you set |
| **standalone defaults** | `HERMES_HOME` only | `~/.hermes-continuity-plugin-data/state/`, `$HERMES_HOME/sessions` |

### Quick start (standalone defaults)

```bash
git clone https://github.com/Mar-IA-no/hermes-continuity-plugin
cd hermes-continuity-plugin
export HERMES_HOME=~/.hermes/hermes-home   # or wherever your Hermes lives
./install.sh
```

The script copies the plugin to `$HERMES_HOME/plugins/dialogue-handoff/`, creates the data directory, and prints the env vars it resolved so you can add them to your shell rc or to Hermes's `.env`.

### Inside `hermes-memory-kit`

Already vendored: bootstrap a workspace with `bootstrap_agent.py` and the plugin is installed automatically with the right paths set.

## Configuration

Env var cascade (canonical first, legacy after, base-derived last):

```
Direct paths (canonical → legacy):
  HERMES_HANDOFF_PATH         || HMK_DIALOGUE_HANDOFF_PATH
  HERMES_ALWAYS_CONTEXT_PATH  || HMK_ALWAYS_CONTEXT_PATH
  HERMES_SESSIONS_DIR         || HMK_SESSIONS_DIR

Bases (canonical → legacy):
  HERMES_AGENT_MEMORY_BASE    || AGENT_MEMORY_BASE / HMK_AGENT_MEMORY_BASE / HMK_BASE_DIR
  HERMES_HOME                 || HMK_HERMES_HOME

Derivation (used only if the corresponding direct path is not set):
  HANDOFF_PATH         := <agent_memory_base>/state/DIALOGUE-HANDOFF.md
  ALWAYS_CONTEXT_PATH  := <agent_memory_base>/state/ALWAYS-CONTEXT.md
  SESSIONS_DIR         := <hermes_home>/sessions
```

If the plugin matches a legacy var, it logs a `logger.warning` once per var (visible in gateway logs). Legacy fallback removal is planned for plugin v2.0.

If neither direct paths nor base + hermes_home are set, the plugin disables itself (no-op hooks) and logs a clear error.

## How it works

- **`post_llm_call` hook** (after every assistant response): if the turn is substantive (`user_msg + assistant_response >= 300 chars`), append it to `## Recent Exchanges` in `DIALOGUE-HANDOFF.md`. Tail is rolling N=4. Each message is verbatim multi-line, capped at 2000 chars.
- **`pre_llm_call` hook** (before every LLM call, only on first turn of a new session): read `## Recent Exchanges` from `DIALOGUE-HANDOFF.md` and inject it as `<previous_session_context>` into the user message. The model sees the thread state and picks up continuity.

The `## Recent Exchanges` block is the canonical source of injection — `pre_llm_call` does **not** reopen session JSONs (which is slow and contaminates context). For handoffs from older versions without the block, a legacy tiered-JSON fallback path is preserved for backwards-compat.

## Tunables

Constants at the top of `plugin/__init__.py`:

```python
_SUBSTANTIVE_MIN_CHARS = 300   # below this, post_llm_call doesn't touch the tail
_TAIL_EXCHANGES        = 4     # how many recent substantive turns to keep
_TAIL_CHARS_PER_MSG    = 2000  # cap per message in the tail
```

## Compatibility

- Hermes Agent >= v0.10 (uses `pre_llm_call` / `post_llm_call` hook signatures introduced in v0.10).
- `hermes-memory-kit` >= v3.1.0 (when used vendored).

## License

MIT.

## Related

- [hermes-memory-kit](https://github.com/Mar-IA-no/hermes-memory-kit) — long-term memory layer (SQLite + FTS5 + embeddings + hybrid retrieval).
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — upstream agent.
