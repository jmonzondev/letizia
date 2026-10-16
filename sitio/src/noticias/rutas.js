// Rutas por lo que son en el disco, no por su texto: tramo a tramo, siguiendo cada enlace antes del «..» que venga detrás, con las
// mayúsculas como las guarda el disco, y comparando carpetas por inode. Lo usan el cargador del juego y la carga de contenido
// (RN-LET-02-19 y 21): lo que se decide sobre una ruta se decide sobre la ruta real.
import { existsSync, lstatSync, realpathSync, statSync } from 'node:fs';
import { dirname, isAbsolute, join, sep } from 'node:path';

export const inodeDe = (ruta) => {
  try {
    const s = statSync(ruta);
    return `${s.dev}:${s.ino}`;
  } catch {
    return null;
  }
};
export const esEnlace = (ruta) => {
  try {
    return lstatSync(ruta).isSymbolicLink();
  } catch {
    return false;
  }
};
/**
 * La ruta real nativa de algo que puede no existir aún: se resuelve el tramo que existe como lo hace el sistema (enlaces antes que
 * «..», mayúsculas como las guarda el disco) y se le añade lo que falta. Lanza si lleva «..» detrás de un tramo que no existe (no se
 * puede saber adónde va) o si pasa por un enlace roto.
 */
export function rutaReal(ruta, desde = process.cwd()) {
  let actual = realpathSync.native(isAbsolute(ruta) ? sep : desde);
  let pendiente = false;
  for (const tramo of ruta.split(/[\\/]+/).filter((t) => t && t !== '.')) {
    if (tramo === '..') {
      if (pendiente) throw new Error(`La ruta ${ruta} lleva «..» detrás de un tramo que no existe: no se puede saber adónde va.`);
      actual = dirname(actual);
      continue;
    }
    if (pendiente) {
      actual = join(actual, tramo);
      continue;
    }
    const candidato = join(actual, tramo);
    let info = null;
    try {
      info = lstatSync(candidato);
    } catch {
      info = null;
    }
    if (info) {
      try {
        actual = realpathSync.native(candidato);
      } catch {
        throw new Error(`La ruta ${ruta} pasa por un enlace roto (${tramo}).`);
      }
    } else {
      actual = candidato;
      pendiente = true;
    }
  }
  return actual;
}
/** ¿La ruta real (su tramo existente) es esa carpeta o está dentro de ella? Por inode, subiendo por los padres. */
export function dentroDe(rutaRealNativa, carpeta) {
  const objetivo = inodeDe(carpeta);
  if (!objetivo) return false;
  let r = rutaRealNativa;
  while (!existsSync(r)) r = dirname(r);
  for (;;) {
    if (inodeDe(r) === objetivo) return true;
    const padre = dirname(r);
    if (padre === r) return false;
    r = padre;
  }
}
/** La carpeta del proyecto Astro (la más cercana con un astro.config.*) que contiene la ruta, o null si no está dentro de ninguno. */
export function proyectoAstroDe(rutaRealNativa) {
  let r = rutaRealNativa;
  while (!existsSync(r)) r = dirname(r);
  for (;;) {
    if (['mjs', 'js', 'ts', 'mts', 'cjs'].some((ext) => existsSync(join(r, `astro.config.${ext}`)))) return r;
    const padre = dirname(r);
    if (padre === r) return null;
    r = padre;
  }
}
