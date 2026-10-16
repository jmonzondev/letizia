# SPEC-LET-01 — Estructura del sitio y páginas estáticas

> **Estado:** APROBADA · **Fecha:** 2026-10-16 · **Aprobada por:** Jose
> Aprobada por Jose el 2026-10-16 (`DEC-L-005`) con D1 decidida (`DEC-L-003`: Astro, formulario en PHP). Siguen abiertas con la
> clienta D2 a D8 (§6) y sus materiales: no cambian los criterios; `tests/sitio/titular.json` se rellena con sus datos reales.
> Plan aprobado: `~/Code/cuaderno/encargos/2026-10-13_flujo_universal/ensayos/plan_letizia_m1.md` (ítem LET-01 y su «Fuera»).

## 1. Problema

Quien sigue a El Archivo de Talavera en Instagram o TikTok no tiene una web propia a la que ir. Desde las redes no sabe quién está
detrás ni quién es la titular, y para escribirle tiene que mandar un mensaje privado. La clienta tampoco tiene un sitio suyo que
enseñar a los anunciantes y a quienes le mandan noticias. La propuesta pone esa web como primer objetivo: «una web propia que
posicione en Google, con noticias, contacto, quiénes somos» (`docs/presupuesto/01-propuesta.md:14`).

Lo único que hay es la maqueta preparada para la reunión del 8-oct, y no sirve como web: no tiene «Quiénes somos», el formulario no
envía a ningún sitio, los enlaces del pie (aviso legal, privacidad y cookies) y el botón de WhatsApp no llevan a nada, y un solo hueco
para «teléfono o correo» impide contestar con un clic. Se ven restos de plantilla («hola@[tu dominio]», «[00.000] seguidores»), las
tipografías se descargan de Google sin consentimiento y la versión «móvil» es el mismo HTML a 390 px, sin etiqueta viewport.

Esta spec fija lo que la visitante encuentra en las páginas fijas del sitio, primero en el móvil, y lo que pasa cuando escribe por el
formulario, que trata datos personales. La sección de noticias (LET-02) y las redes con su consentimiento (LET-03) se montan encima.

## 2. Alcance

- **Dentro:**
  - Seis páginas en direcciones fijas: inicio `/`, quiénes somos `/quienes-somos/`, contacto `/contacto/`, aviso legal
    `/aviso-legal/`, privacidad `/privacidad/` y cookies `/cookies/`, más una página 404 propia.
  - Cabecera común con el logotipo (enlaza a inicio) y el menú Inicio · Quiénes somos · Contacto, que en el móvil se pliega tras un
    botón. Pie común con Aviso legal · Privacidad · Cookies. Cabecera, menú y pie marcados como tales para los lectores de pantalla.
  - Diseño móvil primero con la identidad actual de la marca (logotipo, colores y tipografías que entregue la clienta, partiendo de
    las maquetas), con las tipografías alojadas en el propio sitio, y el visto bueno escrito de la clienta.
  - Título y descripción propios en cada página, idioma declarado como castellano y etiqueta viewport de móvil.
  - Formulario de contacto: nombre, correo, mensaje, casilla de privacidad sin marcar que enlaza a la política e información básica
    de protección de datos. Entrega cada mensaje una vez, como texto, en el correo de la clienta, con respuesta directa a la
    visitante. Confirma en pantalla (y ese envío desde el navegador deja el mismo correo en el buzón), avisa del campo que falla sin
    borrar lo escrito, valida también en el servidor, no deja añadir destinatarios por ningún campo, lleva un campo trampa contra los
    envíos automáticos que ninguna persona puede rellenar, y no admite adjuntos ni en el formulario ni en el servidor.
  - Páginas legales con los datos de la titular: aviso legal y privacidad con la misma titular, y cookies que nombra cada cookie que
    pone el sitio en este ítem o dice que no pone ninguna.
  - Dos guardas: el sitio no entrega los ficheros de trabajo del repositorio y las credenciales del correo no entran en él.
  - Tests de caja negra en `tests/sitio/` contra `SITIO_URL`: valen igual con WordPress que con Astro.
- **Fuera:**
  - Lista y ficha de noticias, la entrada «Noticias» del menú, el sitemap, los datos estructurados y Search Console → LET-02.
  - Instagram y TikTok embebidos y los enlaces a los perfiles → LET-03.
  - Aviso de consentimiento de cookies, cookies de terceros en la página de cookies y analítica → LET-03.
  - «Envíanos tu noticia» con foto o vídeo (maqueta `Landing.dc.html:164`) → decisión D3. Mientras no se tome, CA-LET-01-26 y 32
    dejan el formulario sin adjuntos.
  - Bloque «Anúnciate» con cifras de seguidores y visitas (maqueta `Landing.dc.html:170-183`) → decisión D4.
  - Teléfono o botón de WhatsApp en contacto → decisión D5 (`docs/presupuesto/03-cuestionario-fase0.md:37`).
  - Qué ve la visitante si el correo no sale (un error con otra forma de contacto, nunca «enviado») → criterio que se añade cuando D1
    y D2 fijen cómo sale el correo: hoy no se puede provocar el fallo sin conocer el montaje.
  - Despliegue en IONOS, dominio, https, cabeceras de seguridad, página 404 sin la versión del servidor y que los envíos no se guarden
    en ficheros ni registros (condición 14, `docs/presupuesto/02-condiciones.md:40`) → decisión D8: ningún ítem del plan los recoge.
  - Velocidad de carga, parte del SEO técnico base de M1 (`docs/presupuesto/01-propuesta.md:46`) → decisión D6.
  - Quitar la ubicación (EXIF) de las fotos → LET-02, donde entran las fotos de noticias.
  - Redacción de los textos, fotografía y logotipo nuevo → los aporta la clienta (`docs/presupuesto/01-propuesta.md:48`).
  - Editor para que la clienta publique → LET-02 y decisión D1 (WordPress o Astro con editor).
  - SEO más allá del técnico base → módulo M8. Automatizaciones de correo, redacción y publicación → módulos M4 a M6.

## 3. Estado actual medido

- Nada de sitio hoy: en la base `36baa95` (26 ficheros) no hay páginas, plantillas, estilos, formularios ni configuración de servidor,
  y este commit solo añade la spec y sus tests (32 ficheros):
  `git ls-files | grep -iE '\.(html?|astro|php|jsx?|tsx?|css|scss|xml)$|package\.json|astro\.config|wp-config|robots|sitemap|\.htaccess'`
  sale con 1.
- `tests/sitio/` — lo único que hay de este ítem son sus propios tests (`test_let_01_contacto.py`, `test_let_01_movil.py`,
  `test_let_01_paginas.py`, su apoyo `apoyo_sitio.py` y `titular.json`, vacío a propósito); hoy fallan todos porque no hay sitio
  que pedir (§7).
- `docs/presupuesto/calcular_tarifas.py:14` — único código Python del repo fuera de `tests/`; la landing aparece solo como partida
  de horas: `("M1", "Landing y web de noticias", 32, 43)`. El resto del código son siete ganchos `.sh` del taller, ajenos al sitio.
- `.claude/contrato.json:3` — `"puertas": []`: ninguna puerta comprueba un sitio.
- `.claude/contrato.json:4` — `"test_uno": ""`: no hay ninguna orden del contrato para correr un test.
- `.claude/contrato.json:16` — `"navegador": false`: CA-LET-01-03, 06, 14, 15, 20, 31 y 33 necesitan Chromium sin ventana.
- `.claude/.gitignore:1-2` — solo ignora `settings.local.json` y `worktrees/`; no hay `.gitignore` en la raíz y
  `git -c core.excludesFile=/dev/null check-ignore --no-index -v .env` sale con 1: un `.env` con la clave del correo se podría
  subir. Sin `-c core.excludesFile=/dev/null`, la respuesta depende del ignore global de cada máquina, no del repo.
- `docs/DECISIONES.md:3` — «Siguiente id libre: `DEC-L-001`»; la tabla (`:9-10`, cabecera y separador) no tiene ninguna fila: no
  hay visto bueno de la clienta a ningún diseño.
- Maquetas, fuera del repo, en `~/Code/cuaderno/proyectos/letizia/artefactos/maquetas/`:
  - `Landing.dc.html:5` — el título es «Web automatizada · portada»; no hay `<meta name="description">` ni `<meta name="viewport">`
    (`grep -c viewport` da 0 aquí y en `Landing-movil.dc.html`).
  - `Landing.dc.html:11` — carga Cinzel, Dancing Script, EB Garamond y Playfair Display desde `fonts.googleapis.com`; servida en
    local, el navegador pide cinco ficheros a `fonts.googleapis.com` y `fonts.gstatic.com` en cada página.
  - `Landing.dc.html:20-29` — el logotipo es un enlace a `#inicio` hecho con texto: no hay imagen ni SVG con texto alternativo.
  - `Landing.dc.html:30-33` — el menú solo tiene Noticias, Envíanos tu noticia y Anúnciate, anclas de la misma página; no hay
    «Quiénes somos» (`grep -ic 'quién'` da 0).
  - `Landing.dc.html:154` y `:195-199` — el botón de WhatsApp y los enlaces del pie (Instagram, TikTok, Aviso legal, Privacidad,
    Cookies) son `href="#"`.
  - `Landing.dc.html:155` — «o a hola@[tu dominio]»; lo mismo en `:183` («publicidad@[tu dominio]») y las cifras «[00.000]» y
    «[000.000]» de `:177-179`. `:202` — pie «Maqueta · noticias reales…».
  - `Landing.dc.html:158` — el `<form>` no lleva `action` ni `method`: no envía a ningún sitio.
  - `Landing.dc.html:161` — un solo campo de texto libre «Teléfono o correo» (`name="contacto"`).
  - `Landing.dc.html:164` — pide «Foto o vídeo (opcional)» con `type="file"`.
  - `Landing.dc.html:165` — la casilla de privacidad no es obligatoria (no hay ningún `required` en el fichero), su texto no enlaza a
    la política y pide permiso para usar lo enviado «para informar», es decir, para publicarlo.
  - `Landing-movil.dc.html:5` y `:206` — es el mismo HTML que el de escritorio: `diff` solo cambia el título y el ancho de la vista
    previa (390 px frente a 1440).

## 4. Reglas de negocio

- `RN-LET-01-01` — El sitio **debe** servir seis páginas propias en direcciones fijas: `/`, `/quienes-somos/`, `/contacto/`,
  `/aviso-legal/`, `/privacidad/` y `/cookies/`.
- `RN-LET-01-02` — Desde cualquier página, la visitante **debe** poder llegar a cada una de las otras cinco con un toque en su
  enlace; en el móvil, tras abrir el menú con su botón (`DEC-L-002`: el menú plegado de CA-LET-01-03 se mantiene).
- `RN-LET-01-03` — Cada página **debe** tener un título propio, distinto del de las demás.
- `RN-LET-01-04` — Cada página **debe** tener una descripción propia, distinta de la de las demás.
- `RN-LET-01-05` — Cada página **debe** leerse entera en un móvil de 360 px de ancho sin desplazamiento horizontal.
- `RN-LET-01-06` — Cada página **debe** declarar que está en castellano.
- `RN-LET-01-07` — Ninguna página publicada **debe** mostrar huecos de plantilla.
- `RN-LET-01-08` — Cada página **debe** llevar en la cabecera el logotipo de la marca, con enlace a inicio.
- `RN-LET-01-09` — El formulario de contacto **debe** entregar cada mensaje válido, una sola vez, en el correo que fije la clienta.
- `RN-LET-01-10` — El correo que recibe la clienta **debe** llevar la dirección de la visitante solo como dirección de respuesta.
- `RN-LET-01-11` — El servidor **debe** rechazar cualquier envío que no traiga aceptada la política de privacidad.
- `RN-LET-01-12` — La casilla de privacidad del formulario **debe** enlazar a la política de privacidad.
- `RN-LET-01-13` — Tras un envío correcto, la visitante **debe** ver una confirmación en pantalla.
- `RN-LET-01-14` — Si falta un dato obligatorio o no es válido, la visitante **debe** ver qué campo falla sin perder lo que había escrito.
- `RN-LET-01-15` — El formulario **debe** descartar en silencio los envíos automáticos que rellenan el campo trampa.
- `RN-LET-01-16` — El aviso legal **debe** identificar a la titular con su nombre fiscal, NIF, domicilio y correo.
- `RN-LET-01-17` — Una dirección que no existe **debe** responder con una página 404 propia que lleve a inicio.
- `RN-LET-01-18` — Ninguna página **debe** descargar nada de otro dominio, tipografías incluidas, mientras no exista el
  consentimiento de LET-03.
- `RN-LET-01-19` — El sitio **no debe** entregar los ficheros de trabajo del repositorio (presupuestos, configuración, credenciales,
  tests).
- `RN-LET-01-20` — Las credenciales del correo del formulario **no deben** poder entrar en el repositorio.
- `RN-LET-01-21` — El servidor **debe** rechazar un envío sin nombre, sin mensaje o con un correo no válido.
- `RN-LET-01-22` — Nada de lo que escribe la visitante **debe** poder añadir destinatarios al correo.
- `RN-LET-01-23` — El correo **debe** reproducir el mensaje de la visitante letra por letra, como texto sin formato.
- `RN-LET-01-24` — El formulario **no debe** admitir adjuntos mientras la decisión D3 no diga lo contrario.
- `RN-LET-01-25` — La visitante **debe** marcar ella misma la casilla de privacidad para poder enviar.
- `RN-LET-01-26` — La visitante **debe** ver la información básica de protección de datos en el propio formulario.
- `RN-LET-01-27` — La política de privacidad **debe** identificar como responsable a la misma titular que el aviso legal.
- `RN-LET-01-28` — El diseño **debe** tener el visto bueno escrito de la clienta antes de dar el ítem por hecho.
- `RN-LET-01-29` — El campo trampa **no debe** poder rellenarlo una persona: ni se ve, ni lo anuncian los lectores de pantalla, ni
  recibe el foco.
- `RN-LET-01-30` — La página de cookies **debe** nombrar cada cookie que pone el sitio, o decir que no pone ninguna.

## 5. Criterios de aceptación

Las órdenes se corren desde la raíz del repo con `SITIO_URL` exportada; los tests, con la orden de §7.

- `CA-LET-01-01` (RN-LET-01-01) — Dado el sitio servido en `SITIO_URL`, cuando se piden las seis direcciones siguiendo las
  redirecciones, entonces las seis responden 200 → orden: `for p in "" quienes-somos/ contacto/ aviso-legal/ privacidad/ cookies/; do curl -sL -o /dev/null -w '%{http_code}\n' "$SITIO_URL/$p"; done | paste -sd' ' - | grep -qx '200 200 200 200 200 200'` ⇒ exit 0
- `CA-LET-01-02` (RN-LET-01-02) — Dada cualquiera de las seis páginas, cuando se leen los enlaces de su cabecera, menú y pie (por su
  etiqueta o su papel ARIA, §6), entonces hay uno a cada una de las otras cinco direcciones y ninguno es `href="#"` ni está vacío → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_02_cada_pagina_enlaza_a_las_otras_cinco`
- `CA-LET-01-03` (RN-LET-01-02) — Dado un móvil emulado de 360×740 en cualquiera de las seis páginas recién cargada, cuando se miran
  los enlaces del menú (los que están dentro de `<nav>` o `role="navigation"` y fuera del pie, §6) llamados Inicio, Quiénes somos y
  Contacto, entonces ninguno se ve: el menú está plegado; y cuando la visitante toca el botón del menú (su nombre accesible dice
  «menú»), entonces los tres aparecen en pantalla dentro del menú, con la página devuelta a donde estaba al cargar, y al tocar
  Contacto llega a `/contacto/`. «Se ve» es estar dentro de la pantalla, sin ocultar ni transparentar, y recibir el toque en su
  centro (no lo tapa ni lo recorta nada). Los mismos enlaces repetidos en el pie, o sueltos fuera de un `<nav>`, no cuentan ni para
  «plegado» ni para «aparecen», y desplazar la página hasta unos enlaces que ya estaban más abajo tampoco: un botón que solo baja
  hasta el pie no es un menú → test: `tests/sitio/test_let_01_movil.py::test_ca_let_01_03_menu_se_abre_y_lleva_a_contacto_a_360px`
- `CA-LET-01-04` (RN-LET-01-03) — Dadas las seis páginas, cuando se lee su `<title>`, entonces ninguno está vacío y los seis son
  distintos → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_04_titulos_propios_y_distintos`
- `CA-LET-01-05` (RN-LET-01-04) — Dadas las seis páginas, cuando se lee su `<meta name="description">`, entonces ninguna está vacía y
  las seis son distintas → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_05_descripciones_propias_y_distintas`
- `CA-LET-01-06` (RN-LET-01-05) — Dado un móvil emulado de 360×740 que respeta la etiqueta viewport, cuando se carga cada una de las
  seis páginas, entonces la página no es más ancha que la pantalla (`document.documentElement.scrollWidth <= 360`) → test: `tests/sitio/test_let_01_movil.py::test_ca_let_01_06_sin_desplazamiento_horizontal_a_360px`
- `CA-LET-01-07` (RN-LET-01-06) — Dadas las seis páginas, cuando se lee la etiqueta `<html>` entera (aunque sus atributos vayan en
  varias líneas), entonces hay una sola etiqueta `<html>` por página y lleva el atributo `lang` (no `data-lang` ni otro que acabe
  igual) con valor `es` o `es-ES`: la orden imprime por página «etiquetas `<html>`/etiquetas con ese `lang`» y las seis tienen que dar
  `1/1` (`2/1`, dos etiquetas y una sola con `lang`, no vale) → orden: `for p in "" quienes-somos/ contacto/ aviso-legal/ privacidad/ cookies/; do curl -sL "$SITIO_URL/$p" | tr '\n\r' '  ' | grep -oiE '<html[^>]*>' | awk 'tolower($0) ~ /[[:space:]]lang[[:space:]]*=[[:space:]]*.?es(-es)?([^a-z-]|$)/ {ok++} END {print NR "/" ok+0}'; done | paste -sd' ' - | grep -qx '1/1 1/1 1/1 1/1 1/1 1/1'` ⇒ exit 0
- `CA-LET-01-08` (RN-LET-01-07) — Dadas las seis páginas y la de error, cuando se busca texto de plantilla en lo que se lee de ellas
  (el texto fuera de scripts y estilos y los atributos `content`, `alt`, `title`, `placeholder`, `aria-label`, `value` y `href`), con
  las entidades HTML decodificadas (`&middot;`, `&nbsp;`) y los espacios juntos, entonces no aparece ningún texto entre corchetes
  («[tu dominio]», «[ ]», «[00.000]», «[Texto de quiénes somos]», «[Pendiente]»: en estas páginas no se publican corchetes), ninguna
  variable de plantilla sin sustituir («{{ … }}»), «lorem ipsum», «example.com», «example.org», «example.net» ni el pie «Maqueta ·»
  («TODO» y «XXX» no se buscan: chocan con titulares en mayúsculas y números romanos) → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_08_sin_huecos_de_plantilla`
- `CA-LET-01-09` (RN-LET-01-08) — Dadas las seis páginas, cuando se lee la cabecera (`<header>` o `role="banner"`, §6), entonces
  lleva el logotipo (imagen o SVG con texto alternativo «El Archivo de Talavera») dentro de un enlace a `/` → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_09_logotipo_en_cabecera_enlaza_a_inicio`
- `CA-LET-01-10` (RN-LET-01-09) — Dado el buzón de pruebas vacío, cuando se envía el formulario de `/contacto/` con nombre, correo,
  mensaje y la casilla marcada, entonces llega un único correo, dirigido solo a `CORREO_CONTACTO`, con el nombre, el correo y el
  mensaje escritos → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_10_mensaje_valido_llega_al_correo_de_la_clienta`
- `CA-LET-01-11` (RN-LET-01-10) — Dado un envío válido con el correo `visitante@ejemplo.es`, cuando se lee el correo recibido,
  entonces su `Reply-To` es `visitante@ejemplo.es` y su remitente (`From`) no lo es → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_11_responder_va_a_la_visitante`
- `CA-LET-01-12` (RN-LET-01-11) — Dado un envío directo a la dirección del formulario, sin navegador y sin el campo de la casilla de
  privacidad, cuando el servidor lo recibe, entonces no llega nada al buzón y la respuesta lleva `#envio-error` pidiendo aceptar la
  política de privacidad, sin `#envio-correcto` → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_12_sin_aceptar_privacidad_no_se_envia`
- `CA-LET-01-13` (RN-LET-01-12) — Dada `/contacto/`, cuando se lee la etiqueta de la casilla de privacidad, entonces contiene un
  enlace a `/privacidad/` → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_13_casilla_enlaza_a_privacidad`
- `CA-LET-01-14` (RN-LET-01-13 y RN-LET-01-09) — Dado un móvil emulado y el buzón de pruebas vacío, cuando la visitante rellena bien
  el formulario y toca Enviar, entonces ve, sin salir del sitio, `#envio-correcto` con «Gracias, hemos recibido tu mensaje.», y al
  buzón llega un único correo, dirigido solo a `CORREO_CONTACTO`, con el mensaje escrito (una confirmación sin correo detrás, como la
  de un envío con JavaScript que no manda nada, no cumple) → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_14_confirmacion_en_pantalla_tras_enviar`
- `CA-LET-01-15` (RN-LET-01-14) — Dado el formulario con el nombre y el mensaje escritos y el correo vacío, cuando la visitante toca
  Enviar, entonces ve el aviso del campo Correo, el nombre y el mensaje siguen escritos y no llega nada al buzón. El aviso es el del
  navegador (el campo dispara el evento `invalid`, que no salta si el formulario lleva `novalidate`) o el de la página (el campo
  lleva `aria-invalid="true"` y un aviso con texto, visible, enlazado por `aria-describedby`); que el campo vacío tenga un
  `validationMessage` no cuenta, se muestre o no → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_15_correo_que_falta_se_avisa_sin_perder_lo_escrito`
- `CA-LET-01-16` (RN-LET-01-15) — Dado un envío directo con el campo trampa `web` relleno, cuando el servidor lo recibe, entonces no
  llega nada al buzón y la respuesta es la misma confirmación `#envio-correcto` de un envío normal, sin `#envio-error` → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_16_envio_con_campo_trampa_no_llega`
- `CA-LET-01-17` (RN-LET-01-16) — Dada `/aviso-legal/`, cuando se lee, entonces muestra el nombre fiscal, el NIF, el domicilio y el
  correo de la titular tal como figuran en `tests/sitio/titular.json` (se rellena con el cuestionario,
  `docs/presupuesto/03-cuestionario-fase0.md:36`), y el NIF, NIE o CIF tiene su control válido → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_17_aviso_legal_identifica_a_la_titular`
- `CA-LET-01-18` (RN-LET-01-17) — Dada una dirección que no existe (`/no-existe-ca-let-01/`), cuando se pide, entonces responde 404
  con una página en castellano (`lang` igual a `es` o `es-ES`, la misma regla que CA-LET-01-07: `est` o `es-MX` no valen) que lleva
  el logotipo con enlace a `/` → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_18_pagina_404_propia_con_enlace_a_inicio`
- `CA-LET-01-19` (RN-LET-01-05) — Dadas las seis páginas, cuando se lee su `<meta name="viewport">`, entonces su contenido incluye
  `width=device-width` → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_19_etiqueta_viewport_de_movil`
- `CA-LET-01-20` (RN-LET-01-18) — Dado un móvil emulado, cuando se carga cada una de las seis páginas y la 404 y se desplaza cada
  una, pantalla a pantalla, hasta el final con la red en reposo (lo que se carga al llegar a la vista, como un iframe o una imagen
  `loading="lazy"`, cuenta), entonces ninguna petición va a un dominio distinto del de `SITIO_URL` → test: `tests/sitio/test_let_01_movil.py::test_ca_let_01_20_nada_se_descarga_de_otro_dominio`
- `CA-LET-01-21` (RN-LET-01-19) — Dado el sitio servido, cuando se piden `/.env`, `/.env.local`, `/.env.production` (los que lee
  Astro), `/wp-config.php`, `/.git/config`, `/.git/HEAD` y cada fichero de trabajo del repositorio según `git ls-files` (los `.md` de
  la raíz, `docs/`, `tests/` y lo que empieza por punto), entonces todos responden 4xx → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_21_no_sirve_ficheros_del_repositorio`
- `CA-LET-01-22` (RN-LET-01-20) — Dado el repositorio, cuando se pregunta a git, solo con el `.gitignore` versionado en la raíz (sin el
  ignore global de la máquina ni `.git/info/exclude`), si ignora `.env`, `.env.local`, `.env.production`, `sitio/.env`,
  `sitio/.env.production` y `wp-config.php` (los `.env.*` son los que leen Astro y otros generadores), entonces ignora los seis por una
  regla de ese `.gitignore` que no es una excepción (`!`), y ningún `.env`, `.env.*` ni `wp-config.php` está ya versionado en ninguna
  carpeta (`.env.example`, la plantilla sin secretos, sí puede estarlo) → orden: `git ls-files --error-unmatch .gitignore >/dev/null 2>&1 && ! git ls-files | grep -vE '(^|/)\.env\.example$' | grep -qE '(^|/)(\.env(\.[^/]+)?|wp-config\.php)$' && git -c core.excludesFile=/dev/null check-ignore --no-index -v --non-matching .env .env.local .env.production sitio/.env sitio/.env.production wp-config.php | grep -cE '^\.gitignore:[0-9]+:[^!]' | grep -qx 6` ⇒ exit 0
- `CA-LET-01-23` (RN-LET-01-21) — Dados nueve envíos directos a los que les falta un dato o lo traen mal (el nombre y el mensaje,
  cada uno sin su campo, vacío o solo con espacios y saltos de línea; el correo sin su campo, vacío o «esto-no-es-un-correo»), cuando
  el servidor los recibe, entonces cada respuesta lleva `#envio-error` y ninguna `#envio-correcto`, y no llega nada al buzón → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_23_servidor_rechaza_datos_que_faltan_o_no_valen`
- `CA-LET-01-24` (RN-LET-01-22) — Dados tres envíos directos, cada uno con un solo campo inyectado y el resto válido (el nombre con un
  salto de línea `\r\n` seguido de `Bcc:`, el nombre con un `\n` suelto seguido de `Bcc:`, y el correo con `\r\n` seguido de `Cc:`),
  cuando el servidor procesa cada uno con el buzón vacío, entonces ningún correo del buzón tiene más destinatario que `CORREO_CONTACTO`
  (van por separado porque un servidor que valida el correo rechaza entero el envío que lo trae inyectado y dejaría sin probar el
  nombre, que acaba en el asunto o en el remitente) → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_24_no_se_pueden_inyectar_destinatarios`
- `CA-LET-01-25` (RN-LET-01-23) — Dado un mensaje con etiquetas HTML, tildes, eñes, comillas latinas y un emoji, cuando llega al
  buzón, entonces su texto lo reproduce idéntico y su parte HTML, si la hay, no contiene las etiquetas sin escapar → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_25_mensaje_llega_tal_cual_como_texto`
- `CA-LET-01-26` (RN-LET-01-24) — Dada `/contacto/`, cuando se lee el HTML del formulario, entonces no tiene ningún
  `input type="file"` ni declara `enctype="multipart/form-data"` (lo que hace el servidor al recibir un fichero lo fija
  CA-LET-01-32) → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_26_formulario_sin_adjuntos`
- `CA-LET-01-27` (RN-LET-01-25) — Dada `/contacto/`, cuando se lee la casilla `privacidad`, entonces es una casilla, no viene marcada
  y es obligatoria (`required`) → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_27_casilla_sin_marcar_y_obligatoria`
- `CA-LET-01-28` (RN-LET-01-26) — Dada `/contacto/`, cuando se lee el texto del formulario, entonces nombra Responsable, Finalidad,
  Legitimación, Destinatarios y Derechos → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_28_informacion_basica_de_proteccion_de_datos`
- `CA-LET-01-29` (RN-LET-01-27) — Dada `/privacidad/`, cuando se lee, entonces muestra los mismos cuatro datos de la titular que el
  aviso legal, tomados de `tests/sitio/titular.json` → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_29_privacidad_nombra_a_la_misma_titular`
- `CA-LET-01-30` (RN-LET-01-28) — Dado el visto bueno escrito de la clienta al diseño (no es la aceptación del módulo funcionando de la
  condición 2, `docs/presupuesto/02-condiciones.md:8`, que lo cierra), cuando se apunta, entonces `docs/DECISIONES.md` tiene una fila
  de la tabla cuya primera celda lleva un id `DEC-L-NNN` (con o sin acentos graves, como se escriben las ids en la casa), cuya celda
  «Qué se decidió» empieza por el texto fijo «Visto bueno del diseño de LET-01» (tal cual, sin nada delante: «NO da el visto bueno…» o
  «Retira el visto bueno…» no cuentan) y cuyo estado es `vigente` o `cumplida` (una fila `superada por DEC-L-NNN` ya no vale) → orden: `grep -qE '^\|[^|]*DEC-L-[0-9]{3}[^|]*\|[^|]*\|[[:space:]]*Visto bueno del diseño de LET-01([^[:alnum:]|][^|]*)?\|[^|]*\|[^|]*\|[^|]*(vigente|cumplida)[^|]*\|?[[:space:]]*$' docs/DECISIONES.md` ⇒ exit 0
- `CA-LET-01-31` (RN-LET-01-29) — Dado un móvil emulado en `/contacto/`, cuando se mira el campo trampa `web` del formulario,
  entonces existe una sola vez, no se ve ni desplazando la página hasta donde está (un toque en su centro no le llega), está fuera del
  árbol de accesibilidad (`hidden`, `display:none`, `visibility:hidden`, `type="hidden"` o `aria-hidden="true"` propio o heredado) y
  no se alcanza con el tabulador (no se dibuja o su `tabindex` es negativo) → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_31_campo_trampa_oculto_a_la_visitante`
- `CA-LET-01-32` (RN-LET-01-24) — Dado un envío directo a la dirección del formulario como `multipart/form-data`, con los cuatro
  campos válidos y además una parte de fichero `adjunto` (`nota.txt`, texto), cuando el servidor lo recibe, entonces no llega nada al
  buzón y la respuesta lleva `#envio-error`, sin `#envio-correcto` → test: `tests/sitio/test_let_01_contacto.py::test_ca_let_01_32_servidor_rechaza_un_fichero_adjunto`
- `CA-LET-01-33` (RN-LET-01-30) — Dado un móvil emulado que recorre las seis páginas y la 404 y envía el formulario bien relleno,
  cuando se leen las cookies que le han quedado y el texto de `/cookies/`, entonces la página nombra cada una por su nombre, como
  palabra entera («consideramos» no nombra a `sid`), o, si no le ha quedado ninguna, dice «no utiliza cookies» → test: `tests/sitio/test_let_01_paginas.py::test_ca_let_01_33_cookies_nombra_las_que_pone_el_sitio`

## 6. Contexto

**Qué leer antes de tocar nada**

- Plan aprobado (arriba) y `README.md`, la regla que fija el contrato del repo (`.claude/contrato.json:12-14`).
- `docs/presupuesto/01-propuesta.md:44-60` — módulo M1: lo que incluye en `:46` y lo que no en `:48`.
- `docs/presupuesto/02-condiciones.md:7-10` (alcance cerrado, aceptación por escrito, dos rondas de revisión) y `:40` (condición 14).
- `docs/presupuesto/03-cuestionario-fase0.md:11-13` (dominio, IONOS y correo), `:26-27` (logotipo y colores), `:35-37` (quiénes
  somos, datos del aviso legal, correo y teléfono de contacto).
- Propuesta v6 preparada para la clienta: `~/Code/cuaderno/proyectos/letizia/artefactos/docs/2026-10-08_el-archivo-de-talavera-propuesta_v6-final.md`
  — la landing en `:19`, WordPress frente a Astro en `:133-143` (el constructor MyWebsite de IONOS no admite ninguno) y los datos para
  la landing y el aviso legal en `:245-246`.
- Maquetas, solo como referencia visual: `Landing.dc.html` y `Landing-movil.dc.html` (ruta en §3) y
  `~/Code/cuaderno/proyectos/letizia/artefactos/maquetas-limpias/*.png`. Azul
  noche `#0E1A3A` y oro `#E2B04A`; Cinzel, Playfair Display y EB Garamond (licencia OFL: se pueden alojar en el sitio).

**Contrato de interfaz (lo que los tests dan por fijo)**

| Pieza | Cómo es |
|---|---|
| Direcciones | Las seis de RN-LET-01-01; `/no-existe-ca-let-01/` como ejemplo de dirección que no existe |
| Formulario | Un `<form>` en `/contacto/` con los campos `nombre`, `correo` (`type="email"`), `mensaje`, la casilla `privacidad` y el campo trampa `web`. Funciona sin JavaScript: un envío a su `action` devuelve una página HTML |
| Campo trampa | `web`, una sola vez, dentro del `<form>`. Oculto de verdad: no se ve, está fuera del árbol de accesibilidad y no recibe el foco (p. ej. dentro de un contenedor `hidden`, o `aria-hidden="true"` con `tabindex="-1"` fuera de la pantalla). Desplazarlo fuera de la pantalla o hacerlo transparente no basta: el lector de pantalla lo anuncia y el tabulador llega a él |
| Resultado del envío | `#envio-correcto` con «Gracias, hemos recibido tu mensaje.» o `#envio-error` diciendo qué falla |
| Envío con fichero | Un envío `multipart/form-data` que traiga una parte de fichero se rechaza con `#envio-error` y no sale ningún correo: el formulario nunca lo manda, así que solo lo manda un robot o un cliente manipulado |
| Página de cookies | Nombra cada cookie que pone el sitio por su nombre; si no pone ninguna, lo dice con las palabras «no utiliza cookies» |
| Menú del móvil | Un botón cuyo nombre accesible contiene «menú»; enlaces «Inicio», «Quiénes somos» y «Contacto» dentro de un `<nav>` (o `role="navigation"`) que no está en el pie, y que no se ven hasta tocarlo; abierto, se ve sin desplazar la página (en la cabecera o encima de todo). Los mismos enlaces en el pie o fuera de un `<nav>` no son el menú: un botón que solo baja hasta ellos no cumple |
| Cabecera, menú y pie | `<header>` (o `role="banner"`), `<nav>` (o `role="navigation"`) y `<footer>` (o `role="contentinfo"`): los tests buscan ahí el logotipo y los enlaces entre páginas, y los lectores de pantalla los anuncian así |
| Logotipo | `<img alt>` o `<svg>` con `aria-label` o `<title>` que dice «El Archivo de Talavera» |
| Datos de la titular | `tests/sitio/titular.json`, hoy vacío a propósito; una sola fuente para el aviso legal y la privacidad. Se rellena con los datos reales del cuestionario, nunca con datos de prueba |

**Entorno de los tests**

- Caja negra contra `SITIO_URL`, en local o publicado. El buzón de pruebas es Mailpit en un contenedor (SMTP en 1025, API en
  `BUZON_URL`, p. ej. `http://localhost:8025`) y `CORREO_CONTACTO` es la dirección configurada en el formulario.
- Los tests que envían el formulario (CA-LET-01-10 a 16, 23 a 25, 32 y 33) se corren solo contra un sitio cuyo correo saliente va al
  buzón de pruebas, nunca contra el publicado con el correo real: cada envío de prueba le llegaría a la clienta.
- `uv` con Python 3.12, pytest 8.4.2 y Playwright 1.56.0 (Chromium 141, sin ventana). Si falta el navegador:
  `uv run --no-project --with playwright==1.56.0 playwright install chromium`.

**Riesgo**

- El plan marca el ítem con riesgo «ninguno», pero el formulario trata datos personales (nombre, correo y lo que escriba la
  visitante): por la regla de dosis le corresponde el riesgo «datos», con más de un escéptico en la revisión.

**Decisiones abiertas**

- D1 — Decidida el 2026-10-16 (`DEC-L-003`): Astro, sitio estático en `sitio/` compilado con el dominio público, y el formulario
  enviado por un PHP propio en IONOS que habla SMTP con host, puerto y credenciales por variables de entorno (en local, Mailpit).
  Queda comprobar que el plan de IONOS no es el constructor MyWebsite (`03-cuestionario-fase0.md:12`). Las cookies que ponga el
  sitio las nombra CA-LET-01-33, sean las que sean.
- D2 — ¿Qué dominio (.com o .es) y a nombre de quién? ¿Qué dirección recibe el formulario (`CORREO_CONTACTO`) y por qué servidor sale
  el correo? (`03-cuestionario-fase0.md:11` y `:13`).
- D3 — ¿Contacto simple o «Envíanos tu noticia» con adjuntos? Recomendación: simple ahora y los adjuntos en un ítem propio
  (almacenamiento, límite de tamaño y su propio tratamiento de datos). Mientras tanto, el servidor rechaza cualquier fichero (CA-LET-01-32).
- D4 — ¿Entra «Anúnciate», con sus cifras? El plan no lo incluye; la v6 sí.
- D5 — ¿Se muestra un teléfono o un botón de WhatsApp en contacto? Lo decide la clienta.
- D6 — ¿Dónde va la velocidad de carga del SEO técnico base de M1? Ningún ítem del plan la recoge. Recomendación: LET-02, con el sitemap.
- D7 — El plan sale de `01-propuesta.md` v0.1, la plantilla, que no coincide con la v6 preparada para la clienta (web por etapas, con
  «Envíanos tu noticia» y «Anúnciate»). Hay que confirmar cuál manda.
- D8 — El despliegue en IONOS (https, cabeceras, correo con el dominio, registros sin copias de los envíos) no lo cubre LET-01, LET-02
  ni LET-03. Recomendación: un ítem propio de despliegue.

**Materiales de la clienta que faltan**

- Logotipo vectorial (CA-LET-01-09 y 18), datos del aviso legal (CA-LET-01-17 y 29), correo de contacto (CA-LET-01-10), texto de
  quiénes somos (CA-LET-01-08 caza un hueco entre corchetes o un texto de relleno, no una página con poco texto) y su visto bueno del
  diseño (CA-LET-01-30).

## 7. Puertas

El contrato del repo (`DEC-L-004`) declara `test_uno` = `bash tests/puerta.sh test {ruta}`, `navegador: true` y las puertas `specs`,
`let-01` (`bash tests/puerta.sh let-01`) y `let-02`. El script `tests/puerta.sh` lo crea este ítem: compila `sitio/`, levanta el sitio y el
buzón de pruebas (Mailpit) en puertos libres con una pila Docker propia por carpeta de trabajo, exporta `SITIO_URL`, `BUZON_URL` y
`CORREO_CONTACTO`, corre lo de abajo y apaga la pila. Las puertas de este ítem:

- `bash ~/.claude/bin/spec_valida.sh docs/specs/LET-01-estructura-del-sitio-y-paginas-estaticas.md` ⇒ exit 0 con «OK: … (33
  criterios, cada uno con su test u orden)».
- `PYTHONDONTWRITEBYTECODE=1 SITIO_URL=<sitio> BUZON_URL=<buzón> CORREO_CONTACTO=<correo> uv run --no-project --with pytest==8.4.2 --with playwright==1.56.0 pytest -p no:cacheprovider -q tests/sitio -k let_01`
  ⇒ exit 0 (29 tests). `PYTHONDONTWRITEBYTECODE` y `-p no:cacheprovider` evitan dejar cachés en el repo mientras no haya `.gitignore`.
  CA-LET-01-17 y 29 siguen en rojo, a propósito, mientras `tests/sitio/titular.json` esté vacío.
- Las órdenes de CA-LET-01-01, 07, 22 y 30 ⇒ exit 0.
- Hoy los 29 tests y las 4 órdenes salen en rojo. Los 29 fallan por la misma causa: no hay sitio servido y la primera petición de
  cada uno se rechaza. Las órdenes 01 y 07 fallan por lo mismo, la 22 porque no hay `.gitignore` y la 30 porque no hay visto bueno.
- Ensayo hecho fuera del repo, con un sitio y un buzón falsos que no entran en él (esta spec no crea código ni esqueletos); cuenta lo
  que se midió el 2026-10-13 y el 2026-10-14, no es una puerta:
  - Con la maqueta servida como las seis páginas fallan 28 de los 29 tests, cada uno por lo que pide su criterio (los del
    formulario, porque su campo no se llama `correo`); CA-LET-01-21 pasa, con razón, porque ese servidor no entrega ningún fichero
    del repo (14-oct; el 13-oct eran 25 de 26).
  - Contra un sitio correcto pasan 27 con el `titular.json` del repo, que está vacío, y los 29 en una copia del repo con
    `titular.json` relleno con datos inventados; también con un sitio correcto que pone una cookie de sesión y la nombra en `/cookies/`.
  - Las versiones estropeadas a propósito las detecta solo su test: campo trampa, Reply-To, privacidad, validación en el servidor
    (campo ausente, vacío o en blanco y correo vacío u opcional), inyección de destinatarios, correo en HTML, menú que no se pliega,
    huecos escritos con entidades (`&middot;`, `&nbsp;`) o en un atributo, cabecera y pie sin etiqueta ni papel ARIA (13-oct); campo
    trampa visible («Tu web», al final del formulario: cae por «se ve»), campo trampa desplazado fuera de la pantalla o
    transparente sin `aria-hidden` ni `tabindex="-1"` (caen por «los lectores de pantalla lo anuncian»), servidor que acepta el
    fichero adjunto y manda el correo, página de cookies vacía y página de cookies que dice «no utiliza cookies» con una cookie de
    sesión puesta (14-oct; en cada una fallan 1 de 29). Las válidas pasan: menú desplazado fuera de la pantalla, plegado a altura
    cero o creado al tocar, enlaces del menú repetidos en el pie, cabecera, menú y pie marcados solo con `role`, campo trampa dentro
    de un contenedor `hidden` o fuera de la pantalla con `aria-hidden="true"` y `tabindex="-1"`, y `<html>` con su `lang` en otra
    línea.
  - Segunda vuelta (14-oct), con las seis páginas más altas que la pantalla: un menú siempre a la vista cuyo botón «Menú» solo baja
    hasta el pie, donde se repiten Inicio, Quiénes somos y Contacto, pasaba el test anterior de CA-LET-01-03 (solo descartaba lo que ya
    se veía antes de tocar, y el pie quedaba bajo el borde); el de ahora lo caza en las seis páginas («ya se ven antes de tocar el
    botón: el menú no está plegado»), y caza también el menú plegado que nunca se abre con el botón bajando al pie («no hace aparecer
    … dentro del menú») y el pie sin marcar (un `<div>` final con un `<nav>` de seis enlaces, sin `<footer>` ni `role`, al que el
    botón baja: cae porque «aparecen» se mide con la página devuelta a donde estaba). Una cookie `sid` que `/cookies/` no nombra,
    pero con la palabra «consideramos» en la página, pasaba
    CA-LET-01-33 (buscaba el nombre como subcadena) y ahora cae (palabra entera); la 404 con `lang="est"` cae en CA-LET-01-18. El
    servidor que acepta envíos sin la casilla y el que acepta un fichero adjunto siguen cayendo solo en CA-LET-01-12 y 32. En cada
    una falla 1 de 29.
  - Tercera vuelta (14-oct), con el correo del sitio falso saliendo por SMTP a un Mailpit de verdad. CA-LET-01-24 manda ahora tres
    envíos separados (antes uno solo con el nombre y el correo inyectados a la vez, que un servidor que valida el correo rechazaba
    entero, y el nombre quedaba sin probar): caza al servidor que valida el correo pero pone el nombre crudo en el asunto y saca los
    destinatarios de las cabeceras como `sendmail -t` (llega un `Bcc` a `intruso@ejemplo.es`; la versión anterior lo daba por
    bueno), al que solo quita `\r\n` del nombre (cae por el `\n` suelto) y al que valida el correo con `search` y lo pone crudo en
    `Reply-To` (cae por el `Cc`). CA-LET-01-14 vacía el buzón y exige el correo detrás de la confirmación: caza al sitio que con
    JavaScript pinta `#envio-correcto` y no manda nada (antes pasaba 29 de 29 con el buzón vacío). CA-LET-01-08 caza «[Texto de
    quiénes somos]» (antes, solo una lista cerrada de huecos). En cada mutante falla 1 de 29. Contra el sitio correcto pasan los 29
    (titular relleno en la copia) y, en cinco pasadas seguidas de CA-LET-01-14 y 24, 10 de 10.
  - CA-LET-01-03 abre una pestaña nueva por página. Con una sola pestaña, tocar Contacto en `/contacto/` recargaba la página y esa
    recarga se cruzaba con la carga de la siguiente: falló 2 veces de 25 contra el sitio correcto. Con una pestaña por página, 40
    de 40.
  - La orden de CA-LET-01-07 (14-oct, tercera vuelta): imprime por página «etiquetas `<html>`/etiquetas con `lang` castellano» y
    exige `1/1` seis veces. Da `1/1` con `<html` y `lang="es"` en líneas distintas, con `lang='es'`, `lang=es`, `lang = "es"`,
    `lang="es-ES"` y `LANG="ES"`; `1/0` con `lang="eu" data-lang="es"`, `lang="est"`, `lang="es-MX"` y sin `lang`; `0/0` sin
    etiqueta `<html>`; y `2/1` o `2/2` con dos etiquetas `<html>` (la anterior solo contaba las etiquetas con `lang` y daba 1 con
    `<html><html lang="es">`; la de la v1, `grep -ciE '<html[^>]*lang=.?es'` por líneas, daba 0 con el salto de línea y 1 con
    `data-lang`). Contra el sitio falso con `lang="eu" data-lang="es"` en todas las páginas sale con 1 y, además, cae CA-LET-01-18
    (la 404 tampoco declara `es`); contra el que dobla la etiqueta `<html>` en las seis páginas sale con 1 y los 29 tests pasan.
  - La orden de CA-LET-01-22 (14-oct, tercera vuelta), en repositorios de prueba: sale con 0 con un `.gitignore` versionado que
    ignora `.env`, `.env.*` y `wp-config.php` (también con `.env*` más `!.env.example` y un `.env.example` versionado, y con
    `**/.env`); sale con 1 sin `.gitignore`, con el `.gitignore` sin versionar, si solo ignoran esos ficheros el ignore global de la
    máquina (donde la orden de la v1, `git check-ignore -q .env`, salía con 0) o `.git/info/exclude`, si falta la regla `.env.*` (la
    orden anterior daba 0 con `.env.local` versionado, y Astro lee `.env.production`), si ancla `/.env` a la raíz, si falta
    `wp-config.php`, si des-ignora `sitio/.env` con `!`, o si ya hay un `.env`, un `.env.local`, un `sitio/.env.production` o un
    `sitio/wp-config.php` versionado.
  - La orden de CA-LET-01-30 (14-oct, segunda vuelta), en copias de `docs/DECISIONES.md`: sale con 0 con la fila
    «\| `DEC-L-001` \| 2026-10-20 \| Visto bueno del diseño de LET-01 \| «…» \| LET-01 \| vigente \|», también sin acentos graves, con
    un punto y más texto tras el texto fijo, con estado `cumplida` y sin la barra final; sale con 1 sin ninguna fila, con «La clienta
    NO da el visto bueno del diseño de LET-01» (la anterior, que buscaba «visto bueno del diseño» en cualquier sitio de la fila, salía
    con 0), con el visto bueno `superada por DEC-L-002` y la fila que lo retira, con LET-02, con LET-012, con el texto en minúsculas,
    con «Pendiente:» delante y con una fila sin id `DEC-L-NNN`.
