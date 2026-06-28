/**
 * Pure logic for the diarized live transcript.
 *
 * The backend emits an RTVI `server-message` per finalized user turn:
 *   { type: "speaker-transcript", speaker: <0-based int>, text: <string>, final: true }
 * Deepgram diarization labels speakers within the single mic stream, so
 * `speaker` 0 / 1 map to "Speaker 1" / "Speaker 2" in the UI.
 */

/** One finalized line in the transcript. */
export interface SpeakerTurn {
  readonly id: string;
  readonly speaker: number;
  readonly text: string;
}

export interface TranscriptState {
  readonly turns: readonly SpeakerTurn[];
  /** Speaker index of the most recent turn, or null before anyone has spoken. */
  readonly currentSpeaker: number | null;
}

/** CSS custom properties for each speaker color (cycles past 3 speakers). */
const SPEAKER_COLOR_VARS = ["--speaker-1", "--speaker-2", "--speaker-3"] as const;

export function emptyTranscript(): TranscriptState {
  return { turns: [], currentSpeaker: null };
}

/** "Speaker 1", "Speaker 2", … (1-based label for a 0-based index). */
export function formatSpeaker(speaker: number): string {
  const n = Number.isFinite(speaker) ? Math.max(0, Math.trunc(speaker)) : 0;
  return `Speaker ${n + 1}`;
}

/** `var(--speaker-N)` for the line/chip color. */
export function speakerColor(speaker: number): string {
  const i = Number.isFinite(speaker) ? Math.max(0, Math.trunc(speaker)) : 0;
  return `var(${SPEAKER_COLOR_VARS[i % SPEAKER_COLOR_VARS.length]})`;
}

/** `var(--speaker-N-subtle)` for the line background tint. */
export function speakerColorSubtle(speaker: number): string {
  const i = Number.isFinite(speaker) ? Math.max(0, Math.trunc(speaker)) : 0;
  return `var(${SPEAKER_COLOR_VARS[i % SPEAKER_COLOR_VARS.length]}-subtle)`;
}

interface ParsedTurn {
  readonly speaker: number;
  readonly text: string;
}

/**
 * Validate an incoming RTVI server-message. Returns the speaker + text for a
 * well-formed, final, non-empty `speaker-transcript`; otherwise null (ignored).
 */
export function parseSpeakerMessage(data: unknown): ParsedTurn | null {
  if (typeof data !== "object" || data === null) {
    return null;
  }
  const msg = data as Record<string, unknown>;
  if (msg.type !== "speaker-transcript" || msg.final === false) {
    return null;
  }
  if (typeof msg.text !== "string") {
    return null;
  }
  const text = msg.text.trim();
  if (text.length === 0) {
    return null;
  }
  const rawSpeaker = msg.speaker;
  const speaker =
    typeof rawSpeaker === "number" && Number.isFinite(rawSpeaker)
      ? Math.max(0, Math.trunc(rawSpeaker))
      : 0;
  return { speaker, text };
}

/**
 * Parse a lightweight `speaker-active` message — the live "who's talking now"
 * signal emitted off interim transcripts (no text). Returns the 0-based speaker
 * index, or null if this isn't a speaker-active message.
 */
export function parseSpeakerActive(data: unknown): number | null {
  if (typeof data !== "object" || data === null) {
    return null;
  }
  const msg = data as Record<string, unknown>;
  if (msg.type !== "speaker-active") {
    return null;
  }
  const raw = msg.speaker;
  return typeof raw === "number" && Number.isFinite(raw) ? Math.max(0, Math.trunc(raw)) : 0;
}

/**
 * Update only the live speaker (for the diarization indicator) without appending
 * a transcript turn. Returns the same state when unchanged so React can skip the
 * re-render.
 */
export function setCurrentSpeaker(state: TranscriptState, speaker: number): TranscriptState {
  if (state.currentSpeaker === speaker) {
    return state;
  }
  return { ...state, currentSpeaker: speaker };
}

/** Append a finalized turn, tracking who spoke last. Returns a new state (immutable). */
export function appendTurn(state: TranscriptState, parsed: ParsedTurn): TranscriptState {
  const turn: SpeakerTurn = {
    id: `turn-${state.turns.length}`,
    speaker: parsed.speaker,
    text: parsed.text,
  };
  return {
    turns: [...state.turns, turn],
    currentSpeaker: parsed.speaker,
  };
}
