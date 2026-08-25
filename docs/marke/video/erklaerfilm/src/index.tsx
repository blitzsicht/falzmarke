import {Composition, registerRoot} from 'remotion';
import {Erklaerfilm, FPS, GESAMT_FRAMES} from './Erklaerfilm';

/**
 * Zwei Kompositionen, ein Film. Das Hochformat stapelt, was im Querformat
 * nebeneinander steht — die Anordnung entscheidet src/layout.ts anhand des
 * Seitenverhaeltnisses, nicht eine zweite Fassung der Szenen.
 */
const Root: React.FC = () => (
  <>
    <Composition
      id="Querformat"
      component={Erklaerfilm}
      durationInFrames={GESAMT_FRAMES}
      fps={FPS}
      width={1920}
      height={1080}
    />
    <Composition
      id="Hochformat"
      component={Erklaerfilm}
      durationInFrames={GESAMT_FRAMES}
      fps={FPS}
      width={1080}
      height={1920}
    />
  </>
);

registerRoot(Root);
