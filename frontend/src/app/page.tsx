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

function DiarizationConsole() {
  const client = usePipecatClient();
  const { createSession, purgeCredentials, resetVoiceSession } = useVoiceSession();
  const [sessionActive, setSessionActive] = useState(false);
  const [transportError, setTransportError] = useState<string | null>(null);
  /** Diarized transcript (Speaker 1 / Speaker 2 …) from backend server-messages. */
  const [transcript, setTranscript] = useState<TranscriptState>(emptyTranscript);
  /** True for the whole start flow (create session + connect), so the button stays "Starting…". */
  const [starting, setStarting] = useState(false);

  // Single engine: Freya 1 = full Speechmatics voice assistant (Turkish, transcribes).
  const engine: DiarizationEngine = "freya1";

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
            <SpeakerBadge speaker={transcript.currentSpeaker} />
            <SessionControlPanel isActive onStart={() => {}} onStop={handleStop} />
          </div>
          <TranscriptPanel turns={transcript.turns} />
        </div>
      ) : (
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
