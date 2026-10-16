# Estado de Letizia

> Actualizado: 2026-10-16. Una página para retomar el proyecto sin releerlo. Decisiones: [`DECISIONES.md`](DECISIONES.md). Specs:
> [`specs/`](specs/).

## Qué es

Proyecto para una clienta (marca «El Archivo de Talavera»): una web que sea a la vez landing y web de noticias, que convierte en
noticias las notas de prensa que le llegan por correo, con portada automática en su plantilla y su OK antes de publicar. Además,
seguridad digital: contraseñas, correo con su dominio y copias de seguridad.

## Dónde estamos

| | |
|---|---|
| Fase | Specs del módulo M1 aprobadas; construcción de LET-01 y después LET-02; Fase 0 con la clienta pendiente |
| Documentos | `docs/presupuesto/` (propuesta, condiciones, cuestionario de la Fase 0, tarifas y su script) |
| Specs | `specs/LET-01-estructura-del-sitio-y-paginas-estaticas.md` (APROBADA 2026-10-16, 33 criterios) · `specs/LET-02-seccion-de-noticias.md` (APROBADA 2026-10-16, 24) · `specs/LET-03-redes-embebidas-y-consentimiento-de-cookies.md` (BORRADOR validado el 2026-10-16, 22; se construye tras la Fase 0) |
| Decisiones | `DEC-L-002` a `DEC-L-005`: regla del menú del móvil, D1 (Astro con editor propio y formulario en PHP), contrato del repo y aprobación de las specs |
| Stack | Astro estático en `sitio/` compilado con el dominio público; formulario en un PHP propio para IONOS que habla SMTP por variables de entorno; pila local Docker (PHP-Apache + Mailpit) que levanta `tests/puerta.sh` (`DEC-L-003`) |
| Puertas | `.claude/contrato.json`: `specs`, `let-01` y `let-02`; `test_uno` = `bash tests/puerta.sh test {ruta}`. `let-01` y `let-02` en rojo hasta que LET-01 cree `tests/puerta.sh` y el sitio |
| Tests | `tests/sitio/` (LET-01 y LET-03: pytest y Playwright vía uv contra `SITIO_URL` y un buzón Mailpit) y `tests/test_noticias*.py` (LET-02: Python 3 sin dependencias contra `SITIO`, `DOMINIO` y `JUEGO`) |

## Qué toca ahora

- Construir LET-01 y después LET-02 con el guion `construir`, riesgo «datos» (tres escépticos y auditor al cierre), e integrar cada
  rama leyendo su diff.
- Fase 0 con la clienta: plan de IONOS (que no sea el constructor MyWebsite), dominio y correo de contacto, materiales (logotipo
  vectorial, datos del aviso legal para `tests/sitio/titular.json`, texto de quiénes somos), qué publicaciones se embeben y si hay
  analítica. Después, LET-03.
- Ítems propios tras la Fase 0: editor web para la clienta, despliegue en IONOS (D8), velocidad de carga (D6).
