import { useEffect } from "react";
import { Toaster } from "sonner";
import { Route, Switch, useLocation } from "wouter";

import { CookieNotice } from "./components/CookieNotice";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { useTheme } from "./lib/theme";
import { Batch } from "./pages/Batch";
import { Cookies } from "./pages/Cookies";
import { Home } from "./pages/Home";
import { NotFound } from "./pages/NotFound";
import { Privacy } from "./pages/Privacy";

function ScrollToTop() {
  const [location] = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location]);
  return null;
}

export function App() {
  const { theme, toggle } = useTheme();
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-surface focus:px-4 focus:py-2 focus:shadow-pop"
      >
        Перейти к содержимому
      </a>
      <ScrollToTop />
      <Header theme={theme} onToggleTheme={toggle} />
      <main id="main" className="flex-1">
        <Switch>
          <Route path="/" component={Home} />
          <Route path="/batch" component={Batch} />
          <Route path="/privacy" component={Privacy} />
          <Route path="/cookies" component={Cookies} />
          <Route component={NotFound} />
        </Switch>
      </main>
      <Footer />
      <CookieNotice />
      <Toaster
        theme={theme}
        position="bottom-center"
        toastOptions={{
          style: {
            background: "var(--surface)",
            color: "var(--text)",
            border: "1px solid var(--line)",
            borderRadius: 14,
            fontFamily: "inherit",
          },
        }}
      />
    </div>
  );
}
