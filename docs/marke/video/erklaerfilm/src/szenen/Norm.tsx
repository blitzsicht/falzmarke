import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';
import bericht from '../bericht.json';

/**
 * 9–16 s — der gesetzte Brief, der Stempel, dann die Messung.
 *
 * ── Warum hier das ganze Blatt markiert wird ──────────────────────────────
 * Die erste Fassung zeigte drei Striche am linken Rand: Falzmarke, Lochmarke,
 * Falzmarke. Das legte nahe, das Werkzeug pruefe nur die Marke, die ihm den
 * Namen gibt. Gemessen wurde am Musterbrief anders: Von 29 Pruefungen betreffen
 * **sechs** die Falz- und Lochmarken. Die Mehrheit misst Anschriftfeld (4),
 * Ruecksendeangabe (3), Informationsblock (3), Betreff (5), Textblock (2) und
 * die Abstaende dazwischen, dazu Seitenmasse, Schrifteinbettung und PDF/A.
 *
 * Darum markiert diese Szene alle Zonen — und die Falzmarken sind eine davon,
 * nicht die Sache selbst.
 *
 * Alle Positionen stammen aus einem echten `verify --json`-Lauf
 * (src/bericht.json, Block "zonen"), in Millimetern. Umgerechnet wird nur ueber
 * die Blattmasse: 210 mm breit, 297 mm hoch.
 */

const BREITE_MM = 210;
const HOEHE_MM = 297;
const x = (mm: number) => `${(mm / BREITE_MM) * 100}%`;
const y = (mm: number) => `${(mm / HOEHE_MM) * 100}%`;

export const Norm: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const l = useLayout();

  const blattDa = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  const schlag = spring({frame: frame - 10, fps, config: {damping: 12, mass: 0.6}, durationInFrames: 12});
  const stempelGross = interpolate(schlag, [0, 1], [3.4, 1]);
  const stempelDreh = interpolate(schlag, [0, 1], [-14, 0]);
  const stempelWeg = interpolate(frame, [30, 40], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const z = bericht.zonen;
  const gruen = marke.farben.gruenText;
  const strichstaerke = Math.max(2, l.winzig * 0.09);

  /** Blendet ab `start` in 6 Frames ein. */
  const auf = (start: number) =>
    interpolate(frame, [start, start + 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // Bewusst ohne Beschriftung am Blatt: Woerter wie "Anschriftfeld" lagen dort
  // ueber dem Brieftext und machten beides unlesbar. Die Zonen benennt die Liste
  // rechts, die kurz nach den Linien erscheint — die Zuordnung entsteht ueber
  // die Reihenfolge, nicht ueber Etiketten im Satzspiegel.

  return (
    <Grund>
      <AbsoluteFill
        style={{
          flexDirection: l.richtung,
          alignItems: 'center',
          justifyContent: 'center',
          gap: l.abstand * 1.3,
          padding: l.rand,
        }}
      >
        <div style={{position: 'relative', height: l.blattHoehe, aspectRatio: '210 / 297', opacity: blattDa}}>
          <Img
            src={staticFile('brief-mahnung.png')}
            style={{width: '100%', height: '100%', objectFit: 'contain', border: '1px solid #E3E6EA'}}
          />

          {/* Anschriftfeld: senkrechte Klammer ueber die gemessene Hoehe. */}
          <div
            style={{
              position: 'absolute',
              left: x(z.anschrift[0]),
              top: y(z.anschrift[1]),
              height: y(z.anschrift[2] - z.anschrift[1]),
              width: strichstaerke,
              background: gruen,
              opacity: auf(34),
            }}
          />

          {/* Informationsblock: waagerechte Linie ueber seine Breite. */}
          <div
            style={{
              position: 'absolute',
              left: x(z.infoblock[0]),
              width: x(z.infoblock[1] - z.infoblock[0]),
              top: y(z.infoblock[2]),
              height: strichstaerke,
              background: gruen,
              opacity: auf(42),
            }}
          />

          {/* Betreff. */}
          <div
            style={{
              position: 'absolute',
              left: x(z.betreff[0]),
              width: x(70),
              top: y(z.betreff[1] + 4),
              height: strichstaerke,
              background: gruen,
              opacity: auf(50),
            }}
          />

          {/* Textblock: linke und rechte Grenze. */}
          {[z.textblock[0], z.textblock[1]].map((mm, i) => (
            <div
              key={mm}
              style={{
                position: 'absolute',
                left: x(mm),
                top: y(115),
                height: y(120),
                width: strichstaerke,
                background: gruen,
                opacity: auf(58 + i * 3),
              }}
            />
          ))}

          {/* Falz- und Lochmarken: eine Zone von mehreren, nicht die Sache selbst. */}
          {z.marken.map((mm, i) => (
            <div
              key={mm}
              style={{
                position: 'absolute',
                left: 0,
                top: y(mm),
                width: x(9),
                height: strichstaerke,
                background: gruen,
                opacity: auf(66 + i * 3),
              }}
            />
          ))}

          {/* Der Stempel schlaegt auf und weicht dann. */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: schlag * stempelWeg,
              transform: `scale(${stempelGross}) rotate(${stempelDreh}deg)`,
              pointerEvents: 'none',
            }}
          >
            <Img src={staticFile('logo.svg')} style={{width: '58%'}} />
          </div>
        </div>

        <div style={{maxWidth: l.hoch ? '100%' : '44%'}}>
          <div
            style={{
              fontFamily: marke.schriften.kopf,
              fontWeight: 800,
              fontSize: l.gross,
              lineHeight: 1.15,
              color: marke.farben.tinte,
              opacity: auf(22),
            }}
          >
            {text}
          </div>

          {/* Die Gesamtzahl kommt aus dem Lauf, nicht aus dem Drehbuch. */}
          <div
            style={{
              marginTop: l.klein * 0.8,
              fontFamily: marke.schriften.kopf,
              fontWeight: 600,
              fontSize: l.mittel * 0.72,
              color: gruen,
              opacity: auf(74),
            }}
          >
            {bericht.gesamt} Maße geprüft
          </div>

          <div
            style={{
              marginTop: l.klein * 0.7,
              fontFamily: marke.schriften.mono,
              fontSize: l.winzig * 0.74,
              lineHeight: 1.85,
              color: marke.farben.tinte,
            }}
          >
            {bericht.zeilen.slice(0, 5).map((zeile, i) => (
              <div key={zeile.name} style={{opacity: auf(80 + i * 4), whiteSpace: 'nowrap'}}>
                <span style={{color: gruen, fontWeight: 700}}>OK </span>
                {zeile.name}
              </div>
            ))}
          </div>
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
