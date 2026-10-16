// Cargador del juego de pruebas de la sección de noticias (SPEC-LET-02, §5): crea las noticias A a H con el gestor, las publica,
// retira E, corrige F y después C, y deja el registro JUEGO con el estado que el gestor devuelve para cada una.
//
//   node herramientas/cargar-juego.mjs <carpeta> <registro>
//
// <carpeta> es la carpeta de trabajo que la compilación lee como NOTICIAS_DIR (se regenera entera: sus .md y .jpg se reemplazan);
// nunca puede ser contenido/noticias, donde viven las noticias del sitio publicado. <registro> es el fichero JUEGO (sin versionar).

import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ESTADOS } from '../src/noticias/modelo.js';
import { dentroDe, esEnlace, inodeDe, proyectoAstroDe, rutaReal } from '../src/noticias/rutas.js';
import { corregir, crear, estadoDe, publicar, retirar } from './gestor-noticias.mjs';

const [carpeta, registro] = process.argv.slice(2);
if (!carpeta || !registro) {
  console.error('uso: node herramientas/cargar-juego.mjs <carpeta> <registro>');
  process.exit(2);
}
const sitio = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const JUEGO = join(sitio, '.juego');
const niega = (motivo) => {
  console.error(motivo);
  process.exit(2);
};
const real = (ruta) => {
  try {
    return rutaReal(ruta);
  } catch (fallo) {
    return niega(fallo.message);
  }
};
const VEDADAS = ['contenido', 'public', 'src', 'dist', 'dist-juego', 'node_modules', '.astro'].map((v) => join(sitio, v));

// La carpeta del juego solo puede ser sitio/.juego de verdad (ni un enlace, ni dentro de contenido/, public/, src/…) o una carpeta
// fuera de sitio/ que no sean las noticias reales de otra copia (RN-LET-02-21). Todo se juzga sobre la ruta real.
const carpetaReal = real(carpeta);
const esElJuego = carpetaReal === real(JUEGO);
if (esElJuego && esEnlace(JUEGO)) niega('sitio/.juego es un enlace: el juego de pruebas no se carga a través de enlaces.');
if (VEDADAS.some((v) => dentroDe(carpetaReal, v))) niega(`La carpeta ${carpeta} cae dentro de una carpeta del sitio que no se toca (contenido, public, src, dist…).`);
if (!esElJuego && dentroDe(carpetaReal, sitio)) niega(`La carpeta ${carpeta} no vale: el juego de pruebas solo se carga en sitio/.juego o en una carpeta fuera de sitio/.`);
if (!esElJuego && /(^|[\\/])contenido[\\/]noticias([\\/]|$)/.test(carpetaReal)) niega(`La carpeta ${carpeta} son las noticias reales de otra copia del sitio: no se toca.`);
// Ni dentro de ningún otro proyecto Astro (otra copia del repo: su src/pages, su public…): lo que se cargara ahí saldría publicado en ese sitio.
const proyectoAjeno = (rutaRealNativa) => {
  const proyecto = proyectoAstroDe(rutaRealNativa);
  return proyecto !== null && inodeDe(proyecto) !== inodeDe(sitio) ? proyecto : null;
};
if (!esElJuego && proyectoAjeno(carpetaReal)) niega(`La carpeta ${carpeta} está dentro de otro proyecto Astro (${proyectoAjeno(carpetaReal)}): el juego de pruebas no se carga dentro de otro sitio (RN-LET-02-21).`);
// El registro: un .json que no sea un enlace, fuera de contenido/, public/, src/ y de la carpeta del juego, y que, si existe,
// sea un registro del juego (las ocho letras A a H con un estado): ni package.json, ni los datos de la titular, ni «{}».
if (esEnlace(resolve(registro))) niega(`El registro ${registro} es un enlace: no se sigue.`); // tal como se pidió, antes de resolverlo
const registroRuta = real(registro);
if (esEnlace(registroRuta)) niega(`El registro ${registro} es un enlace: no se sigue.`);
if (!registroRuta.endsWith('.json')) niega(`El registro ${registro} tiene que ser un fichero .json.`);
if (!existsSync(dirname(registroRuta))) niega(`La carpeta del registro ${registro} no existe.`);
for (const vedada of [...VEDADAS, JUEGO]) {
  if (dentroDe(dirname(registroRuta), vedada)) niega(`El registro ${registro} no puede ir dentro de sitio/${vedada.slice(sitio.length + 1)}.`);
}
if (proyectoAjeno(dirname(registroRuta))) niega(`El registro ${registro} no puede ir dentro de otro proyecto Astro (${proyectoAjeno(dirname(registroRuta))}).`);
if (existsSync(registroRuta)) {
  let anterior = null;
  try {
    anterior = JSON.parse(readFileSync(registroRuta, 'utf8'));
  } catch {
    anterior = null;
  }
  const letras = anterior && typeof anterior === 'object' && !Array.isArray(anterior) ? Object.keys(anterior).sort() : null;
  const todas = 'ABCDEFGH'.split('');
  if (!letras || letras.join('') !== todas.join('') || !todas.every((k) => ESTADOS.includes(anterior[k]))) {
    niega(`${registro} existe y no es un registro del juego: no se sobrescribe.`);
  }
}

// JPEG de 32×20 píxeles: la foto de A, que la compilación copia al sitio como cualquier otra imagen.
const FOTO = readFileSync(new URL('./foto-prueba.jpg', import.meta.url));

const madrid = (dia) => new Date(`2026-10-${String(dia).padStart(2, '0')}T10:00:00+02:00`); // hasta el 25-10, Madrid va a +02:00
const dormir = (ms) => new Promise((listo) => setTimeout(listo, ms));

const AYUNTAMIENTO = { organismo: 'Ayuntamiento de Talavera de la Reina', fecha: '2026-10-06' };
const REPETIDO = 'Noticia de prueba repetida: Año Nuevo en Talavera';

// Una por fila de la tabla de §5, en el orden en que se crean (A la primera, H la última). Sin «publicada», no se publica.
const juego = [
  { letra: 'A', direccion: 'prueba-a', titular: 'Noticia de prueba A', entradilla: 'Entradilla de la prueba A.', texto: 'Texto de la prueba A.',
    foto: { fichero: 'foto-prueba-a.jpg', bytes: FOTO }, fotoAutor: 'Autora de prueba', fuente: AYUNTAMIENTO, publicada: madrid(7) },
  { letra: 'B', direccion: 'prueba-b', titular: 'Noticia de prueba B', entradilla: 'Entradilla de la prueba B.', texto: 'Texto de la prueba B.', publicada: madrid(8) },
  { letra: 'C', direccion: 'prueba-c', titular: 'Noticia de prueba C', entradilla: 'Entradilla de la prueba C.', texto: 'Texto de la prueba C.', publicada: madrid(9) },
  { letra: 'D', direccion: 'prueba-d', titular: 'Noticia de prueba D', entradilla: 'Entradilla de la prueba D.', texto: 'Texto de la prueba D.' },
  { letra: 'E', direccion: 'prueba-e', titular: 'Noticia de prueba E', entradilla: 'Entradilla de la prueba E.', texto: 'Texto de la prueba E.', publicada: madrid(2), retirada: true },
  { letra: 'F', direccion: 'prueba-f', titular: 'Noticia de prueba F: «Año Nuevo», "comillas" & </script>', entradilla: 'Entradilla de la prueba F.', texto: 'Texto de la prueba F.', publicada: madrid(5) },
  { letra: 'G', titular: REPETIDO, entradilla: 'Entradilla de la prueba G.', texto: 'Texto de la prueba G.', publicada: madrid(4) },
  { letra: 'H', titular: REPETIDO, entradilla: 'Entradilla de la prueba H.', texto: 'Texto de la prueba H.', publicada: madrid(3) },
];

// La carpeta es de trabajo y se regenera entera, como dist/ al compilar; pero solo si TODO lo que hay en ella es del juego:
// noticias con la marca «prueba: true» en la cabecera (no en el texto) y las fotos que esas noticias nombran. Cualquier otro
// fichero quiere decir que la carpeta es de otro (contenido/noticias, docs/, una carpeta de fotos…) y no se toca.
mkdirSync(carpetaReal, { recursive: true });
const ficheros = readdirSync(carpetaReal, { withFileTypes: true }).filter((e) => e.isFile() && /\.(md|jpe?g|png|webp|avif|gif)$/i.test(e.name));
const cabeceraDe = (nombre) => (readFileSync(join(carpetaReal, nombre), 'utf8').match(/^---\n([\s\S]*?)\n---\n/) || [, ''])[1];
const noticias = ficheros.filter((f) => f.name.endsWith('.md'));
const delJuego = noticias.filter((f) => /^prueba: true$/m.test(cabeceraDe(f.name)));
const fotosDelJuego = new Set(delJuego.flatMap((f) => { const m = cabeceraDe(f.name).match(/^foto: "\.\/([^"]+)"$/m); return m ? [m[1]] : []; }));
const ajenos = ficheros.filter((f) => (f.name.endsWith('.md') ? !delJuego.includes(f) : !fotosDelJuego.has(f.name)));
if (ajenos.length > 0) {
  console.error(`La carpeta ${carpetaReal} tiene ficheros que no son del juego de pruebas (${ajenos.map((f) => f.name).join(', ')}): no se toca.`);
  process.exit(2);
}
for (const f of ficheros) rmSync(join(carpetaReal, f.name));

// Todas llevan la marca del juego: el sitio publicado rechaza cualquier noticia que la tenga (RN-LET-02-19).
for (const noticia of juego) noticia.direccion = crear(carpetaReal, { ...noticia, prueba: true });
for (const noticia of juego) if (noticia.publicada) publicar(carpetaReal, noticia.direccion, { fecha: noticia.publicada });
for (const noticia of juego) if (noticia.retirada) retirar(carpetaReal, noticia.direccion);

// Las dos correcciones, al revés de como se crearon: primero la de F y, un segundo después como mínimo (los gestores guardan la
// fecha con segundos), la de C. Entre publicar la última noticia y corregir F también pasa más de un segundo.
const de = (letra) => juego.find((n) => n.letra === letra).direccion;
await dormir(1100);
corregir(carpetaReal, de('F'), { texto: 'Texto de la prueba F, corregido.' });
await dormir(1100);
corregir(carpetaReal, de('C'), { titular: 'Noticia de prueba C corregida' });

const estados = Object.fromEntries(juego.map((n) => [n.letra, estadoDe(carpetaReal, n.direccion)]));
writeFileSync(registroRuta, `${JSON.stringify(estados, null, 2)}\n`);
console.log(`juego cargado en ${carpeta}: ${juego.map((n) => `${n.letra}=${n.direccion} (${estados[n.letra]})`).join(', ')}`);
