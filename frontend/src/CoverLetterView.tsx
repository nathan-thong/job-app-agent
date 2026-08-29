import { useState } from "react";

import type { DraftResponse } from "./types";
import { formatLetter } from "./letter";

type CoverLetterViewProps = {
  letter: DraftResponse;
  editedText: string | null;
  editing: boolean;
  canEdit: boolean;
  onEdit: (value: string) => void;
  onEditingChange: (editing: boolean) => void;
  onReset: () => void;
};

export function CoverLetterView({
  letter,
  editedText,
  editing,
  canEdit,
  onEdit,
  onEditingChange,
  onReset,
}: CoverLetterViewProps) {
  const visibleText = editedText ?? formatLetter(letter);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "unavailable">("idle");

  const copyVisibleLetter = async () => {
    if (!navigator.clipboard) {
      setCopyStatus("unavailable");
      return;
    }
    try {
      await navigator.clipboard.writeText(visibleText);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("unavailable");
    }
  };

  return (
    <div className="letter">
      {editing || editedText ? (
        <textarea
          className="letter-editor"
          value={visibleText}
          onChange={(event) => onEdit(event.target.value)}
          aria-label="Edited Cover Letter"
          rows={18}
        />
      ) : (
        <>
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
        </>
      )}
      {canEdit ? (
        <div className="letter-actions">
          <button className="button button--ghost" onClick={() => onEditingChange(!editing)}>
            {editing ? "Done editing" : "Edit generated text"}
          </button>
          {editedText ? (
            <button className="button button--ghost" onClick={onReset}>
              Reset to generated
            </button>
          ) : null}
          <button className="button button--secondary" onClick={() => void copyVisibleLetter()}>
            Copy visible letter
          </button>
          <span className="copy-status" role="status" aria-live="polite">
            {copyStatus === "copied"
              ? "Copied to clipboard."
              : copyStatus === "unavailable"
                ? "Clipboard unavailable; select and copy the letter manually."
                : null}
          </span>
        </div>
      ) : null}
      {editedText ? (
        <p className="edit-warning">Edited Cover Letter: the earlier Critique Verdict and provenance apply only to the generated version.</p>
      ) : null}
    </div>
  );
}
