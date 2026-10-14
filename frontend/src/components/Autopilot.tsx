import { Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { runAutopilot, Stopped } from "@/lib/autopilot";

/**
 * Демонстрация для защиты: Shift+D или ссылка «Показать демо» в подвале.
 * Esc или кнопка «Остановить» прерывают показ в любой момент.
 */
export function Autopilot() {
  const [running, setRunning] = useState(false);
  const [caption, setCaption] = useState("");
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);

  const stop = useCallback(() => controller.current?.abort(), []);

  const start = useCallback(async () => {
    if (controller.current) return;
    const abort = new AbortController();
    controller.current = abort;
    setRunning(true);
    setProblem(null);
    setCursor({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
    try {
      await runAutopilot({
        signal: abort.signal,
        caption: setCaption,
        point: async (element) => {
          const box = element.getBoundingClientRect();
          setCursor({ x: box.left + box.width / 2, y: box.top + box.height / 2 });
          await new Promise((resolve) => setTimeout(resolve, 520));
        },
      });
    } catch (error) {
      if (!(error instanceof Stopped)) {
        setProblem(error instanceof Error ? error.message : "Показ прервался.");
      }
    } finally {
      controller.current = null;
      setRunning(false);
      setCaption("");
      setCursor(null);
    }
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (event.key === "Escape" && controller.current) stop();
      if (
        event.shiftKey &&
        event.code === "KeyD" &&
        !target?.closest("input, textarea, [contenteditable]")
      ) {
        event.preventDefault();
        void start();
      }
    };
    const onStart = () => void start();
    window.addEventListener("keydown", onKey);
    window.addEventListener("paragraf:autopilot", onStart);
    if (new URLSearchParams(location.search).has("demo")) void start();
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("paragraf:autopilot", onStart);
    };
  }, [start, stop]);

  if (!running && !problem) return null;
  return (
    <div className="no-print">
      {cursor && (
        <span
          aria-hidden="true"
          className="pointer-events-none fixed z-[100] size-7 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-brand/70 shadow-[0_4px_16px_rgb(0_0_0/0.35)] transition-[left,top] duration-500 ease-out"
          style={{ left: cursor.x, top: cursor.y }}
        />
      )}
      <div className="fixed inset-x-0 bottom-6 z-[100] flex flex-col items-center gap-2 px-4">
        {caption && (
          <p
            role="status"
            className="max-w-[1000px] rounded-2xl bg-[#1b1f2a]/95 px-6 py-3.5 text-center text-[17px] font-medium leading-snug text-white shadow-[0_12px_40px_rgb(0_0_0/0.3)] sm:text-xl"
          >
            {caption}
          </p>
        )}
        {problem && (
          <p role="alert" className="rounded-xl bg-danger-soft px-4 py-2.5 text-sm text-danger">
            {problem}{" "}
            <button type="button" className="underline" onClick={() => setProblem(null)}>
              Закрыть
            </button>
          </p>
        )}
        {running && (
          <button
            type="button"
            onClick={stop}
            className="pressable inline-flex items-center gap-1.5 rounded-full bg-surface/95 px-3.5 py-1.5 text-[13px] font-medium text-text-2 shadow-pop hover:text-text"
          >
            <Square aria-hidden="true" className="size-3" />
            Остановить показ (Esc)
          </button>
        )}
      </div>
    </div>
  );
}
