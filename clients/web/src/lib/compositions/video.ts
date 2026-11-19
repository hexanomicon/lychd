export const recipes = {
  "illustrated-story": "Illustrated story",
  "animated-lesson": "Animated lesson",
  "captioned-excerpt": "Captioned excerpt",
} as const;
export type Recipe = keyof typeof recipes;
