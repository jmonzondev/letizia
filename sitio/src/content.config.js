import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { DIRECCION, ESTADOS, ESTADO_INICIAL } from './noticias/modelo.js';

// Las noticias son ficheros de contenido (DEC-L-003): una carpeta con un .md por noticia, cuyo nombre es su dirección.
// NOTICIAS_DIR cambia la carpeta solo para las pruebas (tests/puerta.sh carga ahí el juego de pruebas de LET-02); sin ella,
// el sitio publicado lee únicamente contenido/noticias y rechaza toda noticia del juego (RN-LET-02-19): la que lleva la marca
// «prueba: true», que le pone el cargador, y las seis direcciones fijas del juego. Una noticia real cuyo titular empieza por
// «Prueba…» (prueba-de-la-evau-en-talavera) no es del juego y se publica.
const PRUEBAS = Boolean(process.env.NOTICIAS_DIR);
const DIRECCION_DEL_JUEGO = /^prueba-[a-f]$/;
const DEL_JUEGO = 'es del juego de pruebas y no puede entrar en el sitio publicado';

const instante = z
  .string()
  .datetime({ offset: true })
  .transform((texto) => new Date(texto));

const leerCarpeta = glob({
  pattern: '*.md',
  base: process.env.NOTICIAS_DIR || './contenido/noticias',
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
  schema: ({ image }) =>
    z
      .object({
        titular: z.string().min(1),
        entradilla: z.string().min(1),
        estado: z.enum(ESTADOS).default(ESTADO_INICIAL),
        publicada: instante.optional(),
        modificada: instante.optional(), // la de la última corrección; si nunca se corrigió, la noticia no la lleva
        foto: image().optional(),
        fotoAutor: z.string().min(1).optional(),
        fuente: z
          .object({ organismo: z.string().min(1), fecha: z.string().regex(/^\d{4}-\d{2}-\d{2}$/) })
          .optional(), // nota de prensa de la que sale
        prueba: z.literal(true).optional(), // la marca de las noticias del juego de pruebas
      })
      .superRefine((datos, contexto) => {
        if (datos.prueba && !PRUEBAS) {
          contexto.addIssue({ code: 'custom', path: ['prueba'], message: `Esta noticia ${DEL_JUEGO}.` });
        }
        if (datos.estado === 'publicada' && !datos.publicada) {
          contexto.addIssue({ code: 'custom', path: ['publicada'], message: 'Una noticia publicada necesita su fecha de publicación.' });
        }
        if (datos.publicada && datos.modificada && datos.modificada < datos.publicada) {
          contexto.addIssue({ code: 'custom', path: ['modificada'], message: 'La corrección no puede ser anterior a la publicación.' });
        }
        if (datos.foto && !datos.fotoAutor) {
          contexto.addIssue({ code: 'custom', path: ['fotoAutor'], message: 'Una foto necesita su autor (RN-LET-02-05).' });
        }
      }),
});

export const collections = { noticias };
