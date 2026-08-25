import React from 'react';
import {AbsoluteFill} from 'remotion';
import {marke} from '../brand';
import {fontFaces} from '../fontFaces';

/** Gemeinsamer Bildgrund: Papier, Hausschrift, Schriftdeklarationen. */
export const Grund: React.FC<{children: React.ReactNode; hintergrund?: string}> = ({
  children,
  hintergrund = marke.farben.papier,
}) => (
  <AbsoluteFill style={{backgroundColor: hintergrund, fontFamily: marke.schriften.text}}>
    <style>{fontFaces}</style>
    {children}
  </AbsoluteFill>
);
