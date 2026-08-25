import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';
import {Typewriter} from '../components/Typewriter';

/**
 * 18–32 s — der Befehl laeuft, das Blatt entsteht.
 *
 * Das Blatt ist der echte Render von examples/brief-mahnung.md
 * (docs/renders/brief-mahnung.png), nicht eine Zeichnung davon. Es wird von
 * oben nach unten aufgedeckt, damit sichtbar wird, in welcher Reihenfolge die
 * Zonen entstehen.
 */
export const Setzen: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const l = useLayout();

  const aufdecken = interpolate(frame, [70, 300], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const blattAuf = interpolate(frame, [60, 90], [0, 1], {extrapolateRight: 'clamp'});
  const schattenAuf = interpolate(frame, [300, 340], [0, 1], {extrapolateRight: 'clamp'});

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
        <div style={{flex: 1, maxWidth: l.hoch ? '100%' : '46%'}}>
          <div
            style={{
              fontFamily: marke.schriften.mono,
              fontSize: l.winzig,
              color: marke.farben.tinte,
              background: '#F4F5F7',
              padding: `${l.winzig * 0.7}px ${l.klein}px`,
              borderRadius: l.winzig * 0.4,
              marginBottom: l.abstand,
            }}
          >
            <span style={{color: marke.farben.grau}}>$ </span>
            <Typewriter text="falzmarke render mahnung.md" startFrame={8} zeichenProSekunde={22} />
          </div>
          <div
            style={{
              fontFamily: marke.schriften.kopf,
              fontWeight: 800,
              fontSize: l.mittel,
              lineHeight: 1.2,
              color: marke.farben.tinte,
              opacity: interpolate(frame, [90, 120], [0, 1], {extrapolateRight: 'clamp'}),
            }}
          >
            {text}
          </div>
        </div>

        <div
          style={{
            position: 'relative',
            height: l.blattHoehe,
            aspectRatio: '210 / 297',
            opacity: blattAuf,
            boxShadow: `0 ${l.winzig * 0.5}px ${l.klein}px rgba(18,30,47,${0.14 * schattenAuf})`,
          }}
        >
          <Img
            src={staticFile('brief-mahnung.png')}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              // Von oben nach unten aufdecken: erst Briefkopf, zuletzt Fusszeile.
              clipPath: `inset(0 0 ${100 - aufdecken}% 0)`,
            }}
          />
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
