import { publicadas } from '../noticias/publicadas.js';
import { direccionPublica, escapaXml } from '../noticias/modelo.js';

// Exactamente las noticias publicadas, con su dirección completa en el dominio público (RN-LET-02-12 a 14).
export async function GET({ site }) {
  const noticias = await publicadas();
  const urls = noticias.map(
    (noticia) => `  <url><loc>${escapaXml(direccionPublica(`/noticias/${noticia.id}/`, site))}</loc></url>\n`,
  );
  const cuerpo = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('')}</urlset>\n`;
  return new Response(cuerpo, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
