// Datos de la titular: una sola fuente para el aviso legal y la política de privacidad (RN-LET-01-16 y RN-LET-01-27).
// Salen de tests/sitio/titular.json, que se rellena con los datos reales del cuestionario de la Fase 0 (apartado C),
// nunca con datos de prueba. Mientras falte alguno, la página no inventa nada: no lo muestra.
import datos from '../../../tests/sitio/titular.json';

const ETIQUETAS = [
  ['nombre_fiscal', 'Nombre fiscal'],
  ['nif', 'NIF'],
  ['domicilio', 'Domicilio'],
  ['correo', 'Correo electrónico'],
];

export const titular = ETIQUETAS.map(([clave, etiqueta]) => ({
  clave,
  etiqueta,
  valor: String(datos[clave] ?? '').trim(),
})).filter((campo) => campo.valor !== '');

const faltan = ETIQUETAS.filter(([clave]) => !String(datos[clave] ?? '').trim()).map(([, etiqueta]) => etiqueta);
if (faltan.length > 0) {
  console.warn(
    `[sitio] tests/sitio/titular.json está incompleto (faltan: ${faltan.join(', ')}): ` +
      'el aviso legal y la privacidad salen sin esos datos hasta que la clienta los entregue.',
  );
}
