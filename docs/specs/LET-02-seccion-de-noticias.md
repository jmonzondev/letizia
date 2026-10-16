# SPEC-LET-02 — Sección de noticias: lista, ficha de cada noticia y solo lo aprobado a la vista

> **Estado:** APROBADA · **Fecha:** 2026-10-16 · **Aprobada por:** Jose
> Aprobada por Jose el 2026-10-16 (`DEC-L-005`) con el gestor decidido (`DEC-L-003`: Astro; las noticias son ficheros de contenido y el
> juego de pruebas lo carga un cargador propio que escribe `JUEGO`). Siguen abiertas con la clienta el plan de IONOS y el dominio (§6):
> no cambian los criterios, solo el valor de `DOMINIO`.

## 1. Problema

Hoy las noticias de El Archivo de Talavera solo existen como publicaciones en sus redes (en Instagram, 37 publicaciones el 6-10). No
hay ninguna página suya donde quede cada noticia: quien busca en Google algo que ella ha contado no lo encuentra, quien quiere pasarlo
por WhatsApp solo puede reenviar una publicación de Instagram, las noticias antiguas se pierden en el perfil y sus portadas no dicen de
dónde sale la información ni de quién es la foto.

Al lector le duele no poder encontrar, abrir y compartir una noticia concreta, ni saber de dónde viene. A la clienta le duele por dos
lados: lo que trabaja no le da visitas ni posicionamiento propios, y le preocupa que salga algo que no ha revisado. Las condiciones del
proyecto prometen que las automatizaciones nunca publican sin su aprobación (condición 9), y el plan aprobado lo extiende a toda esta
sección: ninguna noticia se publica sin su aprobación explícita.

Esta spec da a cada noticia su página con dirección fija, una lista de la más reciente a la más antigua y lo que Google necesita para
encontrarlas (datos de noticia, sitemap y robots.txt). Además garantiza que en la web solo se ve lo que ella marca expresamente como
publicado y que las noticias de prueba nunca llegan al sitio real.

## 2. Alcance

- **Dentro:**
  - Lista de noticias publicadas en `/noticias/`, de la más reciente a la más antigua, cada una con su titular (enlazado a su página) y su fecha.
  - Página propia de cada noticia (ficha): titular como encabezado principal, entradilla, fecha de publicación en castellano y texto; la
    foto con su autor si la hay; la fuente si sale de una nota de prensa; sin huecos cuando falta alguna de las dos.
  - Dirección propia y estable por noticia: no cambia al corregir el titular, no se repite aunque se repita el titular, lleva solo
    minúsculas sin tilde, cifras y guiones, y se declara como canónica con el dominio público.
  - Regla de aprobación: toda noticia nace en borrador; solo se ve lo que la clienta marca como publicado; retirar una noticia la quita de la web.
  - Datos estructurados de noticia (schema.org `NewsArticle`) en cada ficha: titular, fechas con zona horaria e imagen, en JSON válido
    aunque el titular lleve comillas o «&».
  - Sitemap bien formado con exactamente las noticias publicadas y direcciones completas del dominio público; robots.txt que lo señala y
    no bloquea las noticias. Es lo que Search Console necesita del sitio.
  - Juego de pruebas (noticias A a H), el registro que deja su cargador y las comprobaciones de todo lo anterior sobre el sitio servido,
    más la de que ese juego nunca llega al sitio publicado.
- **Fuera:**
  - El gestor con el que la clienta escribe, publica, corrige y retira noticias → decidido el 2026-10-16 (`DEC-L-003`): Astro con un
    editor web propio, que es un ítem aparte de este.
  - Cómo se carga el juego de pruebas en la compilación (y cómo su cargador escribe el registro `JUEGO` de §5) y cómo se sirve en
    local → spec de arquitectura, al fijar el stack.
  - Alta del sitio y verificación de la propiedad en Search Console → despliegue de M1, con la cuenta de Google de la clienta
    (cuestionario de la Fase 0, §A) y el dominio decidido.
  - Secciones o categorías de noticias (la maqueta «Periódico» propone siete) → decisión de la clienta en la Fase 0; si entran, ítem
    nuevo del módulo M1.
  - Paginación de la lista y número de noticias por página → spec de arquitectura, al fijar el stack. Las comprobaciones dan por hecho
    que las seis noticias publicadas del juego caben en la primera página de la lista.
  - Velocidad de carga, que la propuesta incluye en el SEO técnico base de M1 (`docs/presupuesto/01-propuesta.md:46`) → hueco del
    plan: no la reparte entre LET-01, LET-02 y LET-03. La asigna el orquestador; propuesta: LET-01, porque afecta a todas las páginas.
  - Analítica con consentimiento, también en M1 (`docs/presupuesto/01-propuesta.md:46`) → hueco del plan: ningún ítem la recoge. La
    asigna el orquestador; propuesta: LET-03, que ya trata lo que se carga con consentimiento de cookies.
  - Vista previa al compartir por WhatsApp o redes (Open Graph) y los botones de compartir de la maqueta → M8 (optimización de la
    plantilla de noticia, `docs/presupuesto/01-propuesta.md:153`).
  - Otros datos estructurados (organización, migas de pan) y buscador interno → M8.
  - Diseño visual, versión móvil, y título y descripción propios de cada página → LET-01.
  - Instagram y TikTok embebidos → LET-03.
  - Redactar las noticias → la clienta (`docs/presupuesto/02-condiciones.md:14`).
  - Publicación automática en la web a partir de las notas de prensa, y limpiar el HTML que traiga su texto (scripts, iframes, `img`
    con `onerror`) antes de publicarlo → M6, con M4 y M5 antes.
  - Si una noticia ya publicada que se edita vuelve a pasar por aprobación → M5 (canal de aprobación). Recomendación: si la edita la
    automatización, vuelve a borrador; si la corrige la clienta a mano, sigue publicada, como C y F en el juego de pruebas.
  - Quitar los datos de ubicación (GPS) de las fotos al publicarlas → decisión pendiente, a plantear a la clienta en la Fase 0 y anotar
    como `DEC-L-NNN`.
  - Migrar noticias o contenidos antiguos → presupuesto aparte (condición 4, `docs/presupuesto/02-condiciones.md:10`); se pregunta en el
    cuestionario de la Fase 0, §C (`docs/presupuesto/03-cuestionario-fase0.md:38`).

## 3. Estado actual medido

Medido en el commit `36baa95` (el último sin esta spec) y vuelto a abrir sobre el árbol del commit de esta spec, que añade solo la
spec y sus dos tests (ningún fichero del producto cambia).

- `docs/presupuesto/calcular_tarifas.py:14` — es la única mención a las noticias en el código del producto: la tupla
  `("M1", "Landing y web de noticias", 32, 43)` con las horas del módulo para calcular tarifas. No genera ninguna página.
- `.claude/contrato.json:3` — `"puertas": []`: el repo no declara ninguna puerta.
- `.claude/contrato.json:4` — `"test_uno": ""`: el contrato no da orden para correr un test (y `git ls-files` no lista más tests que
  los dos de esta spec, `tests/test_noticias.py` y `tests/test_noticias_publicado.py`, que hoy salen 1 porque no hay sitio).
- `docs/specs/.gitkeep` — fichero vacío (0 bytes): aparte de esta spec, la carpeta no tiene ninguna otra.
- Nada hoy: no hay web, ni lista, ni ficha, ni sitemap, ni robots.txt, ni datos estructurados. Se buscó de tres formas. 1) Los 14
  ficheros versionados que no son `.md` (`git ls-files`): la capa `.claude/` (10), el script de tarifas, `.gitkeep` y los dos tests de
  esta spec. 2) `find` de `*.html`, `*.astro`, `*.php`, `*.mjs`, `*.xml`, `package.json`, `sitemap*` y `robots.txt`: 0 resultados. 3)
  `grep -rniE 'noticia|sitemap|newsarticle|json-ld|ld\+json|search console|robots'` en `.py`, `.html`, `.js`, `.ts`, `.astro`, `.php`,
  `.xml`, `.json`, `.toml`, `.yml` y `.sh` fuera de `.claude/`: solo `docs/presupuesto/calcular_tarifas.py:14` y los dos tests.

## 4. Reglas de negocio

- `RN-LET-02-01` — La sección de noticias **debe** listar las noticias publicadas de la más reciente a la más antigua, cada una con su
  titular y su fecha de publicación.
- `RN-LET-02-02` — Cada noticia publicada **debe** tener una página propia cuya dirección no cambia aunque se corrija el titular.
- `RN-LET-02-03` — La página de una noticia **debe** mostrar el titular como encabezado principal, la entradilla, la fecha de
  publicación en castellano (p. ej. «7 de octubre de 2026») y el texto.
- `RN-LET-02-04` — Una noticia que sale de una nota de prensa **debe** citar su fuente con el formato «Fuente: [organismo], nota de
  prensa del [fecha]».
- `RN-LET-02-05` — La foto publicada con una noticia **debe** llevar su autor con el formato «Foto: [autor]».
- `RN-LET-02-06` — La página de una noticia **no debe** enseñar huecos: ni imágenes rotas ni rótulos vacíos cuando falta la foto o la fuente.
- `RN-LET-02-07` — Una noticia **solo debe** verse en la web cuando la clienta la ha marcado expresamente como publicada: toda noticia
  nueva nace en borrador. Lo fija el plan aprobado, que extiende a esta sección la condición 9 (las automatizaciones nunca publican sin
  su aprobación).
- `RN-LET-02-08` — Una noticia retirada **debe** dejar de verse en la web.
- `RN-LET-02-09` — Cada página de noticia **debe** llevar datos estructurados de tipo noticia (schema.org `NewsArticle`) que repitan el
  titular, la fecha de publicación y la foto que se ven en ella.
- `RN-LET-02-10` — Las fechas de esos datos estructurados (publicación y última modificación) **deben** llevar zona horaria.
- `RN-LET-02-11` — La fecha de última modificación de esos datos estructurados **debe** ser la de la última corrección de la noticia, no
  la de su creación, la de su carga ni la de la compilación del sitio.
- `RN-LET-02-12` — El sitemap del sitio **debe** contener todas las noticias publicadas y ninguna que no lo esté.
- `RN-LET-02-13` — El sitemap **debe** ser XML bien formado.
- `RN-LET-02-14` — Toda dirección del sitemap **debe** ser completa y del dominio público del sitio, nunca la de un entorno local o de pruebas.
- `RN-LET-02-15` — El robots.txt del sitio **debe** indicar a los buscadores la dirección completa del sitemap, en el dominio público.
- `RN-LET-02-16` — Cada página de noticia publicada **debe** poder indexarse en Google bajo su propia dirección canónica, completa y del
  dominio público.
- `RN-LET-02-17` — Dos noticias con el mismo titular **deben** tener direcciones distintas.
- `RN-LET-02-18` — La dirección que el gestor asigna solo a una noticia **debe** llevar únicamente minúsculas sin tilde, cifras y guiones.
- `RN-LET-02-19` — Las noticias del juego de pruebas **no deben** verse nunca en el sitio publicado.
- `RN-LET-02-20` — El gestor de noticias **no debe** escribir fuera de la carpeta de noticias ni sustituir la foto de otra noticia.
- `RN-LET-02-21` — El cargador del juego de pruebas **no debe** tocar la carpeta de las noticias reales, ni por otro nombre ni por un enlace.

## 5. Criterios de aceptación

Se comprueban sobre la compilación de producción servida en local con el juego de pruebas cargado; la 24, sobre el sitio publicado.
Antes de lanzar las órdenes, desde la raíz del repo: `export SITIO=http://127.0.0.1:<puerto> DOMINIO=https://<dominio> JUEGO=<registro>`.
`SITIO` es donde se sirve la compilación (por defecto `http://127.0.0.1:8080`); `DOMINIO`, la dirección pública que esa compilación
escribe en canónicas, sitemap y robots.txt; `JUEGO`, el registro que deja el cargador del juego (por defecto `tests/juego.json`). Cada
orden sale 0 si se cumple su criterio y 1 si no. Hoy todas salen 1 porque no hay sitio; la 24, porque no hay sitio publicado ni dominio.
Solo usan la biblioteca estándar de Python 3.9 o posterior, con el mismo resultado de 3.9 a 3.14 (las fechas ISO 8601 y robots.txt
los leen ellas mismas: `datetime.fromisoformat` y `urllib.robotparser` cambian de una versión a otra), así que no dependen del gestor que
se elija. No corren con `-O` ni `PYTHONOPTIMIZE` (salen 3 sin comprobar nada): sin `assert` darían por bueno un sitio roto. Una copia de
pruebas puede llevar `noindex` a propósito; en ella no aplica la 20.

Juego de pruebas (ninguna otra noticia usa direcciones `prueba-*` ni estos titulares). El cargador crea las noticias en el orden de la
tabla (A la primera, H la última), cada una con la fecha de publicación que indica la tabla; después de publicarlas todas hace las dos
correcciones al revés de como se crearon: primero la de F y, al menos un segundo después (los gestores guardan la fecha de modificación
con segundos), la de C; y al acabar escribe el registro `JUEGO` (sin versionar): un objeto JSON con una clave por noticia, de `A` a `H`,
y el estado que el gestor devuelve tras cargarla, `publicada`, `borrador` o `retirada`. Así una lista ordenada por fecha de modificación
o por orden de creación no da el orden de publicación; una fecha de modificación que no cambia con cada corrección se nota, sea la de
compilación (igual en todas) o la de creación de cada noticia (que dejaría la de F después de la de C); y un borrador o una retirada
que el cargador no llegó a crear no pasan desapercibidos.

| Noticia | Dirección | Titular | Estado | Publicada (hora de Madrid) | Además |
|---|---|---|---|---|---|
| A | `/noticias/prueba-a/` | `Noticia de prueba A` | publicada | 7-10-2026, 10:00 | entradilla `Entradilla de la prueba A.`, texto `Texto de la prueba A.`, foto `foto-prueba-a.jpg` de `Autora de prueba`; sale de una nota de prensa del Ayuntamiento de Talavera de la Reina del 6-10-2026 |
| B | `/noticias/prueba-b/` | `Noticia de prueba B` | publicada | 8-10-2026, 10:00 | sin foto ni nota de prensa |
| C | `/noticias/prueba-c/` | `Noticia de prueba C`, corregido después a `Noticia de prueba C corregida` | publicada | 9-10-2026, 10:00 | la corrección se hace después de publicarla, como la haría la clienta, y después de corregir F |
| D | `/noticias/prueba-d/` | `Noticia de prueba D` | creada sin tocar su estado | — | el registro `JUEGO` la da como `borrador` |
| E | `/noticias/prueba-e/` | `Noticia de prueba E` | publicada y retirada después | — | el registro `JUEGO` la da como `retirada` |
| F | `/noticias/prueba-f/` | `Noticia de prueba F: «Año Nuevo», "comillas" & </script>` | publicada | 5-10-2026, 10:00 | texto `Texto de la prueba F.`, corregido después de publicarla (y antes de corregir C) a `Texto de la prueba F, corregido.` |
| G y H | la que el gestor asigne solo | `Noticia de prueba repetida: Año Nuevo en Talavera`, las dos | publicadas | 4-10-2026 y 3-10-2026, 10:00 | — |

- `CA-LET-02-01` (RN-LET-02-01) — Dado el juego de pruebas, cuando el lector abre la lista de noticias, entonces sus enlaces a direcciones `prueba-*` aparecen en el orden C, B, A, F, y no hay ninguno a D ni a E. C se corrigió la última y F se creó después de C: ordenada por fecha de modificación F iría la segunda, y por creación, la primera → orden: `python3 tests/test_noticias.py test_ca_let_02_01_lista_en_orden` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-02` (RN-LET-02-01) — Dado el juego, cuando el lector abre la lista, entonces ve el titular de A como enlace a su página, la fecha «7 de octubre de 2026» entera («17 de octubre de 2026» no vale) y «9 de octubre de 2026», la fecha de publicación de C; como C se corrigió después, la fecha de su corrección no vale → orden: `python3 tests/test_noticias.py test_ca_let_02_02_lista_con_titular_y_fecha` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-03` (RN-LET-02-02) — Dado el juego, cuando se pide la dirección de A, B, C y F, entonces las cuatro responden 200 sin redirigir → orden: `python3 tests/test_noticias.py test_ca_let_02_03_cada_publicada_tiene_su_pagina` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-04` (RN-LET-02-02) — Dada C, publicada como «Noticia de prueba C» en `/noticias/prueba-c/` y corregida después, cuando el lector abre esa misma dirección, entonces el titular principal es «Noticia de prueba C corregida» y no el anterior, y en la lista ese titular enlaza a `/noticias/prueba-c/`. Así no se rompe un enlace que ya se compartió por WhatsApp → orden: `python3 tests/test_noticias.py test_ca_let_02_04_titular_corregido_misma_direccion` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-05` (RN-LET-02-03) — Dadas A y C, cuando el lector abre sus páginas, entonces en la de A el titular principal (`h1`) es «Noticia de prueba A» y se ven la entradilla, «7 de octubre de 2026» entera («17 de octubre de 2026» o «27 de octubre de 2026» no valen) y el texto, y en la de C se ve «9 de octubre de 2026». La nota de prensa de A es del día 6 y C se corrigió después de publicarla: esas fechas solo pueden salir de la fecha de publicación, no de la de la fuente ni de la de la corrección → orden: `python3 tests/test_noticias.py test_ca_let_02_05_ficha_completa` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-06` (RN-LET-02-04) — Dada A, que sale de una nota de prensa del Ayuntamiento, cuando el lector abre su página, entonces lee «Fuente: Ayuntamiento de Talavera de la Reina, nota de prensa del 6 de octubre de 2026» → orden: `python3 tests/test_noticias.py test_ca_let_02_06_fuente_citada` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-07` (RN-LET-02-05) — Dada A, cuya foto es de «Autora de prueba», cuando el lector abre su página, entonces lee «Foto: Autora de prueba» → orden: `python3 tests/test_noticias.py test_ca_let_02_07_credito_de_la_foto` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-08` (RN-LET-02-06) — Dadas A (con foto) y B (sin foto), cuando se cargan sus páginas, entonces la de A muestra su foto (`foto-prueba-a` en el `src` o el `srcset` de un `img`, o en el `srcset` de un `source` de su `picture`), ningún `img` de las dos va sin `src` o con `src` vacío, ningún `source` de un `picture` va sin `srcset`, y todas sus imágenes (cada `img` por `src` y `srcset`, y cada `source` de un `picture` por `srcset`, que el navegador prefiere al `img`), con las rutas relativas resueltas desde la página y el `srcset` partido como lo parte el navegador (una coma dentro de una dirección no la rompe), responden 200 con tipo `image/*` → orden: `python3 tests/test_noticias.py test_ca_let_02_08_imagenes_sin_romper` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-09` (RN-LET-02-06) — Dada B, sin foto ni nota de prensa, cuando el lector abre su página (titular principal «Noticia de prueba B»), entonces en ninguna parte de ella aparecen los rótulos «Fuente:» ni «Foto:», en mayúsculas o en minúsculas → orden: `python3 tests/test_noticias.py test_ca_let_02_09_sin_rotulos_vacios` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-10` (RN-LET-02-07) — Dada D, creada sin tocar su estado, cuando se lee el registro `JUEGO` y se pide su dirección, entonces el registro tiene a D con el estado `borrador` (si falta, el cargador no la creó y la comprobación no vale) y su dirección responde 404, mientras A responde 200 → orden: `python3 tests/test_noticias.py test_ca_let_02_10_borrador_no_existe` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-11` (RN-LET-02-07) — Dada D en borrador, cuando se lee el registro `JUEGO` y se descargan la portada, la lista y la página de A, entonces el registro tiene a D con el estado `borrador` (si falta, el cargador no la creó y no hay nada que comprobar) y su titular no aparece en ninguna de las tres, ni en el código tal cual ni en el texto visible con las entidades resueltas y los espacios igualados (`prueba&nbsp;D` o el titular partido en dos `span` también cuentan), mientras la lista sí muestra A → orden: `python3 tests/test_noticias.py test_ca_let_02_11_borrador_fuera_de_portada_y_lista` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-12` (RN-LET-02-08) — Dada E, publicada y retirada después, cuando se lee el registro `JUEGO` y alguien abre su dirección, entonces el registro tiene a E con el estado `retirada` (si falta, el cargador no la creó), su dirección responde 404 o 410 y su titular no aparece en la portada, la lista ni la página de A, ni en el código ni en el texto visible con las entidades resueltas. Que no esté en el sitemap lo comprueba CA-LET-02-16 → orden: `python3 tests/test_noticias.py test_ca_let_02_12_retirada_no_se_ve` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-13` (RN-LET-02-09) — Dada A, cuando Google lee su página, entonces encuentra exactamente un bloque `NewsArticle` (vale con `@type` en lista, dentro de `@graph` o anidado en otro nodo, como `mainEntity` de una `WebPage`; un `Article` a secas no vale) con `headline` igual al titular que se ve, `datePublished` del 7-10-2026 e `image` que lleva a la foto de A (`foto-prueba-a` en su dirección). Vale como dirección, como `ImageObject` con `url` o `contentUrl` y como referencia `@id` a un `ImageObject` de los datos de la página; un logo u otra imagen no vale → orden: `python3 tests/test_noticias.py test_ca_let_02_13_datos_estructurados_de_noticia` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-14` (RN-LET-02-09) — Dada F, cuyo titular lleva «», comillas rectas, «&» y `</script>`, cuando Google lee su página, entonces todos sus bloques de datos estructurados son JSON válido y el `headline` es el mismo titular que se ve en el `h1`. Si el gestor quita `</script>` al guardar, vale el titular sin esa etiqueta, siempre que sea igual en los dos sitios; las comillas tipográficas cuentan como rectas → orden: `python3 tests/test_noticias.py test_ca_let_02_14_titular_con_signos` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-15` (RN-LET-02-10, RN-LET-02-11) — Dadas A, C y F, cuando se leen sus datos estructurados, entonces `datePublished` y `dateModified` llevan zona horaria (valen `+02:00`, `+0200`, `+02` y `Z`, leídos igual en cualquier versión de Python), el `datePublished` de A es el 7-10-2026 a las 10:00 de Madrid (08:00 UTC), el `dateModified` de C y el de F, que se corrigieron después de publicarlas, son posteriores a su `datePublished`, y el de C es posterior al de F, que se corrigió antes aunque se creó después; el de A, que no se corrigió nunca, no cambia de una petición a otra (se lee al principio y otra vez al final, después de F y C) y es anterior al de F (el cargador deja pasar al menos un segundo entre publicar la última noticia y corregir F); como prueba de que la corrección de F llegó al sitio, su página muestra «Texto de la prueba F, corregido.» y ya no «Texto de la prueba F.». No pasa un `dateModified` que fuera la hora de compilación o de carga (igual en todas), ni la de creación de cada noticia sin cambiar al corregir (la de F quedaría después de la de C), ni la de publicación, ni la hora de cada petición o de generar cada página al compilar, en orden de publicación (la de A, que se pide o se genera después de F, cambiaría o quedaría después) → orden: `python3 tests/test_noticias.py test_ca_let_02_15_fechas_con_zona_horaria` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-16` (RN-LET-02-12) — Dado el juego, cuando Google lee los sitemaps que señala robots.txt (y los que enlacen si son un índice; `/sitemap.xml` si robots.txt no señala ninguno), entonces encuentra las seis noticias publicadas del juego (A, B, C y F por su dirección; G y H por las dos direcciones a las que la lista enlaza su titular: si la lista no enlaza ese titular a dos direcciones distintas, las seis no se pueden comprobar y la comprobación falla) y ni D ni E; un enlace de la lista que no es una noticia (paginación `/noticias/2/`, un feed) no se exige en el sitemap. Cada dirección de esos sitemaps responde 200: un enlace por número como `$DOMINIO/?p=104` a un borrador o a una retirada no vale aunque no aparezca su ruta (las de otro dominio las rechaza CA-LET-02-18) → orden: `python3 tests/test_noticias.py test_ca_let_02_16_sitemap_con_las_publicadas` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-17` (RN-LET-02-13) — Dado el sitio, cuando se leen esos sitemaps, entonces todos son XML bien formado con raíz `urlset` o `sitemapindex` del espacio de nombres de sitemaps.org, y al menos uno lista direcciones. Un «&» sin escapar en una dirección lo rompe → orden: `python3 tests/test_noticias.py test_ca_let_02_17_sitemap_bien_formado` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-18` (RN-LET-02-14) — Dado el sitio, cuando se leen las direcciones (`loc`) de esos sitemaps, entonces todas empiezan por `$DOMINIO/`: ninguna es relativa, de localhost ni de otro entorno → orden: `python3 tests/test_noticias.py test_ca_let_02_18_sitemap_con_direcciones_publicas` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-19` (RN-LET-02-15) — Dado el sitio, cuando un buscador lee robots.txt, entonces encuentra al menos una línea `Sitemap:`, todas con una dirección que empieza por `$DOMINIO/`, y cada una responde 200 → orden: `python3 tests/test_noticias.py test_ca_let_02_19_robots_senala_el_sitemap` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-20` (RN-LET-02-16) — Dada A en la compilación de producción, cuando Google intenta indexarla, entonces nada se lo impide: ninguna de sus cabeceras `X-Robots-Tag` (se leen todas; las dirigidas a otro robot, como `bingbot: noindex`, no cuentan) ni ninguna etiqueta `meta` de nombre `robots` o `googlebot` (con los atributos en cualquier orden) lleva la directiva `noindex` o `none` (`max-image-preview:none` sí deja indexar), y robots.txt no le impide a Googlebot leerla, evaluado como lo hace Google: se aplica el grupo de `User-agent` de Googlebot o, si no hay, el de `*`; gana la regla más larga que casa; `*` vale cualquier cosa y `$` marca el final; a igual longitud gana `Allow`; un BOM UTF-8 al principio del fichero no cuenta, Google lo ignora. Lo que vean otros buscadores no entra en esta regla → orden: `python3 tests/test_noticias.py test_ca_let_02_20_noticia_indexable` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-21` (RN-LET-02-16) — Dada A, cuando Google lee su página, entonces declara una sola dirección canónica (vale repetida en dos etiquetas iguales; dos distintas no) y es exactamente `$DOMINIO/noticias/prueba-a/` → orden: `python3 tests/test_noticias.py test_ca_let_02_21_canonica_propia` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-22` (RN-LET-02-17) — Dadas G y H, con el mismo titular, cuando el lector abre la lista, entonces ese titular enlaza a dos direcciones distintas y cada una abre una noticia con ese titular → orden: `python3 tests/test_noticias.py test_ca_let_02_22_mismo_titular_direcciones_distintas` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-23` (RN-LET-02-18) — Dadas G y H, cuyas direcciones asigna el gestor solo a partir de un titular con «ñ» y mayúsculas, cuando se leen esas direcciones, entonces tienen la forma `/noticias/<dirección>/` con solo minúsculas sin tilde, cifras y guiones (ni `ñ` ni `%C3`) → orden: `python3 tests/test_noticias.py test_ca_let_02_23_direcciones_limpias` ⇒ exit 0 (hoy, exit 1: no hay sitio)
- `CA-LET-02-24` (RN-LET-02-19) — Dado el sitio publicado en `$DOMINIO`, que tiene que ser una dirección pública (no valen localhost, una IP de esta máquina o de una red privada escrita como sea —`127.1` es 127.0.0.1—, un dominio `.local` o `.test` ni un nombre que resuelva a una de esas IP: contra la compilación local la comprobación no dice nada y falla sin hacer ninguna petición), tras cada despliegue, cuando se piden su portada, su lista, las direcciones `prueba-a` a `prueba-f`, sus sitemaps y cada noticia que estos llevan, entonces portada y lista responden 200, esas direcciones responden 404 o 410 y no están en los sitemaps, y ninguna de las páginas pedidas muestra un titular del juego (en el código o en el texto). Así se ven también G y H, cuya dirección asigna el gestor y puede no salir en la primera página de la lista → orden: `python3 tests/test_noticias_publicado.py test_ca_let_02_24_juego_de_pruebas_fuera_del_publicado` ⇒ exit 0 (hoy, exit 1: no hay sitio publicado ni dominio)

Las siguientes miran la compilación de producción y el gestor, sin servidor: compilan copias de `sitio/` con noticias reales
(`contenido/noticias` de la copia, como el sitio publicado) y necesitan Node y las dependencias de `sitio/`. Salieron de la
revisión de la construcción (16-oct), de sus tres vueltas: cada una fijó un fallo que los 23 criterios anteriores no veían.

- `CA-LET-02-25` (RN-LET-02-02) — Dada una noticia real con un titular que empieza por «Prueba» («Prueba de la EvAU en Talavera»), cuando se compila para producción, entonces compila, la noticia tiene su página en `/noticias/prueba-de-la-evau-en-talavera/` y está en el sitemap: no se la confunde con el juego de pruebas → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_02_titular_real_que_empieza_por_prueba` ⇒ exit 0
- `CA-LET-02-26` (RN-LET-02-19) — Dada una noticia marcada como del juego de pruebas (la marca la pone el cargador) o con una de sus seis direcciones fijas (`prueba-a` a `prueba-f`), cuando se compila para producción, entonces la compilación se niega diciendo que es del juego de pruebas y no deja ninguna página de noticias → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_19_el_juego_de_pruebas_no_entra_en_el_sitio_publicado` ⇒ exit 0
- `CA-LET-02-27` (RN-LET-02-07, RN-LET-02-08) — Dadas una noticia publicada, otra publicada que se retira y un borrador, cada una con su foto en la ficha y otra en el texto, cuando se compila antes y después de retirar la segunda, entonces las fotos del borrador no salen nunca a la compilación, las de la retirada desaparecen con su página y las de la publicada siguen → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_07_08_las_fotos_de_borradores_y_retiradas_no_salen` ⇒ exit 0
- `CA-LET-02-28` (RN-LET-02-11) — Dados un borrador corregido antes de publicarlo y una retirada corregida antes de volver a publicarla, cuando se compila, entonces compila y en las dos `dateModified` es igual a `datePublished`: la corrección anterior a la publicación no cuenta → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_11_borrador_corregido_se_publica_sin_romper_la_compilacion` ⇒ exit 0
- `CA-LET-02-29` (RN-LET-02-20) — Dadas dos noticias con una foto del mismo nombre (`IMG_0001.jpg`) y una tercera cuyo nombre de foto lleva ruta (`../fuera.jpg`), cuando el gestor las crea, entonces rechaza la segunda sin pisar la foto de la primera, rechaza la tercera sin escribir fuera de la carpeta y no deja el fichero de una noticia rechazada → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_07_gestor_no_pisa_fotos_ni_escribe_fuera_de_su_carpeta` ⇒ exit 0
- `CA-LET-02-30` (RN-LET-02-21) — Dada la carpeta de noticias reales con una noticia publicada y un enlace a esa carpeta, cuando el cargador del juego recibe el enlace como carpeta de trabajo, entonces se niega y la noticia real sigue en su sitio → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_19_cargador_no_vacia_contenido_noticias_con_otro_nombre` ⇒ exit 0
- `CA-LET-02-31` (RN-LET-02-02) — Dada una noticia real titulada «Prueba A», cuando el gestor le asigna la dirección y se compila para producción, entonces no recibe la dirección fija `prueba-a` del juego (recibe otra, `prueba-a-2`) y la compilación la publica → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_02_titular_prueba_a_no_toma_una_direccion_del_juego` ⇒ exit 0
- `CA-LET-02-32` (RN-LET-02-20) — Dadas fotos llamadas `otra.md`, `sin-extension` y `foto final.jpg`, cuando el gestor crea la noticia, entonces las rechaza sin escribirlas ni dejar el fichero de la noticia, y acepta `noticia.md.jpg`: solo nombres de fichero de imagen (jpg, png, webp, avif o gif), sin ruta ni espacios → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_20_gestor_rechaza_una_foto_que_no_es_una_imagen` ⇒ exit 0
- `CA-LET-02-33` (RN-LET-02-21) — Dada una carpeta de trabajo con una noticia sin la marca del juego y otro `.md` cualquiera, cuando el cargador la recibe, entonces se niega y no borra nada → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_21_cargador_no_vacia_una_carpeta_con_noticias_ajenas` ⇒ exit 0
- `CA-LET-02-34` (RN-LET-02-19) — Dada la variable `NOTICIAS_DIR` apuntando a `contenido/noticias`, por su nombre o por un enlace, y una noticia marcada del juego en esa carpeta, cuando se compila, entonces la compilación se niega igual que sin la variable: solo otra carpeta la convierte en compilación de pruebas → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_19_noticias_dir_a_las_noticias_reales_no_apaga_las_guardas` ⇒ exit 0
- `CA-LET-02-35` (RN-LET-02-11) — Dada una noticia publicada con fecha futura y corregida antes de esa fecha, cuando se compila, entonces compila y su `dateModified` es la fecha de publicación, nunca una anterior a ella → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_11_publicada_con_fecha_futura_y_corregida_compila` ⇒ exit 0
- `CA-LET-02-36` (RN-LET-02-02, RN-LET-02-07) — Dado un borrador a medias (sin entradilla, con foto sin autor) junto a una noticia publicada, cuando se compila para producción, entonces compila, la publicada tiene su página y del borrador no sale nada; y publicar ese borrador tal cual se rechaza (una foto publicada lleva su autor, RN-LET-02-05) → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_02_un_borrador_a_medias_no_tumba_la_compilacion` ⇒ exit 0
- `CA-LET-02-37` (RN-LET-02-11, RN-LET-02-01) — Dada una noticia publicada y corregida después, cuando se vuelve a llamar a publicar sobre ella, entonces el gestor se niega y no cambian ni su fecha de publicación ni su última corrección → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_11_publicar_dos_veces_no_reinicia_la_fecha_ni_la_correccion` ⇒ exit 0
- `CA-LET-02-38` (RN-LET-02-20) — Dada una dirección con ruta (`../x`) y un fichero con forma de noticia fuera de la carpeta, cuando se llama a publicar, corregir, retirar o consultar el estado con esa dirección, entonces el gestor se niega y el fichero de fuera no cambia → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_20_el_gestor_no_acepta_direcciones_con_ruta` ⇒ exit 0
- `CA-LET-02-39` (RN-LET-02-19) — Dada la variable `NOTICIAS_DIR` escrita como ruta relativa y la compilación lanzada desde otra carpeta con `--root`, o con una almohadilla detrás, o como dirección `file://` de `contenido/noticias`, y una noticia marcada del juego en esa carpeta, cuando se compila, entonces la compilación se niega igual que sin la variable (se resuelve una sola vez, como la lee Astro); y con una carpeta que no existe, se niega diciendo que no es una carpeta → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_19_noticias_dir_se_resuelve_como_lo_lee_astro` ⇒ exit 0
- `CA-LET-02-40` (RN-LET-02-21) — Dados un registro apuntando a una noticia real, una carpeta que solo tiene fotos, una carpeta con una noticia que lleva la marca del juego en el texto y no en la cabecera, y la carpeta del juego con una foto que ninguna noticia del juego nombra, cuando el cargador los recibe, entonces se niega en los cuatro casos sin escribir ni borrar nada → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_21_cargador_no_toca_registro_ni_fotos_ajenos` ⇒ exit 0
- `CA-LET-02-41` (RN-LET-02-02, RN-LET-02-07) — Dados un borrador con el autor de la foto vacío, otro con la fecha de publicación escrita a mano que no es una fecha y una noticia publicada, cuando se compila para producción, entonces compila, la publicada tiene su página y de los borradores no sale nada; y el gestor no deja corregir el titular a vacío, ni la entradilla de una publicada, ni publicar una noticia con el autor de la foto en blanco → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_02_borrador_con_campos_a_medias_no_tumba_la_compilacion` ⇒ exit 0
- `CA-LET-02-42` (RN-LET-02-17, RN-LET-02-20) — Dadas seis altas a la vez con el mismo titular y la misma foto, cuando terminan, entonces hay en la carpeta exactamente tantas noticias como altas que el gestor dio por buenas, y la foto solo se dio por escrita una vez → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_20_crear_a_la_vez_no_pisa_noticias` ⇒ exit 0
- `CA-LET-02-43` (RN-LET-02-19) — Dada una noticia real que pide la dirección fija `prueba-a`, cuando el gestor la crea, entonces se niega; con la marca del juego, la acepta → orden: `python3 tests/test_noticias_compilacion.py test_rn_let_02_19_direccion_fija_del_juego_no_se_pide_para_una_noticia_real` ⇒ exit 0
- `CA-LET-02-44` (RN-LET-02-19) — Dada la puerta `let-02` recién pasada, cuando se mira `sitio/dist` (lo que se subiría al desplegar), entonces no queda ninguna noticia del juego ni en las páginas ni en el sitemap: la puerta recompila la producción al acabar → orden: `bash tests/puerta.sh let-02 >/dev/null 2>&1; [ ! -e sitio/dist/noticias/prueba-a ] && ! grep -qs prueba-a sitio/dist/sitemap.xml` ⇒ exit 0

## 6. Contexto

- Plan aprobado: `~/Code/cuaderno/encargos/2026-10-13_flujo_universal/ensayos/plan_letizia_m1.md` (ítem LET-02 y su «Fuera»).
- `docs/presupuesto/01-propuesta.md:44-60` (§M1: «Desarrollo de las páginas y sección de noticias», 12–16 h; SEO técnico base con
  sitemap y datos estructurados de noticia; Search Console y analítica con consentimiento), `:119-125` (M6: la publicación automática
  en la web) y `:153` (M8: optimización de la plantilla de noticia).
- `docs/presupuesto/02-condiciones.md:29` (condición 9: «Las automatizaciones nunca publican sin tu aprobación»; el plan aprobado la
  extiende a toda la sección de noticias), `:10` (condición 4: lo nuevo se presupuesta aparte) y `:12-18` (lo que no incluye el proyecto).
- `docs/presupuesto/03-cuestionario-fase0.md:5-22` (§A: dominio, IONOS, cuenta de Google con Search Console) y `:38` (noticias antiguas).
- Propuesta v6 entregada a la clienta: `~/Code/cuaderno/proyectos/letizia/artefactos/docs/2026-10-08_el-archivo-de-talavera-propuesta_v6-final.md`.
  Línea 20: web de noticias con un editor para publicar, corregir o borrar. Líneas 133-143: WordPress o Astro con editor, lo elige ella.
  Línea 198: cada noticia cita su fuente y el autor de la foto. Línea 509: riesgo de que su plan de IONOS sea MyWebsite, que no admite
  ninguna de las dos. Línea 539: hoy sus portadas no llevan fuente ni crédito de la foto.
- La marca y sus redes: `~/Code/cuaderno/proyectos/letizia/RESUMEN.md:7`.
- Maquetas de lo que ve el lector (referencia, no código): `~/Code/cuaderno/proyectos/letizia/artefactos/maquetas-limpias/Noticia.png`
  (ficha con «Fuente: [organismo], nota de prensa del [fecha]. Foto: [autor].») y `Periodico.png` (portada).
- Decisiones: (1) gestor y hosting, decidida el 2026-10-16 (`DEC-L-003`): Astro con editor propio en IONOS; las noticias y el juego de
  pruebas son ficheros de contenido, y un cargador propio los crea, corrige y retira y escribe el estado de cada una en `JUEGO`
  (condiciones previas de CA-LET-02-04, CA-LET-02-10, CA-LET-02-11, CA-LET-02-12 y CA-LET-02-15). Siguen abiertas con la clienta, a
  anotar como `DEC-L-NNN`: (2) plan de IONOS; (3) dominio, que es el valor de `DOMINIO`.
- Estructura de direcciones propuesta, a cuadrar con LET-01: la lista en `/noticias/` y cada noticia en `/noticias/<dirección>/`. Si
  LET-01 fija otra, solo cambian las constantes del principio de `tests/test_noticias.py`.
- Las comprobaciones: `tests/test_noticias.py` (de la 01 a la 23, sobre la compilación servida en local) y
  `tests/test_noticias_publicado.py` (la 24, sobre el sitio publicado). Se probaron el 14-10 contra un sitio falso servido en local,
  fuera del repo, con Python 3.9, 3.11, 3.12, 3.13 y 3.14, y las cinco dieron lo mismo. Con el sitio correcto pasan las 23, también en
  doce variantes válidas más: E en 410, la foto de A dentro de un `picture` con un `source` AVIF que carga, el `NewsArticle` anidado como
  `mainEntity` de una `WebPage`, `@type` en lista dentro de `@graph` con la imagen como referencia `@id` a un `ImageObject`, zonas
  horarias `+0200`, fechas en UTC con `Z`, un `srcset` con una coma dentro de la dirección, enlaces de paginación y de feed en la lista
  que no van en el sitemap, la canónica repetida en dos etiquetas iguales, una cabecera `X-Robots-Tag: bingbot: noindex` con
  `max-image-preview:none`, un índice de sitemaps que lleva al de las noticias, y un robots.txt que prohíbe `/noticias/` pero permite
  `/noticias/prueba-` (gana la regla más larga). Con 51 variantes rotas falla exactamente la que toca cada rotura: lista ordenada por
  fecha de modificación o por creación (01), fecha de la corrección de C o «17 de octubre» en la lista (02), titular antiguo en C (04),
  ficha de A sin entradilla o con la fecha de la corrección (05), sin fuente (06), sin crédito (07), imagen rota, `src` vacío, `srcset`
  roto, `source` sin `srcset` o foto ausente (08), rótulo «Fuente:» vacío, también en mayúsculas (09), D accesible (10), registro
  `JUEGO` sin D o con D publicada (10 y 11, que parten las dos de él), D en la portada con enlace, con `&nbsp;` en el titular, o partida
  en dos `span` en la lista (11), E accesible, en la portada (con enlace o con `&nbsp;`) o sin registro (12), otro `headline` o la
  imagen del `NewsArticle` que no es la foto (13), `headline` de F distinto del `h1` (14), fechas sin zona, F sin corregir, y
  `dateModified` igual en todas (hora de compilación), igual a la creación de cada noticia (F después de C) o igual a `datePublished`
  (15), sitemap con D, sin F o sin G (16), G y H fuera de la lista y del sitemap (16, 22 y 23), sitemap con localhost (18), robots.txt
  sin `Sitemap:` (19), robots.txt que bloquea `/noticias/` a todos o solo a Googlebot, y `noindex` en `meta` o en cabecera (20),
  canónica relativa o dos canónicas distintas (21), G y H en la misma dirección (16 y 22), y direcciones con «ñ» o con mayúsculas (23).
  Solo cinco roturas tumban más de un test, por diseño: un JSON-LD sin escapar `</script>` tira la 14 y la 15, que lo leen las dos; un
  sitemap mal formado tira la 17 y, con ella, la 16 y la 18, que lo leen; un registro `JUEGO` sin D tira la 10 y la 11, que parten de
  él; y G y H en una sola dirección, o fuera de la lista, tiran la 22 (y la 23) y la 16, que sin las dos direcciones no puede comprobar
  las seis publicadas. Con `-O` ninguna corre: salen 3 sin dar por bueno un sitio roto. La 24, servida a través de un proxy local con
  un dominio real y público (`example.com` y una IP pública), pasa con un sitio publicado limpio y falla si lleva el juego (A en la
  lista) o si G solo sale en el sitemap; sin `DOMINIO`, con uno local escrito como sea (`127.1`, `2130706433`, `0x7f.1`, `localhost`,
  `[::1]`, una IP privada, `.local`, `.test`) o con un nombre que resuelve a esta máquina (`127.0.0.1.nip.io`), falla sin hacer
  ninguna petición. Contra las mismas variantes, las comprobaciones de la versión anterior de esta spec dejaban pasar D o E con
  `&nbsp;` en la portada, el `dateModified` por creación, el registro sin D en la 11 y G y H fuera de la lista en la 16.

## 7. Puertas

- `bash ~/.claude/bin/spec_valida.sh docs/specs/LET-02-seccion-de-noticias.md` ⇒ exit 0 («OK: … (44 criterios, cada uno con su test u orden)»).
- El contrato del repo (`DEC-L-004`) declara `test_uno` = `bash tests/puerta.sh test {ruta}` y la puerta `let-02` = `bash tests/puerta.sh let-02`
  ⇒ exit 0: carga el juego, compila el sitio con él, lo sirve en local, exporta `SITIO`, `DOMINIO` y `JUEGO`, corre las 23 de
  `python3 tests/test_noticias.py` y después las 19 de `python3 tests/test_noticias_compilacion.py` (CA-LET-02-25 a 43, sin servidor), y al acabar recompila la producción para que `sitio/dist` no se quede con el juego (CA-LET-02-44).
  `tests/puerta.sh` lo crea LET-01; este ítem le añade el juego de pruebas y la puerta `let-02`.
- Hecho en local, sobre la compilación de producción servida con el juego cargado y su registro `JUEGO`: `python3 tests/test_noticias.py`
  ⇒ exit 0 (hoy, exit 1). Tras cada despliegue: `python3 tests/test_noticias_publicado.py` ⇒ exit 0 (hoy, exit 1). La primera es lo que corre la
  puerta `let-02`; la segunda se corre tras cada despliegue, fuera de las puertas locales.
