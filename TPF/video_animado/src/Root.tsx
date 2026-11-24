import React from "react";
import { Composition } from "remotion";
import { Reel } from "./Reel";
import { HORIZONTAL, ReelHorizontal } from "./Horizontal";
import { FPS, H, W } from "./lib/tema";
import { TOTAL } from "./lib/tiempo";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Reel" component={Reel} durationInFrames={TOTAL} fps={FPS} width={W} height={H} />
    <Composition id="ReelHorizontal" component={ReelHorizontal} durationInFrames={TOTAL} fps={FPS} width={HORIZONTAL.ancho} height={HORIZONTAL.alto} />
  </>
);
