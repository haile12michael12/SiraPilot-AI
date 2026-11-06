import { z } from "zod";

const healthStatusSchema = z.object({
  status: z.literal("ok"),
  database: z.literal("connected"),
});

export type HealthStatus = z.infer<typeof healthStatusSchema>;

export async function fetchHealth(signal?: AbortSignal): Promise<HealthStatus> {
  const response = await fetch("/api/v1/health", { signal });
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }
  return healthStatusSchema.parse(await response.json());
}
