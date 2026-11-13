import { afterEach, expect, it, vi } from "vitest";
import { runtimeSnapshot } from "$lib/pages/orb/state/__fixtures__/runtime";
afterEach(() => { vi.unstubAllGlobals(); vi.resetModules(); });
it("uses the independent read endpoint and preserves authorization refusal", async () => {
  const NativeRequest = globalThis.Request;
  vi.stubGlobal("Request", class extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) { super(typeof input === "string" ? new URL(input, "http://localhost") : input, init); }
  });
  const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(runtimeSnapshot()), { headers: { "Content-Type": "application/json" } }))
    .mockResolvedValueOnce(new Response("{}", { status: 403, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetch);
  const { getOrbRuntime } = await import("./orb-runtime");
  const signal = new AbortController().signal;
  expect((await getOrbRuntime(signal)).components).toHaveLength(3);
  const request = fetch.mock.calls[0]![0] as Request;
  expect(request.url).toContain("/api/v1/orb/runtime");
  expect(request.method).toBe("GET");
  await expect(getOrbRuntime()).rejects.toMatchObject({ status: 403 });
});
