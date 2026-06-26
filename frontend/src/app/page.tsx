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
  parseSpeakerMessage,
  type TranscriptState,
} from "../features/dashboard/speakerTranscript";
import { DEFAULT_SESSION_CONFIG } from "../features/session-config/sessionConfig";
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

  // The one event that matters: each finalized turn carries its speaker label.
  // Unwrap defensively in case the client hands us the RTVI envelope.
  useRTVIClientEvent(RTVIEvent.ServerMessage, (data: unknown) => {
    const parsed =
      parseSpeakerMessage(data) ??
      parseSpeakerMessage((data as { data?: unknown } | null)?.data);
    if (parsed) {
      setTranscript((prev) => appendTurn(prev, parsed));
    }
  });

  useRTVIClientEvent(RTVIEvent.Disconnected, () => {
    setSessionActive(false);
    setTranscript(emptyTranscript());
    resetVoiceSession();
  });

  async function handleStart() {
    setTransportError(null);
    setTranscript(emptyTranscript());
    try {
      const creds = await createSession.mutateAsync(DEFAULT_SESSION_CONFIG);
      try {
        await client?.connect({ url: creds.room_url, token: creds.token });
        setSessionActive(true);
      } catch (connectErr) {
        purgeCredentials();
        setTransportError(
          connectErr instanceof Error
            ? connectErr.message
            : "Could not connect to the voice room."
        );
        console.error(connectErr);
      }
    } catch (err) {
      console.error(err);
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
            disabled={createSession.isPending}
            aria-busy={createSession.isPending}
            className="h-11 px-6 text-base"
          >
            {createSession.isPending ? "Starting…" : "Start session"}
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
