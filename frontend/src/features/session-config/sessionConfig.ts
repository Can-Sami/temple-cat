/**
 * Session config for the diarization demo. The voice bot still needs a valid
 * SessionConfig, but none of it is worth a form here — the demo is about the
 * live speaker labels, so we start with sensible Turkish defaults in one click.
 */
export interface SessionConfigPayload {
  system_prompt: string;
  llm_temperature: number;
  llm_max_tokens: number;
  stt_temperature: number;
  tts_voice: string;
  tts_speed: number;
  tts_temperature: number;
  interruptibility_percentage: number;
}

export const DEFAULT_SESSION_CONFIG: SessionConfigPayload = {
  system_prompt: "Sen yardımcı bir sesli asistansın. Kısa, net ve doğal Türkçe konuş.",
  llm_temperature: 0.7,
  llm_max_tokens: 256,
  stt_temperature: 0,
  tts_voice: "leyla",
  tts_speed: 1,
  tts_temperature: 0.3,
  interruptibility_percentage: 70,
};
