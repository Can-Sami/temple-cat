import { Badge } from "@/components/ui/badge";

export type BotState = "Listening" | "Thinking" | "Speaking";

interface Props {
  state: BotState;
}

export function BotStateBadge({ state }: Props) {
  const variant =
    state === "Speaking"
      ? "default"
      : state === "Thinking"
        ? "secondary"
        : "outline";

  return (
    <Badge aria-label="Bot State" aria-live="polite" variant={variant}>
      {state}
    </Badge>
  );
}
