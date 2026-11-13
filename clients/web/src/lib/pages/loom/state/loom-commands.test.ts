import { expect, it } from "vitest";
import { parseLoomCommand } from "./loom-commands";

const stations = [
  { key: "Compose", label: "Compose reply" },
  { key: "wait", label: "Await input" },
  { key: "other", label: "Await input" }
];
it("resolves exact case-sensitive keys before normalized labels", () => {
  expect(parseLoomCommand("inspect Compose", stations)).toEqual({ kind: "station", action: "inspect", key: "Compose" });
  expect(parseLoomCommand("Focus COMPOSE   reply", stations)).toEqual({ kind: "station", action: "focus", key: "Compose" });
  expect(parseLoomCommand("inspect compose", stations).kind).toBe("unsupported");
  expect(parseLoomCommand("inspect wait", stations)).toMatchObject({ key: "wait" });
});
it("rejects ambiguity, prefixes, mixed instructions, and unsupported grammar", () => {
  for (const text of ["inspect Await input", "focus Comp", "inspect wait; execute", "next station", "show stations and publish"]) {
    expect(parseLoomCommand(text, stations).kind).toBe("unsupported");
  }
});
it("distinguishes read-only refusals from unmatched station and unknown commands", () => {
  expect(parseLoomCommand("publish pattern", stations)).toMatchObject({ summary: expect.stringContaining("read-only") });
  expect(parseLoomCommand("inspect missing", stations)).toMatchObject({ summary: expect.stringContaining("No exact station") });
  expect(parseLoomCommand("dance", stations)).toMatchObject({ summary: expect.stringContaining("deterministic English") });
});
it("accepts only the two whole-view commands without a station", () => {
  expect(parseLoomCommand("show pattern", [])).toEqual({ kind: "level", level: "pattern" });
  expect(parseLoomCommand("SHOW STATIONS", [])).toEqual({ kind: "level", level: "stations" });
  expect(parseLoomCommand("inspect wait", []).kind).toBe("unsupported");
});
