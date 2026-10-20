<!-- copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia -->
# Modelos, esfuerzo, ultracode y workflows

> Política vigente desde 2026-10-11, puesta al día el 2026-10-16 (`DEC-U-035` a `044`) y el 2026-10-20 (la principal no escribe código;
> `arreglador` y `ejecutor`, en Opus; `DEC-U-048`, `049` y `050`). Se revisa con `/uso` al cerrar cada tanda y,
> como mínimo, una vez al mes. Fable está dentro de la suscripción: lo que gasta es cupo, no dinero, y pesa unas 2,5 veces Opus. Para
> el usuario cuenta el resultado antes que el gasto.

## Quién hace qué

| Papel | Modelo · esfuerzo | Qué hace |
|---|---|---|
| Sesión principal | **Fable · xhigh · 1M** | Habla con el usuario; define specs y tests con él; decide diseño y arquitectura; planifica tandas; redacta encargos; orquesta e integra leyendo cada diff. **No edita código de producto**: toda edición va por `construir` (y su vuelta `reparar`) o, como mínimo, por un `arreglador` (en XS, un `ejecutor`); la principal lee el diff e integra |
| `auditor` | Fable · max (corre sin el usuario, `DEC-U-038`) | Última revisión antes de desplegar dinero o seguridad; desatascar lo que falló dos veces |
| `explorador`, `documentador`, `revisor` (y `revisor-dinero` en NJ) | **Opus · xhigh · 1M** | Explorar y verificar código, tallar, documentar, revisar diffs de dinero, estados, permisos y seguridad; implementar dinero |
| `arreglador`, `ejecutor` (cuando escriben código) | **Opus 5.5 · xhigh (1M el arreglador)** | Escribir el código que Fable y Opus han definido: arreglos e implementaciones con spec y test (`arreglador`, también en `construir` y `reparar`) y los cambios XS con instrucción exacta (`ejecutor`, con `isolation: worktree` en la llamada y un commit que la principal integra) |
| `ejecutor` con `model: sonnet` en la llamada | **Sonnet · xhigh** | Lo que no es código: textos, mover ficheros, lanzar puertas y resumir sus logs, y los pasos de `cerrar` que ya lo fijan (recuento, clasificar y ficha) |
| Haiku | Solo dentro de guiones, con modelo y esfuerzo explícitos | Solo pasos mecánicos de los guiones con salida comprobada por esquema o script (clasificar con categorías cerradas, transcribir filas); nunca lee código, filtra, resume lo que decide el paso siguiente, decide ni escribe código (`DEC-U-036`) |

- Lo que no tenga spec y test no se delega: vuelve a sesión de diseño con el usuario. En XS y en datos o configuración, la instrucción
  exacta (ruta, texto antes y después) hace de spec y la puerta del contrato hace de test.
- La sesión principal no edita código ni en XS ni «para cerrar a mano»: dentro de `construir`, las refutaciones van a su vuelta
  `reparar`; las notas, y lo que se refute fuera de `construir`, a un `arreglador`.
  Lo niega el hook `principal_no_escribe.sh` en `Edit`, `Write`, `MultiEdit` y `NotebookEdit` sin `agent_id` (la principal): código es
  `.py .ts .tsx .js .jsx .mjs .cjs .mts .cts .sql .sh .go .rs .html .css .scss .json .yaml .yml .toml .astro .php .vue .svelte` y los nombres `Dockerfile`, `Dockerfile.*` y `Procfile`, dentro de un repo git, fuera del cuaderno, `docs/`,
  `.claude/` (sus worktrees sí cuentan), `~/.claude/` (los repos que cuelgan de él, como `pruebas/repo_demo`, sí cuentan) y `*.md`.
  Los datos y la configuración con esas extensiones también: van por `ejecutor` con instrucción exacta. Por `Bash`, `principal_no_commitea.sh` niega el `git commit` de la principal cuyo contenido trae código de producto que no
  coincide por patch-id con un commit existente; `cherry-pick`, `merge`, docs, specs y `.claude/` pasan (`DEC-U-049`).
- Si un `cherry-pick` choca en código al integrar, la principal lo aborta (`git cherry-pick --abort`) y el ítem vuelve a un
  `arreglador`, que lo rehace en una rama nueva desde la base ya integrada; la principal integra de ahí (ver AF-19). Los conflictos en
  `.md` y specs los resuelve la principal.
- Excepción vigente: el arreglo dirigido de `especificar` (`DEC-U-043`) reescribe tests con Sonnet en un agente sin tipo; pendiente de
  revisar (`PENDIENTES.md` §9).
- Atasco repetido (dos veces en el mismo punto): el orquestador propone al usuario subir de modelo (Sonnet → Opus → Fable)
  o `/effort max` para ese turno (ver «Esfuerzo max»).
- Ningún agente hereda el modelo de la sesión: cada uno lleva `model` y `effort` en su frontmatter; una llamada a un agente
  integrado (Plan, general-purpose, fork) lleva `model` siempre. Lo vigila el hook `modelo_explicito.sh`; la red es
  `CLAUDE_CODE_SUBAGENT_MODEL=opus`. `CLAUDE_CODE_EFFORT_LEVEL` no se fija nunca.

## Talla antes de encargar (`/tallar`)

| Talla | Qué es | Quién |
|---|---|---|
| XS | menos de 15 min, un fichero, sin riesgo | `ejecutor` con instrucción exacta |
| S | menos de 1 h, pocos ficheros, spec y test claros | `arreglador` |
| M | 1 a 3 h, varios ficheros o un módulo | `arreglador` si está definido; si toca dinero o permisos, `revisor-dinero`; `revisor` después |
| L | más, o decisión del usuario, migración, cambio de API | La sesión principal (Fable) la diseña con el usuario y la parte en S/M |

La talla la mide `explorador` y se apunta en `~/.claude/uso/estimaciones.tsv` para compararla luego con `/uso`.

## Ultracode y workflows (`DEC-U-035`)

- Son la forma normal de trabajar en todos los repos, no una excepción que se pide en el prompt. Hay clave en `settings.json`:
  `ultracode: true` (cada sesión arranca con ultracode; no cambia el esfuerzo de la sesión) y `workflowSizeGuideline: "unrestricted"`
  (sin tope de agentes: el workflow se dimensiona a la tarea). Un guion por fase en `~/.claude/workflows/` (universal) o
  `.claude/workflows/` (del repo): `entender`, `especificar`, `construir`, `cerrar` y `auditoria`; la fase de
  validar es el «me vale» del usuario probando la app a mano.
- La dosis (lectores, escépticos, lentes, rondas, auditor) la da `~/.claude/bin/dosis.sh --talla … --riesgo …` según la talla y el
  riesgo, nunca según los tokens: dinero, permisos, seguridad y datos llevan varios escépticos de miradas distintas y el `auditor`
  al cierre (lo lanza el guion `cerrar`, fase Auditar, no el orquestador; `DEC-U-044`); lo demás, un escéptico (dos en talla M); lo que no se sabe cuánto hay se busca hasta dos rondas secas. Los jueces de
  `especificar` pueden subir el riesgo del ítem (y con él escépticos y lentes) aunque el encargo diga «ninguno»; el visto bueno del
  validador de forma no es puerta (lo corren los escépticos); y un «integrar con arreglo» del escéptico cierra con un arreglo dirigido
  (Sonnet) y una recomprobación, no con otra síntesis (`DEC-U-042`). Un relanzado desde una spec devuelta lleva el riesgo que fijaron los
  jueces (o el que sube el orquestador con los motivos), deja un solo commit sobre la base con la spec al día y cierra la clase del fallo,
  no solo el mutante; cada escéptico trabaja en su propia carpeta (`DEC-U-044`).
- La máquina recorta paralelismo, no profundidad: el hook `semaforo.sh` mide memoria libre y **sesiones** de Claude vivas antes de
  cada lanzamiento (los subagentes corren dentro del proceso de su sesión y no se cuentan uno a uno) y frena el que no cabe; lo
  recortado se dice y se relanza, y el orquestador propone al usuario por chat qué cerrar. Nada se cierra solo. Umbrales: 1500 MB
  libres (`SEMAFORO_MIN_LIBRE_MB`) y 8 sesiones (`SEMAFORO_MAX_SESIONES`). Orientación por sesión: 2 agentes con navegador, 4 que
  escriben código, hasta 8 que solo leen.
- Cada `agent()` de un workflow lleva `{model, effort}` y una etiqueta (el hook lo exige) y los guiones se revisan antes de lanzarlos.
- Cada ejecución deja una fila en `~/.claude/uso/workflows.tsv` (guion, dosis, agentes, minutos, hallazgos propuestos y confirmados;
  la escribe `bin/medir_workflow.sh`) y `/uso` la compara con lo estimado. La medida cuenta lo que corrió (escépticos, vueltas, notas,
  auditor), no lo que pedía la dosis (`DEC-U-044`).
- Y se documenta sola (`DEC-U-041`): `bin/registrar_ejecucion.sh` deja además su registro JSON (`~/.claude/uso/ejecuciones/`) y el
  guion `bitacora` escribe su entrada en `~/Code/cuaderno/flujo/DIARIO.md`; cada cinco entradas, una síntesis (Fable, max) propone
  en `AFINAR.md` qué afinar, con evidencia, y el usuario decide.
- El contexto de cada repo lo da su contrato (`.claude/contrato.json`, ver `rules/encargos.md`), no el prompt del guion.
- Encargos acotados, sin tope de turnos (`DEC-U-034`, 12-oct: un agente parado a medias cuesta más que uno que acaba): lo que
  evita otro BetLab (5-oct: 4 agentes sin modelo, guion de 25.000 caracteres, 7,8 h sin ninguna salida) es el modelo explícito y
  un encargo que cabe en 60 líneas, no el límite.

## Esfuerzo max (`DEC-U-038`)

- **xhigh con el usuario** (la conversación y todo lo que él lee turno a turno); **`max` en los pasos que corren sin él**: síntesis de
  specs y tests, jueces, `auditor`, desatascar. Va explícito en el `agent()` del guion, nunca por costumbre.
- `max` **nunca se fija en `settings.json` ni por variable de entorno** (`CLAUDE_CODE_EFFORT_LEVEL`): anularía el esfuerzo que lleva
  cada agente. Para una conversación, `/effort max` en ese turno.
- `ultrathink` en el prompt pide razonar más a fondo en un solo turno, sin cambiar el esfuerzo de la sesión.

## Fase previa (`DEC-U-038`)

- Planificar y especificar con el usuario se hace en **Claude Code dentro del repo**, en modo plan, con Fable xhigh y 1M de contexto.
  La app de escritorio sirve solo para pensar sin repo; lo que salga de ahí se trae al repo.
- El plan aprobado alimenta el guion `especificar`; el usuario valida las specs (un cuarto de hora) y luego todo corre solo hasta su
  «me vale» probando la app a mano. Si al validar cambia un criterio, la principal corrige la spec (`.md`) y el test va a un
  `arreglador` o a `especificar` con previa.
- Prueba medida pendiente: dos o tres sesiones de fase previa con `--effort max`, comparando minutos por turno y calidad de las
  specs. Si gana, se queda; si no, la fase previa sigue en xhigh.
