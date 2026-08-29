import { useEffect, useState } from "react";

import { ApiError, getConfig } from "./api";
import { CoverLetterView } from "./CoverLetterView";
import { FindingsView } from "./FindingsView";
import { GapAnalysisView } from "./GapAnalysisView";
import { ExtractionView } from "./ExtractionView";
import { JobPostingInput } from "./JobPostingInput";
import { PipelineStage } from "./PipelineStage";
import { usePipeline } from "./usePipeline";
import type { AppConfig } from "./types";

function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configError, setConfigError] = useState<ApiError | null>(null);
  const [posting, setPosting] = useState("");
  const pipeline = usePipeline();

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

  const isBusy = ["extracting", "analyzing", "drafting", "critiquing", "revising"].includes(pipeline.state);
  const canRun = posting.length >= 50 && posting.length <= 8000 && !isBusy;
  const extractionStageState =
    pipeline.state === "extracting"
      ? "active"
      : pipeline.errorStage === "extraction"
        ? "error"
        : pipeline.extraction
        ? "complete"
        : pipeline.state === "cancelled"
          ? "error"
          : "idle";
  const gapStageState =
    pipeline.state === "analyzing"
      ? "active"
      : pipeline.errorStage === "gap-analysis"
        ? "error"
        : pipeline.gapAnalysis
          ? "complete"
          : pipeline.state === "cancelled"
            ? "error"
            : "idle";
  const draftStageState =
    pipeline.state === "drafting" || pipeline.state === "revising"
      ? "active"
      : pipeline.errorStage === "draft"
        ? "error"
        : pipeline.draft
          ? "complete"
          : pipeline.state === "cancelled"
            ? "error"
            : "idle";
  const critiqueStageState =
    pipeline.state === "critiquing"
      ? "active"
      : pipeline.errorStage === "critique"
        ? "error"
        : pipeline.critique
          ? "complete"
          : pipeline.state === "cancelled"
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
          <PipelineStage number="01" title="Extraction" state={extractionStageState}>
            <p className="stage-description">Identify the role, company, and Requirements exactly as they appear in the Job Posting.</p>
            {config.mock_mode ? <div className="demo-note">Mock mode · the canonical sample is prefilled and read-only.</div> : null}
            <JobPostingInput value={posting} readOnly={config.mock_mode} onChange={setPosting} />
            <div className="action-row">
              <button className="button button--primary" disabled={!canRun} onClick={() => pipeline.run(posting)}>
                {pipeline.state === "analyzing"
                  ? "Analyzing…"
                  : pipeline.state === "drafting" || pipeline.state === "revising"
                    ? "Drafting…"
                    : pipeline.state === "critiquing"
                      ? "Critiquing…"
                      : isBusy
                        ? "Working…"
                        : "Generate Cover Letter"}
                {!isBusy ? <span aria-hidden="true">↗</span> : null}
              </button>
              {isBusy ? (
                <button className="button button--ghost" onClick={pipeline.cancel}>
                  Cancel
                </button>
              ) : null}
            </div>
            {posting.length > 0 && posting.length < 50 ? <p className="validation-copy">Add at least {50 - posting.length} more characters to run Extraction.</p> : null}
            {pipeline.state === "cancelled" ? <p className="cancelled-copy">Pipeline cancelled. Completed stages are preserved and no later stages were scheduled.</p> : null}
            {pipeline.error ? <p className="error-copy">{pipeline.error.message}</p> : null}
          </PipelineStage>

          <div className="future-stages" aria-label="Upcoming pipeline stages">
            <PipelineStage number="02" title="Gap Analysis" state={gapStageState}>
              <p className="future-stage-description">Compare each Requirement with Jordan Ellis’s trusted Profile and keep direct Matches distinct from Adjacent evidence.</p>
            </PipelineStage>
            <PipelineStage number="03" title="Draft" state={draftStageState}>
              <p className="future-stage-description">Build a three or four paragraph Cover Letter from verified Requirement and Profile Evidence provenance.</p>
            </PipelineStage>
            <PipelineStage number="04" title="Critique" state={critiqueStageState}>
              <p className="future-stage-description">Check grounding and writing quality, revising only when a blocking Finding remains.</p>
            </PipelineStage>
          </div>
        </div>

        <aside className="output-column">
          <div className="output-card">
            <div className="output-card-header">
              <div>
                <p className="eyebrow">Stage output</p>
                <h2>Requirements</h2>
              </div>
              {pipeline.extraction ? <span className="count-pill">{pipeline.extraction.requirements.length} found</span> : null}
            </div>
            {pipeline.extraction ? (
              <ExtractionView response={pipeline.extraction} />
            ) : (
              <div className="empty-output">
                <div className="empty-icon" aria-hidden="true">◎</div>
                <h3>Nothing extracted yet</h3>
                <p>Run the first stage to see source-checked Requirements appear here.</p>
              </div>
            )}
          </div>
          {pipeline.gapAnalysis ? (
            <div className="output-card analysis-card">
              <div className="output-card-header">
                <div>
                  <p className="eyebrow">Stage output</p>
                  <h2>Gap Analysis</h2>
                </div>
                <span className="count-pill">{pipeline.gapAnalysis.assessments.length} assessed</span>
              </div>
              <GapAnalysisView response={pipeline.gapAnalysis} />
            </div>
          ) : null}
          {pipeline.draft ? (
            <div className="output-card letter-card">
              <div className="output-card-header">
                <div>
                  <p className="eyebrow">Generated artifact</p>
                  <h2>Cover Letter</h2>
                </div>
                {pipeline.revisionCount > 0 ? <span className="count-pill">Revision {pipeline.revisionCount} / 2</span> : null}
              </div>
              <CoverLetterView letter={pipeline.draft} />
            </div>
          ) : null}
          {pipeline.critique ? (
            <div className="output-card critique-card">
              <FindingsView response={pipeline.critique} capped={pipeline.state === "capped"} />
            </div>
          ) : null}
          <p className="privacy-note"><span aria-hidden="true">◌</span> Mock mode makes zero external model calls. Your Job Posting stays local to this demo.</p>
        </aside>
      </div>
    </main>
  );
}

export default App;
