import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, extract } from "./api";
import type { ExtractionResponse } from "./types";

export type ExtractionState = "idle" | "extracting" | "complete" | "error" | "cancelled";

type ExtractionResult = {
  response: ExtractionResponse | null;
  error: ApiError | null;
  state: ExtractionState;
  run: (posting: string) => Promise<void>;
  cancel: () => void;
  reset: () => void;
};

export function useExtraction(): ExtractionResult {
  const controllerRef = useRef<AbortController | null>(null);
  const [state, setState] = useState<ExtractionState>("idle");
  const [response, setResponse] = useState<ExtractionResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setState((current) => (current === "extracting" ? "cancelled" : current));
  }, []);

  const run = useCallback(async (posting: string) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setState("extracting");
    setResponse(null);
    setError(null);

    try {
      const result = await extract({ posting }, controller.signal);
      if (!controller.signal.aborted) {
        setResponse(result);
        setState("complete");
      }
    } catch (caughtError) {
      if (controller.signal.aborted) {
        setState("cancelled");
      } else if (caughtError instanceof ApiError) {
        setError(caughtError);
        setState("error");
      } else {
        setError(new ApiError("The Extraction stage failed unexpectedly.", "backend"));
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
    setResponse(null);
    setError(null);
  }, [cancel]);

  useEffect(() => cancel, [cancel]);

  return { state, response, error, run, cancel, reset };
}
