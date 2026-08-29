type JobPostingInputProps = {
  value: string;
  readOnly: boolean;
  onChange: (value: string) => void;
};

export function JobPostingInput({ value, readOnly, onChange }: JobPostingInputProps) {
  return (
    <div className="posting-input">
      <div className="field-label-row">
        <label htmlFor="job-posting">Job Posting</label>
        <span>{value.length.toLocaleString()} / 8,000</span>
      </div>
      <textarea
        id="job-posting"
        value={value}
        readOnly={readOnly}
        minLength={50}
        maxLength={8000}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Paste a Job Posting here"
        rows={12}
      />
      {readOnly ? (
        <p className="field-note">This fictional sample is locked so the demo runs on the same text as its fixture.</p>
      ) : (
        <p className="field-note">Use the employer’s own wording. Extraction keeps only Requirements it can verify in this text.</p>
      )}
    </div>
  );
}
