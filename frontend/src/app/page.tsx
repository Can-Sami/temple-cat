"use client";

import { DailyTransport } from "@pipecat-ai/daily-transport";
import { LogLevel, PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import {
  PipecatClientAudio,
  PipecatClientProvider,
  usePipecatClient,
  useRTVIClientEvent,
} from "@pipecat-ai/client-react";
import { useEffect, useState } from "react";

import { SessionControlPanel } from "../features/session-control/SessionControlPanel";
import { SpeakerBadge } from "../features/dashboard/SpeakerBadge";
import { SpeakerIndicator } from "../features/dashboard/SpeakerIndicator";
import { TranscriptPanel } from "../features/dashboard/TranscriptPanel";
import {
  appendTurn,
  emptyTranscript,
  parseSpeakerActive,
  parseSpeakerMessage,
  setCurrentSpeaker,
  type TranscriptState,
} from "../features/dashboard/speakerTranscript";
import {
  DEFAULT_SESSION_CONFIG,
  type DiarizationEngine,
} from "../features/session-config/sessionConfig";
import { useVoiceSession } from "@/hooks/useVoiceSession";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function Segmented<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  readonly label: string;
  readonly value: T;
  readonly onChange: (v: T) => void;
  readonly options: ReadonlyArray<{ value: T; label: string }>;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <div className="inline-flex w-fit rounded-lg border border-border bg-secondary/40 p-0.5">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            aria-pressed={value === o.value}
            onClick={() => onChange(o.value)}
            className={cn(
              "rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors",
              value === o.value
                ? "bg-brand text-brand-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function DiarizationConsole() {
  const client = usePipecatClient();
  const { createSession, purgeCredentials, resetVoiceSession } = useVoiceSession();
  const [sessionActive, setSessionActive] = useState(false);
  const [transportError, setTransportError] = useState<string | null>(null);
  /** Diarized transcript (Speaker 1 / Speaker 2 …) from backend server-messages. */
  const [transcript, setTranscript] = useState<TranscriptState>(emptyTranscript);
  const [engine, setEngine] = useState<DiarizationEngine>("freya1");
  /** True for the whole start flow (create session + connect), so the button stays "Starting…". */
  const [starting, setStarting] = useState(false);

  // freya1 = full Speechmatics assistant (transcript); freya2/3 = diarization-only.
  const isDiarOnly = engine !== "freya1";
  const engineCaption =
    engine === "freya1"
      ? "Full voice assistant · Turkish"
      : engine === "freya2"
        ? "Deepgram · diarization only"
        : "Diarization only";
  const indicatorProvider = engine === "freya2" ? "Deepgram" : undefined;

  // Two signals, both carrying a speaker label (unwrap defensively in case the
  // client hands us the RTVI envelope):
  //   • speaker-transcript (final) → append a transcript turn
  //   • speaker-active (interim)   → just light the live indicator, no turn
  useRTVIClientEvent(RTVIEvent.ServerMessage, (data: unknown) => {
    const envelope = (data as { data?: unknown } | null)?.data;
    const parsed = parseSpeakerMessage(data) ?? parseSpeakerMessage(envelope);
    if (parsed) {
      setTranscript((prev) => appendTurn(prev, parsed));
      return;
    }
    const active = parseSpeakerActive(data) ?? parseSpeakerActive(envelope);
    if (active !== null) {
      setTranscript((prev) => setCurrentSpeaker(prev, active));
    }
  });

  useRTVIClientEvent(RTVIEvent.Disconnected, () => {
    setSessionActive(false);
    setTranscript(emptyTranscript());
    resetVoiceSession();
  });

  async function handleStart() {
    setStarting(true);
    setTransportError(null);
    setTranscript(emptyTranscript());
    try {
      const creds = await createSession.mutateAsync({
        ...DEFAULT_SESSION_CONFIG,
        diarization_engine: engine,
      });
      try {
        // A prior failed/incomplete session can leave the client "started", which
        // makes the next connect() throw. Disconnect first so a fresh start is clean.
        try {
          await client?.disconnect();
        } catch {
          /* wasn't connected — fine */
        }
        await client?.connect({ url: creds.room_url, token: creds.token });
        setSessionActive(true);
      } catch (connectErr) {
        purgeCredentials();
        try {
          await client?.disconnect();
        } catch {
          /* ignore */
        }
        setTransportError(
          connectErr instanceof Error
            ? connectErr.message
            : "Could not connect to the voice room."
        );
        console.error(connectErr);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setStarting(false);
    }
  }

  async function handleStop() {
    await client?.disconnect();
    setSessionActive(false);
    setTranscript(emptyTranscript());
    resetVoiceSession();
    setTransportError(null);
  }

  const apiError =
    createSession.error instanceof Error ? createSession.error.message : null;
  const sessionError = transportError ?? apiError;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-balance font-display text-2xl font-extrabold tracking-tight md:text-3xl">
          Live speaker diarization
        </h2>
        <p className="max-w-prose text-pretty text-sm leading-relaxed text-muted-foreground">
          Start a session and talk. When two people share one mic, each voice is tagged{" "}
          <span className="font-medium text-foreground">Speaker 1</span> /{" "}
          <span className="font-medium text-foreground">Speaker 2</span> live below.
        </p>
      </div>

      {sessionError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not start session</AlertTitle>
          <AlertDescription>{sessionError}</AlertDescription>
        </Alert>
      ) : null}

      {sessionActive ? (
        <div className="flex animate-fade-up flex-col gap-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            {isDiarOnly ? <span /> : <SpeakerBadge speaker={transcript.currentSpeaker} />}
            <SessionControlPanel isActive onStart={() => {}} onStop={handleStop} />
          </div>
          {isDiarOnly ? (
            <SpeakerIndicator speaker={transcript.currentSpeaker} provider={indicatorProvider} />
          ) : (
            <TranscriptPanel turns={transcript.turns} />
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Segmented
              label="Diarization engine"
              value={engine}
              onChange={setEngine}
              options={[
                { value: "freya1", label: "Freya 1" },
                { value: "freya2", label: "Freya 2" },
                { value: "freya3", label: "Freya 3" },
              ]}
            />
            <span className="font-mono text-xs text-muted-foreground">{engineCaption}</span>
          </div>
          <div>
            <Button
              type="button"
              onClick={handleStart}
              disabled={starting}
              aria-busy={starting}
              className="h-11 px-6 text-base"
            >
              {starting ? "Starting…" : "Start session"}
            </Button>
          </div>
        </div>
      )}

      <PipecatClientAudio />
    </div>
  );
}

export default function Page() {
  const [client, setClient] = useState<PipecatClient | null>(null);

  useEffect(() => {
    const transport = new DailyTransport();
    const rtviClient = new PipecatClient({ transport, enableMic: true });
    rtviClient.setLogLevel(LogLevel.INFO);
    setClient(rtviClient);
  }, []);

  if (!client) {
    return (
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
        <div className="h-6 w-2/3 max-w-md animate-pulse rounded-md bg-muted" />
        <div className="h-32 w-full animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  return (
    <PipecatClientProvider client={client}>
      <DiarizationConsole />
    </PipecatClientProvider>
  );
}
