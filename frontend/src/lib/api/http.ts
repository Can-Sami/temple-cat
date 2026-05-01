export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

/** Parse FastAPI-style `{ detail: ... }` or string bodies into a short message. */
export function formatApiErrorBody(body: unknown): string | null {
  if (body == null) return null;
  if (typeof body === "string" && body.trim()) return body.trim();
  if (typeof body !== "object") return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => {
        if (typeof d === "object" && d !== null && "msg" in d)
          return String((d as { msg: string }).msg);
        return String(d);
      })
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }

  const message = (body as { message?: unknown }).message;
  if (typeof message === "string" && message.trim()) return message.trim();

  return null;
}
