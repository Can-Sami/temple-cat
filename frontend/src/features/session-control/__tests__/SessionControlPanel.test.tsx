import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionControlPanel } from "../SessionControlPanel";

test("shows Start Session button when inactive", () => {
  render(<SessionControlPanel isActive={false} onStart={vi.fn()} onStop={vi.fn()} />);
  expect(screen.getByRole("button", { name: /Start Session/i })).toBeInTheDocument();
});

test("shows Stop Session button when active", () => {
  render(<SessionControlPanel isActive={true} onStart={vi.fn()} onStop={vi.fn()} />);
  expect(screen.getByRole("button", { name: /Stop Session/i })).toBeInTheDocument();
});

test("calls onStop when Stop Session is clicked", async () => {
  const onStop = vi.fn();
  render(<SessionControlPanel isActive={true} onStart={vi.fn()} onStop={onStop} />);
  await userEvent.click(screen.getByRole("button", { name: /Stop Session/i }));
  expect(onStop).toHaveBeenCalledTimes(1);
});

test("calls onStart when Start Session is clicked", async () => {
  const onStart = vi.fn();
  render(<SessionControlPanel isActive={false} onStart={onStart} onStop={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: /Start Session/i }));
  expect(onStart).toHaveBeenCalledTimes(1);
});
