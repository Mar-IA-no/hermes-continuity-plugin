# Changelog

## [1.0.0] — 2026-04-24

Initial standalone release.

**Equivalent in code to dialogue-handoff v3.1.0 bundled inside hermes-memory-kit
(commits b3b449e and 0e499d8).** Re-numbered to v1.0.0 because this is the
first release as a standalone repo.

### Changed (vs ex-kit-v3.1.0)

- Env var cascade now accepts `HERMES_*` canonical names with `HMK_*`/legacy
  fallback. `logger.warning()` once per legacy var matched. NO
  `DeprecationWarning` (Python filters those by default in runtime).
- Bases (`HERMES_HOME`, `HERMES_AGENT_MEMORY_BASE`) included in cascade so
  users can configure with 2 env vars instead of 6.
- Plugin manifest declares `compatibility: hermes-memory-kit >= v3.1.0;
  standalone with any Hermes Agent >= v0.10`.
- Auto-disable error message updated to reference canonical names first,
  with a note that legacy names are accepted as fallback.

### Inherited from ex-kit-v3.1.0 (no change)

- `_trunc()` multi-line preservation. (Previously stripped multi-line content
  to first line only — fixed in ex-kit-v3.1.0, preserved here.)
- `## Recent Exchanges` rolling tail (N=4 substantive turns, 2000 chars/msg).
- `_SUBSTANTIVE_MIN_CHARS=300` gate (trivial turns don't overwrite the tail).
- Backwards-compat with v3.0 handoffs: legacy tiered-JSON fallback path
  preserved for handoffs without the `## Recent Exchanges` block.
- Hooks: `pre_llm_call` (first-turn injection), `post_llm_call` (write tail).
