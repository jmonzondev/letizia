import { defineConfig } from 'astro/config';

// DOMINIO es la dirección pública del sitio, sin barra final (https://ejemplo.es): la compilación la escribe en las
// canónicas, el sitemap y robots.txt de las noticias (SPEC-LET-02). Sin ella, esas direcciones no se pueden construir.
const dominio = (process.env.DOMINIO ?? '').trim();
if (dominio && !/^https?:\/\/[^/]+$/.test(dominio)) {
  throw new Error(`DOMINIO=${dominio} no vale: se espera la dirección pública sin barra final, p. ej. https://ejemplo.es`);
}

// Sitio estático: cada página sale como carpeta con su index.html (/contacto/ → contacto/index.html).
export default defineConfig({
  site: dominio || undefined,
  // La compilación de pruebas (NOTICIAS_DIR, el juego) sale siempre a dist-juego: dist, lo que se despliega, no se toca (RN-LET-02-19).
  outDir: process.env.NOTICIAS_DIR ? './dist-juego' : './dist',
  // Y su propia caché de contenido: una compilación de pruebas y una de producción a la vez no se mezclan.
  // La caché de contenido vive en la copia y por modo, nunca en node_modules: las copias de prueba enlazan node_modules y dos
  // compilaciones a la vez en copias distintas se mezclarían el contenido a través de un data-store.json compartido.
  cacheDir: process.env.NOTICIAS_DIR ? './.cache-astro-juego' : './.cache-astro',
  // Y la de Vite (node_modules/.vite por defecto, compartida por las copias que enlazan node_modules): dentro de la copia también.
  vite: { cacheDir: process.env.NOTICIAS_DIR ? './.cache-astro-juego/vite' : './.cache-astro/vite' },
  trailingSlash: 'always',
  build: { format: 'directory' },
  devToolbar: { enabled: false },
});
