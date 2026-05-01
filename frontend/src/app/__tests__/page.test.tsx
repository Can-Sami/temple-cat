import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import Page from "../page";
import { QueryProvider } from "@/providers/query-provider";

vi.mock("@pipecat-ai/daily-transport", () => ({
  DailyTransport: function DailyTransport() {},
}));

vi.mock("@pipecat-ai/client-js", () => {
  class PipecatClient {
    setLogLevel = vi.fn();
    connect = vi.fn();
    disconnect = vi.fn();
  }

  const RTVIEvent = {
    BotStartedSpeaking: "BotStartedSpeaking",
    BotStoppedSpeaking: "BotStoppedSpeaking",
    UserStartedSpeaking: "UserStartedSpeaking",
    UserStoppedSpeaking: "UserStoppedSpeaking",
    Disconnected: "Disconnected",
  };

  const LogLevel = { INFO: "INFO" };

  return { PipecatClient, RTVIEvent, LogLevel };
});

vi.mock("@pipecat-ai/client-react", () => ({
  PipecatClientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  PipecatClientAudio: () => null,
  usePipecatClient: () => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  }),
  useRTVIClientEvent: () => {},
}));

describe("Home page", () => {
  test("shows configure session headline", async () => {
    render(
      <QueryProvider>
        <Page />
      </QueryProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Configure Session/i)).toBeInTheDocument();
    });
  });
});
