import { HACKATHON_THEME } from "../content/gratitudeMission";
import type { WalkthroughStep } from "../demoWalkthrough";

interface DemoWalkthroughProps {
  step: WalkthroughStep;
  index: number;
  total: number;
  isComplete: boolean;
  onAdvance: () => void;
  onDismiss: () => void;
}

export function DemoWalkthrough({
  step,
  index,
  total,
  isComplete,
  onAdvance,
  onDismiss,
}: DemoWalkthroughProps) {
  return (
    <aside className="demo-walkthrough" aria-label="Presentation guide">
      <div className="demo-walkthrough-inner">
        <p className="eyebrow">
          {HACKATHON_THEME} · {index + 1} of {total}
        </p>
        <h2>{step.title}</h2>
        <p>{step.instruction}</p>
        <div className="demo-walkthrough-actions">
          <button type="button" onClick={onDismiss}>
            Skip guide
          </button>
          {!isComplete ? (
            <button type="button" className="primary" onClick={onAdvance}>
              Continue
            </button>
          ) : (
            <button type="button" className="primary" onClick={onDismiss}>
              Close
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
