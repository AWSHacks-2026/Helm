import { useState } from "react";

import type { DashboardModel, IncidentState } from "../orchestration/types";

interface IncidentConsoleProps {
  model: DashboardModel;
  selectedIncidentId: string | null;
  onSelectIncident: (incidentId: string) => void;
}

const incidentTypes = [
  "merge_conflict",
  "intent_conflict",
  "guardrail_block",
  "duplicate_work",
] as const;

type IncidentFilter = "all" | (typeof incidentTypes)[number];

const titleCase = (value: string): string => {
  const label = value.replace(/_/g, " ");

  return label.charAt(0).toUpperCase() + label.slice(1);
};

const formatTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
      return timestamp;
    }

    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(date);
  } catch {
    return timestamp;
  }
};

const resolveSelectedIncident = (
  incidents: IncidentState[],
  selectedIncidentId: string | null,
): IncidentState | undefined =>
  incidents.find((incident) => incident.id === selectedIncidentId) ?? incidents[0];

const filterOptions: IncidentFilter[] = ["all", ...incidentTypes];

const filterLabel = (filter: IncidentFilter): string =>
  filter === "all" ? "All" : titleCase(filter);

const filterEmptyLabel = (filter: IncidentFilter): string =>
  filter === "all" ? "incidents" : `${titleCase(filter).toLowerCase()} incidents`;

export function IncidentConsole({
  model,
  selectedIncidentId,
  onSelectIncident,
}: IncidentConsoleProps) {
  const [selectedFilter, setSelectedFilter] = useState<IncidentFilter>("all");
  const filteredIncidents =
    selectedFilter === "all"
      ? model.incidents
      : model.incidents.filter((incident) => incident.type === selectedFilter);
  const selectedIncident = resolveSelectedIncident(
    filteredIncidents,
    selectedIncidentId,
  );

  return (
    <main className="incident-console">
      <header className="screen-header">
        <div>
          <p className="eyebrow">Incident console</p>
          <h1>Resolve Helm incidents</h1>
          <p>Review the queue, inspect arbitration reasoning, and choose the next task.</p>
        </div>
      </header>

      <div className="filter-pills" aria-label="Incident type filters">
        {filterOptions.map((filter) => (
          <button
            key={filter}
            type="button"
            className={selectedFilter === filter ? "active" : ""}
            onClick={() => setSelectedFilter(filter)}
          >
            {filterLabel(filter)}
          </button>
        ))}
      </div>

      {filteredIncidents.length === 0 ? (
        <p className="empty-state">
          {model.incidents.length === 0
            ? "No incidents in the queue."
            : `No ${filterEmptyLabel(selectedFilter)} in the queue.`}
        </p>
      ) : (
        <section className="incident-layout">
          <aside className="incident-queue" aria-label="Incident queue">
            <h2>Queue</h2>
            <div className="incident-row-list">
              {filteredIncidents.map((incident) => (
                <button
                  key={incident.id}
                  type="button"
                  className={`incident-row status-${incident.status} type-${incident.type} ${
                    selectedIncident?.id === incident.id ? "active" : ""
                  }`}
                  onClick={() => onSelectIncident(incident.id)}
                >
                  <span>{titleCase(incident.type)}</span>
                  <strong>{incident.title}</strong>
                  <small>
                    {titleCase(incident.status)} · {formatTimestamp(incident.createdAt)}
                  </small>
                </button>
              ))}
            </div>
          </aside>

          {selectedIncident && (
            <article className="incident-detail">
              <p className="eyebrow">{titleCase(selectedIncident.type)}</p>
              <h2>{selectedIncident.title}</h2>
              <p>{selectedIncident.summary}</p>

              <dl>
                <div>
                  <dt>Status</dt>
                  <dd>{titleCase(selectedIncident.status)}</dd>
                </div>
                <div>
                  <dt>File path</dt>
                  <dd>
                    {selectedIncident.filePath ? (
                      <code>{selectedIncident.filePath}</code>
                    ) : (
                      "Not tied to a single file"
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Agents</dt>
                  <dd>{selectedIncident.agentIds.join(", ") || "No agents listed"}</dd>
                </div>
                <div>
                  <dt>Reasoning</dt>
                  <dd>{selectedIncident.reasoning ?? "No reasoning captured yet."}</dd>
                </div>
                <div>
                  <dt>Suggested task</dt>
                  <dd>
                    {selectedIncident.suggestedTask ??
                      "No reassignment suggestion captured yet."}
                  </dd>
                </div>
              </dl>

              <details open>
                <summary>Resolved code</summary>
                {selectedIncident.resolvedCode ? (
                  <pre>{selectedIncident.resolvedCode}</pre>
                ) : (
                  <p>No resolved code has been proposed yet.</p>
                )}
              </details>
            </article>
          )}
        </section>
      )}
    </main>
  );
}
