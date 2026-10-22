import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL;

export const API_BASE_URL =
  configuredBaseUrl === undefined ? "http://127.0.0.1:8000" : configuredBaseUrl.replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(
    message: string,
    options: { status?: number; code?: string; details?: Record<string, unknown> } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status ?? 0;
    this.code = options.code ?? "REQUEST_FAILED";
    this.details = options.details ?? {};
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function toApiError(error: unknown, response: Response): ApiError {
  if (isRecord(error) && isRecord(error.error)) {
    const envelope = error.error;
    return new ApiError(
      typeof envelope.message === "string" ? envelope.message : "请求失败。",
      {
        status: response.status,
        code: typeof envelope.code === "string" ? envelope.code : "REQUEST_FAILED",
        details: isRecord(envelope.details) ? envelope.details : {},
      },
    );
  }
  if (isRecord(error) && Array.isArray(error.detail)) {
    const first = error.detail[0];
    const message = isRecord(first) && typeof first.msg === "string" ? first.msg : "请求参数无效。";
    return new ApiError(message, { status: response.status, code: "VALIDATION_ERROR" });
  }
  return new ApiError(response.statusText || "请求失败。", { status: response.status });
}

export function unwrap<T>(data: T | undefined, error: unknown, response: Response): T {
  if (data !== undefined) {
    return data;
  }
  throw toApiError(error, response);
}

export const apiClient = createClient<paths>({
  baseUrl: API_BASE_URL,
  headers: { Accept: "application/json" },
  // Resolve fetch at request time so test interceptors and runtime polyfills can replace it.
  fetch: (input: Request) => globalThis.fetch(input),
});
