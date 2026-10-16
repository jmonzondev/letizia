# SPEC-LET-03 — Redes embebidas y consentimiento de cookies

> **Estado:** BORRADOR · **Fecha:** 2026-10-16 · **Aprobada por:** — (validada por Jose el 2026-10-16, `DEC-L-005`)
> Pasa a APROBADA al cerrar con la clienta, en la Fase 0, las decisiones D1, D2, D3 y D5 (§6); D6 quedó decidida el 2026-10-16
> (`DEC-L-003`: Astro estático en IONOS). D4, D7 y D8 se toman con su recomendación y se cuentan al cierre. No se construye hasta entonces.
> Plan aprobado: `~/Code/cuaderno/encargos/2026-10-13_flujo_universal/ensayos/plan_letizia_m1.md` (ítem LET-03: «Instagram y TikTok
> embebidos; nada de terceros se carga sin consentimiento de cookies»).

## 1. Problema

Hoy no hay web. Quien busca a El Archivo de Talavera solo la encuentra en Instagram y TikTok, y quien no usa esas redes no ve su
trabajo. La propuesta promete una web propia «con las redes embebidas» y «analítica con consentimiento»
(`docs/presupuesto/01-propuesta.md:14` y `:46`).

Lo que le duele al visitante en las webs que embeben redes: al abrir la página ya se cargan Meta y TikTok y le siguen sin haberlo
permitido; el aviso de cookies solo deja aceptar, tapa media pantalla del móvil o vuelve a salir en cada página; y donde iba el vídeo
queda un hueco en blanco si ha dicho que no, si usa un bloqueador o si la publicación ya no existe.

A la clienta le duele lo mismo desde el otro lado. Ella responde de su web si un tercero instala cookies sin permiso, y la guía de la
AEPD pide desde el 11-01-2024 que «Rechazar» esté en la primera capa, al mismo nivel y con el mismo formato que «Aceptar». Quiere que
sus publicaciones se vean y que quien rechaza tenga al menos el enlace a ellas, sin tener que entender de cookies.

## 2. Alcance

- **Dentro:**
  - Aviso de cookies en la primera visita con «Aceptar», «Rechazar» y «Configurar» al mismo nivel, que enlaza a la página de cookies.
  - Panel «Configurar» por finalidades («Redes sociales»; «Analítica» solo si la decisión D3 la incluye), todo apagado de partida.
  - La elección se recuerda 12 meses en todas las páginas y visitas, y se cambia o se retira desde «Configurar cookies» en el pie de
    todas las páginas.
  - Bloqueo previo de cualquier recurso de otro dominio (redes, analítica, tipografías, mapas, librerías, iconos, preconexiones) hasta
    que se consienta su finalidad, en todas las páginas, con JavaScript y sin él, también lo que se cargue tarde o al moverse por la
    página.
  - Embebidos de Instagram y TikTok en la portada (D2): tarjeta sustituta mientras no haya consentimiento, carga sin recargar al
    aceptar y enlace a la publicación si no cargan, fallen al momento o no respondan.
  - En la página de cookies de LET-01: los terceros que se cargan con consentimiento, el registro de la elección y su plazo (LET-01
    deja «cookies de terceros en la página de cookies» a este ítem).
  - Cómo se ven y se usan el aviso y los embebidos en un móvil de 375 px, en un escritorio de 1280 px y solo con el teclado.
  - Tests de caja negra en `tests/sitio/` contra `SITIO_URL`, que no salen a Instagram ni a TikTok.
  - Tope del ítem: las 3–5 h de embebidos (`docs/presupuesto/01-propuesta.md:54`) y la parte de consentimiento de las 2–3 h de
    «páginas legales y consentimiento de cookies» (`:55`), que comparte con las páginas legales de LET-01. Si al implementar no cabe,
    se avisa antes de pasarse (condición 4, `docs/presupuesto/02-condiciones.md:10`).
- **Fuera:**
  - Estructura, plantilla, cabecera, menú, pie, aviso legal, privacidad y el resto de la página de cookies → LET-01.
  - Feed automático con las últimas publicaciones (API, cuenta profesional, claves que caducan) → decisión D1; si se elige, ítem nuevo
    con su coste de renovar las claves (`docs/presupuesto/01-propuesta.md:183`).
  - Publicar o programar en Instagram y TikTok desde la web → módulo M6 (`docs/presupuesto/01-propuesta.md:119-130`).
  - Elegir y dar de alta la analítica → decisión D3. LET-01 y LET-02 la mandan aquí, pero este ítem solo garantiza que, si la hay, no
    carga sin consentimiento.
  - Registro en servidor de cada consentimiento como prueba ante la AEPD → decisión D5, que depende del hosting (D6).
  - Botones de compartir, comentarios de Facebook o píxeles de publicidad → no contratado (`docs/presupuesto/02-condiciones.md:7`):
    presupuesto aparte si la clienta lo pide.
  - Velocidad de carga con los embebidos ya aceptados → hueco del plan: el «SEO técnico base (velocidad)» de M1
    (`docs/presupuesto/01-propuesta.md:46`) no está en LET-01, LET-02 ni LET-03; LET-01 lo deja como decisión abierta y lo asigna el
    orquestador.
  - Enlaces de Instagram o TikTok pegados en el texto de una noticia (WordPress los convierte en el embebido oficial y se saltaría el
    aviso) → al fijar el gestor (D6), una noticia así entra en el juego de pruebas de LET-02; CA-LET-03-01 ya recorre todas las
    páginas del sitemap.
  - Prueba con la red real de que cada embebido muestra la cuenta de la clienta → humo informativo tras el despliegue (ítem de
    despliegue que propone LET-01), no criterio: depende de Meta y TikTok.
  - Borrar las cookies que Instagram o TikTok ya instalaron cuando se retira el consentimiento → el sitio no puede (son de otro
    dominio); cómo borrarlas desde el navegador es texto de la página de cookies de LET-01.
  - Arreglar los embebidos cuando Meta o TikTok cambien sus reglas después de aceptado el módulo → mantenimiento o bolsa de horas
    (`docs/presupuesto/02-condiciones.md:28`).

## 3. Estado actual medido

- Nada hoy: en la base `36baa95` (26 ficheros versionados; lo anterior a este ítem) no hay sitio, plantillas, aviso de cookies,
  embebidos ni tests. `git ls-tree -r --name-only 36baa95 | grep -iE '\.(html?|astro|php|jsx?|tsx?|css|scss|xml)$|package\.json'`
  sale con 1, y `git grep -nliE 'cookie|consentim|instagram|tiktok|embed|iframe|gtag|analytics|umami' 36baa95 -- . ':!*.md'`
  también: esas palabras solo salen en los `.md` del presupuesto. En esa base no existe `tests/`
  (`git ls-tree -r --name-only 36baa95 | grep -c '^tests/'` da 0): lo único que hay ahí ahora es el test de este ítem.
- `docs/presupuesto/calcular_tarifas.py:14` — único código Python: presupuesta M1 como un solo bloque de 32–43 h, sin separar los
  embebidos ni el consentimiento.
- `.claude/contrato.json:3` (el contrato del repo) — `"puertas": []`: no hay ninguna puerta que correr.
- `.claude/contrato.json:4` — `"test_uno": ""`: no hay ninguna forma fijada de correr un test.
- `.claude/contrato.json:16` — `"navegador": false`: 21 de los 22 criterios necesitan Chromium sin ventana.
- Maquetas, fuera del repo, en `~/Code/cuaderno/proyectos/letizia/artefactos/`:
  - `maquetas/Landing.dc.html:11` — pide Cinzel, Dancing Script, EB Garamond y Playfair Display a `fonts.googleapis.com`; lo mismo
    hacen 15 de las 20 maquetas (`Landing-movil.dc.html:11`, `Noticia.dc.html:11`…) y las 7 de `maquetas-limpias/`. Si LET-01
    hereda esas plantillas, el sitio llamaría a Google antes de cualquier consentimiento.
  - `maquetas/Landing.dc.html:137-143` — bloque «EN INSTAGRAM»: el enlace a @ELARCHIVODETALAVERA (`:138`) y tres portadas
    estáticas (`:141-143`) son `href="#"`. No hay embebidos de ninguna red (`grep -ciE 'tiktok-embed|instagram-media|<iframe'`
    da 0). TikTok solo sale como texto o enlace vacío: la frase de `:44`, el botón «TIKTOK» de `:47` (`href="#"`) y el contador
    «seguidores en TikTok» de `:178`.
  - `maquetas/Landing.dc.html:195-199` — en el pie, Instagram, TikTok y Cookies son `href="#"`; no hay aviso ni «Configurar
    cookies» (`grep -ciE 'consent|rechazar|configurar cookies'` da 0 en `Landing`, `Landing-movil` y `Noticia`).

## 4. Reglas de negocio

- `RN-LET-03-01` — El sitio **no debe** pedir nada a otro dominio, ni referenciarlo (preconexiones, precargas, iconos), sin que el
  visitante haya consentido la finalidad de ese recurso.
- `RN-LET-03-02` — El sitio **no debe** guardar en el navegador nada distinto de la elección de cookies del visitante.
- `RN-LET-03-03` — En la primera visita, el sitio **debe** mostrar un aviso con «Aceptar», «Rechazar» y «Configurar» a la vista sin
  desplazarse.
- `RN-LET-03-04` — Rechazar **debe** costar lo mismo que aceptar: un clic en un botón del mismo tamaño y aspecto.
- `RN-LET-03-05` — El aviso **no debe** impedir leer ni navegar por la web, ni en el móvil ni en el escritorio.
- `RN-LET-03-06` — Desplazarse, navegar o cerrar el aviso sin elegir **no debe** contar como aceptar.
- `RN-LET-03-07` — «Configurar» **debe** dejar elegir por finalidad, con todas las finalidades apagadas de partida.
- `RN-LET-03-08` — El panel **debe** nombrar los terceros de cada finalidad.
- `RN-LET-03-09` — El aviso **debe** enlazar a la página de cookies.
- `RN-LET-03-10` — La página de cookies **debe** nombrar los terceros que se cargan con consentimiento, el registro que guarda la
  elección (por su nombre exacto) y su plazo.
- `RN-LET-03-11` — La elección **debe** recordarse en todas las páginas y visitas durante 12 meses (365 días, D4).
- `RN-LET-03-12` — Una elección caducada o ilegible **debe** tratarse como si no hubiera elección.
- `RN-LET-03-13` — El visitante **debe** poder cambiar su elección desde un enlace en el pie de todas las páginas.
- `RN-LET-03-14` — Retirar el consentimiento **debe** cortar los terceros desde la siguiente página que se abra.
- `RN-LET-03-15` — Sin consentimiento de redes, cada embebido **debe** verse como una tarjeta que dice de qué red es y enlaza a la
  publicación.
- `RN-LET-03-16` — Al aceptar redes (desde el aviso, el panel o una tarjeta), los embebidos **deben** cargarse sin recargar la página.
- `RN-LET-03-17` — Si un embebido no carga, **debe** quedar a la vista el enlace a la publicación en lugar de un hueco.
- `RN-LET-03-18` — En el móvil, los embebidos **no deben** provocar desplazamiento horizontal.
- `RN-LET-03-19` — El aviso **debe** poder usarse solo con el teclado.

## 5. Criterios de aceptación

Las órdenes se corren desde la raíz del repo con `SITIO_URL` exportada; los tests, con la orden de §7. Ningún test sale a Instagram ni
a TikTok: el navegador corta toda petición a otro dominio y la anota; cuando un criterio necesita que las redes «carguen», el test
responde con un embebido simulado del ancho mínimo de los oficiales (326 px Instagram, 325 px TikTok), y cuando necesita que no
carguen, las corta al momento o las deja sin respuesta. «Pedir a otro dominio» es cualquier petición que salga del navegador (también
por WebSocket); al recorrer las páginas cuenta además lo que la página referencia de otro dominio aunque no llegue a pedirlo
(`preconnect`, `dns-prefetch`, precargas, iconos, hojas de estilo, guiones, marcos, imágenes, vídeos y sonidos); los enlaces `<a>` no
cuentan, porque las tarjetas enlazan a las redes. «Recorrer todas las páginas» es abrir las seis de LET-01, `/noticias/`, cada
dirección del sitemap de LET-02 (la que señala `robots.txt`, o `/sitemap.xml`) y una que no existe, `/no-existe-ca-let-03/`. «Dejar
reposar» una página es, con ella ya cargada, mover el ratón, bajar con la rueda hasta el final y esperar a que la red quede quieta y
5 segundos más (la portada reposa 15): así cuenta también lo que el sitio pida o guarde tarde, al moverse o al bajar. Los botones y
enlaces se reconocen por su nombre accesible (el que lee un lector de pantalla), así que da igual que se pinten en mayúsculas.

- `CA-LET-03-01` (RN-LET-03-01) — Dado un navegador sin nada guardado, cuando recorre todas las páginas y deja reposar cada una,
  entonces todas las peticiones van al dominio del sitio y ninguna página referencia otro dominio: ni Instagram, ni TikTok, ni
  analítica, ni tipografías, ni mapas, ni librerías de fuera, ni preconexiones ni iconos → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_01_sin_consentimiento_solo_se_pide_al_propio_dominio`
- `CA-LET-03-02` (RN-LET-03-01) — Dado el sitio servido, cuando se descarga la portada sin ejecutar nada y se lee su HTML entero
  (aunque una etiqueta ocupe varias líneas, lleve espacios junto al `=` o comillas simples; sin contar comentarios, `<template>` ni el
  texto de los guiones en línea), entonces no lleva ningún `<script>` ni `<iframe>` cuyo `src` apunte a otro dominio (vale con o sin
  barra final en `SITIO_URL`; sin sitio, la orden falla; `command grep` salta cualquier función o alias llamado `grep`, porque con
  `-v` y sin entrada el binario devuelve 1 y hay sustitutos que devuelven 0) → orden: `u="${SITIO_URL:?}"; u="${u%/}"; h=$(printf '%s' "$u" | sed -E 's#^[a-zA-Z]+://##; s#/.*##' | tr '[:upper:]' '[:lower:]'); p=$(curl -sfL "$u/") && ! printf '%s' "$p" | perl -0777 -ne 's{<!--.*?-->}{}gs; s{<template\b.*?</template>}{}gis; s{(<script\b[^>]*>).*?</script>}{$1}gis; print lc($1), "\n" while m{<(?:script|iframe)\b[^>]*?\ssrc\s*=\s*["\x27]?\s*(?:https?:)?//([^/"\x27\s>?#]+)}gi' | command grep -qvxF "$h"` ⇒ exit 0
- `CA-LET-03-03` (RN-LET-03-01) — Dado un navegador con JavaScript desactivado, cuando recorre todas las páginas y deja reposar cada
  una, entonces tampoco pide nada a otro dominio ni lo referencia (ningún `<noscript>`, marco, imagen, guion, preconexión o icono de
  fuera en el HTML) → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_03_sin_javascript_tampoco_se_pide_a_otro_dominio`
- `CA-LET-03-04` (RN-LET-03-02) — Dado un navegador sin nada guardado, cuando abre la portada, la deja reposar, pulsa «Rechazar» y la
  deja reposar otra vez, entonces antes de elegir no hay ninguna cookie (tampoco las `HttpOnly` que ponga el servidor) ni nada en
  `localStorage` o `sessionStorage`, y después solo queda `consentimiento` en `localStorage`, con `"v": 1`, `"redes": false` y
  `"fecha"` como texto ISO 8601 con zona, la del momento de elegir (±5 minutos) → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_04_antes_de_elegir_nada_guardado_y_al_rechazar_solo_la_eleccion`
- `CA-LET-03-05` (RN-LET-03-03) — Dado un móvil de 375×667 sin nada guardado, cuando abre cada una de las seis páginas de LET-01 y
  `/noticias/`, entonces ve el aviso con «Aceptar», «Rechazar» y «Configurar» enteros dentro de la pantalla, sin desplazarse → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_05_primera_visita_muestra_aviso_con_tres_opciones_en_movil`
- `CA-LET-03-06` (RN-LET-03-04) — Dado el aviso abierto en un móvil de 375×667 y en un escritorio de 1280×800, sin foco ni ratón
  encima, cuando se comparan «Aceptar» y «Rechazar», entonces son el mismo elemento, con el mismo tamaño, peso, estilo, familia,
  interlineado, espaciado y mayúsculas de letra; el mismo color de texto y de fondo, la misma imagen o degradado de fondo, la misma
  sombra, los mismos cuatro bordes y esquinas, el mismo subrayado, sombra de texto, contorno y relleno; la misma opacidad (contando la
  de sus contenedores) y los mismos filtros; y el mismo ancho y alto (±2 px); y un solo clic en «Rechazar» cierra el aviso y deja a la
  vista el centro del contenido → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_06_rechazar_cuesta_lo_mismo_que_aceptar`
- `CA-LET-03-07` (RN-LET-03-05) — Dado el aviso abierto y sin elegir, cuando el visitante gira la rueda en el móvil y en el escritorio
  y pulsa «Quiénes somos» en la cabecera o el menú del escritorio (los de LET-01), entonces la página se desplaza y llega a
  `/quienes-somos/` → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_07_aviso_abierto_no_impide_desplazarse_ni_navegar`
- `CA-LET-03-08` (RN-LET-03-05) — Dados un móvil de 375×667 y un escritorio de 1280×800, cuando sale el aviso, entonces en cada uno
  ocupa como mucho el 40 % del alto de la pantalla (umbral propuesto, a validar con la clienta) → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_08_aviso_ocupa_como_mucho_el_40_por_ciento_en_movil_y_escritorio`
- `CA-LET-03-09` (RN-LET-03-06) — Dado el aviso abierto, cuando el visitante se desplaza, pulsa Escape, pulsa uno a uno todos los
  elementos visibles del aviso que no son los tres botones ni un enlace que lleva a otra página (sin mirar si parecen un mando: así
  entra el de cerrar, se llame como se llame, «Cerrar», «×», «✕» o un icono sin nombre ni cursor de mano, y sea un botón, un enlace
  a ninguna parte, un `<svg>` suelto o cualquier elemento que reaccione al clic; el panel `#panel-cookies` queda fuera porque tiene
  sus propios criterios), pasa a otra página, vuelve a la portada y la deja reposar, entonces no queda guardado ningún
  consentimiento a redes y no se ha pedido nada a otro dominio → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_09_navegar_o_cerrar_el_aviso_no_es_aceptar`
- `CA-LET-03-10` (RN-LET-03-07) — Dado el aviso, cuando pulsa «Configurar», entonces ve la casilla «Redes sociales» y ninguna
  finalidad encendida («Analítica» tampoco, si D3 la añade), y «Guardar» sin tocar nada cierra el panel y el aviso, guarda un rechazo
  como dice el contrato y la portada, al volver a abrirla y dejarla reposar, no pide nada a otro dominio → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_10_configurar_muestra_finalidades_apagadas_y_guardar_es_rechazar`
- `CA-LET-03-11` (RN-LET-03-08) — Dado el panel de configuración, cuando se lee, entonces nombra a Instagram, a Meta y a TikTok,
  cada uno como palabra entera («metadatos» no nombra a Meta) →
  test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_11_panel_nombra_los_terceros_de_redes`
- `CA-LET-03-12` (RN-LET-03-09) — Dado el aviso, cuando se leen sus enlaces, entonces uno lleva a `/cookies/` (la dirección de LET-01)
  y esa página responde 200 → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_12_aviso_enlaza_a_la_pagina_de_cookies`
- `CA-LET-03-13` (RN-LET-03-10) — Dada `/cookies/`, cuando se lee su contenido (`<main>` o `role="main"`, sin cabecera ni pie), entonces
  nombra a Instagram, Meta y TikTok como palabras enteras («metadatos» no nombra a Meta), el registro por su nombre exacto
  (`<code>consentimiento</code>` o «consentimiento», entre comillas; «tu consentimiento» dentro de una frase no lo nombra) y su plazo
  de «12 meses» → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_13_pagina_de_cookies_nombra_terceros_registro_y_plazo`
- `CA-LET-03-14` (RN-LET-03-11) — Dado que el visitante ha pulsado «Aceptar» (un caso) o «Rechazar» (otro), cuando abre otra página y
  cuando vuelve 11 meses después con lo que guardó su navegador (un contexto nuevo con ese estado, con la fecha del registro de hace
  11 meses), entonces el registro sigue el contrato, el aviso no vuelve a salir (se le dan 5 segundos en cada página, los mismos que
  se le dan en CA-LET-03-15 a un aviso que tarda) y la portada carga las dos redes si aceptó, o no pide nada a otro dominio al dejarla
  reposar si rechazó → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_14_la_eleccion_se_recuerda_entre_paginas_y_visitas`
- `CA-LET-03-15` (RN-LET-03-12) — Dado un registro que no vale (guardado hace 12 meses y una semana, JSON roto, de una versión
  anterior, con fecha futura, sin fecha, con la fecha como número o `true` suelto; un caso por cada uno, siete), cuando abre la portada
  y la deja reposar, entonces vuelve a salir el aviso (aunque tarde unos segundos), no se pide nada a otro dominio y la página no da
  errores → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_15_eleccion_caducada_o_ilegible_vuelve_a_preguntar`
- `CA-LET-03-16` (RN-LET-03-13) — Dado que el visitante aceptó, cuando pulsa «Configurar cookies» en el pie (`<footer>` o
  `role="contentinfo"`) de cada página del recorrido (sin la que no existe), entonces se abre el panel con «Redes sociales» marcada →
  test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_16_enlace_del_pie_reabre_el_panel_en_todas_las_paginas`
- `CA-LET-03-17` (RN-LET-03-14) — Dado que aceptó y la portada cargó las dos redes, cuando apaga «Redes sociales» desde el pie, guarda,
  abre de nuevo la portada y la deja reposar, entonces esa página no pide nada a Instagram, Meta ni TikTok y vuelve a mostrar las
  tarjetas → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_17_retirar_redes_corta_los_terceros_en_la_pagina_siguiente`
- `CA-LET-03-18` (RN-LET-03-15) — Dado que no hay consentimiento, cuando abre la portada, entonces hay al menos un hueco de cada red y
  cada uno es una tarjeta sin marco que nombra la red, avisa de que puede instalar cookies, tiene el botón «Aceptar y ver» y el enlace
  «Ver en Instagram» o «Ver en TikTok» a su publicación (`data-url`, que es de esa red) → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_18_sin_consentimiento_cada_embebido_es_una_tarjeta_con_enlace`
- `CA-LET-03-19` (RN-LET-03-16) — Dado que no hay consentimiento, cuando acepta redes desde el aviso, desde el panel o con «Aceptar y
  ver» de una tarjeta (un caso por vía), entonces, sin recargar la página, cada hueco recibe el marco de su red, se pide a las dos
  redes, la elección queda guardada como dice el contrato y, si solo aceptó redes (panel o tarjeta), no se pide nada a ningún otro
  dominio al dejarla reposar → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_19_aceptar_redes_carga_los_embebidos_sin_recargar`
- `CA-LET-03-20` (RN-LET-03-17) — Dado que aceptó redes y las peticiones a Instagram y TikTok fallan al momento (un caso, como con un
  bloqueador) o no reciben respuesta (otro, como con una red que no contesta), cuando pasan 10 segundos (el test espera 12), entonces
  cada hueco dice «No se ha podido cargar» y deja a la vista el enlace a su publicación, no un recuadro en blanco → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_20_si_el_embebido_no_carga_queda_el_enlace_a_la_red`
- `CA-LET-03-21` (RN-LET-03-18) — Dado un móvil de 375×667 que acepta redes, cuando los embebidos simulados ya están en su hueco,
  entonces el documento no es más ancho que la pantalla (`scrollWidth` ≤ 375) → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_21_en_movil_los_embebidos_no_desbordan`
- `CA-LET-03-22` (RN-LET-03-19) — Dado un navegador de escritorio sin nada guardado, cuando el visitante solo pulsa Tab, entonces llega
  a «Rechazar», «Aceptar» y «Configurar» (reconocidos por su nombre accesible, aunque se pinten en mayúsculas; lo que la página
  enfoque de partida también cuenta) antes que a nada del contenido, cada uno con el foco a la vista: al enfocarlo aparece un contorno
  o una sombra de color no transparente que no tenía en reposo (un contorno transparente, como el que deja `outline-none`, o una
  sombra que ya llevaba sin foco no sirven), y Enter sobre «Rechazar» cierra el aviso → test: `tests/sitio/test_let_03_redes_y_consentimiento.py::test_ca_let_03_22_el_aviso_se_usa_solo_con_teclado`

## 6. Contexto

**Qué leer antes de tocar nada**

- Plan aprobado (cabecera) y `README.md`, la única regla que fija el contrato del repo.
- `docs/presupuesto/01-propuesta.md:44-60` (M1: lo que incluye en `:46`, embebidos 3–5 h en `:54`, páginas legales y consentimiento
  de cookies 2–3 h en `:55`), `:183` (renovar claves de Instagram y TikTok es mantenimiento) y `:252` (el 70 % de cada módulo se
  cobra a la aceptación).
- `docs/presupuesto/02-condiciones.md:7`, `:10` y `:28` (lo que no aparece no está; el cambio de alcance se presupuesta aparte; los
  cambios de Meta y TikTok van a mantenimiento).
- `docs/presupuesto/03-cuestionario-fase0.md:14` (tipo de cuenta de Instagram), `:16` (TikTok), `:22` (Google: analítica) y `:29`
  (sus cinco publicaciones favoritas: de ahí salen las que se embeben, D1 y D2).
- SPEC-LET-01 (`docs/specs/LET-01-estructura-del-sitio-y-paginas-estaticas.md`, aprobada): fija las direcciones (`/cookies/`, `/quienes-somos/`), la cabecera, el menú y el pie,
  `SITIO_URL` y el entorno de tests que este ítem reutiliza, y su CA-LET-01-20 ya exige que nada se descargue de otro dominio en sus
  seis páginas.
- SPEC-LET-02 (`docs/specs/LET-02-seccion-de-noticias.md`, aprobada): el sitemap y `robots.txt` que CA-LET-03-01, 03 y 16 usan para recorrer todas las páginas.
- Norma: LSSI art. 22.2 y la guía de cookies de la AEPD (actualizada en julio de 2023, obligatoria desde el 11-01-2024): «Rechazar» en
  la primera capa, en el mismo sitio y con el mismo formato que «Aceptar»; la AEPD da como buena práctica que el consentimiento no
  dure más de 24 meses. Comprobado en la nota de prensa de la AEPD y en resúmenes publicados, no en el texto de la guía.
- Maquetas (§3) solo como referencia visual.

**Contrato de interfaz (lo que los tests dan por fijo)**

| Pieza | Cómo es |
|---|---|
| Aviso | `#aviso-cookies`, la caja del aviso que se ve (no un contenedor a pantalla completa), con tres botones cuyo nombre accesible es exactamente «Aceptar», «Rechazar» y «Configurar» (pueden pintarse en mayúsculas con CSS) y un enlace a `/cookies/`. Nada más de lo que tenga puede valer como aceptar: el test pulsa todo elemento visible del aviso que no sea uno de los tres botones ni un enlace a otra página (el de cerrar, se llame como se llame: un botón, un enlace a ninguna parte como `href="#"`, un `<svg>` o un icono sin nombre ni cursor de mano, o cualquier elemento que reaccione al clic). Con el teclado, al enfocar cada botón aparece un contorno o una sombra de color no transparente que no tenía en reposo |
| Panel | `#panel-cookies`, con una casilla cuya etiqueta dice «Redes sociales» (y «Analítica» si D3 la incluye) y el botón «Guardar». Nombra a Instagram, Meta y TikTok como palabras enteras |
| Cabecera y menú | Los de LET-01: `<header>` (o `role="banner"`) y `<nav>` (o `role="navigation"`), con el enlace «Quiénes somos» visible en el escritorio |
| Pie | `<footer>` (o `role="contentinfo"`), como en LET-01, con un enlace o botón de texto «Configurar cookies» que abre el panel con la elección actual marcada |
| Contenido | El de cada página va en `<main>` (o `role="main"`) |
| Huecos | `[data-embed="instagram"]` o `[data-embed="tiktok"]` con `data-url` = la publicación. Sin consentimiento, dentro: el nombre de la red, la palabra «cookies», el botón «Aceptar y ver» y el enlace «Ver en Instagram» o «Ver en TikTok» a `data-url`. Aceptado, el marco de la red va dentro del hueco. Si no carga: «No se ha podido cargar» y el enlace |
| Registro | `localStorage["consentimiento"]` = `{"v": 1, "fecha": "<texto ISO 8601 con zona>", "redes": true\|false}` (más `"analitica"` si D3 la incluye). No vale si la versión no es 1, la fecha falta, no es un texto ISO 8601, es futura o tiene más de 12 meses (365 días), o el JSON no se lee |
| Página de cookies | `/cookies/` (LET-01): en su `<main>` nombra a Instagram, Meta y TikTok como palabras enteras, el registro por su nombre exacto (`<code>consentimiento</code>` o «consentimiento», entre comillas) y el plazo «12 meses» |

**Entorno de los tests**

- Caja negra contra `SITIO_URL`, la misma variable que LET-01 (la propuesta de partida la llamaba `BASE_URL`). No dependen del stack ni
  del hosting. `uv` con Python 3.12, pytest 8.4.2 y Playwright 1.56.0 (Chromium 141, sin ventana); si falta el navegador:
  `uv run --no-project --with playwright==1.56.0 playwright install chromium`. La orden de CA-LET-03-02 usa `curl` y `perl`.
- Ningún test depende de Meta ni de TikTok: la aceptación del módulo, de la que depende el 70 % del pago, no puede quedar en sus manos.
- Los tests se han probado (14-oct, en una copia aparte del árbol) contra un sitio estático mínimo que cumple la spec: los 31 casos
  en verde y la orden de CA-LET-03-02 con exit 0, en bash y en zsh, con y sin barra final en `SITIO_URL`. El primer intento de ese
  sitio dejaba al `<blockquote>` de TikTok sus márgenes por defecto y la portada medía 381 px en el móvil: lo cazó CA-LET-03-21.
  Y, con la suite entera, contra tres variantes que se saltan un criterio cada una, y cada una cae solo en el test de su criterio:
  los botones enfocados llevan un contorno transparente (`outline: 2px solid transparent`, lo que deja `outline-none`; cae solo
  CA-LET-03-22); llevan sombra siempre y `outline: none` al enfocar (solo CA-LET-03-22); el «×» del aviso es un `<svg>` sin nombre,
  sin `tabindex` ni `onclick` y con el cursor normal que acepta y carga las redes (solo CA-LET-03-09). Con solo su test u orden:
  el «×» es un `<a href="#" aria-label="Cerrar">` que acepta y el «×» es un `<span>` suelto, sin papel ni atributos, que acepta
  (cae CA-LET-03-09 en los dos), y la portada lleva un `<script src='https://www.instagram.com/embed.js'>` partido en dos líneas y
  con espacios junto al `=` (la orden de CA-LET-03-02 sale con 1). CA-LET-03-05, 06, 09, 12 y 22 siguen en verde cuando el aviso
  sale 3 s tarde y los botones se pintan en mayúsculas por CSS. En la vuelta anterior del mismo día, con estos mismos tests salvo
  CA-LET-03-09 y CA-LET-03-22, cayeron solo en su criterio el panel y `/cookies/` que dicen «metadatos» sin nombrar a Meta
  (CA-LET-03-11 y 13) y la elección que caduca en una hora en vez de en 12 meses (CA-LET-03-14, en sus dos casos).

**Decisiones abiertas (dejan la spec en BORRADOR)**

- D1 — ¿Qué se embebe? Recomendado: las publicaciones que elija la clienta, con el embebido oficial y sin claves (cabe en las 3–5 h).
  La otra opción, las últimas de forma automática, pide API, cuenta profesional y claves que caducan: sería un ítem nuevo.
- D2 — ¿Dónde y cuántas? Propuesta: solo en la portada, al menos una publicación de Instagram y un vídeo de TikTok (la maqueta pone
  tres de Instagram y ninguno de TikTok). Si cambia la página, solo cambia `PAGINA_CON_REDES` en el test.
- D3 — ¿Lleva M1 analítica, y cuál? Hay un choque: `01-propuesta.md:46` dice «analítica con consentimiento» y la propuesta v6
  (`~/Code/cuaderno/proyectos/letizia/artefactos/docs/2026-10-08_el-archivo-de-talavera-propuesta_v6-final.md:182` y `:285`) dice
  Umami «sin cookies». Si es sin cookies y se sirve desde el propio dominio, el panel solo tiene «Redes sociales»; si va a otro
  dominio, solo carga con «Analítica» aceptada.
- D5 — ¿Se guarda en el servidor un registro de cada consentimiento? Depende del hosting.
- D6 (del plan) — Decidida el 2026-10-16 (`DEC-L-003`): Astro estático en IONOS, con editor propio. No cambia los criterios, sí cómo se cumplen.

**Decisiones tomadas con recomendación (se cuentan al cierre, no se preguntan)**

- D4 — La elección dura 12 meses (365 días), acepte o rechace: por debajo de los 24 que la AEPD da como máximo recomendable. Los
  tests lo fijan por los dos lados: un registro de hace 11 meses sigue valiendo (CA-LET-03-14) y uno de hace 12 meses y una semana ya
  no (CA-LET-03-15).
- D7 — El aviso se hace con código propio servido desde el sitio, sin un gestor de consentimiento de fuera (chocaría con
  RN-LET-03-01). Cabe en las 2–3 h.
- D8 — Tests con pytest y Playwright contra `SITIO_URL`, como LET-01. El contrato del repo ya declara `test_uno` y `"navegador": true`
  (`DEC-L-004`); la puerta `let-03` se declara al construir este ítem.

## 7. Puertas

El contrato del repo (`DEC-L-004`) declara `test_uno` = `bash tests/puerta.sh test {ruta}` y `navegador: true`; la puerta `let-03`
(`bash tests/puerta.sh let-03`, que corre lo de abajo) se declara al construir este ítem. Las puertas de este ítem:

- `bash ~/.claude/bin/spec_valida.sh docs/specs/LET-03-redes-embebidas-y-consentimiento-de-cookies.md` ⇒ exit 0 con «OK: … (22
  criterios, cada uno con su test u orden)».
- `grep -rhoiE 'ca_let_03_[0-9]{2}' tests | sort -u | wc -l` ⇒ 21: todos los criterios tienen su test menos CA-LET-03-02, que es
  una orden.
- `PYTHONDONTWRITEBYTECODE=1 SITIO_URL=<sitio> uv run --no-project --python 3.12 --with pytest==8.4.2 --with playwright==1.56.0 pytest -p no:cacheprovider -q tests/sitio -k let_03`
  ⇒ exit 0 (21 tests, 31 casos; entre 5 y 8 minutos, casi todo en dejar reposar las páginas). `PYTHONDONTWRITEBYTECODE` y
  `-p no:cacheprovider` evitan dejar cachés en el repo mientras no haya `.gitignore`.
- La orden de CA-LET-03-02 ⇒ exit 0.
- Hoy, sin sitio, los 31 casos salen con exit 1 («El sitio no responde») y la orden con exit 7 (`curl` no conecta).
