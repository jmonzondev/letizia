import { existsSync, lstatSync, readdirSync, readFileSync, realpathSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { imageMetadata } from 'astro/assets/utils';
import { parseFrontmatter } from '@astrojs/markdown-remark';
import yaml from 'js-yaml';
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

// Ningún enlace dentro de sitio/ (salvo node_modules, que las copias de prueba enlazan, y los ficheros de las carpetas de noticias,
// que se dejan fuera uno a uno): Astro lee src/ y copia public/ tal cual, y un enlace en cualquier sitio (public/ entero, una carpeta
// de src/pages, contenido/noticias, dist…) llevaría al sitio lo que apunte, como el juego de dist-juego o de .juego. Tampoco ficheros
// con más de un nombre (enlaces duros) en src/ ni en public/ (con cualquier mayúscula: el disco del Mac no las distingue). Se mira al
// cargar esta configuración, antes de que Astro escriba nada (RN-LET-02-19).
(() => {
  const sitio = realpathSync.native(fileURLToPath(RAIZ));
  const raros = [];
  const recorre = (dir, relativa) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const r = relativa ? `${relativa}/${e.name}` : e.name;
      if (r === 'node_modules') continue;
      const ruta = join(dir, e.name);
      if (e.isSymbolicLink()) raros.push(`${r} (enlace)`);
      else if (e.isDirectory()) {
        if (r !== 'contenido/noticias' && r !== '.juego') recorre(ruta, r);
      } else if (e.isFile() && /^(src|public)\//i.test(r) && lstatSync(ruta).nlink > 1) raros.push(`${r} (enlace duro)`);
    }
  };
  recorre(sitio, '');
  if (raros.length) {
    throw new Error(`Dentro de sitio/ hay enlaces (${raros.slice(0, 6).join(', ')}${raros.length > 6 ? '…' : ''}): Astro lee src/ y copia public/ tal cual, y un enlace llevaría al sitio lo que apunte; quítalos antes de compilar (RN-LET-02-19).`);
  }
})();

// Las imágenes que Astro importa de una publicada se juzgan por las mismas rutas que Astro va a importar: las que su procesador de
// Markdown recoge del texto, ya leídas y decodificadas (entrada.assetImports y rendered.metadata.localImagePaths), no el texto
// escrito, que se puede escribir de mil formas (escapes, entidades, referencias, citas…). Cada una tiene que ser «./nombre.ext», una
// imagen de la misma carpeta con un nombre como el de la foto (sin «./» Vite la buscaría como un paquete, con un package.json de la
// carpeta o de node_modules), un fichero normal (ni enlace, ni carpeta, ni otra cosa) y no la foto de una noticia sin publicar. Y
// ningún dato de la cabecera, salvo la foto, puede empezar por el prefijo con que Astro marca una imagen que importar
// («__ASTRO_IMAGE_»): copiaría al sitio el fichero que nombrara, de cualquier sitio del disco. La foto lo lleva porque el esquema la
// declara imagen, y solo con la forma ya comprobada «./nombre.ext» (RN-LET-02-07, 19 y 20).
const PREFIJO_DE_IMAGEN = '__ASTRO_IMAGE_';
const compruebaImagenesDeLaEntrada = (entrada) => {
  const id = entrada.id;
  const rutas = new Set([...(entrada.assetImports ?? []), ...(entrada.rendered?.metadata?.localImagePaths ?? [])]);
  for (const ruta of rutas) {
    if (typeof ruta !== 'string' || URL.canParse(ruta)) continue; // una dirección de otra web no es un fichero del disco
    const nombre = ruta.startsWith('./') ? ruta.slice(2) : '';
    if (!NOMBRE_DE_FOTO.test(nombre)) {
      throw new Error(`La noticia «${id}»: la imagen «${ruta}» de su texto tiene que escribirse «./nombre.jpg», una imagen de su misma carpeta (sin carpetas, «..», «#», «?» ni «%») (RN-LET-02-19 y RN-LET-02-20).`);
    }
    if (esFotoSinPublicar(nombre)) {
      throw new Error(`La noticia «${id}»: la imagen «${ruta}» de su texto es la foto de una noticia sin publicar, que no sale al sitio (RN-LET-02-07).`);
    }
    let info = null;
    try {
      info = lstatSync(join(CARPETA, nombre));
    } catch {
      info = null;
    }
    if (!info) throw new Error(`La noticia «${id}»: la imagen «${ruta}» de su texto no está en su carpeta (RN-LET-02-20).`);
    if (!info.isFile()) throw new Error(`La noticia «${id}»: la imagen «${ruta}» de su texto no es un fichero normal (un enlace, una carpeta u otra cosa) (RN-LET-02-19 y RN-LET-02-20).`);
  }
  const conPrefijo = [];
  const recorre = (valor, camino) => {
    if (typeof valor === 'string') {
      const fotoComprobada = camino === 'foto' && valor.startsWith(`${PREFIJO_DE_IMAGEN}./`) && NOMBRE_DE_FOTO.test(valor.slice(PREFIJO_DE_IMAGEN.length + 2));
      if (valor.startsWith(PREFIJO_DE_IMAGEN) && !fotoComprobada) conPrefijo.push(camino || '(cabecera)');
    } else if (valor && typeof valor === 'object') {
      for (const [clave, dentro] of Object.entries(valor)) recorre(dentro, camino ? `${camino}.${clave}` : clave);
    }
  };
  recorre(entrada.data, '');
  if (conPrefijo.length) {
    throw new Error(`La noticia «${id}»: ${conPrefijo.join(', ')} empieza por «${PREFIJO_DE_IMAGEN}», que Astro tomaría por una imagen que copiar al sitio; escríbelo de otra forma (RN-LET-02-19 y RN-LET-02-20).`);
  }
  // Si Astro no pudo convertir el texto (por ejemplo, una imagen con un «%» mal escrito), solo lo avisa y guarda la noticia sin texto.
  if (typeof entrada.body === 'string' && entrada.body.trim() !== '' && !entrada.rendered) {
    throw new Error(`La noticia «${id}»: Astro no pudo convertir su texto en página (mira el error de arriba) y saldría sin texto (RN-LET-02-03).`);
  }
};
// La cabecera de una publicada tal como está escrita, antes del esquema (que quita las claves que no conoce): ni el prefijo de
// imagen de Astro en ningún dato, ni un alias YAML en ciclo, ni alias anidados que se multiplican (con un tope de datos, para que
// una cabecera así no cuelgue la compilación) (RN-LET-02-08, 19 y 20).
const datoRaro = (valor) => {
  let vistos = 0;
  const mira = (v, camino, ancestros) => {
    vistos += 1;
    if (vistos > 10_000) return 'la cabecera tiene demasiados datos (alias anidados que se multiplican)';
    if (typeof v === 'string') return v.startsWith(PREFIJO_DE_IMAGEN) ? `${camino || 'la cabecera'} empieza por «${PREFIJO_DE_IMAGEN}»` : null;
    if (!v || typeof v !== 'object') return null;
    if (ancestros.has(v)) return `${camino} se contiene a sí mismo (un alias YAML en ciclo)`;
    ancestros.add(v);
    for (const [clave, dentro] of Object.entries(v)) {
      const raro = mira(dentro, camino ? `${camino}.${clave}` : clave, ancestros);
      if (raro) return raro;
    }
    ancestros.delete(v);
    return null;
  };
  return mira(valor, '', new Set());
};

// Antes de que Astro lea la carpeta se decide qué ficheros entran: la cabecera de cada .md se lee con el mismo extractor y
// analizador que usa Astro (parseFrontmatter), así que lo que Astro no pueda leer lo sabemos aquí. Si el fichero declara publicada
// y no se puede leer, se para con un aviso nuestro (falla cerrado); si no, es un borrador y se deja fuera con un aviso: lo que no
// está publicado nunca tumba el sitio (RN-LET-02-02 y 07). Al glob se le pasa la lista de los que entran (nombres que son
// direcciones: sin caracteres especiales), no un patrón con exclusiones.
// Cuando Astro no puede leer la cabecera, el estado se busca solo en ella, cortada exactamente como la corta Astro (la misma expresión
// de @astrojs/markdown-remark: termina en la primera línea que empieza por «---» o «+++»), nunca en el texto de la noticia. Cuenta
// «publicada» como valor de la clave «estado» de primer nivel en las formas que Astro leería: YAML en bloque (cada clave de primer
// nivel, por la sangría más pequeña de la cabecera, se lee aparte con js-yaml: comillas, escapes, bloques «>-», etiquetas «!!str»,
// claves escapadas o complejas «? estado», fusiones «<<:»), YAML entre llaves o JSON (por fichas, aunque falte la llave de cierre) y
// TOML («+++», también con cadenas de varias líneas). Si la cabecera es ambigua (una comilla sin cerrar delante de una línea
// «estado: publicada»), cuenta como publicada: antes parar con nuestro aviso que dejar fuera en silencio una publicada. Es una
// heurística (spec §6): un alias YAML no se resuelve.
const CABECERA_DE_ASTRO = /(?:^﻿?|^\s*\n)(?:---|\+\+\+)([\s\S]*?\n)(?:---|\+\+\+)/;
const TIPO_DE_CABECERA = /(?:^﻿?|^\s*\n)(---|\+\+\+)/;
const leeYaml = (texto) => {
  try {
    return { ok: true, valor: yaml.load(texto) };
  } catch {
    return { ok: false };
  }
};
const fichasDeLlaves = (texto) => {
  const fichas = [];
  let i = 0;
  while (i < texto.length) {
    const c = texto[i];
    if (/\s/.test(c)) {
      i += 1;
    } else if (c === '#' && (i === 0 || /\s/.test(texto[i - 1]))) {
      while (i < texto.length && texto[i] !== '\n') i += 1;
    } else if ('{}[],:'.includes(c)) {
      fichas.push({ signo: c });
      i += 1;
    } else if (c === '"' || c === "'") {
      let j = i + 1;
      while (j < texto.length) {
        if (c === '"' && texto[j] === '\\') j += 2;
        else if (texto[j] === c && c === "'" && texto[j + 1] === "'") j += 2;
        else if (texto[j] === c) break;
        else j += 1;
      }
      const crudo = texto.slice(i, Math.min(j + 1, texto.length));
      const leido = leeYaml(crudo.length > 1 && crudo.endsWith(c) ? crudo : `${crudo}${c}`);
      fichas.push({ texto: leido.ok && typeof leido.valor === 'string' ? leido.valor : crudo.slice(1, -1) });
      i = j + 1;
    } else {
      let j = i;
      while (j < texto.length && !'{}[],\n'.includes(texto[j]) && !(texto[j] === ':' && (j + 1 >= texto.length || /[\s,{}[\]]/.test(texto[j + 1])))) j += 1;
      fichas.push({ texto: texto.slice(i, j).trim() });
      i = j;
    }
  }
  return fichas;
};
const enLlaves = (bloque) => {
  const f = fichasDeLlaves(bloque);
  let hondo = 0;
  for (let k = 0; k < f.length; k += 1) {
    if (f[k].signo === '{' || f[k].signo === '[') hondo += 1;
    else if (f[k].signo === '}' || f[k].signo === ']') hondo -= 1;
    else if (hondo === 1 && f[k].texto === 'estado' && f[k + 1]?.signo === ':' && f[k + 2]?.texto === 'publicada' && (f[k - 1]?.signo === '{' || f[k - 1]?.signo === ',')) return true;
  }
  return false;
};
const enBloqueYaml = (bloque) => {
  const lineas = bloque.split(/\r?\n/);
  const cuenta = (l) => l.trim() !== '' && !/^\s*#/.test(l);
  const sangria = (l) => l.match(/^[ \t]*/)[0].length;
  const sangrias = lineas.filter(cuenta).map(sangria);
  if (!sangrias.length) return false;
  const base = Math.min(...sangrias);
  const trozos = [];
  for (const l of lineas) {
    if (cuenta(l) && sangria(l) === base && !(trozos.length && /^[ \t]*:(\s|$)/.test(l))) trozos.push([l]);
    else if (trozos.length) trozos[trozos.length - 1].push(l);
  }
  for (const t of trozos) {
    const texto = t.map((l) => l.slice(Math.min(base, sangria(l)))).join('\n');
    const leido = leeYaml(texto);
    if (leido.ok) {
      if (leido.valor && typeof leido.valor === 'object' && !Array.isArray(leido.valor) && leido.valor.estado === 'publicada') return true;
      continue;
    }
    const m = texto.split('\n')[0].match(/^(?:\?\s*)?["']?estado["']?\s*:(.*)$/);
    if (m && /^\s*(?:!!str\s+)?(["']?)publicada\1\s*(?:#.*)?$/.test(m[1])) return true;
  }
  return false;
};
const cadenaToml = (crudo) => {
  if (crudo.startsWith("'")) return crudo.slice(1, -1);
  try {
    return JSON.parse(crudo.replace(/\\U([0-9a-fA-F]{8})/g, (_, h) => String.fromCodePoint(parseInt(h, 16))));
  } catch {
    return crudo.slice(1, -1);
  }
};
const cadenaTomlLarga = (contenido, comillas) => {
  const t = contenido.replace(/^\r?\n/, ''); // TOML quita el salto de línea que sigue a las comillas de apertura
  if (comillas === "'''") return t;
  const unida = t.replace(/\\[ \t]*\r?\n\s*/g, '').replace(/(\\*)"/g, (m, barras) => (barras.length % 2 ? m : `${barras}\\"`)).replace(/\r?\n/g, '\\n');
  return cadenaToml(`"${unida}"`);
};
const enToml = (bloque) => {
  const lineas = bloque.split(/\r?\n/);
  for (let i = 0; i < lineas.length; i += 1) {
    if (/^\s*\[/.test(lineas[i])) return false; // a partir de una tabla, las claves ya no son de primer nivel
    const m = lineas[i].match(/^\s*("(?:[^"\\]|\\.)*"|'[^']*'|[A-Za-z0-9_-]+)\s*=\s*(.*)$/);
    if (!m) continue;
    const clave = /^["']/.test(m[1]) ? cadenaToml(m[1]) : m[1];
    const larga = m[2].match(/^("""|''')([\s\S]*)$/);
    if (larga) {
      let contenido = larga[2];
      let fin = contenido.indexOf(larga[1]);
      while (fin < 0 && i + 1 < lineas.length) {
        i += 1; // las líneas de dentro de la cadena no son claves
        contenido += `\n${lineas[i]}`;
        fin = contenido.indexOf(larga[1]);
      }
      if (clave === 'estado' && cadenaTomlLarga(fin >= 0 ? contenido.slice(0, fin) : contenido, larga[1]) === 'publicada') return true;
      continue;
    }
    const corta = m[2].match(/^("(?:[^"\\]|\\.)*"|'[^']*')\s*(?:#.*)?$/);
    if (clave === 'estado' && corta && cadenaToml(corta[1]) === 'publicada') return true;
  }
  return false;
};
const pareceDeclararPublicada = (texto) => {
  const bloque = CABECERA_DE_ASTRO.exec(texto)?.[1];
  if (bloque == null) return false;
  if (TIPO_DE_CABECERA.exec(texto)?.[1] === '+++') return enToml(bloque);
  // Entre llaves aunque delante haya líneas de comentario, una etiqueta («!!map», «!<…>») o un ancla («&m»), que YAML admite antes de la llave.
  const sinPreambulo = bloque.replace(/^(?:[ \t]*(?:#[^\n]*)?\n)*/, '').replace(/^[ \t]*(?:(?:!\S*|&\S+)[ \t]*)+\n?/, '');
  return /^\s*\{/.test(sinPreambulo) ? enLlaves(sinPreambulo) : enBloqueYaml(bloque);
};
// Las fotos de las noticias sin publicar, por su fichero (dispositivo e inode), no por cómo se escribe su nombre: el disco del Mac no
// distingue mayúsculas y un mismo fichero se puede nombrar de varias formas. Una foto que una publicada declara como suya es pública,
// aunque la nombre también una sin publicar (solo se llega a eso escribiendo a mano: el gestor nunca reutiliza un fichero), así que
// ni la publicada ni el borrador tumban la compilación por ella (RN-LET-02-02 y 07).
const FOTOS_SIN_PUBLICAR = new Set();
const FOTOS_PUBLICADAS = new Set();
const ficheroDe = (nombre) => {
  try {
    const s = statSync(join(CARPETA, nombre));
    return `${s.dev}:${s.ino}`;
  } catch {
    return null;
  }
};
const esFotoSinPublicar = (nombre) => {
  const f = ficheroDe(nombre);
  return f !== null && FOTOS_SIN_PUBLICAR.has(f) && !FOTOS_PUBLICADAS.has(f);
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
    if (datos && typeof datos.foto === 'string') {
      const f = ficheroDe(datos.foto.replace(/^\.\//, ''));
      if (f) (datos.estado === 'publicada' ? FOTOS_PUBLICADAS : FOTOS_SIN_PUBLICAR).add(f);
    }
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
      // La dirección pública la fija DOMINIO y nada más: ni «--site» en la orden la cambia (RN-LET-02-14 a 16).
      const dominioPedido = (process.env.DOMINIO ?? '').trim().replace(/\/+$/, '');
      const sitioDeLaOrden = String(contexto.config.site ?? '').replace(/\/+$/, '');
      if (sitioDeLaOrden !== dominioPedido) {
        throw new Error(`La dirección pública del sitio la fija DOMINIO (${dominioPedido || 'sin poner'}), no «--site» (pedida: ${sitioDeLaOrden || 'ninguna'}) (RN-LET-02-14 a 16).`);
      }
      // Y el sitio se publica en la raíz de su dominio: con otra base, las fotos y su JSON-LD apuntarían adonde no están (RN-LET-02-06 y 09).
      if ((contexto.config.base ?? '/') !== '/') {
        throw new Error(`El sitio se publica en la raíz de su dominio: no pidas otra base con «--base» (pedida: ${contexto.config.base}) (RN-LET-02-06 y 09).`);
      }
      contexto.store.clear();
      const almacen = {
        ...contexto.store,
        set: (entrada) => {
          if (entrada.data.estado === 'publicada') {
            compruebaImagenesDeLaEntrada(entrada);
            return contexto.store.set(entrada);
          }
          contexto.store.delete(entrada.id); // en `astro dev`, una publicada que se retira sale del almacén
          return false;
        },
      };
      const parseData = async (props) => {
        const datos = props.data || {};
        if (datos.estado !== 'publicada') return { ...datos, estado: ESTADOS.includes(datos.estado) ? datos.estado : ESTADO_INICIAL };
        const raro = datoRaro(datos);
        if (raro) throw new Error(`La noticia «${props.id}»: ${raro}; corrígelo antes de publicarla (RN-LET-02-08, 19 y 20).`);
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
      if (DENTRO.length) await leerCarpeta.load({ ...contexto, store: almacen, parseData }); // sin noticias, nada que cargar (ni el centinela)
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
