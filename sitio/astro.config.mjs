import { defineConfig } from 'astro/config';

// Sitio estático: cada página sale como carpeta con su index.html (/contacto/ → contacto/index.html).
export default defineConfig({
  trailingSlash: 'always',
  build: { format: 'directory' },
  devToolbar: { enabled: false },
});
