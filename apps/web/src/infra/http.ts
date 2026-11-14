import { request as apiRequest } from "@job-tracker/shared/api";

// Relative calls share the development proxy and production origin.
export const request = <T>(path: string, init?: RequestInit): Promise<T> =>
  apiRequest<T>(path, { ...init, credentials: init?.credentials ?? "same-origin" }, "/api");
export { ApiError, toQuery } from "@job-tracker/shared/api";
