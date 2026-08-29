import type { DraftResponse } from "./types";

export function formatLetter(letter: DraftResponse): string {
  return [
    letter.salutation,
    ...letter.paragraphs.map((paragraph) => paragraph.prose),
    letter.sign_off,
    letter.candidate_name,
  ].join("\n\n");
}
