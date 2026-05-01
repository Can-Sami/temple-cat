import { Badge } from "@/components/ui/badge";

import type { BotState } from "./voiceBotState";

export type { BotState };

interface Props {
  state: BotState;
}

export function BotStateBadge({ state }: Props) {
  const variant =
    state === "Speaking"
      ? "default"
      : state === "Thinking"
        ? "secondary"
        : state === "Interrupted"
          ? "destructive"
          : "outline";

  return (
    <Badge
      aria-label={state === "Interrupted" ? "Bot State: interrupted — you spoke over the bot" : "Bot State"}
      aria-live={state === "Interrupted" ? "assertive" : "polite"}
      variant={variant}
    >
      {state}
    </Badge>
  );
}
