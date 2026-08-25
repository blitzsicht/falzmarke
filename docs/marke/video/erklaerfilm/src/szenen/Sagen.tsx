import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';
import {Typewriter} from '../components/Typewriter';

const MARKDOWN = [
  '---',
  'profil: example-grafik',
  'form: B',
  'empfaenger:',
  '  - Muster GmbH',
  '  - Frau Erika Muster',
  'betreff: Zahlungserinnerung zu Rechnung Nr. 2026-0815',
  '---',
];

/** 6–18 s — ein Satz an den Agenten, darunter entsteht die Datei. */
export const Sagen: React.FC<{text: string; satz: string}> = ({text, satz}) => {
  const frame = useCurrentFrame();
  const l = useLayout();

  // Die Blase erscheint zuerst, die Datei baut sich danach Zeile fuer Zeile auf.
  const blase = interpolate(frame, [0, 18], [0, 1], {extrapolateRight: 'clamp'});
  const zeilen = Math.max(0, Math.floor((frame - 110) / 14));

  return (
    <Grund>
      <AbsoluteFill style={{padding: l.rand, justifyContent: 'center', gap: l.abstand}}>
        {/* Stilisierter Chat — bewusst gezeichnet, nie ein Screenshot. */}
        <div
          style={{
            alignSelf: 'flex-start',
            maxWidth: l.hoch ? '100%' : '70%',
            background: marke.farben.tinte,
            color: marke.farben.papier,
            borderRadius: `${l.klein}px ${l.klein}px ${l.klein}px ${l.klein * 0.25}px`,
            padding: `${l.klein}px ${l.mittel}px`,
            fontSize: l.klein,
            opacity: blase,
            transform: `translateY(${interpolate(frame, [0, 18], [14, 0], {extrapolateRight: 'clamp'})}px)`,
          }}
        >
          <Typewriter
            text={satz}
            startFrame={12}
            zeichenProSekunde={26}
            cursorFarbe={marke.farben.papier}
          />
        </div>

        {/* Die Datei, die daraufhin entsteht. */}
        <div
          style={{
            fontFamily: marke.schriften.mono,
            fontSize: l.winzig,
            lineHeight: 1.75,
            color: marke.farben.tinte,
            borderLeft: `${Math.round(l.winzig * 0.22)}px solid ${marke.farben.gruen}`,
            paddingLeft: l.klein,
            minHeight: l.winzig * 1.75 * MARKDOWN.length,
          }}
        >
          {MARKDOWN.slice(0, zeilen).map((z) => (
            <div key={z}>{z || ' '}</div>
          ))}
        </div>

        <div style={{fontSize: l.mittel, color: marke.farben.tinte, fontWeight: 600}}>
          {text}
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
