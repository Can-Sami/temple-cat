import { cn } from "@/lib/utils";

import type { BotState } from "./voiceBotState";

export type { BotState } from "./voiceBotState";

/** Dot color per bot state — kept off the speaker palette so the two never read as the same thing. */
const DOT_CLASS: Record<BotState, string> = {
  Listening: "bg-muted-foreground",
  Thinking: "bg-brand animate-pulse",
  Speaking: "bg-success",
  Interrupted: "bg-destructive",
};

interface Props {
  readonly state: BotState;
}

export function BotStateBadge({ state }: Props) {
  return (
    <span
      aria-label={
        state === "Interrupted"
          ? "Bot state: interrupted — you spoke over the bot"
          : "Bot state"
      }
      aria-live={state === "Interrupted" ? "assertive" : "polite"}
      className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary/60 px-3 py-1 text-sm font-medium text-foreground"
    >
      <span className={cn("h-2 w-2 shrink-0 rounded-full", DOT_CLASS[state])} />
      {state}
    </span>
  );
}
