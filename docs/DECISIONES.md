# Decisiones de Letizia

> Actualizado: 2026-10-16 · Siguiente id libre: `DEC-L-004`. Decisiones del usuario sobre este proyecto. Las que valen para todos sus
> proyectos están en el cuaderno (`~/Code/cuaderno/DECISIONES.md`, ids `DEC-U-NNN`). Se añaden al momento, con sus palabras literales.
> Estado: `vigente` · `superada por DEC-L-NNN` · `cumplida`.

## Octubre de 2026

| Id | Fecha | Qué se decidió | Por qué / sus palabras | Dónde aplica | Estado |
|---|---|---|---|---|---|
| `DEC-L-001` | 2026-10-14 | Las tres specs del módulo landing (LET-01 a 03), devueltas por el revisor tras una vuelta de arreglo, se corrigen en una segunda vuelta con Fable a esfuerzo máximo en vez de partirlas o dejarlas. | «sí al blindaje de BetLab y relanza Letizia con Fable» | `docs/specs/`, ramas `especificar/let-0X-v2` | vigente |
| `DEC-L-002` | 2026-10-16 | La regla `RN-LET-01-02` de LET-01 se relaja: la visitante llega a cada una de las otras cinco páginas con un toque en su enlace y, en el móvil, tras abrir el menú con su botón. El menú plegado del móvil (`CA-LET-01-03`) se mantiene y los enlaces no se repiten en el pie. | «A. Relajar la regla» (frente a repetir los enlaces en el pie o quitar el plegado) | `docs/specs/LET-01-estructura-del-sitio-y-paginas-estaticas.md` §4 | vigente |
| `DEC-L-003` | 2026-10-16 | D1: la web se hace con Astro, sitio estático en `sitio/` compilado con el dominio público, y un editor web propio para la clienta (ítem aparte). El formulario de contacto lo envía un PHP propio pequeño en el alojamiento compartido de IONOS, que habla SMTP con host, puerto y credenciales por variables de entorno (en local, Mailpit sin credenciales). Las noticias y el juego de pruebas de LET-02 son ficheros de contenido; un cargador propio escribe `JUEGO`. La pila local (PHP-Apache sirviendo `dist/` y el PHP, más Mailpit) la levanta `tests/puerta.sh`. WordPress y el constructor MyWebsite de IONOS quedan descartados. | «Astro con editor propio» (D1 planteada como WordPress o Astro con editor; «el constructor MyWebsite de IONOS no vale») | LET-01, LET-02 y LET-03; `sitio/`, `tests/puerta.sh`, `.claude/contrato.json` | vigente |
