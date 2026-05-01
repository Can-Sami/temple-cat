import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { createVoiceSession } from "@/lib/api/sessions";
import { ApiError } from "@/lib/api/http";

const payload = {
  system_prompt: "You are helpful.",
  llm_temperature: 0.7,
  llm_max_tokens: 256,
  stt_temperature: 0,
  tts_voice: "sonic",
  tts_speed: 1,
  tts_temperature: 0.3,
  interruptibility_percentage: 70,
};

describe("createVoiceSession", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("returns credentials on success", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        session_id: "sid",
        room_url: "https://daily.example/room",
        token: "tok",
      }),
    });

    const result = await createVoiceSession(payload);
    expect(result).toEqual({
      session_id: "sid",
      room_url: "https://daily.example/room",
      token: "tok",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sessions",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  test("throws ApiError with parsed FastAPI detail", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: "Unprocessable",
      json: async () => ({ detail: "invalid config" }),
    });

    await expect(createVoiceSession(payload)).rejects.toMatchObject({
      name: "ApiError",
      message: "invalid config",
      status: 422,
    });
  });

  test("throws ApiError when response shape is wrong", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ session_id: "only-id" }),
    });

    await expect(createVoiceSession(payload)).rejects.toBeInstanceOf(ApiError);
  });
});
