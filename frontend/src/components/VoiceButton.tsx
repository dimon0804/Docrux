import { LoaderCircle, Mic, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { type Recording, startRecording } from "@/lib/recorder";

let availability: Promise<boolean> | null = null;

/** Включён ли голос на сервере: спрашиваем один раз за сессию страницы. */
function speechAvailable() {
  availability ??= fetch("/api/speech/available")
    .then((response) => (response.ok ? response.json() : { available: false }))
    .then((body: { available?: boolean }) => Boolean(body.available))
    .catch(() => false);
  return availability;
}

type Props = { disabled?: boolean; onText: (text: string) => void };

/** Кнопка микрофона: записывает вопрос и отдаёт распознанный текст. */
export function VoiceButton({ disabled, onText }: Props) {
  const [available, setAvailable] = useState(false);
  const [state, setState] = useState<"idle" | "recording" | "busy">("idle");
  const recording = useRef<Recording | null>(null);

  useEffect(() => {
    let alive = true;
    if ("mediaDevices" in navigator && typeof navigator.mediaDevices.getUserMedia === "function") {
      void speechAvailable().then((value) => alive && setAvailable(value));
    }
    return () => {
      alive = false;
      recording.current?.cancel();
    };
  }, []);

  if (!available) return null;

  const finish = async () => {
    const current = recording.current;
    if (!current) return;
    recording.current = null;
    setState("busy");
    try {
      const audio = await current.stop();
      const response = await fetch("/api/speech", { method: "POST", body: audio });
      const body = (await response.json()) as { text?: string; detail?: string };
      if (!response.ok) throw new Error(body.detail ?? "Не удалось распознать запись.");
      if (body.text) onText(body.text.charAt(0).toUpperCase() + body.text.slice(1));
      else toast.error("Не расслышал вопрос. Попробуйте ещё раз, ближе к микрофону.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Не удалось распознать запись.");
    } finally {
      setState("idle");
    }
  };

  const start = async () => {
    try {
      recording.current = await startRecording(() => void finish());
      setState("recording");
    } catch {
      toast.error("Нет доступа к микрофону. Разрешите его в настройках браузера.");
    }
  };

  const label =
    state === "recording"
      ? "Остановить запись и отправить вопрос"
      : state === "busy"
        ? "Распознаю вопрос"
        : "Задать вопрос голосом";

  return (
    <button
      type="button"
      disabled={disabled || state === "busy"}
      onClick={() => void (state === "recording" ? finish() : start())}
      aria-label={label}
      title={label}
      className={`pressable relative grid size-12 shrink-0 place-items-center rounded-xl border ${
        state === "recording"
          ? "border-danger/40 bg-danger-soft text-danger"
          : "border-line-strong bg-surface text-text-2 hover:border-brand/50 hover:text-text"
      } disabled:opacity-60`}
    >
      {state === "recording" && (
        <span
          aria-hidden="true"
          className="absolute inset-0 animate-ping rounded-xl border-2 border-danger/40 motion-reduce:animate-none"
        />
      )}
      {state === "busy" ? (
        <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
      ) : state === "recording" ? (
        <Square aria-hidden="true" className="size-4" />
      ) : (
        <Mic aria-hidden="true" className="size-5" />
      )}
    </button>
  );
}
