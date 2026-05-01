import { Badge, badgeVariants } from "@/components/ui/badge";
import type { VariantProps } from "class-variance-authority";

export type { BotState } from "./voiceBotState";

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

function badgeVariantForState(state: import("./voiceBotState").BotState): BadgeVariant {
  if (state === "Speaking") {
    return "default";
  }
  if (state === "Thinking") {
    return "secondary";
  }
  if (state === "Interrupted") {
    return "destructive";
  }
  return "outline";
}

interface Props {
  readonly state: import("./voiceBotState").BotState;
}

export function BotStateBadge({ state }: Props) {
  const variant = badgeVariantForState(state);

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
