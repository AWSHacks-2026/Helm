import { useCallback, useState } from "react";

import type { WalkthroughStep } from "../demoWalkthrough";

export function useDemoWalkthrough(steps: WalkthroughStep[]) {
  const [index, setIndex] = useState(0);
  const step = steps[index] ?? steps[0];
  const isComplete = index >= steps.length - 1;

  const advance = useCallback(() => {
    setIndex((current) => Math.min(current + 1, steps.length - 1));
  }, [steps.length]);

  const reset = useCallback(() => {
    setIndex(0);
  }, []);

  return {
    step,
    index,
    total: steps.length,
    isComplete,
    advance,
    reset,
  };
}
