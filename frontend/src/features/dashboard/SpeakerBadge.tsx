"use client";

import * as React from "react";

import { formatSpeaker, speakerColor, speakerColorSubtle } from "./speakerTranscript";

interface Props {
  /** Current speaker index from diarization, or null before anyone has spoken. */
  readonly speaker: number | null;
}

/** Pill showing who's talking now, tinted with that speaker's color. */
export function SpeakerBadge({ speaker }: Props) {
  if (speaker === null) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-dashed border-border px-3 py-1 text-sm font-medium text-muted-foreground">
        <span className="h-2 w-2 shrink-0 rounded-full bg-muted-foreground/50" />
        Waiting for speech…
      </span>
    );
  }

  const color = speakerColor(speaker);
  const style = {
    color,
    borderColor: color,
    backgroundColor: speakerColorSubtle(speaker),
    "--pulse-color": color,
  } as React.CSSProperties;

  return (
    <span
      aria-live="polite"
      aria-label={`Current speaker: ${formatSpeaker(speaker)}`}
      className="inline-flex animate-pulse-speaker items-center gap-2 rounded-full border px-3 py-1 text-sm font-semibold"
      style={style}
    >
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: color }} />
      {formatSpeaker(speaker)}
    </span>
  );
}
