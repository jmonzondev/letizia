#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# PreToolUse (Bash). La sesión principal no commitea código de producto (DEC-U-049, rules/modelos.md): niega, solo en la principal
# (input sin `agent_id`), un `git commit` cuyo contenido trae código de producto que no procede de un commit ya existente. El código
# lo escribe un arreglador en su rama; la principal integra con `git cherry-pick` o `git merge` (esos commits ya existen).
# Spec: ~/Code/cuaderno/encargos/2026-10-20_principal_no_commitea/SPEC.md (criterios CA-PNC-01 a 58; el test los cita por id).
#  1. Qué orden mira (§3, §10b a, c, g, i): el `command` partido en segmentos por ; && || | & salto de línea ( ) $( y acento grave; una
#     cadena entre comillas es un argumento, pero `$(…)` y `…` abren segmento también dentro de comillas dobles (lo de dentro corre
#     antes). Los cuerpos de heredoc (<< fuera de comillas, nunca <<<) son datos. Un segmento es un commit si es `git [opciones]
#     commit`, o `cherry-pick|merge|revert|rebase --continue` (commit del índice sobre HEAD, §10b d). Un subcomando con $ o acento
#     grave no se puede resolver y se niega.
#  2. Dónde corre (§4, §10b h): `-C <dir>` (encadenados), si no el último `cd`/`pushd`, si no el `cwd`. Se admiten ~ y $HOME; otra
#     variable o sustitución no se puede resolver y se NIEGA (fallar abierto aquí sería la puerta de atrás). Un `cd` en una tubería o
#     tras && o || puede no correr: deja el directorio sin resolver. Si no es un repo git, pasa.
#  3. Qué va antes (§5, §10b i): solo `cd`/`pushd`, git de solo lectura, echo/printf/date/pwd/true/ls/cat/head/tail/grep/wc sin
#     escribir (2>&1 y /dev/null no escriben), y add/rm/mv/reset/restore --staged/checkout <ref> -- paths (se evalúan en §6) y
#     cherry-pick/revert -n (se ignoran). Cualquier otro segmento antes del commit niega: no se puede saber qué entra.
#  4. Qué entra (§6, §10b f, j) y qué se niega (§7, §10b e): los ficheros de código de producto (es_codigo_producto, la regla de
#     principal_no_escribe.sh) cuyo parche sin contexto (-U0, git patch-id --stable) no coincide con el de un commit de los últimos 30
#     días (los 60 más recientes por fichero). Las listas salen de git con -z. Con pathspecs entra también el índice.
#  5. Falla abierto (exit 0, sin salida) si el input no es JSON, no hay git/jq o git da un error inesperado.
# Límites conocidos (§9 y §10b): `git am` y `git commit-tree` commitean sin `git commit`; un squash de varios commits sobre un mismo
# fichero se niega aunque sea integración; un commit dentro de un script, `bash -c`, `eval`, un alias de git o `$(echo git)` no se ve;
# un fichero de código con un nombre que git entrecomilla (", \, control) nunca coincide.
# Con `/bin/bash` 3.2 de macOS: sin arrays asociativos, mapfile ni ${var,,}. Solo bash, git, jq, sed, awk y grep.
c="${CLAUDE_PROJECT_DIR:-/nonexistent}/.claude/hooks/$(basename "$0")"
[[ "$0" == "$HOME/.claude/hooks/"* && -x "$c" && ! "$c" -ef "$0" ]] && exit 0  # D3: la copia global se calla si el repo tiene la suya (no si «el repo» es ~)
export GIT_OPTIONAL_LOCKS=0
command -v git >/dev/null 2>&1 || exit 0
command -v jq >/dev/null 2>&1 || exit 0

deny() { jq -n --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'; exit 0; }
MOTIVO_MIXTA='Lanza `git commit` en una orden aparte: en esta misma orden hay escrituras antes del commit y no se puede saber qué entra.'
MOTIVO_DIR='No se puede resolver el directorio del commit: usa una ruta literal (se admiten `~` y `$HOME`).'
MOTIVO_RUTA='No se puede resolver una ruta de la orden (variable, sustitución o --pathspec-from-file): usa rutas literales para poder comprobar qué entra en el commit.'
MOTIVO_SUB='No se puede resolver el subcomando de git (variable o sustitución): escribe `git commit` literal.'
MOTIVO_MUCHOS='Demasiados ficheros para comprobar: integra con `git merge` o `git cherry-pick`, o parte el commit.'
VACIO=4b825dc642cb6eb9a060e54bf8d69288fbee4904   # árbol vacío de git
TAB=$'\t'; US=$'\037'

# ---- entrada: JSON de PreToolUse (agent_id solo dentro de un subagente)
input=$(cat)
# un U+D800 suelto (escapado) en la orden hace fallar a jq: solo si falla, se cambia por U+FFFD (si no, saldría abierto)
printf '%s' "$input" | jq empty 2>/dev/null || input=$(printf '%s' "$input" | LC_ALL=C sed -E 's/\\u[dD][89a-fA-F][0-9a-fA-F]{2}/\\ufffd/g')
parsed=$(printf '%s' "$input" | jq -r '(.agent_id // ""), (.cwd // ""), (.tool_input.command // "")' 2>/dev/null) || exit 0
agente=${parsed%%$'\n'*}; resto=${parsed#*$'\n'}; cwd=${resto%%$'\n'*}
case "$resto" in *$'\n'*) cmd=${resto#*$'\n'} ;; *) cmd="" ;; esac
[ -n "$agente" ] && exit 0
# sin «commit» ni «--continue» (buscados sin comillas ni barras: c'omm'it, c\ommit) no hay nada que mirar: la mayoría sale aquí
case "$cmd" in
  *commit*|*--con*) ;;
  *git*'$'*|*git*'`'*) ;;   # git co$(echo mmit): el subcomando se compone al correr (se niega más abajo si no se resuelve)
  *[\'\"\\]*)   # (con tr: ${cmd//…/} es cuadrático en bash 3.2 y una orden larga lo cuelga)
    plano=$(printf '%s' "$cmd" | tr -d "'\"\\\\\n")   # también el salto que continúa una barra final (git com\⏎mit)
    case "$plano" in *commit*|*--con*) ;; *) exit 0 ;; esac ;;
  *) exit 0 ;;
esac

# la regla de «código de producto» es la de la copia hermana (las copias de los repos viajan juntas), nunca la global por nombre;
# con la hermana antigua (sin la función) se cargaría su hook entero y todo pasaría en silencio: se avisa en vez de eso
hermana="$(dirname "$0")/principal_no_escribe.sh"
if [ ! -r "$hermana" ] || ! grep -q '^es_codigo_producto()' "$hermana"; then
  echo "principal_no_commitea.sh: $hermana no define es_codigo_producto (instala la copia nueva junto a este hook)" >&2; exit 1
fi
source "$hermana"

# ---- analizador léxico: una línea por segmento, en el orden en que corren («D<prof>␟<O|->␟<sep antes>␟<sep después>␟T<palabra>…»,
# ␟ = U+001F). Sin comillas en las palabras; una sustitución deja «$» en su sitio y su contenido sale antes como segmentos propios.
# O = escribe con una redirección (no cuentan N>&M ni /dev/null). Separadores: ^ inicio, ; n(salto) a(&&) o(||) |(tubería) b(&)
# ( ) y $ (fin). Los cuerpos de heredoc se saltan.
LEXER='
function endtok() {
  if (have) {
    if (want) {
      if (wanthd) { nhd++; hdw[nhd] = cur }
      else if (wantout && !((wantdup && cur ~ /^([0-9]+|-)$/) || cur == "/dev/null")) redir = 1
      want = 0; wanthd = 0; wantout = 0; wantdup = 0
    } else { n++; tk[n] = cur }
  }
  cur = ""; have = 0; qd = 0
}
function endseg(code,    line, k) {
  endtok()
  if (want && wantout) redir = 1
  want = 0; wanthd = 0; wantout = 0; wantdup = 0
  if (n > 0 || redir) {
    line = "D" L "\037" (redir ? "O" : "-") "\037" lastsep "\037" code
    for (k = 1; k <= n; k++) line = line "\037T" tk[k]
    print line
    lastsep = code
  } else if (code != "n") lastsep = code
  n = 0; redir = 0
}
function push(type,    k) {
  L++
  sty[L] = type; stq[L] = q; stn[L] = n; for (k = 1; k <= n; k++) stt[L, k] = tk[k]
  str[L] = redir; stc[L] = cur; sth[L] = have; stqd[L] = qd; stl[L] = lastsep
  stw[L] = want; stwo[L] = wantout; stwd[L] = wantdup; stwh[L] = wanthd
  n = 0; redir = 0; cur = ""; have = 0; qd = 0; want = 0; wantout = 0; wantdup = 0; wanthd = 0; q = 0; lastsep = "("
}
function pop(    k) {
  endseg(")")
  q = stq[L]; n = stn[L]; for (k = 1; k <= n; k++) tk[k] = stt[L, k]
  redir = str[L]; cur = stc[L]; have = sth[L]; qd = stqd[L]; lastsep = stl[L]
  want = stw[L]; wantout = stwo[L]; wantdup = stwd[L]; wanthd = stwh[L]
  L--
}
{ lines[++nl] = $0 }
END {
  # línea a línea y con los caracteres en un array (substr carácter a carácter sobre una orden larga es cuadrático en este awk)
  sq = "\047"; dq = "\042"; bs = "\\"; q = 0; L = 0; lastsep = "^"; nhd = 0
  for (ln = 1; ln <= nl; ln++) {
    s = lines[ln]; len = split(s, ch, ""); i = 1; cont = 0
    while (i <= len) {
      c = ch[i]; nx = (i < len) ? ch[i + 1] : ""
      if (q == 1) {   # hasta la comilla simple de cierre, de un trozo
        r = substr(s, i); j = index(r, sq)
        if (j == 0) { cur = cur r; i = len + 1 } else { cur = cur substr(r, 1, j - 1); q = 0; i += j }
        continue
      }
      if (q == 2) {
        if (c == bs) {
          if (nx == "") { cont = 1; i++; continue }
          if (nx == dq || nx == "$" || nx == "`" || nx == bs) { cur = cur nx; i += 2; continue }
          cur = cur c; i++; continue
        }
        if (c == dq) { q = 0; i++; continue }
        if (c == "$" && nx == "(" && ch[i + 2] != "(") { cur = cur "$"; i += 2; push("$"); continue }
        if (c == "`") { cur = cur "$"; i++; push("`"); continue }
        r = substr(s, i)   # hasta el siguiente carácter especial, de un trozo
        if (match(r, /["\\$`]/)) { if (RSTART == 1) { cur = cur c; i++ } else { cur = cur substr(r, 1, RSTART - 1); i += RSTART - 1 } }
        else { cur = cur r; i = len + 1 }
        continue
      }
      if (c == bs) { if (nx == "") { cont = 1; i++; continue }; cur = cur nx; have = 1; i += 2; continue }
      if (c == sq) { q = 1; have = 1; qd = 1; i++; continue }
      if (c == dq) { q = 2; have = 1; qd = 1; i++; continue }
      if (c == " " || c == "\t") { endtok(); i++; continue }
      if (c == "#" && !have) { i = len + 1; continue }
      if (c == "$" && nx == "(" && ch[i + 2] == "(") {   # $(( aritmética )): no corre nada
        p = 2; i += 3; while (i <= len && p > 0) { if (ch[i] == "(") p++; else if (ch[i] == ")") p--; i++ }
        cur = cur "$"; have = 1; continue
      }
      if (c == "$" && nx == "(") { cur = cur "$"; have = 1; i += 2; push("$"); continue }
      if (c == "`") { if (L > 0 && sty[L] == "`") { pop(); i++; continue }; cur = cur "$"; have = 1; i++; push("`"); continue }
      if (c == "(") { endtok(); push("("); i++; continue }
      if (c == ")") { if (L > 0 && sty[L] != "`") pop(); else endseg(")"); i++; continue }
      if (c == ";") { endseg(";"); i++; continue }
      if (c == "|") { if (nx == "|") { endseg("o"); i += 2 } else { endseg("|"); i++; if (ch[i] == "&") i++ }; continue }
      if (c == "&") {
        if (nx == "&") { endseg("a"); i += 2; continue }
        if (nx == ">") { i++; c = ">" } else { endseg("b"); i++; continue }
      }
      if (c == ">" || c == "<") {
        if (have && !qd && cur ~ /^[0-9]+$/) { cur = ""; have = 0 }
        endtok()
        op = c; i++
        while (i <= len && ch[i] ~ /[<>&|]/) { op = op ch[i]; i++ }
        want = 1
        if (op == "<<") { wanthd = 1; if (ch[i] == "-") i++ }
        else if (index(op, ">") > 0) { wantout = 1; wantdup = (substr(op, length(op), 1) == "&") }
        continue
      }
      cur = cur c; have = 1; i++
    }
    # fin de línea: una barra final la continúa; dentro de comillas es parte de la cadena; si no, separa
    if (cont) continue
    if (q != 0) { cur = cur " "; continue }
    endseg("n")
    if (nhd > 0) {   # los cuerpos de heredoc pendientes son datos: se saltan hasta su delimitador
      for (h = 1; h <= nhd; h++) { while (++ln <= nl) { t = lines[ln]; gsub(/^[ \t]+|[ \t]+$/, "", t); if (t == hdw[h]) break } }
      nhd = 0
    }
  }
  while (L > 0) pop()
  endseg("$")
}'

# ---- comparación: P = fichero de código que entra, E = su patch-id, C = patch-id de un commit que lo toca (los 60 más recientes por
# fichero, en el orden de git log). Imprime los ficheros cuyo parche no coincide con ninguno.
COMPARA='
  $1 == "P" { p[++np] = $3 }
  $1 == "E" { e[$3] = $2 }
  $1 == "C" { if (++cnt[$3] <= 60) c[$3 SUBSEP $2] = 1 }
  END { for (i = 1; i <= np; i++) { x = p[i]; if (!(x in e) || !((x SUBSEP e[x]) in c)) print x } }'

# ---- git y rutas
G() { git -c core.quotepath=off -c color.ui=false -c diff.noprefix=false -c diff.mnemonicprefix=false "$@"; }
GL() { G --literal-pathspecs "$@"; }   # para rutas que salen de git (nombres exactos, sin globs)
GDIFF=(--no-renames --no-ext-diff --no-textconv --no-color -U0)   # sin contexto: otro cambio cerca no estropea la coincidencia
# opciones largas de git commit (para resolver abreviaturas como hace git: --mess = --message)
LARGAS_ARG=" file author date message reedit-message reuse-message fixup squash trailer template cleanup pathspec-from-file "
LARGAS=" quiet verbose reset-author signoff no-signoff edit no-edit status no-status gpg-sign no-gpg-sign all include interactive patch only verify no-verify dry-run short branch ahead-behind no-ahead-behind porcelain long null amend no-post-rewrite untracked-files pathspec-file-nul allow-empty allow-empty-message$LARGAS_ARG"
larga() {  # larga <nombre>: LARGA = la opción larga de git commit que nombra (exacta o abreviatura única); vacía si ninguna o ambigua
  local o c=0
  LARGA=""
  case "$LARGAS" in *" $1 "*) LARGA=$1; return 0 ;; esac
  for o in $LARGAS; do case "$o" in "$1"*) LARGA=$o; c=$((c+1)) ;; esac; done
  [ $c -eq 1 ] || LARGA=""
  return 0
}

expande_dir() {  # expande_dir <base> <arg>: imprime la ruta absoluta (sin resolver enlaces); sale 1 si lleva variables o sustituciones
  local a="$2"
  case "$a" in
    '~') a="$HOME" ;;
    '~/'*) a="$HOME/${a:2}" ;;
    '$HOME') a="$HOME" ;;
    '$HOME/'*) a="$HOME/${a:6}" ;;
    '${HOME}') a="$HOME" ;;
    '${HOME}/'*) a="$HOME/${a:8}" ;;
  esac
  case "$a" in ''|*'$'*|*'`'*|'~'*) return 1 ;; esac
  case "$a" in /*) ;; *) a="$1/$a" ;; esac
  printf '%s' "$a"
}
dir_efectivo() {  # directorio donde corre el git del segmento: fija RD y RDST (0 bien, 1 no se puede resolver, 2 no existe)
  local a x ok=$dir_ok
  RDST=0; RD="$curdir"
  if [ "$gunres" -eq 1 ] || [ "$gitenv" -eq 1 ]; then RDST=1; return 0; fi
  for a in "${gC[@]}"; do
    case "$a" in /*|'~'*|'$HOME'*|'${HOME}'*) ok=1 ;; esac   # una ruta absoluta no depende del directorio actual
    if [ "$ok" -eq 0 ]; then RDST=1; return 0; fi
    x=$(expande_dir "$RD" "$a") || { RDST=1; return 0; }
    RD=$(cd "$x" 2>/dev/null && pwd -P) || { RDST=2; return 0; }
  done
  [ "$ok" -eq 0 ] && RDST=1
  return 0
}
tiene_arg() {  # tiene_arg <patrón>: alguno de GA casa con el patrón (glob de case)
  local x
  for x in "${GA[@]}"; do case "$x" in $1) return 0 ;; esac; done
  return 1
}
empaca() { local s="" x; for x in "$@"; do s="$s$US""T$x"; done; printf '%s' "$s"; }
desempaca() { local f k=0; AV=(); IFS=$US read -r -a f <<< "${1#$US}"; while [ $k -lt ${#f[@]} ]; do AV[${#AV[@]}]=${f[k]#T}; k=$((k+1)); done; }
con_variable() { local x; for x in "$@"; do case "$x" in -*) ;; *'$'*|*'`'*) return 0 ;; esac; done; return 1; }

# lee_z <raíz> <args de git…>: LISTA = las rutas de una salida -z, una por línea; las que llevan caracteres de control (no caben en
# una línea) y son código van directas a RAROS: no se pueden comparar y cuentan como no coincidentes
lee_z() {
  local top="$1" f; shift
  LISTA=""
  while IFS= read -r -d '' f; do
    case "$f" in *[[:cntrl:]]*) es_codigo_producto "$top/$f" && RAROS="$RAROS$(printf '%q' "$f")"$'\n' ;; *) LISTA="$LISTA$f"$'\n' ;; esac
  done < <(G "$@" 2>/dev/null)
  return 0
}
# ids_por_fichero <etiqueta>: lee git diff o git log -p y escribe «<etiqueta>␉<patch-id>␉<ruta>» por cada fichero parcheado
# (cada fichero de cada commit lleva su propia cabecera «commit <n>» para que patch-id los dé por separado; una cabecera
# entrecomillada por git no se lee y ese fichero no coincide)
ids_por_fichero() {
  local d mapa ids
  d=$(cat); [ -z "$d" ] && return 0
  mapa=$(printf '%s\n' "$d" | awk '/^diff --git / { n++; l = substr($0, 12); L = length(l); if (substr(l, 1, 1) != "\"" && (L - 5) % 2 == 0) print n "\t" substr(l, 3, (L - 5) / 2) }')
  ids=$(printf '%s\n' "$d" | awk '/^diff --git / { n++; printf "commit %040d\n", n } { print }' | git patch-id --stable) || return 1
  { printf '%s\n' "$ids" | awk 'NF { print "I\t" ($2 + 0) "\t" $1 }'; printf '%s\n' "$mapa" | awk 'NF { print "M\t" $0 }'; } | awk -F'\t' -v tag="$1" '
    $1 == "I" { id[$2] = $3 }
    $1 == "M" && ($2 in id) { print tag "\t" id[$2] "\t" $3 }'
}
add_entries() {  # add_entries <tipo> <rutas, una por línea>: apunta «tipo␉ruta» en ENTR (gana la última entrada de cada ruta)
  local l
  [ -z "$2" ] && return 0
  while IFS= read -r l; do [ -n "$l" ] && ENTR="$ENTR$1$TAB$l"$'\n'; done <<< "$2"
  return 0
}
dry_ruta() {  # dry_ruta <raíz> <tipo> <ruta de un add/rm --dry-run>: la apunta (las de caracteres de control, a RAROS si son código)
  case "$3" in *[[:cntrl:]]*) es_codigo_producto "$1/$3" && RAROS="$RAROS$(printf '%q' "$3")"$'\n'; return 0 ;; esac
  es_codigo_producto "$1/$3" || return 0
  add_entries "$2" "$3"
}

# ---- el commit: qué entra (§6) y qué se niega (§7)
eval_commit() {
  local k t n=${#GA[@]} all=0 amend=0 incl=0 dry=0 dd=0 chars ch nm val mode rev base lista_w m od acc ruta l
  local top kd kinds paths code ncode x D allp sinc nsinc ej msg cmp ids
  PATHS=()
  k=0
  while [ $k -lt $n ]; do
    t=${GA[k]}; k=$((k+1))
    if [ $dd -eq 1 ]; then PATHS[${#PATHS[@]}]=$t; continue; fi
    case "$t" in
      --) dd=1 ;;
      --*)   # el valor de una opción que lo lleva nunca se lee como opción (git commit -m --dry-run)
        nm=${t#--}; val=0; case "$nm" in *=*) nm=${nm%%=*}; val=1 ;; esac
        larga "$nm"
        case "$LARGA" in
          all) all=1 ;;
          amend) amend=1 ;;
          include) incl=1 ;;
          dry-run) dry=1 ;;
          patch|interactive) all=1 ;;   # interactivo: no se sabe qué hunks; se mira todo lo seguido (cota superior)
          pathspec-from-file) deny "$MOTIVO_RUTA" ;;
        esac
        if [ -n "$LARGA" ] && [ $val -eq 0 ]; then case "$LARGAS_ARG" in *" $LARGA "*) k=$((k+1)) ;; esac; fi ;;
      -?*)
        chars=${t#-}
        while [ -n "$chars" ]; do
          ch=${chars:0:1}; chars=${chars:1}
          case "$ch" in
            a|p) all=1 ;;
            i) incl=1 ;;
            m|F|C|c|t) [ -z "$chars" ] && k=$((k+1)); chars="" ;;
            u|S) chars="" ;;
          esac
        done ;;
      *) PATHS[${#PATHS[@]}]=$t ;;
    esac
  done
  [ $dry -eq 1 ] && return 0
  [ -n "$dirty" ] && deny "$MOTIVO_MIXTA"
  if [ $all -eq 1 ]; then mode=all; elif [ ${#PATHS[@]} -gt 0 ]; then mode=paths; else mode=cached; fi
  con_variable "${PATHS[@]}" && deny "$MOTIVO_RUTA"
  if [ $amend -eq 1 ]; then rev=HEAD~1; else rev=HEAD; fi
  base=$(git -C "$RD" rev-parse --verify -q "$rev^{commit}" 2>/dev/null) || base=$VACIO
  top=$(git -C "$RD" rev-parse --show-toplevel 2>/dev/null) || return 0
  ENTR=""; RAROS=""; lista_w=""
  case $mode in
    cached) lee_z "$top" -C "$RD" diff --cached --name-only -z --no-renames "$base"; add_entries c "$LISTA" ;;
    all) lee_z "$top" -C "$RD" diff --name-only -z --no-renames "$base"; lista_w=$LISTA ;;
    paths)   # con pathspecs entra también lo que ya estuviera en el índice (§10b j)
      lee_z "$top" -C "$RD" diff --cached --name-only -z --no-renames "$base"; add_entries c "$LISTA"
      lee_z "$top" -C "$RD" diff --name-only -z --no-renames "$base" -- "${PATHS[@]}"; lista_w=$LISTA ;;
  esac
  # lo que dejarían los add/rm/mv/checkout anteriores de la misma orden, en el mismo repo
  for ((m=0; m<nops; m++)); do
    [ "${OPT[m]}" = "$top" ] || continue
    [ "${OPU[m]}" = 1 ] && deny "$MOTIVO_RUTA"
    desempaca "${OPA[m]}"; od=${OPD[m]}
    case "${OPK[m]}" in
      add)
        while IFS= read -r l; do
          case "$l" in "add '"*"'") acc=add; ruta=${l#add \'} ;; "remove '"*"'") acc=remove; ruta=${l#remove \'} ;; *) continue ;; esac
          ruta=${ruta%\'}
          [ -z "$ruta" ] && continue
          case "$ruta" in *[[:cntrl:]]*) dry_ruta "$top" n "$ruta"; continue ;; esac
          es_codigo_producto "$top/$ruta" || continue
          if [ "$acc" = add ] && ! GL -C "$top" ls-files --error-unmatch -- "$ruta" >/dev/null 2>&1; then add_entries n "$ruta"   # código nuevo sin commit
          else add_entries w "$ruta"; fi
        done <<< "$(G -C "$od" add --dry-run "${AV[@]}" 2>/dev/null)" ;;
      rm)   # un borrado a mano de código no coincide con nada (se mira abajo)
        while IFS= read -r l; do
          case "$l" in "rm '"*"'") ruta=${l#rm \'}; ruta=${ruta%\'}; dry_ruta "$top" n "$ruta" ;; esac
        done <<< "$(G -C "$od" rm --dry-run -f "${AV[@]}" 2>/dev/null)" ;;
      mv)
        for x in "${AV[@]}"; do
          case "$x" in -*) continue ;; /*) ruta=$(norm "$x") ;; *) ruta=$(norm "$od/$x") ;; esac
          dry_ruta "$top" n "${ruta#"$top"/}"
        done ;;
      checkout)
        kd=${AV[0]}; paths=("${AV[@]:2}")
        lee_z "$top" -C "$od" ls-tree -r -z --name-only --full-name "$kd" -- "${paths[@]}"
        add_entries "k:$kd" "$LISTA" ;;
    esac
  done
  add_entries w "$lista_w"
  ENTR=$(printf '%s' "$ENTR" | awk -F'\t' 'NF >= 2 { if (!($2 in k)) o[++c] = $2; k[$2] = $1 } END { for (i = 1; i <= c; i++) print k[o[i]] "\t" o[i] }')
  # solo cuenta el código de producto
  code=""; ncode=0
  while IFS=$'\t' read -r kd ruta; do
    [ -z "$ruta" ] && continue
    es_codigo_producto "$top/$ruta" || continue
    code="$code$kd$TAB$ruta"$'\n'; ncode=$((ncode+1))
  done <<< "$ENTR"
  [ -n "$RAROS" ] && ncode=$((ncode + $(printf '%s' "$RAROS" | awk 'END { print NR }')))
  [ $ncode -eq 0 ] && return 0
  [ $ncode -gt 100 ] && deny "$MOTIVO_MUCHOS"
  # parche de cada fichero que entra (por tipo de origen) y de los commits que lo tocan; coincide si algún patch-id es igual
  sinc="$RAROS"; ENT=""; allp=()
  kinds=$(printf '%s' "$code" | awk -F'\t' '!s[$1]++ { print $1 }')
  while IFS= read -r kd; do
    [ -z "$kd" ] && continue
    paths=()
    while IFS=$'\t' read -r x ruta; do
      [ "$x" = "$kd" ] || continue
      if [ "$kd" = n ]; then sinc="$sinc$ruta"$'\n'; else paths[${#paths[@]}]=$ruta; allp[${#allp[@]}]=$ruta; fi
    done <<< "$code"
    [ "$kd" = n ] && continue
    case "$kd" in
      c) D=$(GL -C "$top" diff --cached "${GDIFF[@]}" "$base" -- "${paths[@]}") || exit 0 ;;
      w) D=$(GL -C "$top" diff "${GDIFF[@]}" "$base" -- "${paths[@]}") || exit 0 ;;
      k:*) D=$(GL -C "$top" diff "${GDIFF[@]}" "$base" "${kd#k:}" -- "${paths[@]}") || exit 0 ;;
    esac
    ids=$(printf '%s\n' "$D" | ids_por_fichero E) || exit 0
    ENT="$ENT$ids"$'\n'
  done <<< "$kinds"
  CAND=""
  if [ ${#allp[@]} -gt 0 ]; then
    CAND=$(set -o pipefail; GL -C "$top" log --all --full-history --since=30.days "${GDIFF[@]}" -p --format= -- "${allp[@]}" | ids_por_fichero C) || exit 0
    cmp=$({ printf '%s' "$code" | awk -F'\t' '$1 != "n" { print "P\t-\t" $2 }'; printf '%s\n' "$ENT"; printf '%s\n' "$CAND"; } | awk -F'\t' "$COMPARA")
    sinc="$sinc$cmp"$'\n'
  fi
  sinc=$(printf '%s' "$sinc" | awk 'NF')
  [ -z "$sinc" ] && return 0
  nsinc=$(printf '%s\n' "$sinc" | awk 'END { print NR }'); ej=$(printf '%s\n' "$sinc" | sed -n '1p')
  msg="La sesión principal no commitea código de producto ($nsinc fichero(s), p. ej. \`$ej\`): el código lo escribe un arreglador en su rama y la principal integra con \`git cherry-pick\` o \`git merge\` (rules/modelos.md, DEC-U-049)."
  deny "$msg"
}
trata_commit() {  # un commit (o un --continue): dónde corre, si es un repo y qué entra
  dir_efectivo
  [ $RDST -eq 1 ] && deny "$MOTIVO_DIR"
  [ $RDST -eq 2 ] && return 0
  git -C "$RD" rev-parse --show-toplevel >/dev/null 2>&1 || return 0   # no es un repo git: pasa
  eval_commit
  return 0
}

# ---- registro de un add/rm/mv/checkout anterior al commit (se evalúa cuando llega el commit)
registra() {  # registra <tipo>
  local tipo="$1" x top2 u=0
  if [ "$tipo" = add ] || [ "$tipo" = rm ]; then
    for x in "${GA[@]}"; do case "$x" in -n|--dry-run) return 0 ;; esac; done
  fi
  if [ "$tipo" = add ]; then
    for x in "${GA[@]}"; do case "$x" in -p|--patch|-i|--interactive|-e|--edit) dirty=1; return 0 ;; esac; done
  fi
  if [ "$tipo" = checkout ]; then
    case "${GA[0]}" in -*|'') dirty=1; return 0 ;; esac
    if [ "${GA[1]}" != "--" ] || [ ${#GA[@]} -lt 3 ]; then dirty=1; return 0; fi
  fi
  dir_efectivo
  if [ $RDST -eq 1 ]; then dirty=1; return 0; fi
  [ $RDST -eq 2 ] && return 0
  top2=$(git -C "$RD" rev-parse --show-toplevel 2>/dev/null) || return 0
  con_variable "${GA[@]}" && u=1
  OPK[nops]=$tipo; OPT[nops]=$top2; OPD[nops]=$RD; OPU[nops]=$u; OPA[nops]=$(empaca "${GA[@]}"); nops=$((nops+1))
}

# ---- un segmento
procesa_cd() {  # procesa_cd <índice de cd|pushd en W>
  local i=$(($1+1)) a target="" x
  # en una tubería o tras && / || el cd puede no correr (o corre en otro proceso): el directorio queda sin resolver (§10b h)
  case "$sprev" in a|o|"|") dir_ok=0; return 0 ;; esac
  case "$snext" in "|"|b) dir_ok=0; return 0 ;; esac
  while [ $i -lt ${#W[@]} ]; do
    a=${W[i]}
    case "$a" in -P|-L|-e|-@|--) ;; *) target=$a; break ;; esac
    i=$((i+1))
  done
  if [ -z "$target" ] || [ "$target" = "-" ]; then dir_ok=0; return 0; fi
  x=$(expande_dir "$curdir" "$target") || { dir_ok=0; return 0; }
  case "$target" in /*|'~'*|'$HOME'*|'${HOME}'*) ;; *) [ "$dir_ok" -eq 0 ] && return 0 ;; esac   # relativo desde un directorio desconocido
  x=$(cd "$x" 2>/dev/null && pwd -P) || { dir_ok=0; return 0; }
  curdir=$x; dir_ok=1
}
procesa_git() {  # procesa_git <índice de git en W>
  local j=$(($1+1)) n=${#W[@]} t sub="" x pos
  gC=(); gunres=0
  while [ $j -lt $n ]; do
    t=${W[j]}
    case "$t" in
      -C) [ $((j+1)) -lt $n ] && gC[${#gC[@]}]=${W[j+1]}; j=$((j+2)) ;;
      -c) j=$((j+2)) ;;
      --git-dir|--work-tree|--namespace|--super-prefix|--config-env|--attr-source) gunres=1; j=$((j+2)) ;;
      --git-dir=*|--work-tree=*) gunres=1; j=$((j+1)) ;;
      -*) j=$((j+1)) ;;
      *) break ;;
    esac
  done
  [ $j -lt $n ] && sub=${W[j]}
  case "$sub" in *'$'*|*'`'*) deny "$MOTIVO_SUB" ;; esac   # git $'commit', git commit${u}, git $(echo commit)…
  GA=(); j=$((j+1))
  while [ $j -lt $n ]; do GA[${#GA[@]}]=${W[j]}; j=$((j+1)); done
  if [ "$sub" = commit ]; then trata_commit; return 0; fi
  case "$sub" in
    cherry-pick|merge|revert|rebase)   # --continue cierra con un commit del índice sobre HEAD (§10b d)
      if tiene_arg '--con*'; then GA=(); trata_commit; return 0; fi ;;
  esac
  [ "$flag" = O ] && { dirty=1; return 0; }
  case "$sub" in
    add|rm|mv|checkout) registra "$sub" ;;
    reset)
      if tiene_arg '--soft' || tiene_arg '--hard' || tiene_arg '--keep' || tiene_arg '--merge'; then dirty=1; return 0; fi
      pos=""; for x in "${GA[@]}"; do case "$x" in --) break ;; -*) ;; *) pos=$x; break ;; esac; done
      if [ -n "$pos" ] && [ "$pos" != HEAD ] && ! tiene_arg '--'; then dirty=1; fi ;;   # mueve HEAD o es ambiguo
    restore)
      if tiene_arg '--staged' || tiene_arg '-S'; then
        if tiene_arg '-W' || tiene_arg '--worktree' || tiene_arg '--source*' || tiene_arg '-s'; then dirty=1; fi
      else dirty=1; fi ;;
    cherry-pick|revert)
      tiene_arg '-n' || tiene_arg '--no-commit' || tiene_arg '-[!-]*n*' || dirty=1 ;;   # -n trae el cambio sin commitear: se ignora
    status|diff|log|show|rev-parse|remote|fetch|ls-files|describe) tiene_arg '--output*' && dirty=1 ;;
    branch) tiene_arg '-[dDmMcCf]*' && dirty=1; tiene_arg '--delete*' && dirty=1; tiene_arg '--move' && dirty=1; tiene_arg '--copy' && dirty=1; tiene_arg '--force' && dirty=1 ;;
    stash|worktree) [ "${GA[0]}" = list ] || dirty=1 ;;
    tag) if [ ${#GA[@]} -gt 0 ] && ! tiene_arg '-l' && ! tiene_arg '--list'; then dirty=1; fi ;;
    config) tiene_arg '--get*' || tiene_arg '--list' || tiene_arg '-l' || dirty=1 ;;
    '') ;;   # git --version, git --help…
    *) dirty=1 ;;
  esac
  return 0
}
procesa() {
  local i=0 n=${#W[@]} t cmd re='^[A-Za-z_][A-Za-z0-9_]*='
  gitenv=0
  while [ $i -lt $n ]; do
    t=${W[i]}
    case "$t" in
      then|do|else|elif|if|while|until|'{'|'!') i=$((i+1)) ;;
      time|exec|xargs|sudo|command|nohup|builtin|env) i=$((i+1)); while [ $i -lt $n ] && [ "${W[i]:0:1}" = "-" ]; do i=$((i+1)); done ;;
      *)
        if [[ $t =~ $re ]]; then
          case "${t%%=*}" in GIT_DIR|GIT_WORK_TREE|GIT_INDEX_FILE|GIT_COMMON_DIR|GIT_OBJECT_DIRECTORY) gitenv=1 ;; esac
          i=$((i+1))
        else break; fi ;;
    esac
  done
  if [ $i -ge $n ]; then [ "$flag" = O ] && dirty=1; return 0; fi
  cmd=${W[i]##*/}
  case "$cmd" in
    git) procesa_git "$i" ;;
    cd|pushd) procesa_cd "$i" ;;
    popd) dir_ok=0 ;;
    echo|printf|date|pwd|true|ls|cat|head|tail|grep|wc) [ "$flag" = O ] && dirty=1 ;;
    *) dirty=1 ;;
  esac
  return 0
}

# ---- recorrido de los segmentos, en el orden en que corren
segs=$(printf '%s\n' "$cmd" | awk "$LEXER")
[ -z "$segs" ] && exit 0
[ -z "$cwd" ] && cwd="$PWD"
curdir=$(cd "$cwd" 2>/dev/null && pwd -P) || exit 0
dir_ok=1; dirty=""; prev_depth=0; nops=0; gitenv=0; gunres=0; gC=(); GA=(); OPK=(); OPT=(); OPD=(); OPU=(); OPA=(); SVD=(); SVO=()
while IFS= read -r linea <&3; do
  IFS=$US read -r -a f <<< "$linea"
  depth=${f[0]#D}; flag=${f[1]}; sprev=${f[2]}; snext=${f[3]}
  W=(); k=4
  while [ $k -lt ${#f[@]} ]; do W[${#W[@]}]=${f[k]#T}; k=$((k+1)); done
  # ámbito: un cd dentro de ( ), $( ) o `…` no sale de ahí
  if [ "$depth" -gt "$prev_depth" ]; then
    k=$((prev_depth+1)); while [ $k -le "$depth" ]; do SVD[k]=$curdir; SVO[k]=$dir_ok; k=$((k+1)); done
  elif [ "$depth" -lt "$prev_depth" ]; then
    curdir=${SVD[depth+1]}; dir_ok=${SVO[depth+1]}
  fi
  prev_depth=$depth
  procesa
done 3<<< "$segs"
exit 0
