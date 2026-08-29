import type { ReactNode } from "react";

export type PipelineStageState = "idle" | "active" | "complete" | "error";

type PipelineStageProps = {
  number: string;
  title: string;
  state: PipelineStageState;
  children?: ReactNode;
};

const stateLabels: Record<PipelineStageState, string> = {
  idle: "Waiting",
  active: "In progress",
  complete: "Complete",
  error: "Needs attention",
};

export function PipelineStage({ number, title, state, children }: PipelineStageProps) {
  return (
    <section
      className={`pipeline-stage pipeline-stage--${state}`}
      aria-labelledby={`stage-${number}`}
      aria-busy={state === "active"}
    >
      <div className="stage-marker" aria-hidden="true">
        {number}
      </div>
      <div className="stage-body">
        <div className="stage-heading">
          <div>
            <p className="eyebrow">Stage {number}</p>
            <h2 id={`stage-${number}`}>{title}</h2>
          </div>
          <span className="stage-status" role="status" aria-live="polite">
            {stateLabels[state]}
          </span>
        </div>
        {children}
      </div>
    </section>
  );
}
