import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export interface SessionConfigPayload {
  system_prompt: string;
  llm_temperature: number;
  llm_max_tokens: number;
  stt_temperature: number;
  tts_voice: string;
  tts_speed: number;
  tts_temperature: number;
  interruptibility_percentage: number;
}

interface Props {
  onSubmit: (payload: SessionConfigPayload) => void;
  /** Disables submit while the server session request is in flight. */
  submitting?: boolean;
}

export function SessionConfigForm({ onSubmit, submitting = false }: Props) {
  const [systemPrompt, setSystemPrompt] = useState("");
  const [llmTemperature, setLlmTemperature] = useState(0.7);
  const [llmMaxTokens, setLlmMaxTokens] = useState(256);
  const [sttTemperature, setSttTemperature] = useState(0.0);
  const [ttsVoice, setTtsVoice] = useState("sonic");
  const [ttsSpeed, setTtsSpeed] = useState(1.0);
  const [ttsTemperature, setTtsTemperature] = useState(0.3);
  const [interruptibility, setInterruptibility] = useState(70);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!systemPrompt.trim()) return;
    onSubmit({
      system_prompt: systemPrompt,
      llm_temperature: llmTemperature,
      llm_max_tokens: llmMaxTokens,
      stt_temperature: sttTemperature,
      tts_voice: ttsVoice,
      tts_speed: ttsSpeed,
      tts_temperature: ttsTemperature,
      interruptibility_percentage: interruptibility,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <label
          htmlFor="system-prompt"
          className="text-sm font-medium leading-none"
        >
          System Prompt
        </label>
        <Textarea
          id="system-prompt"
          aria-label="System Prompt"
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          required
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-2">
          <label htmlFor="llm-temperature" className="text-sm font-medium leading-none">
            LLM Temperature
          </label>
          <Input
            id="llm-temperature"
            type="number"
            step="0.1"
            min="0"
            max="2"
            value={llmTemperature}
            onChange={(e) => setLlmTemperature(Number(e.target.value))}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="llm-max-tokens" className="text-sm font-medium leading-none">
            Max Tokens
          </label>
          <Input
            id="llm-max-tokens"
            type="number"
            min="1"
            max="4096"
            value={llmMaxTokens}
            onChange={(e) => setLlmMaxTokens(Number(e.target.value))}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="stt-temperature" className="text-sm font-medium leading-none">
            STT Temperature
          </label>
          <Input
            id="stt-temperature"
            type="number"
            step="0.1"
            min="0"
            max="1"
            value={sttTemperature}
            onChange={(e) => setSttTemperature(Number(e.target.value))}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="tts-voice" className="text-sm font-medium leading-none">
            TTS Voice
          </label>
          <Input
            id="tts-voice"
            type="text"
            value={ttsVoice}
            onChange={(e) => setTtsVoice(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="tts-speed" className="text-sm font-medium leading-none">
            TTS Speed
          </label>
          <Input
            id="tts-speed"
            type="number"
            step="0.1"
            min="0.5"
            max="2"
            value={ttsSpeed}
            onChange={(e) => setTtsSpeed(Number(e.target.value))}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="tts-temperature" className="text-sm font-medium leading-none">
            TTS Temperature
          </label>
          <Input
            id="tts-temperature"
            type="number"
            step="0.1"
            min="0"
            max="1"
            value={ttsTemperature}
            onChange={(e) => setTtsTemperature(Number(e.target.value))}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="interruptibility" className="text-sm font-medium leading-none">
            Interruptibility Percentage
          </label>
          <Input
            id="interruptibility"
            aria-label="Interruptibility Percentage"
            type="number"
            min="0"
            max="100"
            value={interruptibility}
            onChange={(e) => setInterruptibility(Number(e.target.value))}
          />
        </div>
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={submitting} aria-busy={submitting}>
          {submitting ? "Starting…" : "Start Session"}
        </Button>
      </div>
    </form>
  );
}
