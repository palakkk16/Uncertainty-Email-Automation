export const MAX_MESSAGE_LENGTH = 4000;

/**
 * POST /chat is stateless and copy-only: a field survives only when its
 * text appears in that one string. Follow-up answers have to be joined
 * onto earlier user turns, or the next slot is invisible to the threshold.
 * Assistant text stays out so a question is not copied back as a field.
 * The API rejects more than 4000 characters instead of truncating.
 */
export function stitchUserTurns(turns: readonly string[]): string {
  return turns
    .map((turn) => turn.trim())
    .filter((turn) => turn.length > 0)
    .join("\n");
}

export function exceedsMessageCap(turns: readonly string[]): boolean {
  return stitchUserTurns(turns).length > MAX_MESSAGE_LENGTH;
}
