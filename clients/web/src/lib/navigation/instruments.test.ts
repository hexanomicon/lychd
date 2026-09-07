import { describe, expect, it } from "vitest";
import { bridgeRunHref, loomOriginHref, orbReturnHref, selectedOrbHref } from "./instruments";

describe("instrument navigation hints", () => {
  it("preserves bounded selection without admitting foreign routes or query authority", () => {
    expect(selectedOrbHref("/altar/orb/run-a", "?event=event-a&job=job-a&redirect=https://elsewhere.test", "/altar/orb"))
      .toBe("/orb/run-a?event=event-a&job=job-a");
    for (const path of ["/orb", "//elsewhere/orb/run-a", "/orb/../bridge", "/orb/run-a/extra", "/orb/%2Fbridge", "/orb/%E0%A4", `/orb/${"a".repeat(129)}`]) {
      expect(selectedOrbHref(path, "?event=event-a")).toBeNull();
    }
    expect(selectedOrbHref("/orb/run-a", `?event=${"a".repeat(129)}`)).toBe("/orb/run-a");
  });

  it("carries one Run and event through an exact Pattern and back", () => {
    const target = loomOriginHref("/loom/bridge_chat/1?run=wrong", "run-a", "?event=event-a&job=job-a");
    expect(target).toBe("/loom/bridge_chat/1?run=run-a&event=event-a&job=job-a");
    expect(orbReturnHref("run-a", new URL(target!, "http://localhost").search))
      .toBe("/orb/run-a?event=event-a&job=job-a");
    expect(loomOriginHref("https://elsewhere/loom/p/1", "run-a")).toBeNull();
    expect(bridgeRunHref("/bridge/session-a", "run-a")).toBe("/bridge/session-a?run=run-a");
    expect(bridgeRunHref("//elsewhere/bridge/session-a", "run-a")).toBeNull();
  });
});
