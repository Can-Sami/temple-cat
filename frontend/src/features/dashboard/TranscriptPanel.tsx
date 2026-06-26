"use client";

import * as React from "react";

import { ScrollArea } from "@/components/ui/scroll-area";

import {
  formatSpeaker,
  speakerColor,
  speakerColorSubtle,
  type SpeakerTurn,
} from "./speakerTranscript";

interface Props {
  readonly turns: readonly SpeakerTurn[];
}

/** Color-coded live transcript: each finalized turn tinted by its speaker. */
export function TranscriptPanel({ turns }: Props) {
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Transcript</h3>
        <span className="font-mono text-xs text-muted-foreground">
          {turns.length} {turns.length === 1 ? "turn" : "turns"}
        </span>
      </div>

      <ScrollArea className="h-72 rounded-xl border border-border bg-card/40 p-3">
        {turns.length === 0 ? (
          <p className="px-2 py-10 text-center text-sm text-muted-foreground">
            Speak into the mic. When a second voice joins, Deepgram tags each speaker here.
          </p>
        ) : (
          <ol className="flex flex-col gap-2">
            {turns.map((turn) => {
              const color = speakerColor(turn.speaker);
              return (
                <li
                  key={turn.id}
                  className="flex animate-fade-up flex-col gap-1 rounded-lg border px-3 py-2"
                  style={{ borderColor: color, backgroundColor: speakerColorSubtle(turn.speaker) }}
                >
                  <span
                    className="font-mono text-[11px] font-bold uppercase tracking-wide"
                    style={{ color }}
                  >
                    {formatSpeaker(turn.speaker)}
                  </span>
                  <span className="text-sm leading-relaxed text-foreground">{turn.text}</span>
                </li>
              );
            })}
            <div ref={bottomRef} />
          </ol>
        )}
      </ScrollArea>
    </div>
  );
}
