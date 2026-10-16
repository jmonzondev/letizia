// Gestor de noticias: lo mínimo que hace falta para crear, publicar, corregir y retirar una noticia como fichero de contenido
// (DEC-L-003). Lo usa el cargador del juego de pruebas (cargar-juego.mjs) y lo reutilizará el editor de la clienta.
//
// Una noticia es <carpeta>/<dirección>.md: una cabecera de líneas «clave: valor JSON» (JSON es YAML válido, así que Astro la
// lee tal cual) y el texto debajo. La dirección se asigna una sola vez, al crearla, y no cambia aunque se corrija el titular.
// Un borrador puede estar a medias; lo que se publica tiene que estar completo y bien escrito (lo comprueba publicar()).
// Las operaciones sobre una noticia se turnan con un cerrojo y escriben de forma atómica: dos a la vez no se pisan.

import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { DIRECCION, DIRECCION_DEL_JUEGO, ESTADO_INICIAL, ESTADOS, NOMBRE_DE_FOTO, diaValido, esImagen, fechaValida, isoMadrid } from '../src/noticias/modelo.js';

const CAMPOS = ['titular', 'entradilla', 'estado', 'publicada', 'modificada', 'foto', 'fotoAutor', 'fuente', 'prueba'];

const enBlanco = (valor) => typeof valor !== 'string' || valor.trim() === '';

/** Un campo de texto opcional: si viene, tiene que ser texto (null, números o listas no valen). */
function textoOpcional(valor, campo) {
  if (valor === undefined) return undefined;
  if (typeof valor !== 'string') throw new Error(`El campo «${campo}» tiene que ser texto`);
  return valor;
}

/** La fuente, si viene: organismo con texto y fecha de un día que exista, AAAA-MM-DD (RN-LET-02-04). */
function fuenteValida(fuente) {
  if (fuente === undefined) return undefined;
  if (fuente === null || typeof fuente !== 'object' || Array.isArray(fuente)) throw new Error('La fuente es un objeto con organismo y fecha');
  if (enBlanco(fuente.organismo)) throw new Error('La fuente necesita el organismo');
  if (!diaValido(fuente.fecha)) throw new Error(`La fecha de la nota de prensa «${fuente.fecha}» no es un día que exista (AAAA-MM-DD)`);
  return { organismo: fuente.organismo, fecha: fuente.fecha };
}

const fichero = (carpeta, direccion) => {
  // Una dirección de noticia, nunca una ruta: ni se lee ni se escribe fuera de la carpeta.
  if (typeof direccion !== 'string' || !DIRECCION.test(direccion)) {
    throw new Error(`La dirección «${direccion}» no vale: solo minúsculas sin tilde, cifras y guiones`);
  }
  return join(carpeta, `${direccion}.md`);
};

/** Un .md o una foto que sea un enlace no se toca: podría llevar fuera de la carpeta. */
function sinEnlace(ruta) {
  try {
    if (lstatSync(ruta).isSymbolicLink()) throw new Error(`${ruta} es un enlace: el gestor no lo sigue`);
  } catch (fallo) {
    if (fallo.code !== 'ENOENT') throw fallo;
  }
}

function escribe(carpeta, direccion, { datos, texto }, { nueva = false } = {}) {
  const ruta = fichero(carpeta, direccion);
  sinEnlace(ruta);
  const cabecera = CAMPOS.filter((campo) => datos[campo] !== undefined).map((campo) => `${campo}: ${JSON.stringify(datos[campo])}`);
  const contenido = `---\n${cabecera.join('\n')}\n---\n\n${texto}\n`;
  if (nueva) {
    // Solo si no existe (wx): dos altas a la vez con la misma dirección no se pisan.
    try {
      writeFileSync(ruta, contenido, { flag: 'wx' });
    } catch (fallo) {
      if (fallo.code === 'EEXIST') throw new Error(`La dirección «${direccion}» ya está en uso (otra alta a la vez)`);
      throw fallo;
    }
    return;
  }
  // Atómica: se escribe al lado y se renombra, para que una compilación nunca lea una noticia a medias.
  const temporal = `${ruta}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(temporal, contenido, { flag: 'wx' });
  renameSync(temporal, ruta);
}

function lee(carpeta, direccion) {
  const ruta = fichero(carpeta, direccion);
  sinEnlace(ruta);
  const partes = readFileSync(ruta, 'utf8').match(/^---\n([\s\S]*?)\n---\n\n([\s\S]*)\n$/);
  if (!partes) throw new Error(`${direccion}.md no tiene la forma de una noticia`);
  const datos = Object.fromEntries(
    partes[1].split('\n').map((linea) => {
      const corte = linea.indexOf(': ');
      return [linea.slice(0, corte), JSON.parse(linea.slice(corte + 2))];
    }),
  );
  return { datos, texto: partes[2] };
}

/** Publicar, corregir y retirar leen, cambian y escriben: con un cerrojo por noticia, dos a la vez se turnan en vez de pisarse. */
const procesoVivo = (pid) => {
  try {
    process.kill(pid, 0);
    return true;
  } catch (fallo) {
    return fallo.code === 'EPERM';
  }
};
/** Un cerrojo cuyo proceso ya no existe, o de hace más de un minuto, es huérfano (un kill -9): se retira y se sigue. */
function cerrojoHuerfano(cerrojo) {
  try {
    const [pid, momento] = readFileSync(cerrojo, 'utf8').trim().split(/\s+/);
    return !procesoVivo(Number(pid)) || Date.now() - Number(momento) > 60_000;
  } catch {
    return true;
  }
}
function conCerrojo(carpeta, direccion, trabajo) {
  const cerrojo = `${fichero(carpeta, direccion)}.cerrojo`;
  const espera = new Int32Array(new SharedArrayBuffer(4));
  for (let intento = 0; ; intento += 1) {
    try {
      writeFileSync(cerrojo, `${process.pid} ${Date.now()}`, { flag: 'wx' });
      break;
    } catch (fallo) {
      if (fallo.code !== 'EEXIST' || intento >= 500) throw new Error(`«${direccion}» está en uso por otra operación que no acaba`);
      if (cerrojoHuerfano(cerrojo)) {
        rmSync(cerrojo, { force: true });
        continue;
      }
      Atomics.wait(espera, 0, 0, 10);
    }
  }
  try {
    return trabajo();
  } finally {
    rmSync(cerrojo, { force: true });
  }
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
  if (enBlanco(titular)) throw new Error('Una noticia necesita titular');
  textoOpcional(entradilla, 'entradilla');
  textoOpcional(texto, 'texto');
  fotoAutor = textoOpcional(fotoAutor, 'fotoAutor');
  fuente = fuenteValida(fuente);
  if (foto) {
    // Un nombre de fichero de imagen, no una ruta ni un .md, y unos bytes que sean una imagen: ni escribe fuera de la carpeta, ni se
    // lee como noticia, ni publica algo que tumbaría la compilación.
    if (!NOMBRE_DE_FOTO.test(foto.fichero ?? '')) {
      throw new Error(`El nombre de la foto «${foto.fichero}» no vale: un nombre de fichero de imagen (jpg, png, webp, avif o gif), sin ruta ni espacios`);
    }
    if (!esImagen(foto.bytes)) throw new Error(`La foto «${foto.fichero}» no es una imagen (jpg, png, gif, webp o avif)`);
  }
  mkdirSync(carpeta, { recursive: true });
  const ocupadas = new Set(readdirSync(carpeta).filter((f) => f.endsWith('.md')).map((f) => f.slice(0, -3)));
  if (direccion === undefined) {
    direccion = direccionDe(titular, ocupadas);
  } else if (!DIRECCION.test(direccion) || ocupadas.has(direccion)) {
    throw new Error(`La dirección «${direccion}» no vale o ya está en uso`);
  } else if (DIRECCION_DEL_JUEGO.test(direccion) && !prueba) {
    throw new Error(`La dirección «${direccion}» es del juego de pruebas: una noticia real no puede usarla`);
  }
  // Primero la noticia y después la foto, las dos con «solo si no existe»: si otra alta se adelanta, esta falla sin pisar nada.
  escribe(carpeta, direccion, {
    datos: { titular, entradilla, foto: foto && `./${foto.fichero}`, fotoAutor, fuente, prueba: prueba ? true : undefined },
    texto,
  }, { nueva: true });
  if (foto) {
    const rutaFoto = join(carpeta, foto.fichero);
    try {
      sinEnlace(rutaFoto);
      writeFileSync(rutaFoto, foto.bytes, { flag: 'wx' });
    } catch (fallo) {
      rmSync(fichero(carpeta, direccion)); // la noticia recién creada, sin su foto, no se deja a medias
      if (fallo.code === 'EEXIST') throw new Error(`Ya hay un fichero «${foto.fichero}» en la carpeta: la foto de otra noticia no se pisa`);
      throw fallo;
    }
  }
  return direccion;
}

/**
 * La marca como publicada, con su fecha de publicación (por defecto, ahora). Lo corregido antes de publicarla (un borrador, o una
 * retirada que se vuelve a publicar) forma parte de la noticia que se publica: su última corrección empieza de cero.
 */
export function publicar(carpeta, direccion, { fecha = new Date() } = {}) {
  if (!fechaValida(fecha)) throw new Error(`«${direccion}»: la fecha de publicación no es una fecha`);
  return conCerrojo(carpeta, direccion, () => {
    const noticia = lee(carpeta, direccion);
    if (noticia.datos.estado === 'publicada') {
      throw new Error(`«${direccion}» ya está publicada: para cambiarla usa corregir(); para cambiar su fecha, retírala y publícala de nuevo`);
    }
    // Lo que se publica está completo: titular y entradilla (RN-LET-02-03), autor de la foto (RN-LET-02-05) y fuente bien escrita (RN-LET-02-04).
    if (enBlanco(noticia.datos.titular)) throw new Error(`«${direccion}» no tiene titular: no se publica`);
    if (enBlanco(noticia.datos.entradilla)) throw new Error(`«${direccion}» no tiene entradilla: no se publica`);
    if (noticia.datos.foto && enBlanco(noticia.datos.fotoAutor)) throw new Error(`«${direccion}» tiene foto sin autor: no se publica`);
    if (noticia.datos.foto && !existsSync(join(carpeta, String(noticia.datos.foto).replace(/^\.\//, '')))) {
      throw new Error(`«${direccion}»: su foto «${noticia.datos.foto}» no está en la carpeta: no se publica`);
    }
    if (noticia.datos.fuente !== undefined) fuenteValida(noticia.datos.fuente);
    Object.assign(noticia.datos, { estado: 'publicada', publicada: isoMadrid(fecha) });
    delete noticia.datos.modificada;
    escribe(carpeta, direccion, noticia);
  });
}

/** Corrige titular, entradilla o texto sin cambiar su dirección ni su fecha de publicación, y anota cuándo se corrigió. */
export function corregir(carpeta, direccion, cambios, { ahora = new Date() } = {}) {
  if (!fechaValida(ahora)) throw new Error(`«${direccion}»: la fecha de la corrección no es una fecha`);
  return conCerrojo(carpeta, direccion, () => {
    const noticia = lee(carpeta, direccion);
    // Nada se corrige a vacío ni a algo que no sea texto; la entradilla de una publicada no puede quedar vacía (RN-LET-02-03).
    if (cambios.titular !== undefined && enBlanco(cambios.titular)) throw new Error(`«${direccion}»: el titular no puede quedar vacío`);
    textoOpcional(cambios.entradilla, 'entradilla');
    textoOpcional(cambios.texto, 'texto');
    if (noticia.datos.estado === 'publicada' && cambios.entradilla !== undefined && enBlanco(cambios.entradilla)) {
      throw new Error(`«${direccion}»: la entradilla de una noticia publicada no puede quedar vacía`);
    }
    for (const campo of ['titular', 'entradilla']) if (cambios[campo] !== undefined) noticia.datos[campo] = cambios[campo];
    if (cambios.texto !== undefined) noticia.texto = cambios.texto;
    noticia.datos.modificada = isoMadrid(ahora);
    escribe(carpeta, direccion, noticia);
  });
}

/** La retira de la web: el fichero se queda, pero deja de publicarse. */
export function retirar(carpeta, direccion) {
  return conCerrojo(carpeta, direccion, () => {
    const noticia = lee(carpeta, direccion);
    noticia.datos.estado = 'retirada';
    escribe(carpeta, direccion, noticia);
  });
}

/** El estado con el que la deja el gestor: el que lleva el fichero o, si no lleva ninguno, el de toda noticia nueva. */
export function estadoDe(carpeta, direccion) {
  const { datos } = lee(carpeta, direccion);
  const estado = datos.estado ?? ESTADO_INICIAL;
  if (!ESTADOS.includes(estado)) throw new Error(`${direccion}.md tiene un estado desconocido: ${estado}`);
  return estado;
}
