"use client";

import { DailyTransport } from "@pipecat-ai/daily-transport";
import { LogLevel, PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { PipecatClientAudio, PipecatClientProvider, usePipecatClient, useRTVIClientEvent } from "@pipecat-ai/client-react";
import { useState, useEffect } from "react";
import { SessionConfigForm, SessionConfigPayload } from "../features/session-config/SessionConfigForm";
import { SessionControlPanel } from "../features/session-control/SessionControlPanel";
import { BotStateBadge, BotState } from "../features/dashboard/BotStateBadge";
import { LatencyPanel } from "../features/dashboard/LatencyPanel";
import { useVoiceSession } from "@/hooks/useVoiceSession";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

// Component inside the RTVIProvider
function InterviewDashboard() {
  const client = usePipecatClient();
  const { createSession, purgeCredentials, resetVoiceSession } = useVoiceSession();
  const [sessionActive, setSessionActive] = useState(false);
  const [botState, setBotState] = useState<BotState>("Listening");
  const [latencyMs, setLatencyMs] = useState(0);
  const [userSilenceStartTime, setUserSilenceStartTime] = useState<number | null>(null);
  const [transportError, setTransportError] = useState<string | null>(null);

  // RTVI Event listeners to drive state machine deterministically based on pipeline emitted frames
  useRTVIClientEvent(RTVIEvent.BotStartedSpeaking, () => {
    setBotState("Speaking");
    // Calculate round trip latency if we were tracking user silence
    if (userSilenceStartTime) {
      setLatencyMs(Math.round(performance.now() - userSilenceStartTime));
      setUserSilenceStartTime(null);
    }
  });

  useRTVIClientEvent(RTVIEvent.BotStoppedSpeaking, () => {
    setBotState("Listening");
  });

  useRTVIClientEvent(RTVIEvent.UserStartedSpeaking, () => {
    setBotState("Listening");
    setUserSilenceStartTime(null); // Interruption cancels the timer
  });

  useRTVIClientEvent(RTVIEvent.UserStoppedSpeaking, () => {
    setBotState("Thinking");
    setUserSilenceStartTime(performance.now());
  });

  useRTVIClientEvent(RTVIEvent.Disconnected, () => {
    setSessionActive(false);
    setBotState("Listening");
    setLatencyMs(0);
    resetVoiceSession();
  });

  async function handleStartSession(payload: SessionConfigPayload) {
    setTransportError(null);
    try {
      const creds = await createSession.mutateAsync(payload);
      try {
        await client?.connect({ url: creds.room_url, token: creds.token });
        setSessionActive(true);
      } catch (connectErr) {
        purgeCredentials();
        const message =
          connectErr instanceof Error
            ? connectErr.message
            : "Could not connect to the voice room.";
        setTransportError(message);
        console.error(connectErr);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function handleStopSession() {
    await client?.disconnect();
    setSessionActive(false);
    resetVoiceSession();
    setTransportError(null);
  }

  const apiErrorMessage =
    createSession.error instanceof Error ? createSession.error.message : null;
  const sessionError = transportError ?? apiErrorMessage;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">
          Start a voice interview session, monitor bot state, and stop cleanly when you&apos;re done.
        </p>
      </div>

      {!sessionActive ? (
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Configure Session</CardTitle>
            <CardDescription>Set prompts and model parameters before connecting.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 pt-6">
            {sessionError ? (
              <Alert variant="destructive">
                <AlertTitle>Could not start session</AlertTitle>
                <AlertDescription>{sessionError}</AlertDescription>
              </Alert>
            ) : null}

            <SessionConfigForm
              onSubmit={handleStartSession}
              submitting={createSession.isPending}
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Live Session</CardTitle>
            <CardDescription>You&apos;re connected. Watch status and latency while you speak.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 pt-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="flex flex-wrap items-center gap-3">
                <BotStateBadge state={botState} />
                <Separator orientation="vertical" className="hidden h-8 md:block" />
                <LatencyPanel latencyMs={latencyMs} />
              </div>
            </div>

            <Separator />

            <SessionControlPanel isActive={true} onStart={() => {}} onStop={handleStopSession} />
          </CardContent>
        </Card>
      )}
      <PipecatClientAudio />
    </div>
  );
}

// Wrapper to provide the client
export default function Page() {
  const [client, setClient] = useState<PipecatClient | null>(null);

  useEffect(() => {
    const transport = new DailyTransport();
    const rtviClient = new PipecatClient({
      transport,
      enableMic: true,
    });
    // Server emits `user-llm-text` per RTVI; client-js 1.7 has no handler branch yet (DEBUG fallback).
    rtviClient.setLogLevel(LogLevel.INFO);
    setClient(rtviClient);
  }, []);

  if (!client) {
    return (
      <div className="flex flex-col gap-4">
        <div className="h-4 w-2/3 max-w-md animate-pulse rounded-md bg-muted" />
        <div className="h-40 w-full animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  return (
    <PipecatClientProvider client={client}>
      <InterviewDashboard />
    </PipecatClientProvider>
  );
}
