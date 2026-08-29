import type { AssessmentOutcome, GapAnalysisResponse } from "./types";

type GapAnalysisViewProps = {
  response: GapAnalysisResponse;
};

const outcomeLabels: Record<AssessmentOutcome, string> = {
  match: "Match",
  adjacent: "Adjacent",
  gap: "Gap",
};

export function GapAnalysisView({ response }: GapAnalysisViewProps) {
  return (
    <div className="assessment-list">
      {response.assessments.map((assessment, index) => (
        <article className="assessment" key={`${assessment.requirement.text}-${index}`}>
          <div className="assessment-heading">
            <span className={`outcome outcome--${assessment.outcome}`}>
              {outcomeLabels[assessment.outcome]}
            </span>
            <p>{assessment.requirement.text}</p>
          </div>
          <p className="assessment-reason">{assessment.reason}</p>
          {assessment.evidence.length > 0 ? (
            <details className="evidence-details">
              <summary>Show Profile Evidence ({assessment.evidence.length})</summary>
              <div className="evidence-list">
                {assessment.evidence.map((item, evidenceIndex) => (
                  <div className="evidence-item" key={`${item.text}-${evidenceIndex}`}>
                    <span>{item.source}</span>
                    <p>{item.text}</p>
                  </div>
                ))}
              </div>
            </details>
          ) : null}
        </article>
      ))}
    </div>
  );
}
