import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';
import bericht from '../bericht.json';

/**
 * 32–42 s — die Messung.
 *
 * Die Zeilen stammen aus einem echten `verify --json`-Lauf
 * (scripts/bericht.py schreibt src/bericht.json). Nichts hier ist abgetippt;
 * wer eine Zeile zeigen will, die es im Bericht nicht gibt, faellt beim Bauen
 * der Datei auf.
 *
 * Gruen: die Textvariante #2F8642. Das Flaechen-Gruen #3EB057 erreicht auf
 * Weiss nur 2,78:1 — als Text waere es nicht lesbar genug.
 */
export const Pruefen: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const l = useLayout();

  // Die Marken links am Blatt: drei Striche, die nacheinander angemessen werden.
  const markenAnteil = [0.354, 0.5, 0.707]; // 105, 148,5 und 210 von 297 mm

  return (
    <Grund>
      <AbsoluteFill
        style={{
          flexDirection: l.richtung,
          alignItems: 'center',
          justifyContent: 'center',
          gap: l.abstand * 1.4,
          padding: l.rand,
        }}
      >
        <div style={{position: 'relative', height: l.blattHoehe, aspectRatio: '210 / 297'}}>
          <Img
            src={staticFile('brief-mahnung.png')}
            style={{width: '100%', height: '100%', objectFit: 'contain'}}
          />
          {markenAnteil.map((anteil, i) => {
            const start = 10 + i * 22;
            const breite = interpolate(frame, [start, start + 18], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return (
              <div
                key={anteil}
                style={{
                  position: 'absolute',
                  top: `${anteil * 100}%`,
                  left: 0,
                  width: `${18 * breite}%`,
                  height: Math.max(2, l.winzig * 0.09),
                  background: marke.farben.gruenText,
                  transformOrigin: 'left center',
                }}
              />
            );
          })}
        </div>

        <div style={{flex: 1, maxWidth: l.hoch ? '100%' : '52%'}}>
          <div
            style={{
              fontFamily: marke.schriften.kopf,
              fontWeight: 800,
              fontSize: l.mittel,
              color: marke.farben.tinte,
              marginBottom: l.abstand,
            }}
          >
            {text}
          </div>
          <div style={{fontFamily: marke.schriften.mono, fontSize: l.winzig * 0.92, lineHeight: 2}}>
            {bericht.zeilen.map((zeile, i) => {
              const start = 30 + i * 16;
              const auf = interpolate(frame, [start, start + 12], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              });
              return (
                <div
                  key={zeile.name}
                  style={{
                    opacity: auf,
                    transform: `translateX(${(1 - auf) * l.winzig}px)`,
                    color: marke.farben.tinte,
                    whiteSpace: 'nowrap',
                  }}
                >
                  <span style={{color: marke.farben.gruenText, fontWeight: 700}}>OK </span>
                  {zeile.name}: soll {zeile.soll} ist {zeile.ist}
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
