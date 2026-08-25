import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';

const WEGE = ['drucken', 'versenden', 'archivieren'];

/** 42–52 s — was am Ende dasteht und was man damit tun kann. */
export const Ziel: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const l = useLayout();

  const auf = spring({frame, fps, config: {damping: 200}, durationInFrames: 26});

  return (
    <Grund>
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          padding: l.rand,
          gap: l.abstand * 1.2,
        }}
      >
        {/* Das PDF mit seinen zwei Anhaengen — der Hybridbrief. */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: l.klein * 0.6,
            transform: `scale(${0.9 + auf * 0.1})`,
          }}
        >
          <div
            style={{
              fontFamily: marke.schriften.kopf,
              fontWeight: 800,
              fontSize: l.gross,
              color: marke.farben.tinte,
              letterSpacing: '-0.01em',
            }}
          >
            PDF/A
          </div>
          <div style={{display: 'flex', gap: l.klein * 0.5}}>
            {['brief.md', 'brief.json'].map((name, i) => (
              <div
                key={name}
                style={{
                  fontFamily: marke.schriften.mono,
                  fontSize: l.winzig * 0.9,
                  color: marke.farben.tinte,
                  border: `1px solid ${marke.farben.grau}`,
                  borderRadius: l.winzig * 0.3,
                  padding: `${l.winzig * 0.3}px ${l.winzig * 0.6}px`,
                  opacity: interpolate(frame, [30 + i * 10, 48 + i * 10], [0, 1], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  }),
                }}
              >
                {name}
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            fontFamily: marke.schriften.kopf,
            fontWeight: 800,
            fontSize: l.mittel,
            color: marke.farben.tinte,
            textAlign: 'center',
            maxWidth: l.hoch ? '100%' : '70%',
            lineHeight: 1.2,
          }}
        >
          {text}
        </div>

        <div style={{display: 'flex', flexDirection: l.richtung, gap: l.klein, marginTop: l.klein}}>
          {WEGE.map((weg, i) => (
            <div
              key={weg}
              style={{
                fontSize: l.klein,
                color: marke.farben.grau,
                opacity: interpolate(frame, [120 + i * 14, 144 + i * 14], [0, 1], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                }),
              }}
            >
              {weg}
            </div>
          ))}
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
