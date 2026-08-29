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
  cancel: () => void;
  reset: () => void;
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

  const run = useCallback(async (posting: string) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    let failedStage: Exclude<PipelineErrorStage, null> = "extraction";
    let currentRevisionCount = 0;

    setState("extracting");
    setExtractionResult(null);
    setGapResult(null);
    setDraftResult(null);
    setCritiqueResult(null);
    setRevisionCount(0);
    setError(null);
    setErrorStage(null);

    try {
      const extraction = await extract({ posting }, controller.signal);
      if (controller.signal.aborted) return;
      setExtractionResult(extraction);

      failedStage = "gap-analysis";
      setState("analyzing");
      const analysis = await gapAnalysis({ extraction }, controller.signal);
      if (controller.signal.aborted) return;
      setGapResult(analysis);

      failedStage = "draft";
      setState("drafting");
      let letter = await draft({ extraction, gap_analysis: analysis }, controller.signal);
      if (controller.signal.aborted) return;
      setDraftResult(letter);

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
    cancel,
    reset,
  };
}
