import type { DraftResponse } from "./types";

type CoverLetterViewProps = {
  letter: DraftResponse;
};

export function CoverLetterView({ letter }: CoverLetterViewProps) {
  return (
    <div className="letter">
      <p className="letter-salutation">{letter.salutation}</p>
      {letter.paragraphs.map((paragraph, index) => (
        <div className="letter-paragraph" key={`${paragraph.prose.slice(0, 24)}-${index}`}>
          <p>{paragraph.prose}</p>
          {(paragraph.requirements.length > 0 || paragraph.evidence.length > 0) ? (
            <details className="provenance-details">
              <summary>Why this paragraph?</summary>
              <div className="provenance-content">
                {paragraph.requirements.length > 0 ? (
                  <div>
                    <span className="provenance-label">Addresses</span>
                    <ul>
                      {paragraph.requirements.map((requirement, requirementIndex) => (
                        <li key={`${requirement.text}-${requirementIndex}`}>{requirement.text}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {paragraph.evidence.length > 0 ? (
                  <div>
                    <span className="provenance-label">Verified Profile Evidence</span>
                    <ul>
                      {paragraph.evidence.map((item, evidenceIndex) => (
                        <li key={`${item.text}-${evidenceIndex}`}>
                          <span className="provenance-source">{item.source}</span> {item.text}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            </details>
          ) : null}
        </div>
      ))}
      <p className="letter-signoff">
        {letter.sign_off}
        <br />
        <strong>{letter.candidate_name}</strong>
      </p>
    </div>
  );
}
