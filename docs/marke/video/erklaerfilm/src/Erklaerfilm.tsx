import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import texte from './texte.json';
import {Auftrag} from './szenen/Auftrag';
import {Ohne} from './szenen/Ohne';
import {Norm} from './szenen/Norm';
import {Gleich} from './szenen/Gleich';
import {FuerDich} from './szenen/FuerDich';

export const FPS = 30;

/**
 * Eine Zeitleiste fuer beide Formate.
 *
 * Die Zeiten stehen in docs/marke/texte.yaml, nicht hier. tests/test_marke.py
 * prueft sie auf Lueckenlosigkeit und jede Szene auf mindestens 2,5 Sekunden.
 *
 * Getaktet auf 25 Sekunden. Die erste Fassung lief 60, die zweite 37 — beide
 * waren zu langsam geschnitten. Harte Schnitte, keine Blenden: wer nach zwei
 * Sekunden nicht weiss, worum es geht, ist weg.
 *
 * Dramaturgie: Auftrag -> was ohne feste Form herauskommt (durchgestrichen) ->
 * der gesetzte Brief mit Stempel und Massen -> immer dieselbe Form -> Abbinder.
 */
const nach = (name: string) => {
  const szene = texte.szenen.find((s) => s.name === name);
  if (!szene) {
    throw new Error(
      `Die Szene "${name}" fehlt im Textkanon. ` +
        `Vorhanden: ${texte.szenen.map((s) => s.name).join(', ')}`,
    );
  }
  return {
    from: Math.round(szene.von * FPS),
    durationInFrames: Math.round((szene.bis - szene.von) * FPS),
    text: szene.text,
  };
};

export const Erklaerfilm: React.FC = () => {
  const auftrag = nach('Auftrag');
  const ohne = nach('Ohne');
  const norm = nach('Norm');
  const gleich = nach('Gleich');
  const fuerDich = nach('Für dich');

  return (
    <AbsoluteFill>
      <Sequence from={auftrag.from} durationInFrames={auftrag.durationInFrames}>
        <Auftrag text={auftrag.text} />
      </Sequence>

      <Sequence from={ohne.from} durationInFrames={ohne.durationInFrames}>
        <Ohne text={ohne.text} />
      </Sequence>

      <Sequence from={norm.from} durationInFrames={norm.durationInFrames}>
        <Norm text={norm.text} />
      </Sequence>

      <Sequence from={gleich.from} durationInFrames={gleich.durationInFrames}>
        <Gleich text={gleich.text} ohne={texte.nutzen.ohne} mit={texte.nutzen.mit} />
      </Sequence>

      <Sequence from={fuerDich.from} durationInFrames={fuerDich.durationInFrames}>
        <FuerDich
          stufe1={texte.claimStufe1}
          stufe2={texte.claimStufe2}
          adresse={texte.adresse}
        />
      </Sequence>
    </AbsoluteFill>
  );
};

export const GESAMT_FRAMES = Math.round(texte.dauer * FPS);
