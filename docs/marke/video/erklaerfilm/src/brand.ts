// Marke falzmarke — die einzige Stelle im Film, an der Farben und Schriften stehen.
// Quelle: docs/marke/erscheinungsbild.md. Wer hier etwas aendert, aendert es dort mit.
export const marke = {
  farben: {
    tinte: '#121E2F',      // Text, Blattkontur
    papier: '#FFFFFF',
    gruen: '#3EB057',      // NUR Flaeche — auf Weiss nur 2,78:1
    gruenText: '#2F8642',  // gruener Text auf hellem Grund, 4,56:1
    grau: '#5B6470',       // Zweitrangiges
  },
  schriften: {
    kopf: '"Montserrat", system-ui, sans-serif',
    text: '"Source Sans 3", system-ui, sans-serif',
    mono: '"Menlo", "DejaVu Sans Mono", ui-monospace, monospace',
  },
} as const;
