import { direccionPublica } from '../noticias/modelo.js';

// No bloquea nada y señala el sitemap con su dirección completa (RN-LET-02-15 y 16).
export function GET({ site }) {
  const cuerpo = `User-agent: *\nAllow: /\n\nSitemap: ${direccionPublica('/sitemap.xml', site)}\n`;
  return new Response(cuerpo, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}
