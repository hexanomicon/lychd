import { describe, expect, it } from "vitest";
import { captionTrack, frameAt } from "./cut";

describe("Atelier caption timing", () => {
  it("reads 30 fps timecode and refuses out-of-range frames", () => {
    expect(frameAt("00:00:05:12")).toBe(162);
    expect(frameAt("00:00:05:30")).toBeNull();
  });

  it("exports the exact shared edit and escaped caption text", () => {
    expect(captionTrack(["Ridge & dome", "<Dusk>"], [0, 162, 360])).toBe(
      "WEBVTT\n\n1\n00:00:00.000 --> 00:00:05.400\nRidge &amp; dome\n\n2\n00:00:05.400 --> 00:00:12.000\n&lt;Dusk&gt;\n",
    );
  });
});
