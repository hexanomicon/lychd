/**
 * Canvas ink colour is persisted Project data, so the stored value never changes with the
 * Altar appearance. The default ink is one fixed value in that data; the board paints it with
 * the active theme's ink role so default strokes stay legible on every work plane. Any other
 * stored colour renders exactly as recorded.
 */
export const DEFAULT_INK = "#eef1f4";

export function inkPaint(color: string): string {
  return color.toLowerCase() === DEFAULT_INK ? "var(--color-ink-default)" : color;
}
