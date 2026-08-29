import type { CritiqueResponse } from "./types";

type FindingsViewProps = {
  response: CritiqueResponse;
  capped: boolean;
};

const labels: Record<string, string> = {
  unsupported_claim: "Unsupported claim",
  adjacent_as_match: "Adjacent evidence presented as a Match",
  missing_role_specificity: "Missing role specificity",
  forbidden_structure: "Forbidden structure",
  incoherent_prose: "Incoherent prose",
  word_count: "Word count",
  repetition: "Repetition",
  weak_phrasing: "Weak phrasing",
  generic_tone: "Generic tone",
  missed_opportunity: "Missed opportunity",
};

export function FindingsView({ response, capped }: FindingsViewProps) {
  return (
    <div className="findings-panel">
      <div className="findings-header">
        <div>
          <p className="eyebrow">Critique verdict</p>
          <h3>{capped ? "Revision cap reached" : response.verdict === "pass" ? "Ready to use" : "Needs revision"}</h3>
        </div>
        <span className={`verdict-pill verdict-pill--${response.verdict}`}>
          {response.verdict === "pass" ? "Pass" : "Revise"}
        </span>
      </div>
      {response.findings.length > 0 ? (
        <div className="finding-list">
          {response.findings.map((finding, index) => (
            <article className={`finding finding--${finding.severity}`} key={`${finding.code}-${finding.paragraph_number ?? "letter"}-${index}`}>
              <div className="finding-title">
                <span>{finding.severity}</span>
                <strong>{labels[finding.code] ?? finding.code}</strong>
                {finding.paragraph_number ? <small>Paragraph {finding.paragraph_number}</small> : <small>Letter-wide</small>}
              </div>
              <p>{finding.message}</p>
            </article>
          ))}
        </div>
      ) : (
        <p className="no-findings">No Critique Findings. The Cover Letter passed its checks.</p>
      )}
    </div>
  );
}
