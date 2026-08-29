import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, critique, draft, extract, gapAnalysis } from "./api";
import type {
  CritiqueResponse,
  DraftResponse,
  ExtractionResponse,
  GapAnalysisResponse,
} from "./types";

const MAX_REVISE_ITERATIONS = 2;

export type PipelineState =
  | "idle"
  | "extracting"
  | "analyzing"
  | "drafting"
  | "critiquing"
  | "revising"
  | "passed"
  | "capped"
  | "error"
  | "cancelled";

export type PipelineErrorStage = "extraction" | "gap-analysis" | "draft" | "critique" | null;

type PipelineResult = {
  state: PipelineState;
  extraction: ExtractionResponse | null;
  gapAnalysis: GapAnalysisResponse | null;
  draft: DraftResponse | null;
  critique: CritiqueResponse | null;
  revisionCount: number;
  error: ApiError | null;
  errorStage: PipelineErrorStage;
  run: (posting: string) => Promise<void>;
  retry: () => Promise<void>;
  cancel: () => void;
  reset: () => void;
};

type PreservedPipeline = {
  extraction: ExtractionResponse | null;
  gapAnalysis: GapAnalysisResponse | null;
  draft: DraftResponse | null;
  critique: CritiqueResponse | null;
  revisionCount: number;
};

export function usePipeline(): PipelineResult {
  const controllerRef = useRef<AbortController | null>(null);
  const [state, setState] = useState<PipelineState>("idle");
  const [extractionResult, setExtractionResult] = useState<ExtractionResponse | null>(null);
  const [gapResult, setGapResult] = useState<GapAnalysisResponse | null>(null);
  const [draftResult, setDraftResult] = useState<DraftResponse | null>(null);
  const [critiqueResult, setCritiqueResult] = useState<CritiqueResponse | null>(null);
  const [revisionCount, setRevisionCount] = useState(0);
  const [error, setError] = useState<ApiError | null>(null);
  const [errorStage, setErrorStage] = useState<PipelineErrorStage>(null);
  const postingRef = useRef("");

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setState((current) =>
      current === "extracting" ||
      current === "analyzing" ||
      current === "drafting" ||
      current === "critiquing" ||
      current === "revising"
        ? "cancelled"
        : current,
    );
  }, []);

  const execute = useCallback(async (posting: string, startStage: Exclude<PipelineErrorStage, null>, preserved: PreservedPipeline) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    let failedStage = startStage;
    let currentRevisionCount = preserved.revisionCount;
    let extraction = preserved.extraction;
    let analysis = preserved.gapAnalysis;
    let letter = preserved.draft;

    setError(null);
    setErrorStage(null);

    try {
      if (startStage === "extraction") {
        setState("extracting");
        failedStage = "extraction";
        extraction = await extract({ posting }, controller.signal);
        if (controller.signal.aborted) return;
        setExtractionResult(extraction);
      }

      if (startStage === "extraction" || startStage === "gap-analysis") {
        if (!extraction) throw new Error("Extraction output is unavailable.");
        failedStage = "gap-analysis";
        setState("analyzing");
        analysis = await gapAnalysis({ extraction }, controller.signal);
        if (controller.signal.aborted) return;
        setGapResult(analysis);
      }

      if (startStage === "extraction" || startStage === "gap-analysis" || startStage === "draft") {
        if (!extraction || !analysis) throw new Error("Prior stage output is unavailable.");
        failedStage = "draft";
        setState("drafting");
        const revisionFindings = startStage === "draft" && preserved.critique?.verdict === "revise"
          ? preserved.critique.findings
          : undefined;
        letter = await draft(
          revisionFindings
            ? {
                extraction,
                gap_analysis: analysis,
                previous_cover_letter: letter ?? undefined,
                findings: revisionFindings,
              }
            : { extraction, gap_analysis: analysis },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setDraftResult(letter);
      }

      if (!extraction || !analysis || !letter) throw new Error("Draft context is unavailable.");

      while (true) {
        failedStage = "critique";
        setState("critiquing");
        const result = await critique(
          { extraction, gap_analysis: analysis, cover_letter: letter },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setCritiqueResult(result);

        if (result.verdict === "pass") {
          setState("passed");
          return;
        }
        if (currentRevisionCount >= MAX_REVISE_ITERATIONS) {
          setState("capped");
          return;
        }

        currentRevisionCount += 1;
        setRevisionCount(currentRevisionCount);
        setState("revising");
        failedStage = "draft";
        setState("drafting");
        letter = await draft(
          {
            extraction,
            gap_analysis: analysis,
            previous_cover_letter: letter,
            findings: result.findings,
          },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setDraftResult(letter);
      }
    } catch (caughtError) {
      if (controller.signal.aborted) {
        setState("cancelled");
      } else {
        setError(
          caughtError instanceof ApiError
            ? caughtError
            : new ApiError("The pipeline failed unexpectedly.", "backend"),
        );
        setErrorStage(failedStage);
        setState("error");
      }
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
      }
    }
  }, []);

  const run = useCallback(async (posting: string) => {
    postingRef.current = posting;
    setState("idle");
    setExtractionResult(null);
    setGapResult(null);
    setDraftResult(null);
    setCritiqueResult(null);
    setRevisionCount(0);
    await execute(posting, "extraction", {
      extraction: null,
      gapAnalysis: null,
      draft: null,
      critique: null,
      revisionCount: 0,
    });
  }, [execute]);

  const retry = useCallback(async () => {
    if (!errorStage || !postingRef.current) return;

    const preserved: PreservedPipeline = {
      extraction: extractionResult,
      gapAnalysis: gapResult,
      draft: draftResult,
      critique: critiqueResult,
      revisionCount,
    };
    if (errorStage === "extraction") {
      preserved.extraction = null;
      preserved.gapAnalysis = null;
      preserved.draft = null;
      preserved.critique = null;
      preserved.revisionCount = 0;
      setExtractionResult(null);
      setGapResult(null);
      setDraftResult(null);
      setCritiqueResult(null);
      setRevisionCount(0);
    } else if (errorStage === "gap-analysis") {
      preserved.gapAnalysis = null;
      preserved.draft = null;
      preserved.critique = null;
      preserved.revisionCount = 0;
      setGapResult(null);
      setDraftResult(null);
      setCritiqueResult(null);
      setRevisionCount(0);
    } else if (errorStage === "draft") {
      preserved.critique = preserved.critique?.verdict === "revise" ? preserved.critique : null;
      setCritiqueResult(preserved.critique);
    } else {
      preserved.critique = null;
      setCritiqueResult(null);
    }

    await execute(postingRef.current, errorStage, preserved);
  }, [critiqueResult, draftResult, errorStage, execute, extractionResult, gapResult, revisionCount]);

  const reset = useCallback(() => {
    cancel();
    setState("idle");
    setExtractionResult(null);
    setGapResult(null);
    setDraftResult(null);
    setCritiqueResult(null);
    setRevisionCount(0);
    setError(null);
    setErrorStage(null);
  }, [cancel]);

  useEffect(() => cancel, [cancel]);

  return {
    state,
    extraction: extractionResult,
    gapAnalysis: gapResult,
    draft: draftResult,
    critique: critiqueResult,
    revisionCount,
    error,
    errorStage,
    run,
    retry,
    cancel,
    reset,
  };
}
