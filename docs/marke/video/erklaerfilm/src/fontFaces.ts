import {staticFile} from 'remotion';

/**
 * @font-face fuer alle Kompositionen dieses Films — zentral, nicht je Szene.
 *
 * Uebernommen samt Begruendung aus dem Schwesterprojekt in
 * customer-blitzsicht/marketing/ai-search-promo/remotion/src/fontFaces.ts. Dort
 * trug bis zum 12.08.2026 jede Komposition ihren eigenen Block mit einem
 * absoluten Pfad wie url('/fonts/Inter-Bold.otf'). Der zeigt beim Render auf den
 * Server-Root statt auf Remotions public/: jede Schrift lief in einen 404, und
 * Chrome fiel still auf system-ui zurueck. Sichtbar war das nur im Render-Log,
 * nie im Bild — alle zehn bereits veroeffentlichten Videos sind so entstanden.
 *
 * staticFile() loest gegen public/ auf. font-display: block laesst Remotion auf
 * die Schrift warten, statt einen Frame in Ersatzschrift zu rendern.
 */
export const fontFaces = `
@font-face {
  font-family: 'Montserrat';
  src: url('${staticFile('fonts/Montserrat-ExtraBold.ttf')}') format('truetype');
  font-weight: 800;
  font-display: block;
}
@font-face {
  font-family: 'Montserrat';
  src: url('${staticFile('fonts/Montserrat-SemiBold.ttf')}') format('truetype');
  font-weight: 600;
  font-display: block;
}
@font-face {
  font-family: 'Source Sans 3';
  src: url('${staticFile('fonts/SourceSans3-Regular.otf')}') format('opentype');
  font-weight: 400;
  font-display: block;
}
@font-face {
  font-family: 'Source Sans 3';
  src: url('${staticFile('fonts/SourceSans3-Semibold.otf')}') format('opentype');
  font-weight: 600;
  font-display: block;
}
`;
