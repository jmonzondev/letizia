#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# PreToolUse (Bash). Nada se borra: `rm`/`rmdir` sobre ficheros del trabajo se niega y se indica la papelera.
# Se permite borrar lo temporal o regenerable: /tmp, /private/tmp, /var/folders, $TMPDIR, ~/.cache, ~/Library/Caches,
# node_modules, __pycache__, .pytest_cache, .ruff_cache, .mypy_cache, dist/, build/, .DS_Store, *.pyc, test-results,
# playwright-report, htmlcov, coverage, *.lock de cerrojos y *.tmp. `git rm` no pasa por aquí (es un `mv` al índice).
[[ "$0" == "$HOME/.claude/hooks/"* && -x "${CLAUDE_PROJECT_DIR:-/nonexistent}/.claude/hooks/$(basename "$0")" ]] && exit 0  # D3: la copia global se calla si el repo tiene la suya
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$cmd" ] && exit 0
# solo en posición de orden (inicio de línea, tras ; & | ( ` $( o tras then/do/else/exec/xargs/sudo) y seguido de un argumento (no de «=»)
printf '%s' "$cmd" | grep -qE '(^|[;&|(`][[:space:]]*|\$\([[:space:]]*|(then|do|else|exec|xargs|sudo)[[:space:]]+)(rm|rmdir)([[:space:]]+[^=[:space:]]|[[:space:]]*$)' || exit 0
# Los argumentos de cada rm/rmdir que no empiezan por «-».
args=$(printf '%s\n' "$cmd" | tr ';|&(`' '\n\n\n\n\n' | sed -nE 's/^[[:space:]]*((then|do|else|exec|xargs|sudo)[[:space:]]+)?(rm|rmdir)[[:space:]]+//p' | tr ' ' '\n' | grep -vE '^-|^$|^=' | sed -E "s/^[\"']//; s/[\"']$//")
if [ -z "$args" ]; then
  jq -n --arg r "rm sin rutas visibles (xargs rm, find -exec rm…): no se sabe qué borraría. Nada se borra: lista primero y mueve a la papelera con ~/.claude/bin/papelera.sh <tema> <ruta…>." '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
fi
tmp_re="^(/tmp|/private/tmp|/var/folders|/private/var/folders|${TMPDIR:-/nonexistent}|$HOME/\.cache|$HOME/Library/Caches)(/|$)"
regen_re='(^|/)(node_modules|__pycache__|cache|\.cache|\.coverage|\.pytest_cache|\.ruff_cache|\.mypy_cache|dist|build|\.DS_Store|test-results|playwright-report|htmlcov|coverage|\.next|\.turbo)(/|$)|\.(pyc|tmp|lock|lockdir|log)$'
malos=""
while IFS= read -r a; do
  [ -z "$a" ] && continue
  case "$a" in /*) abs="$a" ;; "~"*) abs="$HOME${a#\~}" ;; *) abs="$(pwd)/$a" ;; esac
  printf '%s' "$abs" | grep -qE "$tmp_re" && continue
  printf '%s' "$abs" | grep -qE "$regen_re" && continue
  malos="$malos $a"
done <<< "$args"
[ -z "$malos" ] && exit 0
jq -n --arg r "Nada se borra con rm (${malos# }). Muévelo a la papelera: ~/.claude/bin/papelera.sh <tema> <ruta…> (usa ../trash_deleted del repo si existe; si no, ~/.claude_trash/<tema>_<fecha>/). Solo se puede borrar lo temporal o regenerable (/tmp, caches, node_modules, __pycache__, dist…)." \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
