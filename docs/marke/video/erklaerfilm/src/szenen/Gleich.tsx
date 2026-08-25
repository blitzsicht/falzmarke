import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';

/**
 * 22–31 s — worum es eigentlich geht.
 *
 * Links: frei gesetzte Ausgabe, jedes Blatt anders — angedeutet durch Balken in
 * wechselnder Breite und Lage, bewusst abstrakt. Es wird kein fremdes Produkt
 * gezeigt und keines schlechtgemacht; die Aussage ist, dass ohne feste Form
 * jedes Ergebnis anders ausfaellt.
 *
 * Rechts: dreimal dasselbe Blatt, weil Form aus Norm und Profil kommt und nicht
 * aus dem Zufall des Modells.
 *
 * Bewusst NICHT gesagt: "normgerecht", "DIN-konform", "zertifiziert". Solange
 * der Abgleich mit dem Originaltext der DIN 5008:2020-03 aussteht, ist keine
 * dieser Behauptungen belegt. Gesagt wird, was nachweisbar ist.
 */

// Drei angedeutete Blaetter mit wechselndem Satzspiegel — jedes anders.
const UNRUHIG = [
  [0.62, 0.30, 0.80, 0.45, 0.70],
  [0.40, 0.85, 0.25, 0.66, 0.38],
  [0.78, 0.52, 0.34, 0.90, 0.28],
];

const Skizze: React.FC<{breiten: number[]; versatz: number; hoehe: number}> = ({
  breiten,
  versatz,
  hoehe,
}) => (
  <div
    style={{
      height: hoehe,
      aspectRatio: '210 / 297',
      border: `1px solid #D6D9DE`,
      background: marke.farben.papier,
      padding: hoehe * 0.07,
      display: 'flex',
      flexDirection: 'column',
      gap: hoehe * 0.035,
      justifyContent: 'flex-start',
      paddingTop: hoehe * (0.07 + versatz * 0.12),
    }}
  >
    {breiten.map((b, i) => (
      <div
        key={i}
        style={{
          width: `${b * 100}%`,
          height: Math.max(2, hoehe * 0.022),
          background: '#C9CDD4',
          alignSelf: i % 2 && versatz > 0.4 ? 'flex-end' : 'flex-start',
        }}
      />
    ))}
  </div>
);

export const Gleich: React.FC<{text: string; ohne: string; mit: string}> = ({
  text,
  ohne,
  mit,
}) => {
  const frame = useCurrentFrame();
  const l = useLayout();
  const hoehe = l.blattHoehe * 0.52;

  const linksAuf  = interpolate(frame, [0, 6],  [0, 1], {extrapolateRight: 'clamp'});
  const rechtsAuf = interpolate(frame, [10, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const satzAuf   = interpolate(frame, [22, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const spalte = (titel: string, auf: number, kinder: React.ReactNode) => (
    <div style={{display: 'flex', flexDirection: 'column', gap: l.klein * 0.7, opacity: auf}}>
      <div style={{fontSize: l.winzig, color: marke.farben.grau}}>{titel}</div>
      <div style={{display: 'flex', gap: l.klein * 0.5}}>{kinder}</div>
    </div>
  );

  return (
    <Grund>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: l.rand, gap: l.abstand}}>
        <div
          style={{
            display: 'flex',
            flexDirection: l.hoch ? 'column' : 'row',
            gap: l.abstand * 1.6,
            alignItems: 'flex-start',
          }}
        >
          {spalte(
            ohne,
            linksAuf,
            UNRUHIG.map((b, i) => <Skizze key={i} breiten={b} versatz={i * 0.45} hoehe={hoehe} />),
          )}
          {spalte(
            mit,
            rechtsAuf,
            [0, 1, 2].map((i) => (
              <Img
                key={i}
                src={staticFile('brief-mahnung.png')}
                style={{
                  height: hoehe,
                  aspectRatio: '210 / 297',
                  objectFit: 'contain',
                  border: `1px solid #D6D9DE`,
                }}
              />
            )),
          )}
        </div>

        <div
          style={{
            fontFamily: marke.schriften.kopf,
            fontWeight: 800,
            fontSize: l.gross,
            lineHeight: 1.15,
            color: marke.farben.tinte,
            textAlign: 'center',
            opacity: satzAuf,
            transform: `translateY(${(1 - satzAuf) * l.klein}px)`,
          }}
        >
          {text}
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
