"""SPEC-LET-01 — formulario de contacto de /contacto/.

Caja negra: los envíos directos se hacen como un navegador sin JavaScript (POST a la dirección del formulario) y lo
que llega se lee en el buzón de pruebas (Mailpit, BUZON_URL). Ningún envío de prueba debe salir a un correo real: el
sitio contra el que se corren tiene su correo saliente apuntando al buzón de pruebas.
"""

import re
import unicodedata
import uuid
from urllib.parse import urlsplit

from apoyo_sitio import (
    FUERA_DEL_ARBOL_DE_ACCESIBILIDAD,
    PAGINAS,
    RECIBE_EL_FOCO,
    SE_VE_EN_LA_PAGINA,
    FormularioContacto,
    anfitrion,
    cabeceras,
    correo_contacto,
    destinatarios,
    direcciones,
    esperar_mensajes,
    mensaje,
    mensajes_tras_espera,
    movil,
    ruta_de,
    sitio_url,
    vaciar_buzon,
    valores_validos,
)


def _marca():
    return uuid.uuid4().hex[:12]


def _sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))


def _texto_por_id(respuesta, ident):
    nodo = respuesta.doc.por_id(ident)
    return None if nodo is None else nodo.texto()


def test_ca_let_01_10_mensaje_valido_llega_al_correo_de_la_clienta():
    # CA-LET-01-10
    formulario = FormularioContacto()
    destino = correo_contacto()
    vaciar_buzon()
    marca = _marca()
    valores = valores_validos(marca)
    formulario.enviar(valores)
    recibidos = esperar_mensajes(1)
    assert recibidos, "No ha llegado ningún correo al buzón tras un envío válido"
    recibidos = mensajes_tras_espera(2)
    assert len(recibidos) == 1, f"Han llegado {len(recibidos)} correos; debe llegar uno solo"
    assert set(destinatarios(recibidos[0])) == {destino}, (
        f"El correo va a {destinatarios(recibidos[0])}; debe ir solo a {destino}"
    )
    texto = mensaje(recibidos[0]["ID"]).get("Text") or ""
    for campo in ("nombre", "correo", "mensaje"):
        assert valores[campo] in texto, f"El correo no trae el {campo} escrito: {valores[campo]!r}"


def test_ca_let_01_11_responder_va_a_la_visitante():
    # CA-LET-01-11
    formulario = FormularioContacto()
    vaciar_buzon()
    formulario.enviar(valores_validos(_marca()))
    recibidos = esperar_mensajes(1)
    assert recibidos, "No ha llegado ningún correo al buzón tras un envío válido"
    completo = mensaje(recibidos[0]["ID"])
    assert direcciones(completo.get("ReplyTo")) == ["visitante@ejemplo.es"], (
        f"Reply-To es {direcciones(completo.get('ReplyTo'))}; debe ser visitante@ejemplo.es"
    )
    remitente = (completo.get("From") or {}).get("Address", "").lower()
    assert remitente != "visitante@ejemplo.es", "El correo sale con la dirección de la visitante como remitente"


def test_ca_let_01_12_sin_aceptar_privacidad_no_se_envia():
    # CA-LET-01-12
    formulario = FormularioContacto()
    vaciar_buzon()
    respuesta = formulario.enviar(valores_validos(_marca()), quitar=("privacidad",))
    assert not mensajes_tras_espera(3), "Ha llegado un correo sin aceptar la política de privacidad"
    error = _texto_por_id(respuesta, "envio-error")
    assert error is not None, "La respuesta no lleva el aviso #envio-error"
    assert "privacidad" in error.lower(), f"El aviso no pide aceptar la política de privacidad: {error!r}"
    assert respuesta.doc.por_id("envio-correcto") is None, "La respuesta dice «enviado» sin haber aceptado la privacidad"


def test_ca_let_01_13_casilla_enlaza_a_privacidad():
    # CA-LET-01-13
    formulario = FormularioContacto()
    casilla = formulario.campo("privacidad")
    assert casilla is not None, "El formulario no tiene la casilla «privacidad»"
    etiquetas = []
    nodo = casilla.padre
    while nodo is not None:
        if nodo.tag == "label":
            etiquetas.append(nodo)
        nodo = nodo.padre
    ident = casilla.attrs.get("id")
    if ident:
        etiquetas += [n for n in formulario.pagina.doc.todos("label") if n.attrs.get("for") == ident]
    assert etiquetas, "La casilla de privacidad no tiene etiqueta (<label>)"
    rutas = {ruta_de(a.attrs.get("href"), formulario.pagina.url) for e in etiquetas for a in e.todos("a")}
    assert "/privacidad" in rutas, f"La etiqueta de la casilla no enlaza a /privacidad/ (enlaza a {rutas or 'nada'})"


def test_ca_let_01_14_confirmacion_en_pantalla_tras_enviar():
    # CA-LET-01-14
    FormularioContacto()
    destino = correo_contacto()
    from playwright.sync_api import expect

    vaciar_buzon()
    with movil() as pestana:
        pestana.goto(sitio_url() + PAGINAS["contacto"])
        valores = valores_validos(_marca())
        pestana.locator('[name="nombre"]').fill(valores["nombre"])
        pestana.locator('[name="correo"]').fill(valores["correo"])
        pestana.locator('[name="mensaje"]').fill(valores["mensaje"])
        pestana.locator('[name="privacidad"]').check()
        pestana.get_by_role("button", name=re.compile("enviar", re.IGNORECASE)).tap()
        confirmacion = pestana.locator("#envio-correcto")
        expect(confirmacion, "No aparece la confirmación #envio-correcto").to_be_visible(timeout=15000)
        assert "hemos recibido tu mensaje" in confirmacion.inner_text().lower(), (
            f"La confirmación no dice «Gracias, hemos recibido tu mensaje.»: {confirmacion.inner_text()!r}"
        )
        assert urlsplit(pestana.url).hostname == anfitrion(), f"Tras enviar, la visitante sale del sitio: {pestana.url}"
    # La confirmación no vale sin la entrega: con JavaScript, el navegador puede enviar por otro camino que el POST
    # directo de CA-LET-01-10, y ese camino tiene que dejar el mismo correo en el buzón.
    recibidos = esperar_mensajes(1)
    assert recibidos, "La pantalla dice «enviado», pero no ha llegado ningún correo al buzón"
    recibidos = mensajes_tras_espera(2)
    assert len(recibidos) == 1, f"Han llegado {len(recibidos)} correos tras enviar desde el navegador; debe llegar uno solo"
    assert set(destinatarios(recibidos[0])) == {destino}, (
        f"El correo va a {destinatarios(recibidos[0])}; debe ir solo a {destino}"
    )
    texto = mensaje(recibidos[0]["ID"]).get("Text") or ""
    assert valores["mensaje"] in texto, f"El correo recibido no trae el mensaje escrito en el navegador: {valores['mensaje']!r}"


# El aviso que la visitante ve cuando el campo Correo falla puede venir de dos caminos, y los dos se miden por lo que se
# ve, no por lo que el campo «podría» decir: el navegador (el formulario no lleva «novalidate» y el campo dispara el
# evento «invalid», el que pinta la burbuja nativa) o la página (el campo lleva aria-invalid="true" y un aviso con texto
# enlazado por aria-describedby que se ve). Que el campo vacío tenga un validationMessage no prueba nada: lo tiene
# siempre que es «required», se muestre o no.
AVISO_VISIBLE_DEL_CAMPO = """e => {
    if (e.getAttribute('aria-invalid') !== 'true') return '';
    const ids = (e.getAttribute('aria-describedby') || '').split(/\\s+/).filter(Boolean);
    const se_ve = n => n.checkVisibility({opacityProperty: true, visibilityProperty: true})
        && n.getBoundingClientRect().width > 0 && n.getBoundingClientRect().height > 0;
    return ids.map(i => document.getElementById(i)).filter(n => n && se_ve(n) && n.textContent.trim())
              .map(n => n.textContent.trim()).join(' ');
}"""


def test_ca_let_01_15_correo_que_falta_se_avisa_sin_perder_lo_escrito():
    # CA-LET-01-15
    FormularioContacto()
    from playwright.sync_api import expect

    vaciar_buzon()
    with movil() as pestana:
        pestana.goto(sitio_url() + PAGINAS["contacto"])
        valores = valores_validos(_marca())
        pestana.locator('[name="nombre"]').fill(valores["nombre"])
        pestana.locator('[name="mensaje"]').fill(valores["mensaje"])
        pestana.locator('[name="privacidad"]').check()
        correo = pestana.locator('[name="correo"]')
        correo.evaluate(
            "e => { window.__invalidCorreo = false; "
            "e.addEventListener('invalid', ev => { if (ev.isTrusted) window.__invalidCorreo = true; }); }"
        )
        pestana.get_by_role("button", name=re.compile("enviar", re.IGNORECASE)).tap()
        expect(correo).to_be_visible()
        avisa_el_navegador = pestana.evaluate("window.__invalidCorreo === true")
        avisa_la_pagina = correo.evaluate(AVISO_VISIBLE_DEL_CAMPO)
        assert avisa_el_navegador or avisa_la_pagina, (
            "Al tocar Enviar con el correo vacío la visitante no ve ningún aviso: el navegador no avisa del campo (evento "
            "«invalid»; con «novalidate» no salta) y el campo no lleva aria-invalid=\"true\" con un aviso visible "
            "enlazado por aria-describedby"
        )
        assert pestana.locator('[name="nombre"]').input_value() == valores["nombre"], "Se ha perdido el nombre escrito"
        assert pestana.locator('[name="mensaje"]').input_value() == valores["mensaje"], "Se ha perdido el mensaje escrito"
        assert pestana.locator("#envio-correcto").count() == 0 or not pestana.locator("#envio-correcto").is_visible(), (
            "Aparece «enviado» con el correo vacío"
        )
    assert not mensajes_tras_espera(3), "Ha llegado un correo con el campo Correo vacío"


def test_ca_let_01_16_envio_con_campo_trampa_no_llega():
    # CA-LET-01-16
    formulario = FormularioContacto()
    assert formulario.campo("web") is not None, "El formulario no tiene el campo trampa «web»"
    vaciar_buzon()
    valores = valores_validos(_marca())
    valores["web"] = "https://ofertas-automaticas.example"
    respuesta = formulario.enviar(valores)
    assert not mensajes_tras_espera(3), "Ha llegado al buzón un envío con el campo trampa relleno"
    assert respuesta.doc.por_id("envio-correcto") is not None, "La respuesta no es la confirmación de un envío normal"
    assert respuesta.doc.por_id("envio-error") is None, "La respuesta delata al envío automático con un error"


def test_ca_let_01_23_servidor_rechaza_datos_que_faltan_o_no_valen():
    # CA-LET-01-23
    FormularioContacto()
    vaciar_buzon()
    # Que falte un dato es tanto no mandar el campo como mandarlo vacío o solo con espacios: un servidor que solo mira si
    # el campo existe deja pasar «nombre=» y «mensaje=».
    casos = {
        "sin el campo nombre": ({}, ("nombre",)),
        "con el nombre vacío": ({"nombre": ""}, ()),
        "con el nombre solo con espacios": ({"nombre": "   "}, ()),
        "sin el campo mensaje": ({}, ("mensaje",)),
        "con el mensaje vacío": ({"mensaje": ""}, ()),
        "con el mensaje solo con espacios y saltos de línea": ({"mensaje": " \r\n \r\n "}, ()),
        "sin el campo correo": ({}, ("correo",)),
        "con el correo vacío": ({"correo": ""}, ()),
        "con el correo «esto-no-es-un-correo»": ({"correo": "esto-no-es-un-correo"}, ()),
    }
    fallos = []
    for caso, (cambios, quitar) in casos.items():
        valores = {**valores_validos(_marca()), **cambios}
        respuesta = FormularioContacto().enviar(valores, quitar=quitar)
        if respuesta.doc.por_id("envio-error") is None or respuesta.doc.por_id("envio-correcto") is not None:
            fallos.append(f"{caso}: la respuesta no es un aviso #envio-error")
    llegados = mensajes_tras_espera(3)
    if llegados:
        fallos.append(f"han llegado {len(llegados)} correo(s) con datos que faltan o no valen")
    assert not fallos, "\n".join(fallos)


def test_ca_let_01_24_no_se_pueden_inyectar_destinatarios():
    # CA-LET-01-24
    FormularioContacto()
    destino = correo_contacto()
    # Un campo por envío, con el resto válido. Un servidor que valida el correo (CA-LET-01-23) rechaza entero un envío que
    # lo traiga inyectado, y el nombre, que acaba en el asunto o en el remitente, se quedaría sin probar. El segundo nombre
    # lleva solo el salto de línea «\n»: un filtro que solo quita «\r\n» lo deja pasar.
    intentos = {
        "nombre con «Bcc:» tras un salto de línea": {"nombre": "Ana\r\nBcc: intruso@ejemplo.es"},
        "nombre con «Bcc:» tras un «\\n» suelto": {"nombre": "Ana\nBcc: intruso@ejemplo.es"},
        "correo con «Cc:» tras un salto de línea": {"correo": "visitante@ejemplo.es\r\nCc: intruso@ejemplo.es"},
    }
    fallos = []
    for intento, cambios in intentos.items():
        vaciar_buzon()
        FormularioContacto().enviar({**valores_validos(_marca()), **cambios})
        llegados = mensajes_tras_espera(3)
        ajenos = sorted({d for m in llegados for d in destinatarios(m) if d != destino})
        if ajenos:
            fallos.append(f"{intento}: el envío ha añadido destinatarios {ajenos}")
    assert not fallos, "\n".join(fallos)


def test_ca_let_01_24_correo_entre_comillas_no_inyecta_cabeceras():
    # CA-LET-01-24 y CA-LET-01-25: un correo entre comillas puede llevar un salto de línea escapado (una barra «\» y
    # el salto) y pasar por un validador de direcciones que sí rechaza el «\r\n» a secas. Si el servidor lo copia a
    # una cabecera, la visitante escribe cabeceras del correo: añade destinatarios (Cc) o cambia el tipo del contenido
    # (parte HTML).
    FormularioContacto()
    destino = correo_contacto()
    intentos = {
        "correo entre comillas con «Content-Type: text/html»": '"a\\\nContent-Type:text/html;\\\nX:"@ejemplo.es',
        "correo entre comillas con «Cc:» y una cabecera inventada": '"a\\\nCc:intruso@ejemplo.es,\\\nX-R:"@ejemplo.es',
    }
    fallos = []
    for intento, correo in intentos.items():
        vaciar_buzon()
        marca = _marca()
        valores = {**valores_validos(marca), "correo": correo, "mensaje": f"Prueba {marca}: <b>ñandú</b> y un enlace"}
        respuesta = FormularioContacto().enviar(valores)
        if respuesta.doc.por_id("envio-correcto") is not None or respuesta.doc.por_id("envio-error") is None:
            fallos.append(f"{intento}: la respuesta no es un aviso #envio-error (la visitante ve «enviado» o nada)")
        for llegado in mensajes_tras_espera(3):
            completo = mensaje(llegado["ID"])
            ajenos = sorted({d for d in destinatarios(completo) if d != destino})
            if ajenos:
                fallos.append(f"{intento}: el correo lleva destinatarios ajenos {ajenos}")
            nombres = cabeceras(llegado["ID"])
            inventadas = sorted(n for n in nombres if n in ("cc", "bcc") or (n.startswith("x-") and n != "x-mailer"))
            if inventadas:
                fallos.append(f"{intento}: el correo lleva cabeceras que escribió la visitante: {inventadas}")
            if completo.get("HTML"):
                fallos.append(f"{intento}: el correo lleva una parte HTML; debe ser solo texto sin formato")
    assert not fallos, "\n".join(fallos)


def test_ca_let_01_25_mensaje_llega_tal_cual_como_texto():
    # CA-LET-01-25
    formulario = FormularioContacto()
    vaciar_buzon()
    valores = valores_validos(_marca())
    valores["mensaje"] = f"Prueba {_marca()}: <b>ñandú</b> en el «café» de la Plaza del Pan, ¿vale? 🎉"
    formulario.enviar(valores)
    recibidos = esperar_mensajes(1)
    assert recibidos, "No ha llegado ningún correo al buzón tras un envío válido"
    completo = mensaje(recibidos[0]["ID"])
    assert valores["mensaje"] in (completo.get("Text") or ""), (
        "El texto del correo no reproduce el mensaje letra por letra (tildes, eñes, emoji y etiquetas como texto)"
    )
    assert "<b>ñandú</b>" not in (completo.get("HTML") or ""), "Lo escrito por la visitante se interpreta como HTML"


def test_ca_let_01_26_formulario_sin_adjuntos():
    # CA-LET-01-26
    formulario = FormularioContacto()
    de_fichero = [n for n in formulario.nodo.todos("input") if n.attrs.get("type", "").lower() == "file"]
    assert not de_fichero, "El formulario admite adjuntos (input type=file)"
    assert "multipart" not in formulario.nodo.attrs.get("enctype", "").lower(), (
        "El formulario declara enctype=multipart/form-data, la codificación de los adjuntos"
    )


def test_ca_let_01_27_casilla_sin_marcar_y_obligatoria():
    # CA-LET-01-27
    casilla = FormularioContacto().campo("privacidad")
    assert casilla is not None, "El formulario no tiene la casilla «privacidad»"
    assert casilla.attrs.get("type", "").lower() == "checkbox", "«privacidad» no es una casilla"
    assert "checked" not in casilla.attrs, "La casilla de privacidad viene marcada de antemano"
    assert "required" in casilla.attrs, "La casilla de privacidad no es obligatoria (falta required)"


def test_ca_let_01_28_informacion_basica_de_proteccion_de_datos():
    # CA-LET-01-28
    formulario = FormularioContacto()
    texto = _sin_tildes(formulario.nodo.texto())
    faltan = [t for t in ("responsable", "finalidad", "legitimacion", "destinatarios", "derechos") if t not in texto]
    assert not faltan, f"En el formulario falta la información básica de protección de datos: {faltan}"


def test_ca_let_01_31_campo_trampa_oculto_a_la_visitante():
    # CA-LET-01-31
    formulario = FormularioContacto()
    assert formulario.campo("web") is not None, "El formulario no tiene el campo trampa «web»"
    with movil() as pestana:
        pestana.goto(sitio_url() + PAGINAS["contacto"], wait_until="load")
        trampa = pestana.locator('form [name="web"]')
        assert trampa.count() == 1, f"Hay {trampa.count()} campos «web» en el formulario; debe haber uno"
        assert not trampa.evaluate(SE_VE_EN_LA_PAGINA), (
            "El campo trampa «web» se ve en la página: una persona puede rellenarlo y su mensaje se descarta sin aviso"
        )
        assert trampa.evaluate(FUERA_DEL_ARBOL_DE_ACCESIBILIDAD), (
            "Los lectores de pantalla anuncian el campo trampa «web»: falta ocultarlo (hidden, display:none o aria-hidden)"
        )
        assert not trampa.evaluate(RECIBE_EL_FOCO), "El campo trampa «web» se alcanza con el tabulador (falta tabindex=-1)"


def test_ca_let_01_32_servidor_rechaza_un_fichero_adjunto():
    # CA-LET-01-32
    formulario = FormularioContacto()
    vaciar_buzon()
    adjunto = {"adjunto": ("nota.txt", "Fichero de prueba que el formulario nunca manda.\n".encode("utf-8"), "text/plain")}
    respuesta = formulario.enviar(valores_validos(_marca()), ficheros=adjunto)
    assert not mensajes_tras_espera(3), "Ha llegado al buzón un envío con un fichero adjunto"
    assert respuesta.doc.por_id("envio-correcto") is None, "La respuesta da por enviado un mensaje con un fichero adjunto"
    assert respuesta.doc.por_id("envio-error") is not None, "La respuesta a un envío con fichero no lleva el aviso #envio-error"
