import { describe, expect, test } from "vitest";

import { botStateOnUserStartedSpeaking, shouldStartThinkingOnUserStopped } from "../voiceBotState";

describe("botStateOnUserStartedSpeaking", () => {
  test("shows Interrupted when bot audio is active", () => {
    expect(botStateOnUserStartedSpeaking(true)).toBe("Interrupted");
  });

  test("shows Listening when bot is not speaking", () => {
    expect(botStateOnUserStartedSpeaking(false)).toBe("Listening");
  });
});

describe("shouldStartThinkingOnUserStopped", () => {
  test("does not enter Thinking while bot audio is active", () => {
    expect(shouldStartThinkingOnUserStopped(true)).toBe(false);
  });

  test("enters Thinking only when bot is silent", () => {
    expect(shouldStartThinkingOnUserStopped(false)).toBe(true);
  });
});
