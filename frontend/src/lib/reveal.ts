import { useEffect } from "react";

/**
 * Блоки с классом reveal плавно появляются, когда доходят до экрана.
 * Положение проверяется при прокрутке, а не через IntersectionObserver: он
 * срабатывает не во всех браузерах, а скрытый навсегда блок хуже отсутствия анимации.
 * Новые блоки (после смены страницы или разбора) подхватываются сами.
 */
export function useReveal() {
  useEffect(() => {
    let frame = 0;
    const check = () => {
      frame = 0;
      const limit = window.innerHeight * 0.92;
      document.querySelectorAll<HTMLElement>(".reveal:not([data-shown])").forEach((item) => {
        if (item.getBoundingClientRect().top < limit) item.setAttribute("data-shown", "");
      });
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(check);
    };
    check();
    const added = new MutationObserver(schedule);
    added.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      cancelAnimationFrame(frame);
      added.disconnect();
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, []);
}
