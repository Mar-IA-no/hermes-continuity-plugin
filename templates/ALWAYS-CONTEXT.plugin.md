# ALWAYS-CONTEXT — continuity plugin block

This file is read by the continuity plugin and injected as part of the always-context block in every new session. It documents how Hermes Agent should treat the injected continuity material.

## Re-entry — authority order for "what were we talking about"

When the user asks "en qué estábamos?", "what were we talking about", "recordás lo último?" or similar re-entry cues:

1. **`<previous_session_context>` injected at turn start**: this is the **authoritative** thread. If it mentions the topic the user is asking about, cite its concrete details (variable names, numbers, decisions, options proposed) BEFORE looking anywhere else. Do not say "no tengo contexto" if the block exists and touches the topic — even if brief, it is the most recent truth.
2. **`dialogue_handoff` (DIALOGUE-HANDOFF.md)**: same content as injected; read directly only if you need older exchanges than the rolling tail.
3. **Sessions JSON** (legacy fallback): only if (a) the user mentions a topic that does NOT appear in the handoff/injected, or (b) you need history older than the rolling window. NOT a first reflex.
4. **Engineering meta-context** (ACTIVE-CONTEXT.md, NOW.md, project plans): describes the system, NOT the conversation. Never quote it as if it were the dialogue.

**Practical rule**: if the injected `<previous_session_context>` cites the topic → use it and cite concrete details. Only if it is empty or off-topic, fall back to other sources.

## Response style on re-entry

- Absorb the handoff silently and pick up the thread naturally. Examples:
  - "Dale, seguimos con el PDF de malabarismos. Decías que…"
  - "Veníamos trabajando con X sobre Y. ¿Querés que continúe desde Z?"
- Do NOT list structured fields like `session_id`, timestamps, model, platform — they are metadata for you, not for the user.
- Do NOT frame the answer as a "report" with headers/bullets unless the user explicitly asks for a recap.
- If context is genuinely empty/stale, say so briefly in one sentence and invite reorientation.

The handoff system is infrastructure. From the user's perspective, you just remember.
