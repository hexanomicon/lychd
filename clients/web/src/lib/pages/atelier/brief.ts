/** Local editor for the text-only ShortVideoBrief wire document. The receiver validates its own copy. */
export const recipes = {
  "illustrated-story": "Illustrated story",
  "animated-lesson": "Animated lesson",
  "captioned-excerpt": "Captioned excerpt",
} as const;
export type Recipe = keyof typeof recipes;
export type Brief = {
  recipe: Recipe;
  script: string;
  duration_seconds: number;
  not_before?: string;
  latest_start_at?: string;
};
export const wireBytes = 8192;

export function sampleBrief(): Brief {
  return {
    recipe: "illustrated-story",
    duration_seconds: 12,
    script: "The last light crosses the ridge.\nThe observatory dome opens.\nThe first star appears.",
  };
}

function utcKey(value: unknown): string {
  if (typeof value !== "string") throw new Error("Enter both UTC bounds as timestamps with seconds.");
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(?:Z|\+00:00)$/.exec(value);
  if (!match || value.startsWith("0000")) throw new Error("Use UTC dates with seconds and Z or +00:00.");
  const stamp = match[1]!;
  const calendar = new Date(stamp + "Z");
  if (!Number.isFinite(calendar.getTime()) || calendar.toISOString().slice(0, 19) !== stamp) {
    throw new Error("Enter a real UTC date and time.");
  }
  return stamp + (match[2] ?? "").padEnd(6, "0");
}

export function validateBrief(input: unknown): Brief {
  if (!input || typeof input !== "object" || Array.isArray(input))
    throw new Error("A brief must be a JSON object.");
  const fields = input as Record<string, unknown>;
  const allowed = ["recipe", "script", "duration_seconds", "not_before", "latest_start_at"];
  if (Object.keys(fields).some((key) => !allowed.includes(key)))
    throw new Error("Remove unsupported fields from the brief.");
  const { recipe, script, duration_seconds, not_before, latest_start_at } = fields;
  if (typeof recipe !== "string" || !Object.hasOwn(recipes, recipe))
    throw new Error("Choose one of the three short-video recipes.");
  if (
    typeof script !== "string" ||
    !script.replace(/[\p{White_Space}\u001c-\u001f]/gu, "") ||
    !script.isWellFormed()
  )
    throw new Error("Enter a script with readable Unicode text.");
  if (Array.from(script).length > 8000) throw new Error("The script exceeds 8,000 characters.");
  if (
    typeof duration_seconds !== "number" ||
    !Number.isInteger(duration_seconds) ||
    duration_seconds < 1 ||
    duration_seconds > 180
  ) {
    throw new Error("Request a whole duration from 1 to 180 seconds.");
  }
  const result: Brief = { recipe: recipe as Recipe, script, duration_seconds };
  if (Object.hasOwn(fields, "not_before") || Object.hasOwn(fields, "latest_start_at")) {
    const first = utcKey(not_before),
      last = utcKey(latest_start_at);
    if (first >= last) throw new Error("The latest start must be later than the opening UTC time.");
    result.not_before = not_before as string;
    result.latest_start_at = latest_start_at as string;
  }
  if (new TextEncoder().encode(JSON.stringify(result)).length > wireBytes)
    throw new Error("The brief exceeds 8,192 UTF-8 bytes.");
  return result;
}

export function decodeBrief(text: string): Brief {
  if (new TextEncoder().encode(text).length > wireBytes)
    throw new Error("The file exceeds 8,192 UTF-8 bytes.");
  let decoded: unknown;
  try {
    decoded = JSON.parse(text);
  } catch {
    throw new Error("The file contains invalid JSON.");
  }
  // JSON.parse collapses duplicate keys and normalizes 1.0 to 1. Check the original flat wire tokens.
  const names = new Set<string>();
  for (const token of text.matchAll(/"(?:\\[\s\S]|[^"\\])*"/g)) {
    const rest = text.slice(token.index + token[0].length);
    if (!/^\s*:/.test(rest)) continue;
    const key: string = JSON.parse(token[0]);
    if (names.has(key)) throw new Error("Duplicate brief field.");
    names.add(key);
    if (key === "duration_seconds" && !/^\s*:\s*-?(?:0|[1-9]\d*)\s*[,}]/.test(rest)) {
      throw new Error("Duration must be a JSON integer.");
    }
  }
  return validateBrief(decoded);
}

export function timecode(seconds: number) {
  const frames = Math.max(0, Math.floor((Number.isFinite(seconds) ? seconds : 0) * 30 + 0.000001));
  return [
    Math.floor(frames / 108000),
    Math.floor(frames / 1800) % 60,
    Math.floor(frames / 30) % 60,
    frames % 30,
  ]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}
