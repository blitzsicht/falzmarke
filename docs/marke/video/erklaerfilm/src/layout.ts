import {useVideoConfig} from 'remotion';

/**
 * Eine Zeitleiste, zwei Formate.
 *
 * Der Unterschied zwischen Quer- und Hochformat ist kein zweiter Film, sondern
 * eine Anordnung: Was quer nebeneinander steht, stapelt hoch untereinander.
 * Alle Groessen haengen an der kurzen Kante, damit Text in beiden Formaten
 * gleich gross wirkt.
 */
export const useLayout = () => {
  const {width, height} = useVideoConfig();
  const hoch = height > width;
  const kurz = Math.min(width, height);
  return {
    hoch,
    width,
    height,
    /** Richtung fuer zweispaltige Anordnungen. */
    richtung: (hoch ? 'column' : 'row') as 'column' | 'row',
    /** Schriftgrade, an der kurzen Kante bemessen. */
    gross: kurz * 0.062,
    mittel: kurz * 0.042,
    klein: kurz * 0.030,
    winzig: kurz * 0.022,
    rand: kurz * 0.075,
    abstand: kurz * 0.035,
    /** Breite des Zeichens, wenn es als Marke im Bild steht. */
    kurzLogo: kurz * 0.16,
    /** Hoehe, auf die das Briefblatt skaliert wird. */
    blattHoehe: (hoch ? height * 0.42 : height * 0.72),
  };
};
