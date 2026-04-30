interface Props {
  latencyMs: number;
}

export function LatencyPanel({ latencyMs }: Props) {
  return (
    <div aria-label="Round Trip Latency">
      {latencyMs} ms
    </div>
  );
}
