import { render, screen } from "@testing-library/react";

import { AppShell } from "../AppShell";

test("renders page chrome", () => {
  render(
    <AppShell title="Temple-cat Voice AI Interview">
      <div>Body</div>
    </AppShell>
  );

  expect(
    screen.getByRole("heading", { name: /temple-cat voice ai interview/i })
  ).toBeInTheDocument();
  expect(screen.getByText("Body")).toBeInTheDocument();
});

