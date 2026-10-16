// Cargador del juego de pruebas de la sección de noticias (SPEC-LET-02, §5): crea las noticias A a H con el gestor, las publica,
// retira E, corrige F y después C, y deja el registro JUEGO con el estado que el gestor devuelve para cada una.
//
//   node herramientas/cargar-juego.mjs <carpeta> <registro>
//
// <carpeta> es la carpeta de trabajo que la compilación lee como NOTICIAS_DIR (se regenera entera: sus .md y .jpg se reemplazan);
// nunca puede ser contenido/noticias, donde viven las noticias del sitio publicado. <registro> es el fichero JUEGO (sin versionar).

import { mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { corregir, crear, estadoDe, publicar, retirar } from './gestor-noticias.mjs';

const [carpeta, registro] = process.argv.slice(2);
if (!carpeta || !registro) {
  console.error('uso: node herramientas/cargar-juego.mjs <carpeta> <registro>');
  process.exit(2);
}
const produccion = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'contenido', 'noticias');
// Misma carpeta aunque se llegue por otro nombre: un enlace, o «Contenido/Noticias» en un disco que no distingue mayúsculas.
const esLaMisma = (a, b) => {
  try {
    const [x, y] = [statSync(a), statSync(b)];
    return x.dev === y.dev && x.ino === y.ino;
  } catch {
    return false;
  }
};
if (resolve(carpeta) === produccion || esLaMisma(carpeta, produccion)) {
  console.error('El juego de pruebas no puede cargarse en contenido/noticias: es lo que lee el sitio publicado.');
  process.exit(2);
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

// La carpeta es de trabajo y se regenera entera, como dist/ al compilar; pero solo si lo que hay en ella es del juego. Un .md
// sin la marca «prueba: true» quiere decir que la carpeta es de otro (contenido/noticias, docs/…) y no se toca.
mkdirSync(carpeta, { recursive: true });
const ficheros = readdirSync(carpeta, { withFileTypes: true }).filter((e) => e.isFile() && /\.(md|jpg)$/.test(e.name));
const ajenos = ficheros.filter((f) => f.name.endsWith('.md') && !/^prueba: true$/m.test(readFileSync(join(carpeta, f.name), 'utf8')));
if (ajenos.length > 0) {
  console.error(`La carpeta ${carpeta} tiene ficheros que no son del juego de pruebas (${ajenos.map((f) => f.name).join(', ')}): no se toca.`);
  process.exit(2);
}
for (const f of ficheros) rmSync(join(carpeta, f.name));

// Todas llevan la marca del juego: el sitio publicado rechaza cualquier noticia que la tenga (RN-LET-02-19).
for (const noticia of juego) noticia.direccion = crear(carpeta, { ...noticia, prueba: true });
for (const noticia of juego) if (noticia.publicada) publicar(carpeta, noticia.direccion, { fecha: noticia.publicada });
for (const noticia of juego) if (noticia.retirada) retirar(carpeta, noticia.direccion);

// Las dos correcciones, al revés de como se crearon: primero la de F y, un segundo después como mínimo (los gestores guardan la
// fecha con segundos), la de C. Entre publicar la última noticia y corregir F también pasa más de un segundo.
const de = (letra) => juego.find((n) => n.letra === letra).direccion;
await dormir(1100);
corregir(carpeta, de('F'), { texto: 'Texto de la prueba F, corregido.' });
await dormir(1100);
corregir(carpeta, de('C'), { titular: 'Noticia de prueba C corregida' });

const estados = Object.fromEntries(juego.map((n) => [n.letra, estadoDe(carpeta, n.direccion)]));
writeFileSync(registro, `${JSON.stringify(estados, null, 2)}\n`);
console.log(`juego cargado en ${carpeta}: ${juego.map((n) => `${n.letra}=${n.direccion} (${estados[n.letra]})`).join(', ')}`);
