import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';

/** 0–6 s — der Anlass, in einem Satz. */
export const Wunsch: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const l = useLayout();
  const auf = interpolate(frame, [0, 20], [0, 1], {extrapolateRight: 'clamp'});
  const hoch = interpolate(frame, [0, 30], [18, 0], {extrapolateRight: 'clamp'});

  return (
    <Grund>
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'flex-start',
          padding: l.rand,
          gap: l.abstand,
        }}
      >
        <Img src={staticFile('logo.svg')} style={{width: l.kurzLogo, opacity: auf}} />
        <div
          style={{
            fontFamily: marke.schriften.kopf,
            fontWeight: 800,
            fontSize: l.gross,
            lineHeight: 1.18,
            color: marke.farben.tinte,
            opacity: auf,
            transform: `translateY(${hoch}px)`,
            maxWidth: l.hoch ? '100%' : '78%',
          }}
        >
          „{text}“
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
