// Lo que comparten el sitio y el gestor de noticias (herramientas/): estados, forma de la dirección, fechas y direcciones públicas.
// Sin imports de Astro: lo lee también Node sin compilar nada.

export const ESTADOS = ['borrador', 'publicada', 'retirada'];

// Toda noticia nace en borrador (RN-LET-02-07): solo se ve la que se marca expresamente como publicada.
export const ESTADO_INICIAL = 'borrador';

// Solo minúsculas sin tilde, cifras y guiones (RN-LET-02-18).
export const DIRECCION = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

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
