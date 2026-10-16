import { statSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { DIRECCION, DIRECCION_DEL_JUEGO, ESTADOS, ESTADO_INICIAL } from './noticias/modelo.js';

// Las noticias son ficheros de contenido (DEC-L-003): una carpeta con un .md por noticia, cuyo nombre es su dirección.
// NOTICIAS_DIR cambia la carpeta solo para las pruebas (tests/puerta.sh carga ahí el juego de pruebas de LET-02); sin ella,
// el sitio publicado lee únicamente contenido/noticias y rechaza toda noticia del juego (RN-LET-02-19): la que lleva la marca
// «prueba: true», que le pone el cargador, y las seis direcciones fijas del juego. Una noticia real cuyo titular empieza por
// «Prueba…» (prueba-de-la-evau-en-talavera) no es del juego y se publica.
const RAIZ = new URL('../', import.meta.url); // la raíz del proyecto Astro (sitio/), contra la que Astro resuelve las rutas
const PRODUCCION = fileURLToPath(new URL('contenido/noticias', RAIZ));
const mismaCarpeta = (a, b) => {
  try {
    const [x, y] = [statSync(a), statSync(b)];
    return x.dev === y.dev && x.ino === y.ino;
  } catch {
    return false;
  }
};

// NOTICIAS_DIR se resuelve UNA sola vez y exactamente como la lee Astro (new URL(ruta, raíz del proyecto)): da igual desde qué
// carpeta se lance la orden, y «#», «?», «%xx» o file:// no cambian la carpeta que se compara con la que se compila. Tiene que
// existir, y apuntar a contenido/noticias (por su nombre o por un enlace) no es compilar pruebas: las guardas siguen puestas.
function carpetaDePruebas() {
  const valor = process.env.NOTICIAS_DIR;
  if (!valor) return null;
  let ruta;
  try {
    ruta = fileURLToPath(new URL(valor, RAIZ));
  } catch {
    throw new Error(`NOTICIAS_DIR=${valor} no es una carpeta: se espera la ruta de la carpeta con el juego de pruebas`);
  }
  let info = null;
  try {
    info = statSync(ruta);
  } catch {
    info = null;
  }
  if (!info || !info.isDirectory()) {
    throw new Error(`NOTICIAS_DIR=${valor} no es una carpeta que exista (${ruta}): el juego de pruebas se carga antes de compilar`);
  }
  if (resolve(ruta) === resolve(PRODUCCION) || mismaCarpeta(ruta, PRODUCCION)) return null;
  return ruta;
}
const CARPETA_PRUEBAS = carpetaDePruebas();
const PRUEBAS = CARPETA_PRUEBAS !== null;
const DEL_JUEGO = 'es del juego de pruebas y no puede entrar en el sitio publicado';

// Fecha ISO 8601 con zona horaria (RN-LET-02-10). Lo que no lo sea se queda en null: en un borrador no importa (no se publica)
// y en una publicada lo rechaza la comprobación de abajo. Así un borrador escrito a mano con una fecha mal no tumba el sitio.
const FECHA_CON_ZONA = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})$/;
const instante = z
  .string()
  .optional()
  .transform((texto) => {
    if (texto === undefined) return undefined;
    const fecha = FECHA_CON_ZONA.test(texto) ? new Date(texto) : null;
    return fecha && !Number.isNaN(fecha.getTime()) ? fecha : null;
  });

const leerCarpeta = glob({
  pattern: '*.md',
  base: PRUEBAS ? CARPETA_PRUEBAS : PRODUCCION,
  generateId: ({ entry }) => {
    const direccion = entry.replace(/\.md$/, '');
    if (!DIRECCION.test(direccion)) {
      throw new Error(`La noticia «${entry}» no vale: su dirección solo puede llevar minúsculas sin tilde, cifras y guiones.`);
    }
    if (!PRUEBAS && DIRECCION_DEL_JUEGO.test(direccion)) {
      throw new Error(`La noticia «${entry}» ${DEL_JUEGO}.`);
    }
    return direccion;
  },
});

const noticias = defineCollection({
  // Cada compilación empieza con el almacén vacío: el de la anterior queda en .astro/ y, si esta carpeta está vacía o es otra,
  // el cargador de Astro no lo limpia, y las noticias de prueba de una compilación acabarían en la siguiente (RN-LET-02-19).
  //
  // Y al almacén solo entra lo publicado (RN-LET-02-07 y 08): un borrador o una retirada se valida, pero no se guarda, y con
  // ella no se guardan sus fotos; si no, Astro las copia a dist/ y se siguen sirviendo en una dirección que Google ya tiene.
  loader: {
    ...leerCarpeta,
    load: async (contexto) => {
      contexto.store.clear();
      const almacen = {
        ...contexto.store,
        set: (entrada) => {
          if (entrada.data.estado === 'publicada') return contexto.store.set(entrada);
          contexto.store.delete(entrada.id); // en `astro dev`, una publicada que se retira sale del almacén
          return false;
        },
      };
      await leerCarpeta.load({ ...contexto, store: almacen });
    },
  },
  // Solo lo publicado tiene que estar completo y bien escrito: un borrador a medias, sea cual sea el campo que le falte, no puede
  // tumbar la compilación de todo el sitio. Lo que aquí es laxo lo exige publicar() en el gestor y esta comprobación al publicar.
  schema: ({ image }) =>
    z
      .object({
        titular: z.string().default(''),
        entradilla: z.string().default(''),
        estado: z.enum(ESTADOS).default(ESTADO_INICIAL),
        publicada: instante,
        modificada: instante, // la de la última corrección; si nunca se corrigió, la noticia no la lleva
        foto: image().optional(),
        fotoAutor: z.string().optional(),
        fuente: z.object({ organismo: z.string().default(''), fecha: z.string().default('') }).optional(), // nota de prensa de la que sale
        prueba: z.literal(true).optional(), // la marca de las noticias del juego de pruebas
      })
      .superRefine((datos, contexto) => {
        const falta = (campo, mensaje) => contexto.addIssue({ code: 'custom', path: [campo], message: mensaje });
        if (datos.prueba && !PRUEBAS) falta('prueba', `Esta noticia ${DEL_JUEGO}.`);
        if (datos.estado !== 'publicada') return;
        if (!datos.titular.trim()) falta('titular', 'Una noticia publicada necesita titular (RN-LET-02-03).');
        if (!datos.entradilla.trim()) falta('entradilla', 'Una noticia publicada necesita entradilla (RN-LET-02-03).');
        if (!(datos.publicada instanceof Date)) {
          falta('publicada', 'Una noticia publicada necesita su fecha de publicación, ISO 8601 con zona horaria (RN-LET-02-10).');
        }
        if (datos.modificada === null) falta('modificada', 'La fecha de la última corrección tiene que ser ISO 8601 con zona horaria (RN-LET-02-10).');
        if (datos.foto && !(datos.fotoAutor ?? '').trim()) falta('fotoAutor', 'Una foto publicada necesita su autor (RN-LET-02-05).');
        if (datos.fuente && !datos.fuente.organismo.trim()) falta('fuente', 'La fuente necesita el organismo (RN-LET-02-04).');
        if (datos.fuente && !/^\d{4}-\d{2}-\d{2}$/.test(datos.fuente.fecha)) falta('fuente', 'La fecha de la nota de prensa tiene la forma AAAA-MM-DD (RN-LET-02-04).');
      }),
});

export const collections = { noticias };
