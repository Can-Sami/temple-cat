import { describe, expect, it } from "vitest";

import {
  appendTurn,
  emptyTranscript,
  formatSpeaker,
  parseSpeakerActive,
  parseSpeakerMessage,
  setCurrentSpeaker,
  speakerColor,
} from "../speakerTranscript";

describe("formatSpeaker", () => {
  it("maps a 0-based index to a 1-based label", () => {
    expect(formatSpeaker(0)).toBe("Speaker 1");
    expect(formatSpeaker(1)).toBe("Speaker 2");
  });

  it("clamps invalid input to Speaker 1", () => {
    expect(formatSpeaker(-3)).toBe("Speaker 1");
    expect(formatSpeaker(Number.NaN)).toBe("Speaker 1");
  });
});

describe("speakerColor", () => {
  it("returns distinct vars for speaker 0 and 1", () => {
    expect(speakerColor(0)).toBe("var(--speaker-1)");
    expect(speakerColor(1)).toBe("var(--speaker-2)");
  });

  it("cycles the palette past the third speaker", () => {
    expect(speakerColor(3)).toBe(speakerColor(0));
  });
});

describe("parseSpeakerMessage", () => {
  it("accepts a well-formed final message", () => {
    expect(
      parseSpeakerMessage({ type: "speaker-transcript", speaker: 1, text: "hello", final: true })
    ).toEqual({ speaker: 1, text: "hello" });
  });

  it("trims text and defaults a missing speaker to 0", () => {
    expect(
      parseSpeakerMessage({ type: "speaker-transcript", text: "  hi  ", final: true })
    ).toEqual({ speaker: 0, text: "hi" });
  });

  it.each([
    ["wrong type", { type: "metrics", speaker: 0, text: "x", final: true }],
    ["explicitly non-final", { type: "speaker-transcript", speaker: 0, text: "x", final: false }],
    ["empty text", { type: "speaker-transcript", speaker: 0, text: "   ", final: true }],
    ["non-string text", { type: "speaker-transcript", speaker: 0, text: 5, final: true }],
    ["not an object", "speaker-transcript"],
    ["null", null],
  ])("ignores %s", (_label, input) => {
    expect(parseSpeakerMessage(input)).toBeNull();
  });
});

describe("parseSpeakerActive", () => {
  it("reads the live speaker off a speaker-active message", () => {
    expect(parseSpeakerActive({ type: "speaker-active", speaker: 1 })).toBe(1);
    expect(parseSpeakerActive({ type: "speaker-active", speaker: 0 })).toBe(0);
  });

  it("defaults a missing or invalid speaker to 0", () => {
    expect(parseSpeakerActive({ type: "speaker-active" })).toBe(0);
    expect(parseSpeakerActive({ type: "speaker-active", speaker: -2 })).toBe(0);
    expect(parseSpeakerActive({ type: "speaker-active", speaker: Number.NaN })).toBe(0);
  });

  it.each([
    ["wrong type", { type: "speaker-transcript", speaker: 0, text: "x", final: true }],
    ["not an object", "speaker-active"],
    ["null", null],
  ])("ignores %s", (_label, input) => {
    expect(parseSpeakerActive(input)).toBeNull();
  });
});

describe("setCurrentSpeaker", () => {
  it("updates currentSpeaker live without appending a turn", () => {
    const s = appendTurn(emptyTranscript(), { speaker: 0, text: "hi" });
    const s2 = setCurrentSpeaker(s, 1);
    expect(s2.currentSpeaker).toBe(1);
    expect(s2.turns).toBe(s.turns); // turns untouched
  });

  it("returns the same state when the speaker is unchanged", () => {
    const s = setCurrentSpeaker(emptyTranscript(), 0);
    expect(setCurrentSpeaker(s, 0)).toBe(s);
  });
});

describe("appendTurn", () => {
  it("appends turns immutably and tracks the current speaker", () => {
    const s0 = emptyTranscript();
    expect(s0.currentSpeaker).toBeNull();

    const s1 = appendTurn(s0, { speaker: 0, text: "first" });
    expect(s0.turns).toHaveLength(0); // original untouched
    expect(s1.turns).toHaveLength(1);
    expect(s1.currentSpeaker).toBe(0);

    const s2 = appendTurn(s1, { speaker: 1, text: "second" });
    expect(s2.turns.map((t) => t.text)).toEqual(["first", "second"]);
    expect(s2.turns.map((t) => t.id)).toEqual(["turn-0", "turn-1"]);
    expect(s2.currentSpeaker).toBe(1);
  });
});
