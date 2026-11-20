import { describe, expect, it } from "vitest";
import {
  exampleDisposition,
  type EvidenceCase,
  type LookupPermission,
  type ProbeAllowance,
} from "./affect-example";

describe("worked receipt inquiry", () => {
  it.each<[EvidenceCase, ProbeAllowance, LookupPermission, string]>([
    ["key", "one", "permitted", "probe"],
    ["key", "one", "needs_review", "review"],
    ["key", "spent", "permitted", "stop"],
    ["key", "spent", "needs_review", "stop"],
    ["repeat", "one", "permitted", "stop"],
    ["conflict", "one", "permitted", "review"],
    ["confirmed", "one", "permitted", "stop"],
  ])("projects %s with allowance %s and permission %s as %s", (evidence, budget, permission, expected) => {
    expect(exampleDisposition(evidence, budget, permission).kind).toBe(expected);
  });
});
