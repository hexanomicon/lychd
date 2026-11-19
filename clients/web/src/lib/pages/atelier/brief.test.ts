import { expect, it } from "vitest";
import { decodeBrief, recipes, sampleBrief, timecode, validateBrief } from "./brief";

it("round-trips all three recipes and preserves exact Unicode script and UTC microseconds", () => {
  for (const recipe of Object.keys(recipes)) {
    const input = {
      ...sampleBrief(),
      recipe,
      script: '  A scope, "recipe": and 🌒.  ',
      not_before: "2026-11-19T18:00:00.000001Z",
      latest_start_at: "2026-11-19T18:00:00.000002+00:00",
    };
    expect(decodeBrief(JSON.stringify(input))).toEqual(input);
  }
  expect(validateBrief(sampleBrief())).not.toHaveProperty("not_before");
  expect(timecode(5.4)).toBe("00:00:05:12");
});

it.each([
  { duration_seconds: 0 },
  { duration_seconds: 181 },
  { duration_seconds: 2.2 },
  { duration_seconds: true },
  { script: "\u0085\n" },
  { script: "a".repeat(8001) },
  { script: "🌒".repeat(2200) },
  { script: "\ud800" },
  { recipe: "new-recipe" },
  { url: "https://example.com" },
  { not_before: null, latest_start_at: null },
  { not_before: "2026-11-19T18:00:00Z" },
  { latest_start_at: "2026-11-19T18:00:00Z" },
  { not_before: "2026-02-31T00:00:00Z", latest_start_at: "2026-04-02T00:00:00Z" },
  { not_before: "2026-11-19T00:00:00+01:00", latest_start_at: "2026-11-19T02:00:00Z" },
  { not_before: "2026-11-19T00:00:00.21Z", latest_start_at: "2026-11-19T00:00:00.210000Z" },
])("refuses unsupported wire fields or limits (%#)", (patch) => {
  expect(() => validateBrief({ ...sampleBrief(), ...patch })).toThrow();
});
it("rejects duplicates after resolving JSON string escapes and refuses floating JSON duration tokens", () => {
  const base = '{"recipe":"animated-lesson","script":"orbit","duration_seconds":12}';
  expect(() => decodeBrief(base.slice(0, -1) + ',"scr\\u0069pt":"replacement"}')).toThrow("Duplicate");
  expect(() => decodeBrief(base.replace("12}", "1.2e1}"))).toThrow("integer");
  expect(() => decodeBrief(base.padEnd(8193, " "))).toThrow("8,192");
  expect(decodeBrief(base.replace("12}", "180}")).duration_seconds).toBe(180);
});
