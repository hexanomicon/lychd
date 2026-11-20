const glyphs: Record<string, string> = {
  catalogue: "▤",
  project: "◇",
  séance: "◉",
  "source turn": "❞",
  run: "▷",
  reference: "↗",
  concern: "?",
  decision: "◆",
  assessment: "⊙",
  "working material": "✎",
  recall: "◎",
  "public note": "▧",
};
export function atlasGlyph(kind: string) {
  return glyphs[kind] ?? "·";
}
