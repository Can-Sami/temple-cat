interface Props {
  readonly latencyMs: number;
}

export function LatencyPanel({ latencyMs }: Props) {
  return (
    <div
      aria-label="Round Trip Latency"
      className="inline-flex items-center rounded-lg border bg-card px-3 py-2 text-sm tabular-nums text-muted-foreground ring-1 ring-foreground/10"
    >
      {latencyMs} ms
    </div>
  );
}
