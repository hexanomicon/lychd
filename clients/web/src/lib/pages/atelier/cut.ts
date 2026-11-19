import { timecode } from "./brief";

export function frameAt(time: string): number | null {
  const parts = /^(\d{2}):([0-5]\d):([0-5]\d):([0-2]\d)$/.exec(time.trim());
  return parts
    ? ((Number(parts[1]) * 60 + Number(parts[2])) * 60 + Number(parts[3])) * 30 + Number(parts[4])
    : null;
}

export function captionTrack(lines: string[], bounds: number[]): string {
  const timestamp = (frame: number) => {
    const ms = Math.round((frame * 1000) / 30);
    return timecode(frame / 30).slice(0, 8) + "." + String(ms % 1000).padStart(3, "0");
  };
  return (
    "WEBVTT\n\n" +
    lines
      .map(
        (line, index) =>
          `${index + 1}\n${timestamp(bounds[index]!)} --> ${timestamp(bounds[index + 1]!)}\n${line.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")}\n`,
      )
      .join("\n")
  );
}
