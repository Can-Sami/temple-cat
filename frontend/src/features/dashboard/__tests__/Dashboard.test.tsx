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

test("renders latency value in ms", () => {
  render(<LatencyPanel latencyMs={245} />);
  expect(screen.getByText(/245 ms/i)).toBeInTheDocument();
});

test("renders zero latency", () => {
  render(<LatencyPanel latencyMs={0} />);
  expect(screen.getByText(/0 ms/i)).toBeInTheDocument();
});
