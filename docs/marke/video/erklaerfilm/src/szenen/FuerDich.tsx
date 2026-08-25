import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';

/**
 * 52–60 s — Abbinder.
 *
 * Der Installationsbefehl kommt aus dem Textkanon (docs/marke/texte.yaml) und
 * wird von tests/test_marke.py geprueft: Er muss eine Herkunft nennen.
 * `pipx install falzmarke` gibt es nicht — das Paket liegt nicht auf PyPI.
 */
export const FuerDich: React.FC<{
  claim: string;
  installation: string;
  adresse: string;
}> = ({claim, installation, adresse}) => {
  const frame = useCurrentFrame();
  const l = useLayout();
  const auf = interpolate(frame, [0, 22], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <Grund>
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          padding: l.rand,
          gap: l.abstand,
        }}
      >
        <Img
          src={staticFile('logo.svg')}
          style={{width: l.kurzLogo * 2.1, opacity: auf}}
        />
        <div
          style={{
            fontFamily: marke.schriften.kopf,
            fontWeight: 800,
            fontSize: l.mittel,
            lineHeight: 1.2,
            color: marke.farben.tinte,
            textAlign: 'center',
            maxWidth: l.hoch ? '100%' : '76%',
            opacity: interpolate(frame, [16, 40], [0, 1], {extrapolateRight: 'clamp'}),
          }}
        >
          {claim}
        </div>
        <div
          style={{
            fontFamily: marke.schriften.mono,
            fontSize: l.winzig * 0.82,
            color: marke.farben.tinte,
            background: '#F4F5F7',
            padding: `${l.winzig * 0.5}px ${l.klein}px`,
            borderRadius: l.winzig * 0.3,
            opacity: interpolate(frame, [46, 70], [0, 1], {extrapolateRight: 'clamp'}),
            maxWidth: '92%',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {installation}
        </div>
        <div
          style={{
            fontSize: l.klein,
            color: marke.farben.grau,
            opacity: interpolate(frame, [60, 84], [0, 1], {extrapolateRight: 'clamp'}),
          }}
        >
          {adresse}
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
