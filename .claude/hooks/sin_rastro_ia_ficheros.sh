#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# PreToolUse (Write|Edit|MultiEdit|NotebookEdit). Niega escribir rastro de IA en ficheros que no sean de configuración
# de la IA: «Generated with/by Claude», «Co-Authored-By», «Claude Code», «Anthropic», «Claude <modelo>».
# Exentos: .claude/, CLAUDE.md, taller/, ~/.claude*, scratchpad, encargos, memoria.
[[ "$0" == "$HOME/.claude/hooks/"* && -x "${CLAUDE_PROJECT_DIR:-/nonexistent}/.claude/hooks/$(basename "$0")" ]] && exit 0  # D3: la copia global se calla si el repo tiene la suya
input=$(cat)
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' 2>/dev/null)
[ -z "$path" ] && exit 0
case "$path" in
  *"/.claude/"*|*"/.claude-a/"*|*"/.claude_trash/"*|*"CLAUDE.md"|*"CLAUDE.local.md"|*"/taller/"*|*"/scratchpad/"*|*"/encargos/"*|*"/memory/"*|*"/.claude.json"*|*"/cuaderno/"*|*"/.claude/plans/"*) exit 0 ;;
esac
texto=$(printf '%s' "$input" | jq -r '[.tool_input.content, .tool_input.new_string, (.tool_input.edits[]?.new_string), .tool_input.new_source] | map(select(. != null)) | join("\n")' 2>/dev/null)
[ -z "$texto" ] && exit 0
if printf '%s' "$texto" | grep -qiE 'co-authored-by|generated[[:space:]]+(with|by)[[:space:]]+claude|claude[[:space:]]+code|anthropic|claude[[:space:]]+(opus|sonnet|haiku|fable)'; then
  jq -n --arg p "$path" --arg r "Rastro de IA en el contenido que vas a escribir en $path (Generated with Claude, Co-Authored-By, Claude Code, Anthropic o nombre de modelo). El producto no menciona la IA: quítalo." \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
fi
exit 0
