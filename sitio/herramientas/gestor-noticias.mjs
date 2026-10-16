// Gestor de noticias: lo mínimo que hace falta para crear, publicar, corregir y retirar una noticia como fichero de contenido
// (DEC-L-003). Lo usa el cargador del juego de pruebas (cargar-juego.mjs) y lo reutilizará el editor de la clienta.
//
// Una noticia es <carpeta>/<dirección>.md: una cabecera de líneas «clave: valor JSON» (JSON es YAML válido, así que Astro la
// lee tal cual) y el texto debajo. La dirección se asigna una sola vez, al crearla, y no cambia aunque se corrija el titular.

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { DIRECCION, DIRECCION_DEL_JUEGO, ESTADO_INICIAL, ESTADOS, NOMBRE_DE_FOTO, isoMadrid } from '../src/noticias/modelo.js';

const CAMPOS = ['titular', 'entradilla', 'estado', 'publicada', 'modificada', 'foto', 'fotoAutor', 'fuente', 'prueba'];

const fichero = (carpeta, direccion) => {
  // Una dirección de noticia, nunca una ruta: ni se lee ni se escribe fuera de la carpeta.
  if (typeof direccion !== 'string' || !DIRECCION.test(direccion)) {
    throw new Error(`La dirección «${direccion}» no vale: solo minúsculas sin tilde, cifras y guiones`);
  }
  return join(carpeta, `${direccion}.md`);
};

function escribe(carpeta, direccion, { datos, texto }) {
  const cabecera = CAMPOS.filter((campo) => datos[campo] !== undefined).map((campo) => `${campo}: ${JSON.stringify(datos[campo])}`);
  writeFileSync(fichero(carpeta, direccion), `---\n${cabecera.join('\n')}\n---\n\n${texto}\n`);
}

function lee(carpeta, direccion) {
  const partes = readFileSync(fichero(carpeta, direccion), 'utf8').match(/^---\n([\s\S]*?)\n---\n\n([\s\S]*)\n$/);
  if (!partes) throw new Error(`${direccion}.md no tiene la forma de una noticia`);
  const datos = Object.fromEntries(
    partes[1].split('\n').map((linea) => {
      const corte = linea.indexOf(': ');
      return [linea.slice(0, corte), JSON.parse(linea.slice(corte + 2))];
    }),
  );
  return { datos, texto: partes[2] };
}

/** Dirección a partir del titular: minúsculas sin tilde, cifras y guiones; si ya está en uso o es una del juego de pruebas, con «-2», «-3»… */
export function direccionDe(titular, ocupadas) {
  const base =
    titular
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80)
      .replace(/-+$/, '') || 'noticia';
  let direccion = base;
  for (let n = 2; ocupadas.has(direccion) || DIRECCION_DEL_JUEGO.test(direccion); n += 1) direccion = `${base}-${n}`;
  return direccion;
}

/**
 * Crea una noticia. Nace en borrador (no lleva estado) y devuelve su dirección, la que se pide o la que asigna el gestor.
 * Con `prueba: true` queda marcada como del juego de pruebas, y el sitio publicado no la acepta (RN-LET-02-19).
 */
export function crear(carpeta, { titular, entradilla = '', texto = '', direccion, foto, fotoAutor, fuente, prueba }) {
  if (typeof titular !== 'string' || titular.trim() === '') throw new Error('Una noticia necesita titular');
  mkdirSync(carpeta, { recursive: true });
  const ocupadas = new Set(readdirSync(carpeta).filter((f) => f.endsWith('.md')).map((f) => f.slice(0, -3)));
  if (direccion === undefined) {
    direccion = direccionDe(titular, ocupadas);
  } else if (!DIRECCION.test(direccion) || ocupadas.has(direccion)) {
    throw new Error(`La dirección «${direccion}» no vale o ya está en uso`);
  }
  if (foto) {
    // Un nombre de fichero de imagen, no una ruta ni un .md, y que no sea el de otra foto: ni escribe fuera de la carpeta, ni se
    // lee como noticia, ni pisa la foto de otra noticia.
    if (!NOMBRE_DE_FOTO.test(foto.fichero)) {
      throw new Error(`El nombre de la foto «${foto.fichero}» no vale: un nombre de fichero de imagen (jpg, png, webp, avif o gif), sin ruta ni espacios`);
    }
    if (existsSync(join(carpeta, foto.fichero))) {
      throw new Error(`Ya hay un fichero «${foto.fichero}» en la carpeta: la foto de otra noticia no se pisa`);
    }
    writeFileSync(join(carpeta, foto.fichero), foto.bytes);
  }
  escribe(carpeta, direccion, {
    datos: { titular, entradilla, foto: foto && `./${foto.fichero}`, fotoAutor, fuente, prueba: prueba ? true : undefined },
    texto,
  });
  return direccion;
}

/**
 * La marca como publicada, con su fecha de publicación (por defecto, ahora). Lo corregido antes de publicarla (un borrador, o una
 * retirada que se vuelve a publicar) forma parte de la noticia que se publica: su última corrección empieza de cero.
 */
export function publicar(carpeta, direccion, { fecha = new Date() } = {}) {
  const noticia = lee(carpeta, direccion);
  if (noticia.datos.estado === 'publicada') {
    throw new Error(`«${direccion}» ya está publicada: para cambiarla usa corregir(); para cambiar su fecha, retírala y publícala de nuevo`);
  }
  // Lo que se publica está completo: la ficha lleva entradilla (RN-LET-02-03) y una foto lleva su autor (RN-LET-02-05).
  if (!noticia.datos.entradilla || String(noticia.datos.entradilla).trim() === '') throw new Error(`«${direccion}» no tiene entradilla: no se publica`);
  if (noticia.datos.foto && !noticia.datos.fotoAutor) throw new Error(`«${direccion}» tiene foto sin autor: no se publica`);
  Object.assign(noticia.datos, { estado: 'publicada', publicada: isoMadrid(fecha) });
  delete noticia.datos.modificada;
  escribe(carpeta, direccion, noticia);
}

/** Corrige titular, entradilla o texto sin cambiar su dirección ni su fecha de publicación, y anota cuándo se corrigió. */
export function corregir(carpeta, direccion, cambios, { ahora = new Date() } = {}) {
  const noticia = lee(carpeta, direccion);
  for (const campo of ['titular', 'entradilla']) if (cambios[campo] !== undefined) noticia.datos[campo] = cambios[campo];
  if (cambios.texto !== undefined) noticia.texto = cambios.texto;
  noticia.datos.modificada = isoMadrid(ahora);
  escribe(carpeta, direccion, noticia);
}

/** La retira de la web: el fichero se queda, pero deja de publicarse. */
export function retirar(carpeta, direccion) {
  const noticia = lee(carpeta, direccion);
  noticia.datos.estado = 'retirada';
  escribe(carpeta, direccion, noticia);
}

/** El estado con el que la deja el gestor: el que lleva el fichero o, si no lleva ninguno, el de toda noticia nueva. */
export function estadoDe(carpeta, direccion) {
  const { datos } = lee(carpeta, direccion);
  const estado = datos.estado ?? ESTADO_INICIAL;
  if (!ESTADOS.includes(estado)) throw new Error(`${direccion}.md tiene un estado desconocido: ${estado}`);
  return estado;
}

