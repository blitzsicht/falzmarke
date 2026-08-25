import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

/**
 * Schreibt `text` Zeichen fuer Zeichen ab `startFrame`.
 * Portiert aus customer-blitzsicht/marketing/ai-search-promo/remotion.
 */
export const Typewriter: React.FC<{
  text: string;
  startFrame: number;
  zeichenProSekunde: number;
  style?: React.CSSProperties;
  cursorFarbe?: string;
}> = ({text, startFrame, zeichenProSekunde, style, cursorFarbe = 'currentColor'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vergangen = Math.max(0, frame - startFrame);
  const sichtbar = Math.floor((vergangen / fps) * zeichenProSekunde);
  const zeigen = text.slice(0, sichtbar);
  const blinkt = sichtbar < text.length && Math.floor(frame / 8) % 2 === 0;

  return (
    <span style={style}>
      {zeigen}
      {blinkt ? (
        <span
          style={{
            display: 'inline-block',
            width: '0.55em',
            height: '1.05em',
            background: cursorFarbe,
            verticalAlign: 'text-bottom',
            marginLeft: '0.06em',
          }}
        />
      ) : null}
    </span>
  );
};
