import { existsSync, lstatSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import yaml from 'js-yaml';
import sharp from 'sharp'; // estático: una importación dinámica aquí pasaría por el ejecutor de Vite, que ya está cerrado al sincronizar
import { DIRECCION, DIRECCION_DEL_JUEGO, ESTADOS, ESTADO_INICIAL, NOMBRE_DE_FOTO, diaValido, instanteValido } from './noticias/modelo.js';

// Las noticias son ficheros de contenido (DEC-L-003): una carpeta con un .md por noticia, cuyo nombre es su dirección. El sitio
// publicado lee únicamente contenido/noticias y rechaza toda noticia del juego de pruebas (RN-LET-02-19): la que lleva la marca
// «prueba: true», que le pone el cargador, y las seis direcciones fijas del juego. Una noticia real cuyo titular empieza por
// «Prueba…» (prueba-de-la-evau-en-talavera) no es del juego y se publica.
//
// La ÚNICA carpeta de pruebas es sitio/.juego (ahí carga el juego tests/puerta.sh). NOTICIAS_DIR solo sirve para pedir esa
// compilación de pruebas: se resuelve como la lee Astro (contra la raíz de sitio/), tiene que existir y tiene que ser esa carpeta
// (la misma, por su inode: ni por otro nombre, ni por un enlace, ni «#», «?» o «%xx» en la ruta). A Astro nunca le llega una ruta
// escrita por nadie: la base del glob es siempre una de las dos carpetas fijas, como dirección file://.
const RAIZ = new URL('../', import.meta.url);
const PRODUCCION = fileURLToPath(new URL('contenido/noticias', RAIZ));
const JUEGO = fileURLToPath(new URL('.juego', RAIZ));
const mismaCarpeta = (a, b) => {
  try {
    const [x, y] = [statSync(a), statSync(b)];
    return x.dev === y.dev && x.ino === y.ino;
  } catch {
    return false;
  }
};
function compilaPruebas() {
  const valor = process.env.NOTICIAS_DIR;
  if (!valor) return false;
  let ruta;
  try {
    ruta = fileURLToPath(new URL(valor, RAIZ));
  } catch {
    throw new Error(`NOTICIAS_DIR=${valor} no es una ruta de carpeta: la única carpeta del juego de pruebas es sitio/.juego`);
  }
  let info = null;
  try {
    info = statSync(ruta);
  } catch {
    info = null;
  }
  if (!info || !info.isDirectory()) {
    throw new Error(`NOTICIAS_DIR=${valor} no es una carpeta que exista (${ruta}): el juego de pruebas se carga en sitio/.juego antes de compilar`);
  }
  if (!mismaCarpeta(ruta, JUEGO) || mismaCarpeta(JUEGO, PRODUCCION)) {
    throw new Error(`NOTICIAS_DIR=${valor} no es la carpeta del juego de pruebas (sitio/.juego): solo ahí se compilan pruebas, y nunca sobre contenido/noticias`);
  }
  return true;
}
const PRUEBAS = compilaPruebas();
const CARPETA = PRUEBAS ? JUEGO : PRODUCCION;
const DEL_JUEGO = 'es del juego de pruebas y no puede entrar en el sitio publicado';

// Antes de que Astro lea la carpeta: un .md cuyo nombre no es una dirección o cuya cabecera no se puede leer tumbaría la compilación
// con un error ajeno. Se lee cada cabecera con el mismo analizador YAML que usa Astro (js-yaml): si está publicado, se para aquí con
// un aviso nuestro (falla cerrado); si no, es un borrador y se deja fuera del glob con un aviso. Lo que no está publicado nunca tumba
// el sitio (RN-LET-02-02 y 07). Lo que no es un fichero normal (una carpeta, un enlace) también se deja fuera.
const cabeceraDe = (texto) => {
  const m = texto.match(/^---\r?\n([\s\S]*?)\r?\n---(\r?\n|$)/);
  return m ? m[1] : null;
};
const pareceDeclararPublicada = (texto) => /^["']?estado["']?:\s*["']?publicada\b/m.test(texto);
const escapaGlob = (nombre) => nombre.replace(/[\\*?[\]{}()!]/g, '\\$&');
function excluidos() {
  const fuera = [];
  if (!existsSync(CARPETA)) return fuera;
  for (const nombre of readdirSync(CARPETA).filter((f) => f.endsWith('.md'))) {
    const ruta = join(CARPETA, nombre);
    let info = null;
    try {
      info = lstatSync(ruta);
    } catch {
      info = null;
    }
    if (!info || !info.isFile()) {
      console.warn(`[noticias] «${nombre}» no es un fichero normal (carpeta o enlace): se deja fuera.`);
      fuera.push(nombre);
      continue;
    }
    const direccion = nombre.slice(0, -3);
    const texto = readFileSync(ruta, 'utf8');
    const cabecera = cabeceraDe(texto);
    let datos = null;
    let error = cabecera === null ? 'no empieza por una cabecera entre «---»' : null;
    if (cabecera !== null) {
      try {
        datos = yaml.load(cabecera);
        if (!datos || typeof datos !== 'object' || Array.isArray(datos)) error = 'la cabecera no es una lista de campos';
      } catch (fallo) {
        error = fallo.message.split('\n')[0];
      }
    }
    const publicada = datos && typeof datos === 'object' && !Array.isArray(datos) ? datos.estado === 'publicada' : pareceDeclararPublicada(cabecera ?? texto);
    if (!DIRECCION.test(direccion)) {
      if (publicada) throw new Error(`La noticia «${nombre}» no vale: su dirección solo puede llevar minúsculas sin tilde, cifras y guiones (RN-LET-02-18).`);
      console.warn(`[noticias] «${nombre}» no tiene nombre de dirección: se deja fuera (es un borrador).`);
      fuera.push(nombre);
    } else if (error) {
      if (publicada) throw new Error(`La noticia «${nombre}» no se puede leer (${error}): corrígela antes de publicarla.`);
      console.warn(`[noticias] «${nombre}» tiene la cabecera mal escrita (${error}): se deja fuera (es un borrador).`);
      fuera.push(nombre);
    } else if (publicada) {
      for (const campo of ['publicada', 'modificada']) {
        if (datos[campo] instanceof Date) {
          throw new Error(`La noticia «${nombre}»: la fecha «${campo}» va sin comillas y el YAML la convierte en otra cosa; escríbela entre comillas, ISO 8601 con zona horaria (RN-LET-02-10).`);
        }
      }
    }
  }
  return fuera;
}
const FUERA = excluidos();

// Lo que se valida es solo lo publicado (ver el cargador de abajo), y se valida con manga ancha en los tipos para que el aviso
// sea el nuestro y no uno de tipos: un texto que no es texto cuenta como vacío, una fecha que no es fecha cuenta como inválida.
const texto = z.any().optional().transform((valor) => (typeof valor === 'string' ? valor : ''));
// Fecha ISO 8601 con zona (RN-LET-02-10): undefined si no viene, Date si vale, null si no vale.
const instante = z.any().optional().transform((valor) => {
  if (valor === undefined || valor === null) return undefined;
  if (valor instanceof Date) return Number.isNaN(valor.getTime()) ? null : valor;
  return instanteValido(valor) ? new Date(valor) : null; // texto ISO 8601 con zona y con un día que exista; si no, inválida
});
const fuente = z.any().optional().transform((valor) => {
  if (valor === undefined || valor === null) return undefined;
  if (typeof valor !== 'object' || Array.isArray(valor)) return null;
  return { organismo: typeof valor.organismo === 'string' ? valor.organismo : '', fecha: typeof valor.fecha === 'string' ? valor.fecha : '' };
});

const leerCarpeta = glob({
  pattern: ['*.md', ...FUERA.map((nombre) => `!${escapaGlob(nombre)}`)],
  base: pathToFileURL(CARPETA).href,
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
  // Al almacén solo entra lo publicado (RN-LET-02-07 y 08), y solo lo publicado se valida: un borrador o una retirada, tengan lo
  // que tengan a medias, ni se guardan (así no salen a dist/ ni ellos ni sus fotos) ni pueden tumbar la compilación del sitio.
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
      const parseData = async (props) => {
        const datos = props.data || {};
        if (datos.estado !== 'publicada') return { ...datos, estado: ESTADOS.includes(datos.estado) ? datos.estado : ESTADO_INICIAL };
        // Una publicada con la foto fuera de su carpeta, ausente, que no es un fichero normal o que no se puede decodificar se para
        // aquí con un aviso nuestro, antes de que Astro la copie o falle. La decodifica sharp, el mismo que usa Astro.
        if (datos.foto !== undefined) {
          const foto = datos.foto;
          if (typeof foto !== 'string' || !/^\.\/[^/\\]+$/.test(foto) || !NOMBRE_DE_FOTO.test(foto.slice(2))) {
            throw new Error(`La noticia «${props.id}»: la foto de una publicada tiene que ser un fichero de imagen de su carpeta, «./nombre.jpg» (RN-LET-02-06 y RN-LET-02-20).`);
          }
          const ruta = join(CARPETA, foto.slice(2));
          let info = null;
          try {
            info = lstatSync(ruta);
          } catch {
            info = null;
          }
          if (!info) throw new Error(`La noticia «${props.id}»: la foto «${foto}» no existe en su carpeta (RN-LET-02-06).`);
          if (!info.isFile()) throw new Error(`La noticia «${props.id}»: la foto «${foto}» no es un fichero normal (carpeta o enlace) (RN-LET-02-06 y RN-LET-02-20).`);
          try {
            await sharp(ruta, { failOn: 'error' }).toBuffer();
          } catch (fallo) {
            throw new Error(`La noticia «${props.id}»: la foto «${foto}» no es una imagen que se pueda leer (${fallo.message.split('\n')[0]}) (RN-LET-02-06).`);
          }
        }
        return contexto.parseData(props);
      };
      await leerCarpeta.load({ ...contexto, store: almacen, parseData });
    },
  },
  schema: ({ image }) =>
    z
      .object({
        titular: texto,
        entradilla: texto,
        estado: z.any().optional().transform((valor) => (ESTADOS.includes(valor) ? valor : ESTADO_INICIAL)),
        publicada: instante,
        modificada: instante, // la de la última corrección; si nunca se corrigió, la noticia no la lleva
        foto: image().optional(),
        fotoAutor: texto,
        fuente, // nota de prensa de la que sale
        prueba: z.any().optional(), // la marca de las noticias del juego de pruebas
      })
      .superRefine((datos, contexto) => {
        const falta = (campo, mensaje) => contexto.addIssue({ code: 'custom', path: [campo], message: mensaje });
        if (datos.prueba && !PRUEBAS) falta('prueba', `Esta noticia ${DEL_JUEGO}.`); // la marca, escrita como sea
        if (datos.estado !== 'publicada') return;
        if (!datos.titular.trim()) falta('titular', 'Una noticia publicada necesita titular (RN-LET-02-03).');
        if (!datos.entradilla.trim()) falta('entradilla', 'Una noticia publicada necesita entradilla (RN-LET-02-03).');
        if (!(datos.publicada instanceof Date)) {
          falta('publicada', 'Una noticia publicada necesita su fecha de publicación, ISO 8601 con zona horaria (RN-LET-02-10).');
        }
        if (datos.modificada === null) falta('modificada', 'La fecha de la última corrección tiene que ser ISO 8601 con zona horaria (RN-LET-02-10).');
        if (datos.foto && !datos.fotoAutor.trim()) falta('fotoAutor', 'Una foto publicada necesita su autor (RN-LET-02-05).');
        if (datos.fuente === null) falta('fuente', 'La fuente es el organismo y la fecha de su nota de prensa (RN-LET-02-04).');
        if (datos.fuente && !datos.fuente.organismo.trim()) falta('fuente', 'La fuente necesita el organismo (RN-LET-02-04).');
        if (datos.fuente && !diaValido(datos.fuente.fecha)) falta('fuente', 'La fecha de la nota de prensa tiene que ser un día que exista, AAAA-MM-DD (RN-LET-02-04).');
      }),
});

export const collections = { noticias };
