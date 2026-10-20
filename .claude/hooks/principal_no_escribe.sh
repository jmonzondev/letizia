#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# PreToolUse (Edit|Write|MultiEdit|NotebookEdit). La sesión principal no edita código de producto (rules/modelos.md): el código lo
# escribe un arreglador o un guion (construir y su vuelta reparar) y la principal lee el diff e integra.
#  - Principal o subagente: Claude Code pone `agent_id` en el input solo cuando el hook salta dentro de un subagente, un agente de un
#    guion o un compañero de equipo; sin `agent_id` es la principal (también una sesión `claude -p` o `--agent`).
#  - Código de producto: extensión .py .ts .tsx .js .jsx .mjs .cjs .mts .cts .sql .sh .go .rs .html .css .scss .json .yaml .yml .toml .astro .php .vue .svelte, o nombre Dockerfile, Dockerfile.* o Procfile, en un fichero de un repo
#    git cuya ruta dentro del repo no pasa por docs/ ni .claude/, y el repo no es el cuaderno (ni sus worktrees) ni ~/.claude. Los
#    worktrees de los agentes (.claude/worktrees/…) son repos por sí mismos, así que su código cuenta. Fuera de un repo (scratchpad,
#    /tmp, ~/.cache de los bots de NJ) no es producto y pasa.
#  - Por Bash no mira: la regla vale igual. (El `git commit` de la principal lo mira principal_no_commitea.sh, DEC-U-049.)
#  - Una sola regla de «código de producto»: la función es_codigo_producto <ruta_absoluta> (sale 0 si lo es). Si se carga con `source`
#    (principal_no_commitea.sh, desde su carpeta), solo define las funciones y vuelve: no lee la entrada ni sale.
c="${CLAUDE_PROJECT_DIR:-/nonexistent}/.claude/hooks/$(basename "$0")"
[[ "$0" == "$HOME/.claude/hooks/"* && -x "$c" && ! "$c" -ef "$0" ]] && exit 0  # D3: la copia global se calla si el repo tiene la suya (no si «el repo» es ~)
niega() { jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"La sesión principal no edita código: encárgalo a construir/reparar o a un arreglador; en XS y configuración, a un ejecutor con instrucción exacta (rules/modelos.md)."}}'; exit 0; }
# carpeta existente más cercana (el fichero o su carpeta pueden ser nuevos), resuelta sin enlaces; el tramo que aún no existe
# no tiene enlaces, así que sus . y .. se quitan a mano y se vuelve a buscar (si no, a/nueva/../../docs/../a.py pasaría por docs/)
norm() ( set -f; IFS=/; out=(); for x in $1; do case "$x" in ""|.) ;; ..) [ ${#out[@]} -gt 0 ] && unset "out[$((${#out[@]}-1))]" ;; *) out+=("$x") ;; esac; done; printf '/%s' "${out[@]}" )
ubica() {  # (sin dirname: es un fork por llamada)
  case "$1" in */*) d="${1%/*}" ;; *) d=. ;; esac; [ -z "$d" ] && d=/
  resto="${1##*/}"
  while [ ! -d "$d" ] && [ "$d" != "/" ]; do resto="${d##*/}/$resto"; case "$d" in */*) d="${d%/*}" ;; *) d=. ;; esac; [ -z "$d" ] && d=/; done
  real=$(cd "$d" 2>/dev/null && pwd -P)
}
# veredicto de la carpeta de un fichero con extensión (o nombre) de producto: sale 0 si cuenta como código de producto
_ecp_veredicto() {
  local p="$1" d resto real info top comun prefijo dentro
  ubica "$p" || return 1
  case "/$resto/" in */./*|*/../*) ubica "$(norm "$real/$resto")" || return 1 ;; esac
  # raíz, carpeta común y tramo dentro del repo los da git, con las mayúsculas del disco (APFS no las distingue y `pwd -P` conserva las tecleadas)
  info=$(git -C "$real" rev-parse --show-toplevel --path-format=absolute --git-common-dir --show-prefix 2>/dev/null) || {
    # un git sin --path-format (< 2.31): solo raíz y tramo; sin carpeta común no hay exención del cuaderno (cuenta como código)
    top=$(git -C "$real" rev-parse --show-toplevel 2>/dev/null) || return 1
    info="$top"$'\n\n'"$(git -C "$real" rev-parse --show-prefix 2>/dev/null)"
  }
  { IFS= read -r top; IFS= read -r comun; IFS= read -r prefijo; } <<< "$info"
  [ -z "$top" ] && return 1
  [ -z "$_ecp_casa" ] && _ecp_casa=$(cd "$HOME" && pwd -P)
  case "$top/" in "$_ecp_casa/.claude/") return 1 ;; esac
  case "$comun" in "$_ecp_casa/Code/cuaderno/.git") return 1 ;; esac
  dentro="$prefijo$resto"
  case "/$dentro" in */docs/*|*/.claude/*) return 1 ;; esac
  return 0
}
_ecp_dir="?"; _ecp_val=1; _ecp_casa=""   # memoria: los ficheros de una misma carpeta comparten veredicto (el último componente nunca es docs/ ni .claude/)
es_codigo_producto() {  # es_codigo_producto <ruta_absoluta>: sale 0 si es código de producto, 1 si no
  local p="$1" b ext d
  while [ "$p" != "/" ] && [ "${p%/}" != "$p" ]; do p="${p%/}"; done
  b="${p##*/}"; ext=""; case "$b" in *.*) ext="${b##*.}" ;; esac
  case "$ext" in *[!A-Za-z0-9]*) ext="" ;; esac
  case "$ext" in *[[:upper:]]*) ext=$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]') ;; esac   # (no [A-Z]: en locales UTF-8 casa con minúsculas)
  case "$ext" in py|ts|tsx|js|jsx|mjs|cjs|mts|cts|sql|sh|go|rs|html|css|scss|json|yaml|yml|toml|astro|php|vue|svelte) ;; *) case "$b" in Dockerfile|Dockerfile.*|Procfile) ;; *) return 1 ;; esac ;; esac
  case "$p" in *[[:cntrl:]]*) return 0 ;; esac  # un salto de línea en una carpeta («docs⏎/») se lo comería dirname
  d="${p%/*}"
  [ "$d" = "$_ecp_dir" ] && return "$_ecp_val"
  _ecp_veredicto "$p"; _ecp_val=$?; _ecp_dir="$d"
  return "$_ecp_val"
}
[[ "${BASH_SOURCE[0]}" != "$0" ]] && return 0  # cargado con source: solo las funciones
input=$(cat)
# un U+D800 suelto (escapado) en el contenido hace fallar a jq y dejaría pasar la edición: solo si falla, se cambia por U+FFFD
printf '%s' "$input" | jq empty 2>/dev/null || input=$(printf '%s' "$input" | LC_ALL=C sed -E 's/\\u[dD][89a-fA-F][0-9a-fA-F]{2}/\\ufffd/g')
[ -n "$(printf '%s' "$input" | jq -r '.agent_id // empty' 2>/dev/null)" ] && exit 0
p=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' 2>/dev/null)
[ -z "$p" ] && exit 0
case "$p" in /*) ;; *) p="$(printf '%s' "$input" | jq -r '.cwd // empty')/$p" ;; esac
es_codigo_producto "$p" && niega
exit 0
