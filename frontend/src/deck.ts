// The deck values mirror the server canonical deck in
// backend/app/services.py (DECK). Display labels are derived here, so the
// landing strip and the room can never disagree on a value (V4).
export const DECK = ["0", "1", "2", "3", "5", "8", "13", "21", "?", "pass"];

export function cardLabel(value: string): string {
  return value === "pass" ? "Pass" : value;
}
