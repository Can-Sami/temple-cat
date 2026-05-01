import { render, screen } from "@testing-library/react";
import { BotStateBadge } from "../BotStateBadge";
import { LatencyPanel } from "../LatencyPanel";

test("renders speaking state", () => {
  render(<BotStateBadge state="Speaking" />);
  expect(screen.getByText(/Speaking/i)).toBeInTheDocument();
});

test("renders listening state", () => {
  render(<BotStateBadge state="Listening" />);
  expect(screen.getByText(/Listening/i)).toBeInTheDocument();
});

test("renders thinking state", () => {
  render(<BotStateBadge state="Thinking" />);
  expect(screen.getByText(/Thinking/i)).toBeInTheDocument();
});

test("renders interrupted state", () => {
  render(<BotStateBadge state="Interrupted" />);
  expect(screen.getByText(/Interrupted/i)).toBeInTheDocument();
});

test("renders backend TTFB and wall-clock latency", () => {
  render(<LatencyPanel backendTtsTtfbMs={120} wallClockLatencyMs={245} />);
  expect(screen.getByText(/120 ms \(bot TTS TTFB\)/i)).toBeInTheDocument();
  expect(screen.getByText(/245 ms wall-clock/i)).toBeInTheDocument();
});

test("renders awaiting metrics when backend TTFB missing", () => {
  render(<LatencyPanel backendTtsTtfbMs={null} wallClockLatencyMs={0} />);
  expect(screen.getByText(/awaiting metrics/i)).toBeInTheDocument();
});
