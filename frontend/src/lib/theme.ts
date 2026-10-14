import { useCallback, useEffect, useState } from "react";
import { flushSync } from "react-dom";

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

  const toggle = useCallback((origin?: { x: number; y: number }) => {
    const next: Theme = current() === "dark" ? "light" : "dark";
    const apply = () => {
      document.documentElement.dataset.theme = next;
      try {
        localStorage.setItem(KEY, next);
      } catch {
        // Хранилище недоступно: тема сменится только до перезагрузки.
      }
      setTheme(next);
    };
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!document.startViewTransition || calm || !origin) {
      apply();
      return;
    }
    // Новая тема раскрывается кругом от кнопки, которую нажали.
    const transition = document.startViewTransition(() => flushSync(apply));
    const radius = Math.hypot(
      Math.max(origin.x, window.innerWidth - origin.x),
      Math.max(origin.y, window.innerHeight - origin.y),
    );
    transition.ready
      .then(() => {
        document.documentElement.animate(
          {
            clipPath: [
              `circle(0px at ${origin.x}px ${origin.y}px)`,
              `circle(${radius}px at ${origin.x}px ${origin.y}px)`,
            ],
          },
          {
            duration: 520,
            easing: "cubic-bezier(0.23, 1, 0.32, 1)",
            pseudoElement: "::view-transition-new(root)",
          },
        );
      })
      .catch(() => {});
  }, []);

  return { theme, toggle };
}
