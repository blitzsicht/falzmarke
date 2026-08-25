import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';
import bericht from '../bericht.json';

/**
 * 8–15 s — der gesetzte Brief, dann der Stempel, dann die Masse.
 *
 * Das Blatt ist der echte Render von examples/brief-mahnung.md. Der Stempel
 * schlaegt auf und verblasst zur Marke am Rand; danach erscheinen die
 * Falz- und Lochmarken an ihren Positionen, mit den Werten aus einem echten
 * `verify --json`-Lauf (src/bericht.json).
 *
 * Die Anteile sind keine Schaetzung: 105, 148,5 und 210 mm von 297 mm
 * Blatthoehe — dieselben Sollwerte, die das Programm misst.
 */
const MARKEN = [
  {anteil: 105 / 297, wert: '105,0 mm'},
  {anteil: 148.5 / 297, wert: '148,5 mm'},
  {anteil: 210 / 297, wert: '210,0 mm'},
];

export const Norm: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const l = useLayout();

  const blattDa = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});

  // Der Stempel: von gross und schief auf klein und gerade, in acht Frames.
  const schlag = spring({frame: frame - 10, fps, config: {damping: 12, mass: 0.6}, durationInFrames: 12});
  const stempelGross = interpolate(schlag, [0, 1], [3.4, 1]);
  const stempelDreh = interpolate(schlag, [0, 1], [-14, 0]);
  const stempelWeg = interpolate(frame, [30, 40], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

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

          {/* Die Marken am linken Blattrand, mit ihren Sollwerten. */}
          {MARKEN.map((m, i) => {
            const start = 34 + i * 6;
            const auf = interpolate(frame, [start, start + 6], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return (
              // Beschriftung LINKS NEBEN dem Blatt, nicht darauf: auf dem Blatt
              // legte sie sich ueber den Brieftext und machte beides unlesbar.
              <div
                key={m.wert}
                style={{
                  position: 'absolute',
                  top: `${m.anteil * 100}%`,
                  right: '100%',
                  marginRight: l.winzig * 0.5,
                  transform: 'translateY(-50%)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: l.winzig * 0.4,
                  opacity: auf,
                }}
              >
                <span
                  style={{
                    fontFamily: marke.schriften.mono,
                    fontSize: l.winzig * 0.72,
                    color: marke.farben.gruenText,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {m.wert}
                </span>
                <div
                  style={{
                    width: l.klein * (0.6 + auf * 0.9),
                    height: Math.max(2, l.winzig * 0.1),
                    background: marke.farben.gruenText,
                  }}
                />
              </div>
            );
          })}

          {/* Der Stempel schlaegt mittig auf und weicht dann. */}
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
              opacity: interpolate(frame, [22, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
            }}
          >
            {text}
          </div>
          <div
            style={{
              marginTop: l.klein,
              fontFamily: marke.schriften.mono,
              fontSize: l.winzig * 0.8,
              lineHeight: 1.9,
              color: marke.farben.tinte,
            }}
          >
            {bericht.zeilen.slice(0, 4).map((z, i) => {
              const start = 56 + i * 5;
              const auf = interpolate(frame, [start, start + 5], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              });
              return (
                <div key={z.name} style={{opacity: auf, whiteSpace: 'nowrap'}}>
                  <span style={{color: marke.farben.gruenText, fontWeight: 700}}>OK </span>
                  {z.name}: {z.ist}
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
