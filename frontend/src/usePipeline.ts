import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, extract, gapAnalysis } from "./api";
import type { ExtractionResponse, GapAnalysisResponse } from "./types";

export type PipelineState = "idle" | "extracting" | "analyzing" | "complete" | "error" | "cancelled";
export type PipelineErrorStage = "extraction" | "gap-analysis" | null;

type PipelineResult = {
  state: PipelineState;
  extraction: ExtractionResponse | null;
  gapAnalysis: GapAnalysisResponse | null;
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
  const [error, setError] = useState<ApiError | null>(null);
  const [errorStage, setErrorStage] = useState<PipelineErrorStage>(null);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setState((current) => (current === "extracting" || current === "analyzing" ? "cancelled" : current));
  }, []);

  const run = useCallback(async (posting: string) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setState("extracting");
    setExtractionResult(null);
    setGapResult(null);
    setError(null);
    setErrorStage(null);
    let completedExtraction: ExtractionResponse | null = null;

    try {
      const extraction = await extract({ posting }, controller.signal);
      if (controller.signal.aborted) return;
      completedExtraction = extraction;
      setExtractionResult(extraction);
      setState("analyzing");

      const analysis = await gapAnalysis({ extraction }, controller.signal);
      if (!controller.signal.aborted) {
        setGapResult(analysis);
        setState("complete");
      }
    } catch (caughtError) {
      if (controller.signal.aborted) {
        setState("cancelled");
      } else {
        setError(caughtError instanceof ApiError ? caughtError : new ApiError("The pipeline failed unexpectedly.", "backend"));
        setErrorStage(completedExtraction ? "gap-analysis" : "extraction");
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
    setError(null);
    setErrorStage(null);
  }, [cancel]);

  useEffect(() => cancel, [cancel]);

  return {
    state,
    extraction: extractionResult,
    gapAnalysis: gapResult,
    error,
    errorStage,
    run,
    cancel,
    reset,
  };
}
