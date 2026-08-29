import type { ExtractionResponse, Necessity } from "./types";

type ExtractionViewProps = {
  response: ExtractionResponse;
};

const necessityLabels: Record<Necessity, string> = {
  required: "Required",
  preferred: "Preferred",
  unstated: "Unstated",
};

export function ExtractionView({ response }: ExtractionViewProps) {
  return (
    <div className="extraction-result">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Verified output</p>
          <h3>
            {response.job_title ?? "Role details not stated"}
            {response.company ? <span> at {response.company}</span> : null}
          </h3>
        </div>
        <span className="verified-mark">✓ Source checked</span>
      </div>
      <div className="requirement-list">
        {response.requirements.map((requirement, index) => (
          <article className="requirement" key={`${requirement.text}-${index}`}>
            <span className={`necessity necessity--${requirement.necessity}`}>
              {necessityLabels[requirement.necessity]}
            </span>
            <p>{requirement.text}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
