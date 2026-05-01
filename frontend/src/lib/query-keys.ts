/** Central query keys for voice session server state (TanStack Query). */

export const voiceSessionKeys = {
  all: ["voice-session"] as const,
  credentials: () => [...voiceSessionKeys.all, "credentials"] as const,
};
