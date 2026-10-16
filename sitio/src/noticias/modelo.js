// Lo que comparten el sitio y el gestor de noticias (herramientas/): estados, forma de la dirección, fechas y direcciones públicas.
// Sin imports de Astro: lo lee también Node sin compilar nada.

export const ESTADOS = ['borrador', 'publicada', 'retirada'];

// Toda noticia nace en borrador (RN-LET-02-07): solo se ve la que se marca expresamente como publicada.
export const ESTADO_INICIAL = 'borrador';

// Solo minúsculas sin tilde, cifras y guiones (RN-LET-02-18).
export const DIRECCION = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

// Las seis direcciones fijas del juego de pruebas (SPEC-LET-02 §5): el gestor no las asigna a una noticia real y el sitio
// publicado las rechaza (RN-LET-02-19).
export const DIRECCION_DEL_JUEGO = /^prueba-[a-f]$/;

// Nombre de fichero de una foto: sin ruta ni espacios y con extensión de imagen; «otra.md» no vale, el cargador lo leería como noticia.
export const NOMBRE_DE_FOTO = /^[a-z0-9][a-z0-9._-]*\.(jpe?g|png|webp|avif|gif)$/i;

const ZONA = 'Europe/Madrid';

/** «7 de octubre de 2026», con el día que es en Madrid. */
export function fechaLarga(fecha) {
  return new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'long', year: 'numeric', timeZone: ZONA }).format(fecha);
}

/** «2026-10-06» (un día sin hora, como el de una nota de prensa) escrito como «6 de octubre de 2026». */
export function diaLargo(dia) {
  return new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(
    new Date(`${dia}T00:00:00Z`),
  );
}

/** Fecha ISO 8601 con la zona horaria de Madrid, p. ej. «2026-10-07T10:00:00+02:00» (RN-LET-02-10). */
export function isoMadrid(fecha) {
  const partes = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', {
      timeZone: ZONA,
      hourCycle: 'h23',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'longOffset',
    })
      .formatToParts(fecha)
      .map((parte) => [parte.type, parte.value]),
  );
  const desfase = partes.timeZoneName.replace('GMT', '') || '+00:00';
  return `${partes.year}-${partes.month}-${partes.day}T${partes.hour}:${partes.minute}:${partes.second}${desfase}`;
}

/** Dirección completa en el dominio público con el que se compila el sitio (variable DOMINIO). */
export function direccionPublica(ruta, sitio) {
  if (!sitio) {
    throw new Error('Falta DOMINIO: la compilación necesita la dirección pública del sitio (p. ej. DOMINIO=https://ejemplo.es npm run build).');
  }
  return new URL(ruta, sitio).href;
}

export function escapaXml(texto) {
  return texto.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Fecha ISO 8601 con zona horaria, como la escribe isoMadrid (RN-LET-02-10).
export const FECHA_CON_ZONA = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})$/;

/** ¿Es «AAAA-MM-DD» de un día que existe? («2026-02-30» no.) */
export function diaValido(dia) {
  if (typeof dia !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(dia)) return false;
  const fecha = new Date(`${dia}T00:00:00Z`);
  return !Number.isNaN(fecha.getTime()) && fecha.toISOString().slice(0, 10) === dia;
}

/** ¿Es una fecha de verdad (un Date con valor)? */
export function fechaValida(fecha) {
  return fecha instanceof Date && !Number.isNaN(fecha.getTime());
}

/** ¿Los bytes empiezan como una imagen (jpg, png, gif, webp o avif)? Una «foto» que no lo sea tumbaría la compilación. */
export function esImagen(bytes) {
  if (!bytes || typeof bytes.length !== 'number' || bytes.length < 12) return false;
  const b = bytes;
  if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return true; // JPEG
  if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return true; // PNG
  if (b[0] === 0x47 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x38) return true; // GIF
  const latin1 = (desde, hasta) => String.fromCharCode(...b.slice(desde, hasta));
  if (latin1(0, 4) === 'RIFF' && latin1(8, 12) === 'WEBP') return true;
  if (latin1(4, 12) === 'ftypavif') return true;
  return false;
}
