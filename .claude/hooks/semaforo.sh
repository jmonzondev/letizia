#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# PreToolUse (Agent|Workflow). Tope adaptativo: antes de lanzar un agente mide la memoria libre del Mac y las sesiones de
# Claude vivas. Si no hay sitio, niega ESE lanzamiento con el motivo; el orquestador espera o le propone al usuario por chat qué
# cerrar (nunca se cierra nada solo). Umbrales (ajustables por entorno): SEMAFORO_MIN_LIBRE_MB (1500), SEMAFORO_MAX_SESIONES (8).
# Nota: los subagentes corren dentro del proceso de su sesión, así que lo que se cuenta son sesiones (interactivas y -p), no agentes.
[[ "$0" == "$HOME/.claude/hooks/"* && -x "${CLAUDE_PROJECT_DIR:-/nonexistent}/.claude/hooks/$(basename "$0")" ]] && exit 0  # D3: la copia global se calla si el repo tiene la suya
input=$(cat)
min_libre=${SEMAFORO_MIN_LIBRE_MB:-1500}; max_ses=${SEMAFORO_MAX_SESIONES:-8}
pag=$(sysctl -n hw.pagesize 2>/dev/null || echo 16384)
vs=$(vm_stat 2>/dev/null)
libres=$(printf '%s' "$vs" | awk -v p="$pag" '/Pages free|Pages inactive|Pages speculative|Pages purgeable/ {gsub("\\.","",$NF); s+=$NF} END {printf "%d", s*p/1048576}')
swap=$(sysctl -n vm.swapusage 2>/dev/null | sed -nE 's/.*used = ([0-9.,]+)M.*/\1/p' | tr ',' '.' | cut -d. -f1)
swap_total=$(sysctl -n vm.swapusage 2>/dev/null | sed -nE 's/.*total = ([0-9.,]+)M.*/\1/p' | tr ',' '.' | cut -d. -f1)
# sesiones vivas: procesos claude que no son el daemon ni sus ayudantes de terminal
sesiones=$(ps -axo command | grep -E '^(/[^ ]*/)?claude(\.exe)?( |$)' | grep -vcE 'bg-pty-host|bg-spare|daemon run|mcp |--version')
motivo=""
if [ "${libres:-0}" -lt "$min_libre" ]; then motivo="memoria libre ${libres} MB (mínimo ${min_libre}); swap ${swap:-?}/${swap_total:-?} MB"; fi
if [ "${sesiones:-0}" -gt "$max_ses" ]; then motivo="${motivo:+$motivo; }sesiones de claude vivas: $sesiones (techo $max_ses)"; fi
[ -z "$motivo" ] && exit 0
jq -n --arg r "Semáforo en rojo: $motivo. No lances más agentes ahora: espera a que termine uno, o propón al usuario por chat qué cerrar (VS Code, Chrome, otra sesión). Nada se cierra solo. Vuelve a intentarlo después." \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
