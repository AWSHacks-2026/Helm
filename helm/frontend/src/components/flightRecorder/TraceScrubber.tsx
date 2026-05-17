import type { FlightTrace } from "../../flightRecorder/types";

type Playback = {
  frameIndex: number;
  frameCount: number;
  isPlaying: boolean;
  frame: { title: string; atMs: number };
  play: () => void;
  pause: () => void;
  reset: () => void;
  stepForward: () => void;
  stepBack: () => void;
  seek: (index: number) => void;
};

type Props = {
  trace: FlightTrace;
  playback: Playback;
};

const formatMs = (ms: number): string => {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}:${remainder.toString().padStart(2, "0")}`;
};

export function TraceScrubber({ trace, playback }: Props) {
  const maxIndex = Math.max(0, playback.frameCount - 1);

  return (
    <section className="trace-scrubber" aria-label="Timeline scrubber">
      <div className="trace-scrubber-meta">
        <span>
          Step {playback.frameIndex + 1} / {playback.frameCount}
        </span>
        <span>{formatMs(playback.frame.atMs)}</span>
      </div>
      <input
        type="range"
        min={0}
        max={maxIndex}
        value={playback.frameIndex}
        onChange={(event) => playback.seek(Number(event.target.value))}
        aria-label="Scrub timeline"
      />
      <div className="trace-scrubber-controls">
        <button type="button" onClick={playback.stepBack} disabled={playback.frameIndex === 0}>
          Step back
        </button>
        {playback.isPlaying ? (
          <button type="button" onClick={playback.pause}>
            Pause
          </button>
        ) : (
          <button type="button" onClick={playback.play}>
            Play
          </button>
        )}
        <button
          type="button"
          onClick={playback.stepForward}
          disabled={playback.frameIndex >= maxIndex}
        >
          Step forward
        </button>
        <button type="button" onClick={playback.reset}>
          Reset
        </button>
      </div>
      <p className="trace-scrubber-meta">
        <strong>{playback.frame.title}</strong>
        <span>{trace.label}</span>
      </p>
    </section>
  );
}
