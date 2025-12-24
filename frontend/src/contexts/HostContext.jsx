import React, { createContext, useContext, useMemo, useState } from "react";

const HostContext = createContext(null);

export function HostProvider({ children }) {
  const [selectedHostId, setSelectedHostId] = useState("");

  const value = useMemo(
    () => ({ selectedHostId, setSelectedHostId }),
    [selectedHostId]
  );

  return <HostContext.Provider value={value}>{children}</HostContext.Provider>;
}

export function useHost() {
  const ctx = useContext(HostContext);
  if (!ctx) throw new Error("useHost must be used within HostProvider");
  return ctx;
}
