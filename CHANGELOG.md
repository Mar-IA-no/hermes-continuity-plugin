# Changelog

## [1.1.1] — 2026-04-25

HERMES_PLATFORM env-var fallback when host runtime does not pass `platform` kwarg to the hooks. Required for use cases like `hermes chat -q` (hardcodes `platform="cli"`) when the same agent process serves multiple platforms.

### Added

- New helper `_resolve_platform(provided)` returns the explicit kwarg if truthy, else falls back to `os.environ.get("HERMES_PLATFORM")`. Lets the same agent process serve different platforms by setting HERMES_PLATFORM before each invocation.
- `_on_post_llm_call` and `_on_pre_llm_call` apply this resolution at the start of their try block, so all downstream behavior (path resolution, tail read/write) honors the env override.

### Backwards compatibility

- When the kwarg is provided AND truthy, it wins over the env var. No behavior change for hosts that already pass platform explicitly (gateways, etc).
- When neither kwarg nor env is set, resolves to `""` → legacy file (same as v1.1.0 default).


## [1.1.0] — 2026-04-24

Per-platform working memory. Same agent can live in multiple channels (CLI, Telegram, Minecraft, Discord) simultaneously without contaminating the working memory of one channel with turns from another.

### Added

- **Per-platform handoff files**: `post_llm_call(platform=...)` writes to a per-platform file. Convention:
  - `platform=""` or `platform="cli"` → legacy `DIALOGUE-HANDOFF.md` (back-compat with all existing deploys).
  - `platform="minecraft"` → `DIALOGUE-HANDOFF.minecraft.md`.
  - `platform="telegram"` → `DIALOGUE-HANDOFF.telegram.md`.
  - any other platform → `DIALOGUE-HANDOFF.<platform>.md` (sanitized).
- **Per-platform reading**: `pre_llm_call(platform=...)` reads only the file that matches the current platform. A Minecraft session never reads CLI's handoff.
- **Optional legacy fallback** for upgrade-in-place: env var `HERMES_HANDOFF_FALLBACK_LEGACY=true` makes pre_llm_call fall back to the legacy file when the per-platform file does not exist yet. Default `false` (strict per-platform isolation).
- New helper `_per_platform_path(base_path, platform)` derives the path from the resolved `_HANDOFF_PATH` (works regardless of cascade source — direct env, legacy, or base-derived).
- New helper `_resolve_handoff_path(platform)` handles fallback semantics.

### Changed

- `_on_post_llm_call` writes to the per-platform path instead of the static `_HANDOFF_PATH`.
- `_on_pre_llm_call` accepts `platform` kwarg and reads from the per-platform path.
- `_read_existing_tail(platform)` is now scoped per-platform.
- Plugin manifest `compatibility` and description updated.

### Backwards compatibility

- Deploys that don't pass `platform` (or pass `cli`) keep using `DIALOGUE-HANDOFF.md` exactly as before. No migration required.
- Plugin tests for v1.0.0 (substantive gate, recent exchanges, trunc multi-line) pass unchanged.

### Inherited from v1.0.0 (no change)

- Env var cascade `HERMES_*` canonical || `HMK_*` legacy with `logger.warning()` once.
- `_trunc()` multi-line preservation.
- `## Recent Exchanges` rolling tail (N=4 substantive turns, 2000 chars/msg).
- `_SUBSTANTIVE_MIN_CHARS=300` gate.

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
