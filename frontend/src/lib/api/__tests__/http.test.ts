import { describe, expect, test } from "vitest";

import { formatApiErrorBody } from "@/lib/api/http";

describe("formatApiErrorBody", () => {
  test("reads string detail", () => {
    expect(formatApiErrorBody({ detail: "oops" })).toBe("oops");
  });

  test("joins validation detail array", () => {
    expect(
      formatApiErrorBody({
        detail: [{ msg: "too short" }, { msg: "bad field" }],
      })
    ).toBe("too short; bad field");
  });

  test("reads structured error message when detail is absent", () => {
    expect(
      formatApiErrorBody({
        error: "bot_startup_failed",
        message: "Voice bot failed to start.",
      })
    ).toBe("Voice bot failed to start.");
  });
});
