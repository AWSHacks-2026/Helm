import type { TraceFileState } from "../../flightRecorder/types";

type Props = {
  file?: TraceFileState;
};

export function TraceFilePanel({ file }: Props) {
  if (!file) {
    return (
      <section className="trace-file-panel" aria-label="File state">
        <p>No file state for this step.</p>
      </section>
    );
  }

  return (
    <section
      className={`trace-file-panel status-${file.status}`}
      aria-label="File state"
    >
      <header>
        <h3>{file.path}</h3>
        <span className="file-status">{file.status}</span>
      </header>
      <pre>{file.snippet}</pre>
    </section>
  );
}
