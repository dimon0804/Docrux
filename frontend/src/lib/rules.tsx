import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

import { type DocType, fetchDocTypes, fetchRules, type Rule } from "./api";

type Reference = {
  rules: Map<string, Rule>;
  ruleList: Rule[];
  docTypes: DocType[];
  loaded: boolean;
  failed: boolean;
};

const empty: Reference = {
  rules: new Map(),
  ruleList: [],
  docTypes: [],
  loaded: false,
  failed: false,
};

const ReferenceContext = createContext<Reference>(empty);

/** Справочные данные сервиса: пункты Положения и типы документов. */
export function ReferenceProvider({ children }: { children: ReactNode }) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [docTypes, setDocTypes] = useState<DocType[]>([]);
  const [status, setStatus] = useState<"loading" | "ok" | "failed">("loading");

  useEffect(() => {
    const abort = new AbortController();
    Promise.all([fetchRules(abort.signal), fetchDocTypes(abort.signal)])
      .then(([loadedRules, loadedTypes]) => {
        setRules(loadedRules);
        setDocTypes(loadedTypes);
        setStatus("ok");
      })
      .catch(() => {
        if (!abort.signal.aborted) setStatus("failed");
      });
    return () => abort.abort();
  }, []);

  const value = useMemo<Reference>(
    () => ({
      rules: new Map(rules.map((rule) => [rule.number, rule])),
      ruleList: rules,
      docTypes,
      loaded: status === "ok",
      failed: status === "failed",
    }),
    [rules, docTypes, status],
  );

  return <ReferenceContext.Provider value={value}>{children}</ReferenceContext.Provider>;
}

export function useReference() {
  return useContext(ReferenceContext);
}
