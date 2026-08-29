import type { AppConfig, ExtractionRequest, ExtractionResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type ApiErrorKind = "rate_limit" | "validation" | "backend" | "network";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;

  constructor(message: string, kind: ApiErrorKind, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(
      "The backend could not be reached. Check that the local API is running.",
      "network",
    );
  }

  if (!response.ok) {
    if (response.status === 429) {
      throw new ApiError(
        "The demo request limit has been reached. Try again later.",
        "rate_limit",
        response.status,
      );
    }
    if (response.status === 422) {
      throw new ApiError(
        "The Job Posting must be between 50 and 8,000 characters.",
        "validation",
        response.status,
      );
    }
    throw new ApiError(
      "The backend could not complete this stage. You can retry it.",
      "backend",
      response.status,
    );
  }

  return (await response.json()) as T;
}

export function getConfig(signal?: AbortSignal): Promise<AppConfig> {
  return request<AppConfig>("/config", { signal });
}

export function extract(
  payload: ExtractionRequest,
  signal?: AbortSignal,
): Promise<ExtractionResponse> {
  return request<ExtractionResponse>("/extract", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}
