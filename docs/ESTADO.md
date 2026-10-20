# Estado de Letizia

> Actualizado: 2026-10-20. Una página para retomar el proyecto sin releerlo. Decisiones: [`DECISIONES.md`](DECISIONES.md). Specs:
> [`specs/`](specs/). Último cierre: [`sesiones/2026-10-20_cierre.md`](sesiones/2026-10-20_cierre.md).

## Qué es

Proyecto para una clienta (marca «El Archivo de Talavera»): una web que sea a la vez landing y web de noticias, que convierte en
noticias las notas de prensa que le llegan por correo, con portada automática en su plantilla y su OK antes de publicar. Además,
seguridad digital: contraseñas, correo con su dominio y copias de seguridad.

## Dónde estamos

| | |
|---|---|
| Fase | LET-01 y LET-02 construidas en la tanda del 16 al 20 de octubre, cerrada con reparos de la auditoría; LET-03 espera a la Fase 0 con la clienta, que sigue pendiente |
| Documentos | `docs/presupuesto/` (propuesta, condiciones, cuestionario de la Fase 0, tarifas y su script) |
| Specs | `specs/LET-01-estructura-del-sitio-y-paginas-estaticas.md` (IMPLEMENTADA 2026-10-20, 33 criterios; CA-LET-01-17, 29 y 30 esperan los datos y el visto bueno de la clienta) · `specs/LET-02-seccion-de-noticias.md` (IMPLEMENTADA 2026-10-20, 51) · `specs/LET-03-redes-embebidas-y-consentimiento-de-cookies.md` (BORRADOR validado el 2026-10-16, 22; se construye tras la Fase 0) |
| Decisiones | `DEC-L-002` a `DEC-L-007`: regla del menú del móvil, D1 (Astro con editor propio y formulario en PHP), contrato del repo, aprobación de las specs, alcance de las guardas de LET-02 y cierre de la tanda con la auditoría |
| Sitio | `sitio/` (Astro): seis páginas fijas y la 404 con cabecera, menú plegable y pie; el formulario de contacto lo envía `sitio/public/enviar.php` por SMTP; lista `/noticias/`, ficha de cada noticia, `sitemap.xml` y `robots.txt`; gestor de noticias y cargador del juego de pruebas en `sitio/herramientas/`. Las noticias reales van en `sitio/contenido/noticias/`, hoy vacía |
| Stack | Astro estático en `sitio/` compilado con el dominio público; formulario en un PHP propio para IONOS que habla SMTP por variables de entorno; pila local Docker (PHP-Apache + Mailpit) que levanta `tests/puerta.sh` (`DEC-L-003`) |
| Puertas | `.claude/contrato.json`: `specs`, `let-01` y `let-02`; `test_uno` = `bash tests/puerta.sh test {ruta}`. Las tres en verde en la auditoría de cierre del 2026-10-20: `let-01` con 29 tests (CA-LET-01-17 y 29 apartados con aviso) y las órdenes de CA-LET-01-01, 07 y 22; `let-02` con 23 tests y 26 comprobaciones de compilación y gestor. `specs`, en verde al cerrar |
| Tests | `tests/sitio/` (pytest y Playwright vía uv contra `SITIO_URL` y un buzón Mailpit: 31 tests de LET-01 y 21 de LET-03, estos sin puerta hasta construirla) y `tests/test_noticias*.py` (LET-02, Python 3 sin dependencias: 23 contra la compilación de pruebas servida, 26 de compilación y gestor, y `test_noticias_publicado.py` para el sitio ya publicado, CA-LET-02-24) |

## Qué cerró la tanda

- **LET-01:** las seis páginas fijas y la 404, el menú que se pliega en el móvil y el formulario de contacto que entrega el correo, con
  sus 31 tests y las órdenes de sus criterios en la puerta `let-01`.
- **LET-02:** la lista y la ficha de cada noticia publicada, con sitemap, `robots.txt` y datos de noticia para Google; el gestor y el
  cargador del juego de pruebas; y las guardas para que en la web solo salga lo publicado, con su alcance fijado en `DEC-L-006`.
- 51 commits: 2 de función, 16 arreglos (1 de LET-01 y 15 de LET-02, tras las vueltas de revisión), 18 de specs, 6 de decisiones, 6 del
  contrato, 2 de tests y 1 de estado. La auditoría de cierre da las puertas en verde y no encuentra ningún camino que lleve el juego de
  pruebas o un borrador al sitio publicado.

## Qué queda

- Tres huecos medios de la auditoría que ningún test mira (hallazgos 51 a 53 de la nota de cierre): una noticia puede cargar contenido y
  cookies de otras webs sin consentimiento; retirar una noticia cuya foto usa otra deja la compilación parada y la retirada en la web; y
  una noticia con fecha futura sale publicada al momento.
- Decisiones de Jose: la entrada «Noticias» del menú (hoy `/noticias/` no se enlaza desde ninguna página), qué hacer con una fecha futura
  (embargo), qué fecha lleva una noticia que se vuelve a publicar, las imágenes del texto de un borrador, la redirección tras enviar el
  formulario y dónde viven las noticias reales (si se versionan o no).
- En total, 60 hallazgos (3 de prioridad alta, 12 media y 45 baja); 2 se cerraron en la tanda. 19 no tocan este repo: 18 son del método
  de trabajo (entre ellos los tres de prioridad alta) y 1 de NJ Events. Lista y estado de cada uno en la nota de cierre.

## Qué toca ahora

- Decidir con Jose los huecos de arriba y darles criterio y test en LET-02 (y en LET-01 lo del formulario), antes del editor.
- Fase 0 con la clienta: plan de IONOS (que no sea el constructor MyWebsite), dominio y correo de contacto, materiales (logotipo
  vectorial, datos del aviso legal para `tests/sitio/titular.json`, texto de quiénes somos, visto bueno del diseño), qué publicaciones
  se embeben y si hay analítica. Después, LET-03.
- Ítems propios tras la Fase 0: editor web para la clienta, despliegue en IONOS (D8: compilar siempre desde cero con el dominio real,
  límite de envíos del formulario, cabeceras del servidor) y velocidad de carga (D6).
