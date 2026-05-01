import type { SessionConfigPayload } from "@/features/session-config/SessionConfigForm";
import { ApiError, formatApiErrorBody } from "@/lib/api/http";

export interface VoiceSessionCredentials {
  session_id: string;
  room_url: string;
  token: string;
}

export async function createVoiceSession(
  payload: SessionConfigPayload
): Promise<VoiceSessionCredentials> {
  const response = await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const msg =
      formatApiErrorBody(body) ||
      `Request failed (${response.status} ${response.statusText})`;
    throw new ApiError(msg, response.status, body);
  }

  const rec = body as Partial<VoiceSessionCredentials>;
  if (
    typeof rec.session_id !== "string" ||
    typeof rec.room_url !== "string" ||
    typeof rec.token !== "string"
  ) {
    throw new ApiError("Invalid session response from server", response.status, body);
  }

  return {
    session_id: rec.session_id,
    room_url: rec.room_url,
    token: rec.token,
  };
}
