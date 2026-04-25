# Architecture

Where this plugin sits in the agent stack.

## Two memory systems, one agent

| Layer | Lives | Scope | Persistence |
|---|---|---|---|
| **Working memory** (this plugin) | `DIALOGUE-HANDOFF.md` + `<previous_session_context>` injection | per session, last N substantive turns | Markdown file, append-mostly |
| **Long-term memory** (e.g. [hermes-memory-kit](https://github.com/Mar-IA-no/hermes-memory-kit)) | SQLite `library.db` + FTS5 + embeddings | durable facts, skills, episodes — cross-session | DB, indexed |

These are **orthogonal** layers. The continuity plugin works without long-term memory. The long-term memory works without the continuity plugin. They communicate, if at all, through the convention that long-term memory **may** read `DIALOGUE-HANDOFF.md` to learn about the most recent turns when consolidating.

This separation matches the patterns that the field has converged to in 2025-2026 (see ENGRAM, MemMachine, OpenMemory): mixing working and long-term contaminates both — turning every conversational turn into a long-term fact pollutes the long-term store with noise; collapsing long-term retrieval into the prompt context bloats every turn.

## Hooks

The plugin registers two hooks in Hermes Agent's plugin system (`provides_hooks` in `plugin.yaml`):

```
                       ┌──────────────────────────┐
turn N starts          │ pre_llm_call(             │
─────────────────────► │   user_message,           │
  (first_turn=True)    │   conversation_history,   │
                       │   is_first_turn=True      │
                       │ )                          │
                       └────────────┬─────────────┘
                                    │ reads ## Recent Exchanges
                                    ▼
                       inject as <previous_session_context>
                                    │
                                    ▼
                       LLM receives the augmented user message
                                    │
                                    ▼
                       LLM responds
                                    │
                       ┌────────────┴─────────────┐
                       │ post_llm_call(            │
                       │   user_message,           │
                       │   assistant_response,     │
                       │   conversation_history    │
                       │ )                          │
                       └────────────┬─────────────┘
                                    │ if substantive (>=300 chars combined):
                                    │   - prepend new exchange to tail
                                    │   - keep top N (default N=4)
                                    │   - rewrite DIALOGUE-HANDOFF.md
                                    │ if trivial:
                                    │   - update Last Turn metadata only
                                    │   - leave Recent Exchanges intact
                                    ▼
turn N done
```

## Why a markdown file

Storing the tail in a single markdown file (instead of a database) gives:

- **Trivial inspection**: `cat DIALOGUE-HANDOFF.md` shows the full state. No SQL, no schema migrations.
- **Trivial editing**: a user can manually edit the tail (e.g. fix a typo, redact something). Plugin re-reads on next turn.
- **No external dependency**: no SQLite, no server, no migration. Works in any environment that can read/write a file.
- **Tier compatibility**: long-term memory layers can read the file too, and the plugin can read older formats with a fallback parser.

Trade-off: writes are full-file rewrites (small files, no concurrency issue in practice). For agents producing thousands of turns per minute, a DB-backed approach would be needed; this plugin targets the conversational range (one turn every few seconds).

## State file format

`DIALOGUE-HANDOFF.md`:

```markdown
# DIALOGUE-HANDOFF

## Last Turn
- platform: cli
- session_id: ...
- timestamp: ...
- model: ...
- substantive: true|false

## Session Path
- /path/to/session.json

## Last User Message (headline)
- (first line, truncated)

## Last Assistant Response (headline)
- (first line, truncated)

## Last Working Set
- (file paths touched in tools this turn)

## Resume Hint
- (one-liner)

## Recent Exchanges
<!-- multi-line verbatim tail of last N substantive turns -->

### Exchange @ <timestamp> (<platform>, session <id>)
USER: <full user message, multi-line preserved, capped at _TAIL_CHARS_PER_MSG>
HERMES: <full assistant response, multi-line preserved, capped at _TAIL_CHARS_PER_MSG>

### Exchange @ ...
USER: ...
HERMES: ...
```

Older format (without `## Recent Exchanges`) is still readable: the plugin falls back to reading the linked session JSON for the tail content.

## Compatibility

- Hermes Agent ≥ v0.10 (uses `pre_llm_call` / `post_llm_call` hook signatures introduced in v0.10).
- `hermes-memory-kit` ≥ v3.1.0 when used vendored.
