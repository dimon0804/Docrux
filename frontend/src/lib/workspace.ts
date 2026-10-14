import { useCallback, useEffect, useReducer, useRef } from "react";

import {
  analyze,
  type Analysis,
  type Answer,
  ApiError,
  ask,
  type CheckResponse,
  checkFile,
  recheck,
} from "./api";

export type Turn = {
  id: number;
  question: string;
  answer: Answer | null;
  error: string | null;
};

export type Workspace = {
  phase: "idle" | "reading" | "ready";
  file: File | null;
  preview: string | null;
  docType: string;
  analysis: Analysis | null;
  check: Answer | null;
  image: string | null;
  turns: Turn[];
  asking: boolean;
  error: string | null;
  focus: string[];
  edited: string[];
};

type Action =
  | { type: "pick"; file: File; preview: string | null }
  | { type: "type"; docType: string }
  | { type: "start" }
  | { type: "done"; analysis: Analysis; check: Answer; image: string; first: Turn | null }
  | { type: "fail"; error: string }
  | { type: "ask"; turn: Turn }
  | { type: "answer"; id: number; answer: Answer | null; error: string | null }
  | { type: "focus"; keys: string[] }
  | { type: "edited"; key: string; result: CheckResponse }
  | { type: "reset" };

const initial: Workspace = {
  phase: "idle",
  file: null,
  preview: null,
  docType: "",
  analysis: null,
  check: null,
  image: null,
  turns: [],
  asking: false,
  error: null,
  focus: [],
  edited: [],
};

function reducer(state: Workspace, action: Action): Workspace {
  switch (action.type) {
    case "pick":
      return { ...initial, docType: state.docType, file: action.file, preview: action.preview };
    case "type":
      return { ...state, docType: action.docType };
    case "start":
      return { ...state, phase: "reading", error: null };
    case "done":
      return {
        ...state,
        phase: "ready",
        analysis: action.analysis,
        check: action.check,
        image: action.image,
        turns: action.first ? [action.first] : [],
        focus: action.first?.answer?.highlight ?? action.check.highlight,
      };
    case "fail":
      return { ...state, phase: "idle", error: action.error };
    case "ask":
      return { ...state, asking: true, turns: [...state.turns, action.turn] };
    case "answer":
      return {
        ...state,
        asking: false,
        focus: action.answer?.highlight ?? state.focus,
        turns: state.turns.map((turn) =>
          turn.id === action.id ? { ...turn, answer: action.answer, error: action.error } : turn,
        ),
      };
    case "focus":
      return { ...state, focus: action.keys };
    case "edited": {
      if (!state.analysis) return state;
      // Рамки на снимке остаются от распознавания, значение и проверка приходят с сервера.
      const fresh = new Map(action.result.fields.map((field) => [field.key, field]));
      const fields = state.analysis.fields.map((field) => {
        const next = fresh.get(field.key);
        if (!next) return field;
        const changed = field.key === action.key;
        return {
          ...field,
          value: next.value,
          found: next.found,
          box: changed ? null : field.box,
          confidence: changed ? null : field.confidence,
          handwritten: changed ? false : field.handwritten,
        };
      });
      return {
        ...state,
        analysis: { ...state.analysis, fields, validation: action.result.validation },
        check: action.result.check,
        edited: state.edited.includes(action.key) ? state.edited : [...state.edited, action.key],
      };
    }
    case "reset":
      return { ...initial, docType: state.docType };
  }
}

function message(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Что-то пошло не так. Попробуйте ещё раз.";
}

export function useWorkspace() {
  const [state, dispatch] = useReducer(reducer, initial);
  const controller = useRef<AbortController | null>(null);
  const counter = useRef(0);
  const previewUrl = useRef<string | null>(null);

  const release = useCallback(() => {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null;
  }, []);

  useEffect(
    () => () => {
      controller.current?.abort();
      release();
    },
    [release],
  );

  const pick = useCallback(
    (file: File): string | null => {
      const problem = checkFile(file);
      if (problem) return problem;
      controller.current?.abort();
      release();
      const isImage = file.type.startsWith("image/") || /\.(jpe?g|png)$/i.test(file.name);
      previewUrl.current = isImage ? URL.createObjectURL(file) : null;
      dispatch({ type: "pick", file, preview: previewUrl.current });
      return null;
    },
    [release],
  );

  const setDocType = useCallback((docType: string) => dispatch({ type: "type", docType }), []);

  const read = useCallback(
    async (question: string) => {
      if (!state.file) return;
      controller.current?.abort();
      const abort = new AbortController();
      controller.current = abort;
      dispatch({ type: "start" });
      const asked = question.trim();
      try {
        const result = await analyze(state.file, {
          docType: state.docType || undefined,
          question: asked || undefined,
          signal: abort.signal,
        });
        const first: Turn | null = result.answer
          ? { id: ++counter.current, question: asked, answer: result.answer, error: null }
          : null;
        dispatch({
          type: "done",
          analysis: result.analysis,
          check: result.check,
          image: result.image,
          first,
        });
      } catch (error) {
        if (abort.signal.aborted) return;
        dispatch({ type: "fail", error: message(error) });
      }
    },
    [state.file, state.docType],
  );

  const question = useCallback(
    async (text: string) => {
      const asked = text.trim();
      if (!asked || !state.analysis || state.asking) return;
      const id = ++counter.current;
      dispatch({ type: "ask", turn: { id, question: asked, answer: null, error: null } });
      try {
        const answer = await ask(state.analysis, asked);
        dispatch({ type: "answer", id, answer, error: null });
      } catch (error) {
        dispatch({ type: "answer", id, answer: null, error: message(error) });
      }
    },
    [state.analysis, state.asking],
  );

  const focus = useCallback((keys: string[]) => dispatch({ type: "focus", keys }), []);

  /** Значение поля поправили вручную: сервер приводит его к формату и перепроверяет документ. */
  const edit = useCallback(
    async (key: string, value: string | boolean): Promise<string | null> => {
      if (!state.analysis) return null;
      try {
        const result = await recheck(state.analysis, [{ key, value }]);
        dispatch({ type: "edited", key, result });
        const field = result.fields.find((item) => item.key === key);
        if (typeof value === "string" && value.trim() && field && !field.found) {
          return "Значение не похоже на ожидаемое для этого поля. Проверьте формат.";
        }
        return null;
      } catch (error) {
        return message(error);
      }
    },
    [state.analysis],
  );

  const reset = useCallback(() => {
    controller.current?.abort();
    release();
    dispatch({ type: "reset" });
  }, [release]);

  return { state, pick, setDocType, read, question, focus, edit, reset };
}
