import { useEffect, useState } from "react";

import { ApiError, getConfig } from "./api";
import { ExtractionView } from "./ExtractionView";
import { JobPostingInput } from "./JobPostingInput";
import { PipelineStage } from "./PipelineStage";
import { useExtraction } from "./useExtraction";
import type { AppConfig } from "./types";

function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configError, setConfigError] = useState<ApiError | null>(null);
  const [posting, setPosting] = useState("");
  const extraction = useExtraction();

  useEffect(() => {
    const controller = new AbortController();
    getConfig(controller.signal)
      .then((loadedConfig) => {
        setConfig(loadedConfig);
        setPosting(loadedConfig.sample_posting ?? "");
      })
      .catch((caughtError) => {
        if (!controller.signal.aborted) {
          setConfigError(
            caughtError instanceof ApiError
              ? caughtError
              : new ApiError("The app configuration could not be loaded.", "backend"),
          );
        }
      });
    return () => controller.abort();
  }, []);

  if (configError) {
    return (
      <main className="shell shell--centered">
        <p className="eyebrow">Job App Agent</p>
        <h1>Configuration unavailable</h1>
        <p className="error-copy">{configError.message}</p>
        <button className="button button--secondary" onClick={() => window.location.reload()}>
          Try again
        </button>
      </main>
    );
  }

  if (!config) {
    return (
      <main className="shell shell--centered" aria-busy="true">
        <div className="loader" aria-hidden="true" />
        <p>Loading the local pipeline…</p>
      </main>
    );
  }

  const isBusy = extraction.state === "extracting";
  const canRun = posting.length >= 50 && posting.length <= 8000 && !isBusy;
  const stageState =
    extraction.state === "extracting"
      ? "active"
      : extraction.state === "complete"
        ? "complete"
        : extraction.state === "error" || extraction.state === "cancelled"
          ? "error"
          : "idle";

  return (
    <main className="shell">
      <header className="hero">
        <div className="hero-kicker">
          <span className="signal-dot" aria-hidden="true" />
          Local, traceable application workflow
        </div>
        <h1>Turn a Job Posting into a grounded Cover Letter.</h1>
        <p className="hero-copy">
          Start with the employer’s words. This first stage extracts verifiable Requirements before any drafting begins.
        </p>
        <div className="profile-chip">
          <span className="profile-avatar">JE</span>
          <span>
            Using <strong>{config.profile_name}</strong> · fictional demo Profile
          </span>
        </div>
      </header>

      <div className="workflow-grid">
        <div className="input-column">
          <PipelineStage number="01" title="Extraction" state={stageState}>
            <p className="stage-description">Identify the role, company, and Requirements exactly as they appear in the Job Posting.</p>
            {config.mock_mode ? <div className="demo-note">Mock mode · the canonical sample is prefilled and read-only.</div> : null}
            <JobPostingInput value={posting} readOnly={config.mock_mode} onChange={setPosting} />
            <div className="action-row">
              <button className="button button--primary" disabled={!canRun} onClick={() => extraction.run(posting)}>
                {isBusy ? "Extracting…" : "Run Extraction"}
                {!isBusy ? <span aria-hidden="true">↗</span> : null}
              </button>
              {isBusy ? (
                <button className="button button--ghost" onClick={extraction.cancel}>
                  Cancel
                </button>
              ) : null}
            </div>
            {posting.length > 0 && posting.length < 50 ? <p className="validation-copy">Add at least {50 - posting.length} more characters to run Extraction.</p> : null}
            {extraction.state === "cancelled" ? <p className="cancelled-copy">Extraction cancelled. No later stages were scheduled.</p> : null}
            {extraction.error ? <p className="error-copy">{extraction.error.message}</p> : null}
          </PipelineStage>

          <div className="future-stages" aria-label="Upcoming pipeline stages">
            <PipelineStage number="02" title="Gap Analysis" state="idle" />
            <PipelineStage number="03" title="Draft" state="idle" />
            <PipelineStage number="04" title="Critique" state="idle" />
          </div>
        </div>

        <aside className="output-column">
          <div className="output-card">
            <div className="output-card-header">
              <div>
                <p className="eyebrow">Stage output</p>
                <h2>Requirements</h2>
              </div>
              {extraction.response ? <span className="count-pill">{extraction.response.requirements.length} found</span> : null}
            </div>
            {extraction.response ? (
              <ExtractionView response={extraction.response} />
            ) : (
              <div className="empty-output">
                <div className="empty-icon" aria-hidden="true">◎</div>
                <h3>Nothing extracted yet</h3>
                <p>Run the first stage to see source-checked Requirements appear here.</p>
              </div>
            )}
          </div>
          <p className="privacy-note"><span aria-hidden="true">◌</span> Mock mode makes zero external model calls. Your Job Posting stays local to this demo.</p>
        </aside>
      </div>
    </main>
  );
}

export default App;
