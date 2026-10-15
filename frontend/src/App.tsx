import { useEffect } from "react";
import { Toaster } from "sonner";
import { Route, Switch, useLocation } from "wouter";

import { Autopilot } from "./components/Autopilot";
import { CookieNotice } from "./components/CookieNotice";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { useReveal } from "./lib/reveal";
import { useTheme } from "./lib/theme";
import { Batch } from "./pages/Batch";
import { Cookies } from "./pages/Cookies";
import { Home } from "./pages/Home";
import { NotFound } from "./pages/NotFound";
import { Privacy } from "./pages/Privacy";
import { Sandbox } from "./pages/Sandbox";
import { SelfCheck } from "./pages/SelfCheck";

function ScrollToTop() {
  const [location] = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location]);
  return null;
}

export function App() {
  const { theme, toggle } = useTheme();
  useReveal();
  return (
    <div className="flex min-h-dvh flex-col">
      <div className="topo" aria-hidden="true" />
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
          <Route path="/sandbox" component={Sandbox} />
          <Route path="/selfcheck" component={SelfCheck} />
          <Route path="/privacy" component={Privacy} />
          <Route path="/cookies" component={Cookies} />
          <Route component={NotFound} />
        </Switch>
      </main>
      <Footer />
      <CookieNotice />
      <Autopilot />
      <Toaster
        theme={theme}
        position="bottom-center"
        toastOptions={{
          style: {
            background: "var(--surface)",
            color: "var(--text)",
            border: "1px solid var(--line)",
            borderRadius: 16,
            fontFamily: "inherit",
          },
        }}
      />
    </div>
  );
}
