import { describe, expect, it } from "vitest";
import { boundedDockWidth, defaultDockLayout, parseDockLayout } from "./dock";

describe("Bridge layout preferences", () => {
  it("bounds width and ignores stored content or authority fields", () => {
    expect(parseDockLayout(JSON.stringify({ width: 9999, side: "left", open: false, draft: "private", sessionId: "session-b", consent: "approve" })))
      .toEqual({ width: 720, side: "left", open: false });
    expect(boundedDockWidth(-90)).toBe(320);
  });
  it.each([null, "invalid", "null", "[]", '{"width":"700","side":"elsewhere","open":"yes"}'])("uses safe defaults for %s", (raw) => {
    expect(parseDockLayout(raw)).toEqual(defaultDockLayout);
  });
});
