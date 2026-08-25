import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';
import bericht from '../bericht.json';

/**
 * 4–9 s — was ohne feste Form herauskommt.
 *
 * Ein Blatt, drei Zustaende: derselbe Brief als brief.txt, brief.docx und
 * brief.pdf. Der Inhalt bleibt gleich, die Form springt — Schrift, Raender und
 * die Stelle, an der die Anschrift landet. Das ist die Erfahrung, die Leute
 * tatsaechlich machen, wenn ein Modell "einen Brief" liefert.
 *
 * Die erste Fassung dieser Szene zeigte graue Balken auf einem schiefen Blatt.
 * Das war eine Behauptung, kein Beleg, und sah gestellt aus. Jetzt steht da ein
 * lesbarer Brief, der bei jedem Format woanders sitzt.
 *
 * Kein fremdes Produkt wird gezeigt oder schlechtgemacht: `.txt` und `.docx`
 * sind Dateiformate. Die Aussage ist nicht "jenes Werkzeug taugt nichts",
 * sondern "ohne feste Form ist jedes Ergebnis ein anderes".
 *
 * Der Brieftext kommt aus examples/brief-mahnung.md (ueber bericht.json), nicht
 * aus dieser Datei.
 */

type Zustand = {
  datei: string;
  schrift: string;
  /** Innenabstand des Blattes, als Anteil seiner Hoehe. */
  rand: number;
  zeilenabstand: number;
  kopfMittig: boolean;
  /** Wie viele Leerzeilen vor der Anschrift stehen — sie landet jedes Mal woanders. */
  vorlauf: number;
  betreffFett: boolean;
  laufweite: string;
};

const ZUSTAENDE: Zustand[] = [
  {
    datei: 'brief.txt',
    schrift: marke.schriften.mono,
    rand: 0.055,
    zeilenabstand: 1.5,
    kopfMittig: false,
    vorlauf: 0,
    betreffFett: false,
    laufweite: '0',
  },
  {
    datei: 'brief.docx',
    schrift: marke.schriften.text,
    rand: 0.115,
    zeilenabstand: 1.9,
    kopfMittig: true,
    vorlauf: 2,
    betreffFett: false,
    laufweite: '0.01em',
  },
  {
    datei: 'brief.pdf',
    schrift: marke.schriften.text,
    rand: 0.085,
    zeilenabstand: 1.6,
    kopfMittig: false,
    vorlauf: 1,
    betreffFett: true,
    laufweite: '0',
  },
];

/** Wie lange ein Zustand steht, in Frames. */
const TAKT = 26;

export const Ohne: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const l = useLayout();

  const da = interpolate(frame, [0, 4], [0, 1], {extrapolateRight: 'clamp'});
  const i = Math.min(ZUSTAENDE.length - 1, Math.floor(frame / TAKT));
  const z = ZUSTAENDE[i];

  // Der Strich faehrt erst, wenn alle drei Zustaende zu sehen waren.
  const strich = spring({
    frame: frame - ZUSTAENDE.length * TAKT,
    fps,
    config: {damping: 200, mass: 0.4},
    durationInFrames: 8,
  });

  const blattHoehe = l.blattHoehe;
  const schrift = blattHoehe * 0.026;
  const {empfaenger, betreff, anrede} = bericht.brieftext;

  return (
    <Grund>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: l.rand, gap: l.abstand}}>
        <div style={{opacity: da, display: 'flex', flexDirection: 'column', alignItems: 'flex-start'}}>
          {/* Dateireiter — sagt ohne Worte, dass es dreimal dasselbe Anliegen ist. */}
          <div
            style={{
              fontFamily: marke.schriften.mono,
              fontSize: schrift * 0.95,
              color: marke.farben.grau,
              background: '#EDEFF2',
              border: '1px solid #D6D9DE',
              borderBottom: 'none',
              borderRadius: `${schrift * 0.4}px ${schrift * 0.4}px 0 0`,
              padding: `${schrift * 0.35}px ${schrift * 1.1}px`,
            }}
          >
            {z.datei}
          </div>

          <div style={{position: 'relative'}}>
            <div
              style={{
                height: blattHoehe,
                aspectRatio: '210 / 297',
                border: '1px solid #D6D9DE',
                background: marke.farben.papier,
                padding: blattHoehe * z.rand,
                fontFamily: z.schrift,
                fontSize: schrift,
                lineHeight: z.zeilenabstand,
                letterSpacing: z.laufweite,
                color: '#3A4250',
                overflow: 'hidden',
              }}
            >
              <div style={{textAlign: z.kopfMittig ? 'center' : 'left', marginBottom: schrift * 0.8}}>
                Beispiel GmbH
              </div>

              {/* Vorlauf: die Anschrift landet in jedem Format woanders. */}
              {Array.from({length: z.vorlauf}).map((_, k) => (
                <div key={k}>&nbsp;</div>
              ))}

              {empfaenger.map((zeile) => (
                <div key={zeile}>{zeile}</div>
              ))}

              <div style={{height: schrift * z.zeilenabstand}} />

              <div style={{fontWeight: z.betreffFett ? 700 : 400}}>{betreff}</div>

              <div style={{height: schrift * z.zeilenabstand * 0.6}} />

              <div>{anrede}</div>
              <div>unsere Rechnung Nr. 2026-0815 ist bis heute nicht beglichen.</div>
            </div>

            {/* Durchgestrichen, sobald alle drei Formen zu sehen waren. */}
            {/* Erst zeichnen, wenn der Strich wirklich faehrt: bei Laenge null
                setzt strokeLinecap="round" sonst einen roten Punkt in die Ecke. */}
            {strich > 0.001 ? (
              <svg
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}
              >
                <line
                  x1="4"
                  y1="8"
                  x2={4 + 92 * strich}
                  y2={8 + 84 * strich}
                  stroke="#A32F2F"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                />
              </svg>
            ) : null}
          </div>
        </div>

        <div
          style={{
            fontFamily: marke.schriften.kopf,
            fontWeight: 800,
            fontSize: l.gross,
            color: marke.farben.tinte,
            opacity: interpolate(
              frame,
              [ZUSTAENDE.length * TAKT + 4, ZUSTAENDE.length * TAKT + 12],
              [0, 1],
              {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
            ),
          }}
        >
          {text}
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
