import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';
import {Typewriter} from '../components/Typewriter';

/**
 * 0–4 s — sofort hinein.
 *
 * Kein Vorspann, kein Logo: Der Film beginnt mit dem Satz, den ein Mensch
 * tatsaechlich tippt. Wer nach zwei Sekunden noch nicht weiss, worum es geht,
 * klickt weg.
 *
 * Gezeigt wird das Eingabefeld eines Chats — abgerundetes Feld, blinkender
 * Cursor, runder Absendeknopf, der angeht, sobald etwas dasteht. Das Muster
 * kennt jeder, der schon einmal ein Sprachmodell benutzt hat, und es sagt ohne
 * Beschriftung, was hier passiert. Es ist ein allgemeines Bedienmuster: kein
 * fremdes Logo, kein Produktname, keine nachgebaute Oberflaeche.
 */
export const Auftrag: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const l = useLayout();

  const feld = spring({frame, fps, config: {damping: 200}, durationInFrames: 8});

  // Der Knopf geht an, sobald genug Text steht, und wird beim Abschicken kurz gedrueckt.
  const TIPPT_AB = 12;
  const zeichenProSekunde = 62;
  const fertigBei = TIPPT_AB + (text.length / zeichenProSekunde) * fps;
  const aktiv = interpolate(frame, [fertigBei - 8, fertigBei], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const druck = spring({
    frame: frame - (fertigBei + 6),
    fps,
    config: {damping: 14, mass: 0.4},
    durationInFrames: 10,
  });
  const gedrueckt = 1 - 0.14 * Math.sin(druck * Math.PI);

  const knopfGrosse = l.mittel * 1.5;

  return (
    <Grund>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: l.rand}}>
        <div
          style={{
            width: l.hoch ? '100%' : '84%',
            display: 'flex',
            alignItems: 'center',
            gap: l.klein,
            background: '#F7F8FA',
            border: '1px solid #DCE0E6',
            borderRadius: knopfGrosse * 0.9,
            padding: `${l.klein * 0.85}px ${l.klein * 0.9}px ${l.klein * 0.85}px ${l.mittel}px`,
            boxShadow: `0 ${l.winzig * 0.3}px ${l.klein}px rgba(18,30,47,0.06)`,
            opacity: feld,
            transform: `translateY(${(1 - feld) * l.klein}px)`,
          }}
        >
          <div
            style={{
              flex: 1,
              fontSize: l.mittel,
              lineHeight: 1.3,
              color: marke.farben.tinte,
              minHeight: l.mittel * 1.3,
            }}
          >
            <Typewriter
              text={text}
              startFrame={TIPPT_AB}
              zeichenProSekunde={zeichenProSekunde}
              cursorFarbe={marke.farben.tinte}
            />
          </div>

          {/* Absendeknopf: grau, solange nichts dasteht. */}
          <div
            style={{
              flexShrink: 0,
              width: knopfGrosse,
              height: knopfGrosse,
              borderRadius: '50%',
              background: aktiv > 0.5 ? marke.farben.tinte : '#C9CDD4',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transform: `scale(${gedrueckt})`,
            }}
          >
            <svg
              width={knopfGrosse * 0.5}
              height={knopfGrosse * 0.5}
              viewBox="0 0 24 24"
              fill="none"
              stroke={marke.farben.papier}
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </div>
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
