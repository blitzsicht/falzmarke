import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {marke} from '../brand';
import {useLayout} from '../layout';
import {Grund} from '../components/Grund';

/**
 * 21–26 s — Abbinder.
 *
 * Der Claim steht in zwei Stufen: erst wofuer es ist, dann die Pointe. Als ein
 * Satz gelesen ging beides unter.
 *
 * Kein Installationsbefehl mehr. Ein `uvx --from git+https://…`-Aufruf ist auf
 * einer Endkarte weder lesbar noch merkbar, und er brachte ein drittes
 * Schriftbild ins Bild — Montserrat fuer den Claim, Source Sans 3 fuer die
 * Adresse und Monospace im grauen Kasten. Wer den Befehl braucht, findet ihn im
 * README.
 *
 * Die Adresse steht klein und grau darunter, in derselben Schrift wie der Claim.
 */
export const FuerDich: React.FC<{
  stufe1: string;
  stufe2: string;
  adresse: string;
}> = ({stufe1, stufe2, adresse}) => {
  const frame = useCurrentFrame();
  const l = useLayout();

  const zeichen = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});
  const eins = interpolate(frame, [8, 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const zwei = interpolate(frame, [22, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fuss = interpolate(frame, [38, 48], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const stufe = (text: string, auf: number, farbe: string): React.CSSProperties => ({
    fontFamily: marke.schriften.kopf,
    fontWeight: 800,
    fontSize: l.gross,
    lineHeight: 1.16,
    color: farbe,
    textAlign: 'center',
    maxWidth: l.hoch ? '100%' : '82%',
    opacity: auf,
    transform: `translateY(${(1 - auf) * l.winzig * 0.6}px)`,
  });

  return (
    <Grund>
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          padding: l.rand,
          gap: l.klein * 0.7,
        }}
      >
        <Img
          src={staticFile('logo.svg')}
          style={{width: l.kurzLogo * 2.1, opacity: zeichen, marginBottom: l.klein}}
        />

        <div style={stufe(stufe1, eins, marke.farben.tinte)}>{stufe1}</div>
        <div style={stufe(stufe2, zwei, marke.farben.tinte)}>{stufe2}</div>

        <div
          style={{
            marginTop: l.abstand * 1.8,
            fontFamily: marke.schriften.kopf,
            fontWeight: 600,
            fontSize: l.winzig * 0.95,
            letterSpacing: '0.04em',
            color: marke.farben.grau,
            opacity: fuss,
          }}
        >
          {adresse}
        </div>
      </AbsoluteFill>
    </Grund>
  );
};
