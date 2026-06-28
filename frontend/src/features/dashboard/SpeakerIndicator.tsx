"use client";

import * as React from "react";

import { formatSpeaker, speakerColor, speakerColorSubtle } from "./speakerTranscript";

interface Props {
  /** Current speaker index, or null before anyone has spoken. */
  readonly speaker: number | null;
  /** Optional provider name shown small underneath (e.g. "Deepgram"). */
  readonly provider?: string;
}

/** Big "Speaker N is talking" indicator for the diarization-only tabs (no transcript). */
export function SpeakerIndicator({ speaker, provider }: Props) {
  const active = speaker !== null;

  return (
    <div className="flex flex-col items-center justify-center gap-5 rounded-2xl border border-border bg-card/40 py-20 text-center">
      {active ? (
        <span
          className="inline-flex animate-pulse-speaker items-center gap-3 rounded-full border px-7 py-3.5 text-2xl font-bold tracking-tight md:text-3xl"
          style={
            {
              color: speakerColor(speaker),
              borderColor: speakerColor(speaker),
              backgroundColor: speakerColorSubtle(speaker),
              "--pulse-color": speakerColor(speaker),
            } as React.CSSProperties
          }
        >
          <span
            className="h-3 w-3 shrink-0 rounded-full"
            style={{ backgroundColor: speakerColor(speaker) }}
          />
          {formatSpeaker(speaker)} is talking
        </span>
      ) : (
        <span className="text-lg text-muted-foreground">Listening… start talking</span>
      )}

      {provider ? (
        <span className="font-mono text-xs text-muted-foreground">{provider}</span>
      ) : null}
    </div>
  );
}
