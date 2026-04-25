#!/bin/bash
# install.sh — drop-in installer for hermes-continuity-plugin.
#
# Detects configuration mode from env vars (kit / bases / direct / defaults),
# resolves all paths, validates writability, and copies the plugin to
# $HERMES_HOME/plugins/dialogue-handoff/. Prints the env vars it resolved
# so you can add them to your shell rc or to Hermes's .env.
#
# HERMES_HOME is REQUIRED in all modes — we have to copy the plugin somewhere.

set -e

# Paso 1: HERMES_HOME es requerido
if [ -z "$HERMES_HOME" ]; then
  cat <<'EOF' >&2
ERROR: HERMES_HOME is not set.

Hermes Agent reads plugins from $HERMES_HOME/plugins/. Set HERMES_HOME to
your Hermes install directory before running this script.

Examples:
  export HERMES_HOME=~/.hermes/hermes-home
  export HERMES_HOME=~/agents/my-agent/hermes-home

If you use hermes-memory-kit, the bootstrap already vendors this plugin
and resolves paths automatically — you don't need install.sh.
EOF
  exit 2
fi

if [ ! -d "$HERMES_HOME" ]; then
  echo "INFO: $HERMES_HOME does not exist, creating it."
  mkdir -p "$HERMES_HOME"
fi

# Paso 2: resolver paths del plugin — modo según env vars presentes
if [ -n "$HERMES_HANDOFF_PATH" ] && [ -n "$HERMES_ALWAYS_CONTEXT_PATH" ] && [ -n "$HERMES_SESSIONS_DIR" ]; then
  MODE="direct"

elif [ -n "$HERMES_AGENT_MEMORY_BASE" ]; then
  MODE="bases"
  : "${HERMES_HANDOFF_PATH:=$HERMES_AGENT_MEMORY_BASE/state/DIALOGUE-HANDOFF.md}"
  : "${HERMES_ALWAYS_CONTEXT_PATH:=$HERMES_AGENT_MEMORY_BASE/state/ALWAYS-CONTEXT.md}"
  : "${HERMES_SESSIONS_DIR:=$HERMES_HOME/sessions}"

else
  MODE="defaults"
  DATA_ROOT="$HOME/.hermes-continuity-plugin-data"
  echo "INFO: no plugin paths set. Using standalone defaults at $DATA_ROOT"
  echo "      To use a kit-integrated layout instead, set HERMES_AGENT_MEMORY_BASE first and re-run."
  HERMES_HANDOFF_PATH="$DATA_ROOT/state/DIALOGUE-HANDOFF.md"
  HERMES_ALWAYS_CONTEXT_PATH="$DATA_ROOT/state/ALWAYS-CONTEXT.md"
  HERMES_SESSIONS_DIR="$HERMES_HOME/sessions"
  mkdir -p "$DATA_ROOT/state"
fi

# Paso 3: validar paths escribibles
mkdir -p "$(dirname "$HERMES_HANDOFF_PATH")"
mkdir -p "$(dirname "$HERMES_ALWAYS_CONTEXT_PATH")"
mkdir -p "$HERMES_SESSIONS_DIR"

# Paso 4: copiar plugin
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_SRC="$SCRIPT_DIR/plugin"
PLUGIN_DST="$HERMES_HOME/plugins/dialogue-handoff"

if [ ! -d "$PLUGIN_SRC" ]; then
  echo "ERROR: plugin source not found at $PLUGIN_SRC" >&2
  exit 3
fi

if [ -d "$PLUGIN_DST" ]; then
  BACKUP="$HERMES_HOME/plugin-backups/dialogue-handoff.$(date +%Y%m%d-%H%M%S).bak"
  mkdir -p "$(dirname "$BACKUP")"
  echo "INFO: existing plugin found at $PLUGIN_DST"
  echo "      Rotating to $BACKUP (so it does not collide with the new install)."
  mv "$PLUGIN_DST" "$BACKUP"
fi

mkdir -p "$(dirname "$PLUGIN_DST")"
cp -r "$PLUGIN_SRC" "$PLUGIN_DST"

# Paso 5: emitir snippet de export
cat <<EOF

✓ hermes-continuity-plugin installed at: $PLUGIN_DST
  Mode used: $MODE

Add to your shell rc (~/.bashrc, ~/.profile) or Hermes's .env:

  export HERMES_HANDOFF_PATH=$HERMES_HANDOFF_PATH
  export HERMES_ALWAYS_CONTEXT_PATH=$HERMES_ALWAYS_CONTEXT_PATH
  export HERMES_SESSIONS_DIR=$HERMES_SESSIONS_DIR

Then enable the plugin in your Hermes config.yaml:

  plugins:
    enabled:
      - dialogue-handoff

And restart Hermes (gateway or CLI session).
EOF
