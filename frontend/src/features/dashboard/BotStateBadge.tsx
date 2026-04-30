export type BotState = "Listening" | "Thinking" | "Speaking";

interface Props {
  state: BotState;
}

export function BotStateBadge({ state }: Props) {
  return (
    <div aria-label="Bot State" aria-live="polite">
      {state}
    </div>
  );
}
