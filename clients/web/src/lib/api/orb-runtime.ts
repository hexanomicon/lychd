import createClient from "openapi-fetch";
import type { paths } from "./openapi";
import type { OrbRuntimeSnapshot } from "./models";

const client = createClient<paths>();

/** Read-only and independent of any selected Run or Run event stream. */
export async function getOrbRuntime(signal?: AbortSignal): Promise<OrbRuntimeSnapshot> {
  const result = await client.GET("/api/v1/orb/runtime", { signal });
  const status = result.response.status;
  if (result.error !== undefined || result.data === undefined) {
    throw Object.assign(new Error(`Runtime observations unavailable (${status}).`), { status });
  }
  return result.data;
}
