import {Composition} from 'remotion';
import {Reel} from './Reel';
import {FPS, TOTAL_FRAMES} from './timeline';

export const Root: React.FC = () => (
  <Composition
    id="LumiSyncReel"
    component={Reel}
    durationInFrames={TOTAL_FRAMES}
    fps={FPS}
    width={1080}
    height={1920}
  />
);
