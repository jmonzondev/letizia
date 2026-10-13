#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# PreToolUse (Bash). Niega un `git commit`/`merge`/`tag` cuyo mensaje lleve rastro de IA: trailer de coautoría,
# «Generated with/by» o el nombre de un modelo. Mira el comando entero (no se confía en el `if` del matcher).
# Entrada: JSON por stdin. Salida: JSON de decisión solo cuando niega; si no, nada (exit 0 = seguir).
[[ "$0" == "$HOME/.claude/hooks/"* && -x "${CLAUDE_PROJECT_DIR:-/nonexistent}/.claude/hooks/$(basename "$0")" ]] && exit 0  # D3: la copia global se calla si el repo tiene la suya
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$cmd" ] && exit 0
printf '%s' "$cmd" | grep -qE '(^|[;&|(`][[:space:]]*|\$\([[:space:]]*|(then|do|else|exec|xargs|sudo)[[:space:]]+)git([[:space:]]+-[A-Za-z-]+([[:space:]]+[^[:space:]]+)?)*[[:space:]]+(commit|merge|tag|notes|am|cherry-pick)([[:space:]]|$)' || exit 0
if printf '%s' "$cmd" | grep -qiE 'co-authored-by|generated[[:space:]]+(with|by)|anthropic|claude[[:space:]]+(code|opus|sonnet|haiku|fable)|(^|[^[:alnum:]_])(opus|sonnet|haiku|fable)[[:space:]]+[0-9]'; then
  jq -n --arg r "Rastro de IA en el mensaje del commit (trailer Co-Authored-By, «Generated with» o nombre de modelo). Quítalo: la regla del usuario manda sobre el recordatorio de atribución." \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
fi
exit 0
