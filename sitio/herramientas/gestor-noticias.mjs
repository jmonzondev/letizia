// Gestor de noticias: lo mínimo que hace falta para crear, publicar, corregir y retirar una noticia como fichero de contenido
// (DEC-L-003). Lo usa el cargador del juego de pruebas (cargar-juego.mjs) y lo reutilizará el editor de la clienta.
//
// Una noticia es <carpeta>/<dirección>.md: una cabecera de líneas «clave: valor JSON» (JSON es YAML válido, así que Astro la
// lee tal cual) y el texto debajo. La dirección se asigna una sola vez, al crearla, y no cambia aunque se corrija el titular.
// Un borrador puede estar a medias; lo que se publica tiene que estar completo y bien escrito (lo comprueba publicar()).
// Las operaciones sobre una noticia se turnan con un cerrojo y escriben de forma atómica: dos a la vez no se pisan.

import { spawnSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseFrontmatter } from '@astrojs/markdown-remark';
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

function escribe(carpeta, direccion, { datos, texto }, { nueva = false, mio = null } = {}) {
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
  if (mio && !mio()) {
    rmSync(temporal, { force: true });
    throw new Error(`«${direccion}»: otra operación tomó el cerrojo mientras se trabajaba; no se escribe nada`);
  }
  renameSync(temporal, ruta);
}

function lee(carpeta, direccion) {
  const ruta = fichero(carpeta, direccion);
  sinEnlace(ruta);
  // La cabecera se lee con el mismo extractor y analizador que usa Astro: lo que Astro no pueda leer, el gestor tampoco, y lo dice.
  let frontmatter;
  let content;
  try {
    ({ frontmatter, content } = parseFrontmatter(readFileSync(ruta, 'utf8'), { frontmatter: 'remove' }));
  } catch (fallo) {
    throw new Error(`${direccion}.md tiene la cabecera mal escrita: ${fallo.message.split('\n')[0]}`);
  }
  if (!frontmatter || typeof frontmatter !== 'object' || Array.isArray(frontmatter)) throw new Error(`${direccion}.md no tiene la forma de una noticia`);
  const datos = { ...frontmatter };
  for (const campo of ['publicada', 'modificada']) if (datos[campo] instanceof Date) datos[campo] = isoMadrid(datos[campo]);
  return { datos, texto: content.replace(/^(\r?\n)+/, '').replace(/(\r?\n)+$/, '') };
}

const SITIO = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// Una foto vale si la mide el medidor de imágenes de Astro, la decodifica sharp (el que usa Astro) y su formato casa con la
// extensión. Se comprueba en un proceso aparte, dentro de sitio/, porque esas dos herramientas son asíncronas y el gestor no.
const COMPRUEBA_FOTO = `
import sharp from 'sharp';
import { imageMetadata } from 'astro/assets/utils';
const trozos = [];
for await (const trozo of process.stdin) trozos.push(trozo);
const bytes = Buffer.concat(trozos);
const nombre = process.argv[process.argv.length - 1];
let meta;
try { meta = await imageMetadata(bytes, nombre); } catch (fallo) { console.error('Astro no puede medir la imagen: ' + String(fallo.message).split('\\n')[0]); process.exit(3); }
try { await sharp(bytes, { failOn: 'error' }).toBuffer(); } catch (fallo) { console.error('no se puede decodificar: ' + String(fallo.message).split('\\n')[0]); process.exit(3); }
const ext = nombre.toLowerCase().split('.').pop();
const esperado = { jpg: 'jpg', jpeg: 'jpg', png: 'png', gif: 'gif', webp: 'webp' }[ext];
const formato = meta.format === 'jpeg' ? 'jpg' : meta.format;
if (formato !== esperado) { console.error('el formato ' + meta.format + ' no casa con la extensión .' + ext); process.exit(3); }
console.log(formato + ' ' + meta.width + 'x' + meta.height);
`;
function compruebaFoto(nombre, bytes) {
  const r = spawnSync(process.execPath, ['--input-type=module', '-e', COMPRUEBA_FOTO, '--', nombre], { cwd: SITIO, input: bytes, encoding: 'utf8', timeout: 60_000 });
  if (r.status !== 0) {
    const motivo = (r.stderr || '').trim().split('\n').filter(Boolean).pop() || 'no se pudo comprobar';
    throw new Error(`La foto «${nombre}» no vale: ${motivo}`);
  }
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
const leeDueno = (dir) => {
  try {
    return readFileSync(join(dir, 'dueno'), 'utf8');
  } catch {
    return null;
  }
};
/** Un dueño cuyo proceso ya no existe, o de hace más de un minuto, dejó el cerrojo huérfano (un kill -9). */
const esHuerfano = (dueno) => {
  const [pid, momento] = dueno.trim().split(/\s+/);
  const numero = Number(pid);
  return !(numero > 0) || !procesoVivo(numero) || !(Number(momento) > 0) || Date.now() - Number(momento) > 60_000;
};
/**
 * Romper un cerrojo huérfano, de uno en uno: los rompedores se turnan con un segundo cerrojo («.rompiendo») y, ya dentro, vuelven a
 * leer el dueño. Mientras el directorio huérfano exista nadie puede crear uno nuevo en su sitio, así que si el dueño sigue siendo el
 * juzgado huérfano, renombrarlo es seguro: nunca se mueve un cerrojo vivo. Un «.rompiendo» de más de cinco segundos es de un
 * rompedor muerto y se retira.
 */
function rompeHuerfano(dir, duenoVisto) {
  const rompiendo = `${dir}.rompiendo`;
  try {
    mkdirSync(rompiendo);
  } catch (fallo) {
    if (fallo.code !== 'EEXIST') throw fallo;
    try {
      if (Date.now() - statSync(rompiendo).mtimeMs > 5000) {
        const viejo = `${rompiendo}.viejo.${process.pid}.${Date.now()}`;
        renameSync(rompiendo, viejo); // atómico: solo uno se lo lleva
        rmSync(viejo, { recursive: true, force: true });
      }
    } catch {
      /* ya no está o se lo llevó otro */
    }
    return;
  }
  try {
    if (leeDueno(dir) !== duenoVisto) return; // ya no es el huérfano que vimos
    if (duenoVisto === null && Date.now() - statSync(dir).mtimeMs < 60_000) return; // sin dueño pero reciente: alguien lo está tomando
    const roto = `${dir}.roto.${process.pid}.${Date.now()}`;
    renameSync(dir, roto);
    rmSync(roto, { recursive: true, force: true });
  } catch {
    /* otro se adelantó o ya no está */
  } finally {
    rmSync(rompiendo, { recursive: true, force: true });
  }
}
/**
 * Publicar, corregir y retirar leen, cambian y escriben: con un cerrojo por noticia, dos a la vez se turnan en vez de pisarse.
 * El cerrojo es un directorio (mkdir es atómico y exclusivo) con un fichero «dueno». Un huérfano se rompe con rompeHuerfano, de uno en
 * uno. El dueño comprueba antes de escribir que el cerrojo sigue siendo suyo, y al soltarlo solo retira el suyo.
 */
function conCerrojo(carpeta, direccion, trabajo) {
  const dir = `${fichero(carpeta, direccion)}.cerrojo`;
  const marca = randomBytes(6).toString('hex');
  let yo = '';
  const espera = new Int32Array(new SharedArrayBuffer(4));
  for (let intento = 0; ; intento += 1) {
    try {
      mkdirSync(dir);
      yo = `${process.pid} ${Date.now()} ${marca}`; // la hora de cuando se toma, no de cuando se empezó a esperar
      writeFileSync(join(dir, 'dueno.tmp'), yo);
      renameSync(join(dir, 'dueno.tmp'), join(dir, 'dueno')); // atómico: nadie lee un dueño a medias
      break;
    } catch (fallo) {
      if (fallo.code !== 'EEXIST' || intento >= 6000) throw new Error(`«${direccion}» está en uso por otra operación que no acaba (un minuto)`);
      Atomics.wait(espera, 0, 0, 10); // cada vuelta espera 10 ms, pase lo que pase con el cerrojo: 6000 vueltas son el minuto prometido
      let esFichero = false;
      try {
        esFichero = lstatSync(dir).isFile();
      } catch {
        continue; // ya no está: se vuelve a intentar
      }
      if (esFichero) {
        // No es un cerrojo de los nuestros (un fichero suelto): se aparta, de forma atómica, y se sigue.
        const basura = `${dir}.basura.${process.pid}.${Date.now()}`;
        try {
          renameSync(dir, basura); // atómico: solo uno se lo lleva…
          rmSync(basura, { force: true }); // …y, ya suyo, lo retira: no quedan restos en la carpeta
        } catch {
          /* otro lo apartó antes */
        }
        continue;
      }
      const dueno = leeDueno(dir);
      let sinDuenoYViejo = false;
      if (dueno === null) {
        try {
          sinDuenoYViejo = Date.now() - statSync(dir).mtimeMs > 60_000; // el proceso murió entre crear el cerrojo y apuntarse
        } catch {
          continue;
        }
      }
      if ((dueno !== null && esHuerfano(dueno)) || sinDuenoYViejo) {
        rompeHuerfano(dir, dueno);
        continue;
      }
    }
  }
  const mio = () => leeDueno(dir) === yo;
  try {
    return trabajo(mio);
  } finally {
    if (mio()) rmSync(dir, { recursive: true, force: true });
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
      throw new Error(`El nombre de la foto «${foto.fichero}» no vale: un nombre de fichero de imagen (jpg, png, webp o gif), sin ruta ni espacios`);
    }
    if (!esImagen(foto.bytes)) throw new Error(`La foto «${foto.fichero}» no es una imagen (jpg, png, gif o webp)`);
    compruebaFoto(foto.fichero, foto.bytes);
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
  return conCerrojo(carpeta, direccion, (mio) => {
    const noticia = lee(carpeta, direccion);
    if (noticia.datos.estado === 'publicada') {
      throw new Error(`«${direccion}» ya está publicada: para cambiarla usa corregir(); para cambiar su fecha, retírala y publícala de nuevo`);
    }
    // Lo que se publica está completo: titular y entradilla (RN-LET-02-03), autor de la foto (RN-LET-02-05) y fuente bien escrita (RN-LET-02-04).
    if (enBlanco(noticia.datos.titular)) throw new Error(`«${direccion}» no tiene titular: no se publica`);
    if (enBlanco(noticia.datos.entradilla)) throw new Error(`«${direccion}» no tiene entradilla: no se publica`);
    if (noticia.datos.foto && enBlanco(noticia.datos.fotoAutor)) throw new Error(`«${direccion}» tiene foto sin autor: no se publica`);
    if (noticia.datos.foto) {
      const nombreFoto = String(noticia.datos.foto).replace(/^\.\//, '');
      if (!/^\.\//.test(String(noticia.datos.foto)) || !NOMBRE_DE_FOTO.test(nombreFoto)) {
        throw new Error(`«${direccion}»: su foto «${noticia.datos.foto}» no vale: tiene que ser «./nombre.jpg» (jpg, png, webp o gif) en su misma carpeta, sin ruta (RN-LET-02-20)`);
      }
      const rutaFoto = join(carpeta, nombreFoto);
      if (!existsSync(rutaFoto)) throw new Error(`«${direccion}»: su foto «${noticia.datos.foto}» no está en la carpeta: no se publica`);
      sinEnlace(rutaFoto);
      compruebaFoto(nombreFoto, readFileSync(rutaFoto)); // la foto puede haber cambiado desde que se creó
    }
    if (noticia.datos.fuente !== undefined) fuenteValida(noticia.datos.fuente);
    Object.assign(noticia.datos, { estado: 'publicada', publicada: isoMadrid(fecha) });
    delete noticia.datos.modificada;
    escribe(carpeta, direccion, noticia, { mio });
  });
}

/** Corrige titular, entradilla o texto sin cambiar su dirección ni su fecha de publicación, y anota cuándo se corrigió. */
export function corregir(carpeta, direccion, cambios, { ahora = new Date() } = {}) {
  if (!fechaValida(ahora)) throw new Error(`«${direccion}»: la fecha de la corrección no es una fecha`);
  return conCerrojo(carpeta, direccion, (mio) => {
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
    escribe(carpeta, direccion, noticia, { mio });
  });
}

/** La retira de la web: el fichero se queda, pero deja de publicarse. */
export function retirar(carpeta, direccion) {
  return conCerrojo(carpeta, direccion, (mio) => {
    const noticia = lee(carpeta, direccion);
    noticia.datos.estado = 'retirada';
    escribe(carpeta, direccion, noticia, { mio });
  });
}

/** El estado con el que la deja el gestor: el que lleva el fichero o, si no lleva ninguno, el de toda noticia nueva. */
export function estadoDe(carpeta, direccion) {
  const { datos } = lee(carpeta, direccion);
  const estado = datos.estado ?? ESTADO_INICIAL;
  if (!ESTADOS.includes(estado)) throw new Error(`${direccion}.md tiene un estado desconocido: ${estado}`);
  return estado;
}
