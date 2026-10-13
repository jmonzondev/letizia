#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# PreToolUse (Bash). Nada pregunta y nada se destruye: las órdenes de git que descartan trabajo se niegan y el motivo remite a
# ~/.claude/bin/git_seguro.sh, que hace lo mismo guardando antes una copia en la papelera.
#   git checkout -- / git restore  -> git_seguro.sh descartar <ficheros>
#   git clean                      -> git_seguro.sh limpiar
#   git branch -D|-d               -> git_seguro.sh borrar-rama <rama>
#   git stash drop|clear           -> git_seguro.sh soltar-stash [n]
#   git reset --hard               -> git_seguro.sh reset-duro <ref>
#   alembic downgrade              -> git_seguro.sh downgrade-seguro <destino>
[[ "$0" == "$HOME/.claude/hooks/"* && -x "${CLAUDE_PROJECT_DIR:-/nonexistent}/.claude/hooks/$(basename "$0")" ]] && exit 0  # D3: la copia global se calla si el repo tiene la suya
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$cmd" ] && exit 0
# Los cuerpos de heredoc (<<EOF … EOF) son datos, no órdenes: se quitan antes de mirar (D9). La línea del «<<» sí se mira.
cmd=$(printf '%s\n' "$cmd" | awk -v q="'" '
  BEGIN { re = "<<-?[[:space:]]*[\"" q "]?[A-Za-z_][A-Za-z0-9_]*[\"" q "]?" }
  inh { if ($0 == term || $0 ~ ("^[[:space:]]*" term "[[:space:]]*$")) inh = 0; next }
  { print; if (match($0, re)) { t = substr($0, RSTART, RLENGTH); sub(/^<<-?[[:space:]]*/, "", t); gsub("[\"" q "]", "", t); term = t; inh = 1 } }')
deny() { jq -n --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'; exit 0; }
g='(^|[;&|(`][[:space:]]*|\$\([[:space:]]*|(then|do|else|exec|xargs|sudo)[[:space:]]+)git([[:space:]]+-[A-Za-z-]+([[:space:]]+[^[:space:]]+)?)*[[:space:]]+'
printf '%s' "$cmd" | grep -qE "${g}(checkout[[:space:]]+(--|[^[:space:]]+[[:space:]]+--[[:space:]])|restore([[:space:]]|$))" && deny "Esa orden descarta cambios sin copia. Usa: ~/.claude/bin/git_seguro.sh descartar <ficheros> (copia a la papelera y luego restaura)."
printf '%s' "$cmd" | grep -qE "${g}clean([[:space:]]|$)" && deny "git clean borra lo no seguido. Usa: ~/.claude/bin/git_seguro.sh limpiar (mueve lo no seguido a la papelera)."
printf '%s' "$cmd" | grep -qE "${g}branch[[:space:]]+(-D|-d|--delete)" && deny "Borrar una rama pierde sus commits. Usa: ~/.claude/bin/git_seguro.sh borrar-rama <rama> (deja la etiqueta papelera/<rama>_<fecha> y la borra)."
printf '%s' "$cmd" | grep -qE "${g}stash[[:space:]]+(drop|clear)" && deny "Soltar un stash lo pierde. Usa: ~/.claude/bin/git_seguro.sh soltar-stash [n] (lo guarda como parche en la papelera)."
printf '%s' "$cmd" | grep -qE "${g}reset[[:space:]]+(--hard|--merge)" && deny "reset --hard tira el trabajo desde ese commit. Usa: ~/.claude/bin/git_seguro.sh reset-duro <ref> (etiqueta y parche en la papelera antes)."
printf '%s' "$cmd" | grep -qE '(^|[;&|(`][[:space:]]*|\$\([[:space:]]*|(then|do|else|exec|xargs|sudo)[[:space:]]+)alembic[[:space:]]+downgrade' && deny "alembic downgrade borra columnas o tablas con sus datos. Usa: ~/.claude/bin/git_seguro.sh downgrade-seguro <destino> (vuelca la base antes)."
exit 0
