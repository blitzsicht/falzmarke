import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import texte from './texte.json';
import {Wunsch} from './szenen/Wunsch';
import {Sagen} from './szenen/Sagen';
import {Setzen} from './szenen/Setzen';
import {Pruefen} from './szenen/Pruefen';
import {Ziel} from './szenen/Ziel';
import {FuerDich} from './szenen/FuerDich';

export const FPS = 30;

/**
 * Eine Zeitleiste fuer beide Formate.
 *
 * Die Zeiten stehen nicht hier, sondern in docs/marke/texte.yaml und kommen
 * ueber texte.json herein. So laesst sich das Drehbuch aendern, ohne den Film
 * anzufassen — und tests/test_marke.py prueft die Zeitleiste auf Lueckenlosigkeit
 * und jede Zeile auf mindestens 2,5 Sekunden Lesezeit.
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
  const wunsch = nach('Wunsch');
  const sagen = nach('Sagen');
  const setzen = nach('Setzen');
  const pruefen = nach('Prüfen');
  const ziel = nach('Ziel');
  const fuerDich = nach('Für dich');

  return (
    <AbsoluteFill>
      <Sequence from={wunsch.from} durationInFrames={wunsch.durationInFrames}>
        <Wunsch text={wunsch.text} />
      </Sequence>

      <Sequence from={sagen.from} durationInFrames={sagen.durationInFrames}>
        <Sagen text={sagen.text} satz={wunsch.text} />
      </Sequence>

      <Sequence from={setzen.from} durationInFrames={setzen.durationInFrames}>
        <Setzen text={setzen.text} />
      </Sequence>

      <Sequence from={pruefen.from} durationInFrames={pruefen.durationInFrames}>
        <Pruefen text={pruefen.text} />
      </Sequence>

      <Sequence from={ziel.from} durationInFrames={ziel.durationInFrames}>
        <Ziel text={ziel.text} />
      </Sequence>

      <Sequence from={fuerDich.from} durationInFrames={fuerDich.durationInFrames}>
        <FuerDich
          claim={texte.claim}
          installation={texte.installation}
          adresse={texte.adresse}
        />
      </Sequence>
    </AbsoluteFill>
  );
};

export const GESAMT_FRAMES = Math.round(texte.dauer * FPS);
