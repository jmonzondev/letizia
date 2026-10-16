import { getCollection } from 'astro:content';

/** Las noticias que la clienta ha marcado expresamente como publicadas, de la más reciente a la más antigua (por fecha de publicación). */
export async function publicadas() {
  const noticias = await getCollection('noticias', ({ data }) => data.estado === 'publicada');
  return noticias.sort((a, b) => b.data.publicada - a.data.publicada || (a.id < b.id ? -1 : 1));
}
