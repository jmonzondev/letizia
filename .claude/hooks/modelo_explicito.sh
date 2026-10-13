#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# PreToolUse (Agent|Workflow). Que ningún fan-out herede el modelo de la sesión por descuido.
# Agent: si la llamada no trae `model`, el tipo tiene que ser un agente propio con `model:` explícito (≠ inherit)
#        en .claude/agents del proyecto o en ~/.claude/agents. Los integrados (Plan, general-purpose, fork…) van con model.
# Workflow: cada `agent(` del guion lleva `model`. Si no, se niega con el motivo.
[[ "$0" == "$HOME/.claude/hooks/"* && -x "${CLAUDE_PROJECT_DIR:-/nonexistent}/.claude/hooks/$(basename "$0")" ]] && exit 0  # D3: la copia global se calla si el repo tiene la suya
input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // empty')
deny() { jq -n --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'; exit 0; }
case "$tool" in
  Agent|Task)
    model=$(printf '%s' "$input" | jq -r '.tool_input.model // empty')
    [ -n "$model" ] && exit 0
    tipo=$(printf '%s' "$input" | jq -r '.tool_input.subagent_type // empty')
    case "$tipo" in
      ""|Plan|general-purpose|fork|claude|Explore|statusline-setup|claude-code-guide)
        deny "La llamada a Agent (${tipo:-sin tipo}) no fija model. Pon model: sonnet (o haiku/opus): los integrados heredan el modelo de la sesión." ;;
    esac
    for d in "${CLAUDE_PROJECT_DIR:-.}/.claude/agents" "$HOME/.claude/agents"; do
      f="$d/$tipo.md"
      if [ -f "$f" ]; then
        m=$(sed -n '1,/^---$/p' "$f" | sed -n '2,$p' | grep -E '^model:' | head -1 | sed -E 's/^model:[[:space:]]*//; s/[[:space:]]*$//')
        case "$m" in ""|inherit) deny "El agente $tipo no fija model (o pone inherit) en $f y la llamada tampoco: pasa model en la llamada." ;; *) exit 0 ;; esac
      fi
    done
    deny "Agente $tipo no encontrado en .claude/agents ni en ~/.claude/agents y la llamada no fija model." ;;
  Workflow)
    script=$(printf '%s' "$input" | jq -r '.tool_input.script // empty')
    sp=$(printf '%s' "$input" | jq -r '.tool_input.scriptPath // empty')
    [ -z "$script" ] && [ -n "$sp" ] && [ -f "$sp" ] && script=$(cat "$sp")
    [ -z "$script" ] && exit 0
    n_agent=$(printf '%s' "$script" | grep -oE '(^|[^[:alnum:]_.])agent[[:space:]]*\(' | wc -l | tr -d ' ')
    n_model=$(printf '%s' "$script" | grep -oE "(^|[^[:alnum:]_])model[[:space:]]*:[[:space:]]*['\"\`a-zA-Z]" | wc -l | tr -d ' ')
    if [ "$n_agent" -gt 0 ] && [ "$n_model" -lt "$n_agent" ]; then
      deny "El guion tiene $n_agent llamadas agent( y solo $n_model fijan model. Cada agent() lleva {model, effort}: si no, hereda el modelo de la sesión."
    fi ;;
esac
exit 0
