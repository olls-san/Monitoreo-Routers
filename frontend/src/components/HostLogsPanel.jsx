import React, { useMemo, useState } from "react";
import { useHost } from "../contexts/HostContext.jsx";

const LEVELS = ["ALL", "INFO", "OK", "WARN", "ERROR"];

export default function HostLogsPanel({ logs = null, title = "Logs del host" }) {
  const { selectedHostId } = useHost();
  const [level, setLevel] = useState("ALL");

  const filtered = useMemo(() => {
    if (!Array.isArray(logs)) return [];
    return logs
      .filter((l) => String(l.hostId) === String(selectedHostId))
      .filter((l) => (level === "ALL" ? true : l.level === level));
  }, [logs, selectedHostId, level]);

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-950 p-4">
      <div className="flex items-center gap-2">
        <div className="font-semibold">{title}</div>
        <div className="ml-auto flex gap-2">
          {LEVELS.map((lv) => (
            <button
              key={lv}
              onClick={() => setLevel(lv)}
              className={`px-2 py-1 rounded-lg text-xs border ${
                level === lv
                  ? "border-blue-700 bg-blue-900/20 text-blue-200"
                  : "border-gray-800 bg-gray-900 text-gray-300 hover:bg-gray-800"
              }`}
            >
              {lv}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-gray-800 bg-black p-3 text-sm font-mono overflow-auto max-h-[420px]">
        {!logs ? (
          <div className="text-gray-500">Sin logs aún (placeholder).</div>
        ) : filtered.length === 0 ? (
          <div className="text-gray-500">No hay logs para este host / filtro.</div>
        ) : (
          filtered.map((l, idx) => (
            <div key={idx} className="flex gap-3 py-1">
              <div className="text-gray-500 w-[180px] shrink-0">{l.timestamp}</div>
              <div className="w-[70px] shrink-0">{l.level}</div>
              <div className="text-gray-400 w-[120px] shrink-0">{l.source}</div>
              <div className="text-gray-200">{l.message}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
