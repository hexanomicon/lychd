import { expect, it } from "vitest";
import { inspectionQuery, inspectionSelection, sameInspectionBinding } from "./inspection";
it("requires every exact inspection binding once and preserves it", () => {
  const binding = { source_id: "fixture", source_generation: "gen-1", profile_id: "remote", profile_revision: "2" };
  expect(inspectionSelection(inspectionQuery(binding))).toEqual({ binding });
  expect(inspectionSelection("?source_id=fixture").error).toBeTruthy();
  expect(inspectionSelection(`${inspectionQuery(binding)}&generation=gen-2`).error).toBeTruthy();
  expect(sameInspectionBinding(binding, { ...binding, source_generation: "gen-2" })).toBe(false);
});
