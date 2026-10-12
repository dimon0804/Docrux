import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const KEY = "paragraf:theme";

function current(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function stored(): Theme | null {
  try {
    const value = localStorage.getItem(KEY);
    return value === "dark" || value === "light" ? value : null;
  } catch {
    return null;
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(current);

  // Пока пользователь сам не выбрал тему, следуем за настройкой системы.
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const follow = (event: MediaQueryListEvent) => {
      if (stored()) return;
      const next = event.matches ? "dark" : "light";
      document.documentElement.dataset.theme = next;
      setTheme(next);
    };
    media.addEventListener("change", follow);
    return () => media.removeEventListener("change", follow);
  }, []);

  const toggle = useCallback(() => {
    const next: Theme = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(KEY, next);
    } catch {
      // Хранилище недоступно: тема сменится только до перезагрузки.
    }
    setTheme(next);
  }, []);

  return { theme, toggle };
}
