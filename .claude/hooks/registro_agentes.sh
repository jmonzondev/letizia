#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# Registra en ~/.claude/uso/agentes.tsv qué modelo y esfuerzo usa cada subagente, para comparar lo estimado con lo real.
#  - PostToolUse (Agent): resolvedModel, modelsUsed, tokens y duración que devuelve la herramienta.
#  - Cualquier evento de herramienta dentro de un subagente (agent_id presente): agent_type y effort.level, una línea por agente.
# Columna `cuenta`: A si la sesión corre con CLAUDE_CONFIG_DIR=~/.claude-a, B si es ~/.claude (D1). El TSV es uno para las dos.
# Nunca escribe el prompt ni el contenido. Compatible con bash 3.2.
[[ "$0" == "$HOME/.claude/hooks/"* && -x "${CLAUDE_PROJECT_DIR:-/nonexistent}/.claude/hooks/$(basename "$0")" ]] && exit 0  # D3: la copia global se calla si el repo tiene la suya
input=$(cat)
dir="$HOME/.claude/uso"; mkdir -p "$dir/agentes" 2>/dev/null
f="$dir/agentes.tsv"; [ -f "$f" ] || printf 'fecha\tevento\tsesion\tagent_id\tagent_type\tmodelo\tesfuerzo\ttokens\tms\tmodelos_usados\tcuenta\n' > "$f"
ahora=$(date '+%Y-%m-%d %H:%M:%S')
cuenta=$(basename "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"); case "$cuenta" in .claude) cuenta=B ;; .claude-a) cuenta=A ;; esac
ev=$(printf '%s' "$input" | jq -r '.hook_event_name // ""')
tool=$(printf '%s' "$input" | jq -r '.tool_name // ""')
ses=$(printf '%s' "$input" | jq -r '(.session_id // "")[0:8]')
aid=$(printf '%s' "$input" | jq -r '.agent_id // ""')
if [ "$ev" = "PostToolUse" ] && { [ "$tool" = "Agent" ] || [ "$tool" = "Task" ]; }; then
  printf '%s' "$input" | jq -r --arg t "$ahora" --arg s "$ses" --arg c "$cuenta" '[$t, "agente_terminado", $s, (.tool_response.agentId // ""), (.tool_input.subagent_type // ""), (.tool_response.resolvedModel // (.tool_input.model // "?")), (.tool_input.effort // ""), ((.tool_response.totalTokens // "") | tostring), ((.tool_response.totalDurationMs // "") | tostring), ((.tool_response.modelsUsed // []) | join(",")), $c] | @tsv' >> "$f"
  exit 0
fi
if [ -n "$aid" ] && [ ! -e "$dir/agentes/$aid" ]; then
  : > "$dir/agentes/$aid"
  printf '%s' "$input" | jq -r --arg t "$ahora" --arg s "$ses" --arg c "$cuenta" '[$t, "dentro_del_agente", $s, .agent_id, (.agent_type // ""), "", ((.effort.level // .effort // "") | tostring), "", "", "", $c] | @tsv' >> "$f"
fi
exit 0
