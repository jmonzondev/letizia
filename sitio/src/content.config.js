import { existsSync, lstatSync, readdirSync, readFileSync, realpathSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { imageMetadata } from 'astro/assets/utils';
import { parseFrontmatter } from '@astrojs/markdown-remark';
import sharp from 'sharp'; // estático: una importación dinámica aquí pasaría por el ejecutor de Vite, que ya está cerrado al sincronizar
import { DIRECCION, DIRECCION_DEL_JUEGO, ESTADOS, ESTADO_INICIAL, NOMBRE_DE_FOTO, diaValido, instanteValido } from './noticias/modelo.js';
import { esEnlace, rutaReal } from './noticias/rutas.js';

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

// Antes de que Astro lea la carpeta se decide qué ficheros entran: la cabecera de cada .md se lee con el mismo extractor y
// analizador que usa Astro (parseFrontmatter), así que lo que Astro no pueda leer lo sabemos aquí. Si el fichero declara publicada
// y no se puede leer, se para con un aviso nuestro (falla cerrado); si no, es un borrador y se deja fuera con un aviso: lo que no
// está publicado nunca tumba el sitio (RN-LET-02-02 y 07). Al glob se le pasa la lista de los que entran (nombres que son
// direcciones: sin caracteres especiales), no un patrón con exclusiones.
// Cuando Astro no puede leer la cabecera, el estado se busca en el texto de la cabecera y solo en él (nunca en el texto de la
// noticia): lo que va entre las dos primeras líneas «---» (o «+++», TOML). Cuenta cualquier clave «estado» (con o sin comillas,
// seguida de «:» o «=») cuyo valor, con sus líneas de continuación y sin comentarios, lleve «publicada»: así se reconoce lo que Astro
// leería como publicada en cualquier forma (texto, entre comillas, bloque «>-», etiqueta «!!str», TOML).
const pareceDeclararPublicada = (texto) => {
  const limpio = texto.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n');
  const bloque = limpio.match(/^\s*(---|\+\+\+)[ \t]*\n([\s\S]*?)(?:\n\1[ \t]*(?:\n|$)|$)/);
  if (!bloque) return false;
  const lineas = bloque[2].split('\n');
  for (let i = 0; i < lineas.length; i += 1) {
    const clave = lineas[i].match(/(?:^|[{,])\s*["']?estado["']?\s*[:=]([\s\S]*)$/);
    if (!clave) continue;
    let valor = clave[1];
    for (let j = i + 1; j < lineas.length && /^\s+\S/.test(lineas[j]); j += 1) valor += `\n${lineas[j]}`;
    if (/publicada/i.test(valor.replace(/(^|\s)#.*$/gm, ''))) return true;
  }
  return false;
};
function incluidos() {
  const dentro = [];
  if (!existsSync(CARPETA)) return dentro;
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
      continue;
    }
    let texto;
    try {
      texto = readFileSync(ruta, 'utf8');
    } catch (fallo) {
      console.warn(`[noticias] «${nombre}» no se puede leer (${fallo.code}): se deja fuera.`);
      continue;
    }
    const direccion = nombre.slice(0, -3);
    let datos = null;
    let error = null;
    try {
      const { frontmatter } = parseFrontmatter(texto);
      if (!frontmatter || typeof frontmatter !== 'object' || Array.isArray(frontmatter)) error = 'la cabecera no es una lista de campos';
      else datos = frontmatter;
    } catch (fallo) {
      error = String(fallo.message).split('\n')[0];
    }
    const publicada = datos ? datos.estado === 'publicada' : pareceDeclararPublicada(texto);
    if (!DIRECCION.test(direccion)) {
      if (publicada) throw new Error(`La noticia «${nombre}» no vale: su dirección solo puede llevar minúsculas sin tilde, cifras y guiones (RN-LET-02-18).`);
      console.warn(`[noticias] «${nombre}» no tiene nombre de dirección: se deja fuera (es un borrador).`);
      continue;
    }
    if (error) {
      if (publicada) throw new Error(`La noticia «${nombre}» no se puede leer (${error}): corrígela antes de publicarla.`);
      console.warn(`[noticias] «${nombre}» tiene la cabecera mal escrita (${error}): se deja fuera (es un borrador).`);
      continue;
    }
    if (publicada) {
      for (const [campo, valor] of [['publicada', datos.publicada], ['modificada', datos.modificada], ['fuente.fecha', datos.fuente && datos.fuente.fecha]]) {
        if (valor instanceof Date) {
          throw new Error(`La noticia «${nombre}»: la fecha «${campo}» va sin comillas y el YAML la convierte en otra cosa; escríbela entre comillas (RN-LET-02-10 y RN-LET-02-04).`);
        }
      }
    }
    dentro.push(nombre);
  }
  return dentro;
}
const DENTRO = incluidos();

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
  pattern: DENTRO.length ? DENTRO : ['__ninguna-noticia__.md'],
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
      // La carpeta de salida se juzga por su ruta real (tramo a tramo, siguiendo enlaces, con las mayúsculas del disco): tiene que ser
      // exactamente sitio/dist (producción) o sitio/dist-juego (pruebas), carpetas de verdad y no enlaces, y ninguna otra: ni un
      // --outDir en la orden, ni un enlace llamado dist, ni un disco que no distingue mayúsculas lo cambian (RN-LET-02-19). Como se
      // comprueba al sincronizar el contenido, antes de que Astro vacíe la salida, una salida negada no toca la carpeta pedida.
      const sitio = realpathSync.native(fileURLToPath(RAIZ));
      const pedida = fileURLToPath(contexto.config.outDir);
      const esperada = join(sitio, PRUEBAS ? 'dist-juego' : 'dist');
      let salida;
      try {
        salida = rutaReal(pedida, sitio);
      } catch (fallo) {
        throw new Error(`La carpeta de salida ${pedida} no vale: ${fallo.message}`);
      }
      for (const nombre of ['dist', 'dist-juego']) {
        if (esEnlace(join(sitio, nombre))) throw new Error(`sitio/${nombre} es un enlace: dist y dist-juego tienen que ser carpetas de verdad, no se compila a través de enlaces (RN-LET-02-19).`);
      }
      if (salida !== esperada) {
        throw new Error(`La compilación ${PRUEBAS ? 'de pruebas (NOTICIAS_DIR) solo puede salir a sitio/dist-juego' : 'solo puede salir a sitio/dist'}: no pidas otra carpeta con --outDir (pedida: ${pedida}; su ruta real: ${salida}).`);
      }
      // Y dentro de public/ no puede haber enlaces: Astro copia public/ tal cual a la salida, y un enlace llevaría al sitio lo que
      // apunte (el juego compilado en dist-juego, las noticias en bruto…).
      const enlacesEn = (dir) => readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isSymbolicLink() ? [join(dir, e.name)] : e.isDirectory() ? enlacesEn(join(dir, e.name)) : []));
      const publica = join(sitio, 'public');
      const enlaces = existsSync(publica) ? enlacesEn(publica) : [];
      if (enlaces.length) {
        throw new Error(`Dentro de public/ hay enlaces (${enlaces.map((e) => e.slice(sitio.length + 1)).join(', ')}): public/ se copia tal cual al sitio y no puede llevar enlaces (RN-LET-02-19).`);
      }
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
          const bytes = readFileSync(ruta);
          let meta;
          try {
            meta = await imageMetadata(bytes, ruta);
          } catch (fallo) {
            throw new Error(`La noticia «${props.id}»: la foto «${foto}» no se puede medir como imagen (${String(fallo.message).split('\n')[0]}) (RN-LET-02-06).`);
          }
          try {
            await sharp(bytes, { failOn: 'error' }).toBuffer();
          } catch (fallo) {
            throw new Error(`La noticia «${props.id}»: la foto «${foto}» no es una imagen que se pueda leer (${String(fallo.message).split('\n')[0]}) (RN-LET-02-06).`);
          }
          const ext = foto.toLowerCase().split('.').pop();
          const esperado = { jpg: 'jpg', jpeg: 'jpg', png: 'png', gif: 'gif', webp: 'webp' }[ext];
          if ((meta.format === 'jpeg' ? 'jpg' : meta.format) !== esperado) {
            throw new Error(`La noticia «${props.id}»: la foto «${foto}» es un ${meta.format} con extensión .${ext}; el navegador la mostraría rota (RN-LET-02-06).`);
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
