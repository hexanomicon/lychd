import { describe, expect, it } from "vitest";
import { accentOptions, defaultAccent, parseAppearance, serializeAppearance } from "./preferences";

describe("bounded appearance preference", () => {
  it("retains only a supported, versioned decorative accent", () => {
    for (const option of accentOptions) expect(parseAppearance(serializeAppearance(option.id))).toBe(option.id);
  });
  it.each([
    null, "", "{", "[]", "null", "true", '"iris"',
    '{"version":2,"accent":"iris"}', '{"version":"1","accent":"iris"}',
    '{"version":1,"accent":"url(https://example.test/image)"}',
    '{"version":1,"accent":"iris","css":"display:none"}',
    '{"accent":"iris"}', '{"version":1,"accent":{}}', " ".repeat(129)
  ])("falls back safely for unsupported data %s", (raw) => {
    expect(parseAppearance(raw)).toBe(defaultAccent);
  });
  it("keeps every supported accent legible as text against each canonical work surface", () => {
    function luminance(hex: string) {
      const channels = [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16) / 255)
        .map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
      return channels[0]! * 0.2126 + channels[1]! * 0.7152 + channels[2]! * 0.0722;
    }
    for (const option of accentOptions) {
      for (const surface of ["#000000", "#0d0f12", "#171a1f", "#24272e"]) {
        expect((luminance(option.color) + 0.05) / (luminance(surface) + 0.05)).toBeGreaterThanOrEqual(4.5);
      }
    }
  });
});
