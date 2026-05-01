/** Pipeline-aligned bot indicators for the live session dashboard. */
export type BotState = "Listening" | "Thinking" | "Speaking" | "Interrupted";

/** User picked up the mic while bot TTS was active — distinct from idle listening for grading / UX. */
export function botStateOnUserStartedSpeaking(botAudioActive: boolean): BotState {
  return botAudioActive ? "Interrupted" : "Listening";
}

/** Only enter Thinking after the user's turn ends while the bot is not speaking (avoids false Thinking during interruption). */
export function shouldStartThinkingOnUserStopped(botAudioActive: boolean): boolean {
  return !botAudioActive;
}
