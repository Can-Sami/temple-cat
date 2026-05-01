interface Props {
  /** Pipeline-reported TTS time-to-first-byte from RTVI metrics (primary). */
  readonly backendTtsTtfbMs: number | null;
  /** Client wall-clock estimate UserStoppedSpeaking → BotStartedSpeaking (secondary). */
  readonly wallClockLatencyMs: number;
}

export function LatencyPanel({ backendTtsTtfbMs, wallClockLatencyMs }: Props) {
  const primary =
    backendTtsTtfbMs != null ? `${backendTtsTtfbMs} ms (bot TTS TTFB)` : "— (awaiting metrics)";
  const secondary =
    wallClockLatencyMs > 0 ? `${wallClockLatencyMs} ms wall-clock` : "wall-clock —";

  return (
    <div
      aria-label="Latency: bot TTS TTFB and wall-clock estimate"
      className="inline-flex flex-col gap-0.5 rounded-lg border bg-card px-3 py-2 text-sm tabular-nums text-muted-foreground ring-1 ring-foreground/10"
    >
      <span className="font-medium text-foreground">{primary}</span>
      <span className="text-xs">{secondary}</span>
    </div>
  );
}
