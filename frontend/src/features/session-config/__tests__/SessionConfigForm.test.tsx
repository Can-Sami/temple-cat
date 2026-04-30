import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionConfigForm } from "../SessionConfigForm";

test("renders system prompt and interruptibility inputs", () => {
  render(<SessionConfigForm onSubmit={vi.fn()} />);
  expect(screen.getByLabelText(/System Prompt/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Interruptibility Percentage/i)).toBeInTheDocument();
});

test("submits valid payload including interruptibility percentage", async () => {
  const onSubmit = vi.fn();
  render(<SessionConfigForm onSubmit={onSubmit} />);
  await userEvent.type(screen.getByLabelText(/System Prompt/i), "You are concise");
  const pctInput = screen.getByLabelText(/Interruptibility Percentage/i);
  await userEvent.clear(pctInput);
  await userEvent.type(pctInput, "70");
  await userEvent.click(screen.getByRole("button", { name: /Start Session/i }));
  expect(onSubmit).toHaveBeenCalledWith(
    expect.objectContaining({ interruptibility_percentage: 70 })
  );
});

test("does not submit when system prompt is empty", async () => {
  const onSubmit = vi.fn();
  render(<SessionConfigForm onSubmit={onSubmit} />);
  await userEvent.click(screen.getByRole("button", { name: /Start Session/i }));
  expect(onSubmit).not.toHaveBeenCalled();
});
