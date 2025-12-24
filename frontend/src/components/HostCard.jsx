import React from "react";

function statusFromHealth(health) {
  if (health?.online == null) return "SIN RESPUESTA";
  if (health.online === false) return "OFFLINE";
  // online true
  const ms = health?.latency_ms;
  if (typeof ms === "number" && ms > 90) return "WARNING";
  return "ONLINE";
}

function badgeClasses(status) {
  if (status === "ONLINE") return "bg-green-900/40 text-green-300 border-green-800";
  if (status === "WARNING") return "bg-yellow-900/30 text-yellow-300 border-yellow-800";
  if (status === "OFFLINE") return "bg-red-900/30 text-red-300 border-red-800";
  return "bg-gray-800 text-gray-300 border-gray-700";
}

function latencyPill(ms) {
  if (ms == null) return { label: "—", cls: "bg-gray-800 text-gray-300 border-gray-700" };
  const v = Math.round(ms);
  if (v <= 35) return { label: `${v} ms`, cls: "bg-green-900/30 text-green-300 border-green-800" };
  if (v <= 90) return { label: `${v} ms`, cls: "bg-yellow-900/20 text-yellow-300 border-yellow-800" };
  return { label: `${v} ms`, cls: "bg-red-900/20 text-red-300 border-red-800" };
}

export default function HostCard({
  host,
  health,
  selected,
  onSelect,
  onGoCheckups,
  onGoCommands,
  onGoHistory,
}) {
  const status = statusFromHealth(health);
  const lat = latencyPill(health?.latency_ms ?? null);

  return (
    <div
      onClick={onSelect}
      className={`rounded-2xl border cursor-pointer transition p-4 bg-gray-900 ${
        selected ? "border-blue-600 shadow-lg shadow-blue-900/20" : "border-gray-800 hover:border-gray-700"
      }`}
    >
      <div className="flex items-start gap-2">
        <div className={`px-2 py-1 text-xs rounded-lg border ${badgeClasses(status)}`}>
          {status}
        </div>

        <div className={`ml-auto px-2 py-1 text-xs rounded-lg border ${lat.cls}`}>
          {lat.label}
        </div>
      </div>

      <div className="mt-3">
        <div className="text-lg font-semibold">{host.name}</div>
        <div className="text-sm text-gray-400 mt-1">
          {host.ip} • {host.type}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
          <div className="text-xs text-gray-500">Último check</div>
          <div className="text-gray-200 mt-1">—</div>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
          <div className="text-xs text-gray-500">Última acción</div>
          <div className="text-gray-200 mt-1">—</div>
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onGoCheckups();
          }}
          className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm"
        >
          Chequeo
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onGoCommands();
          }}
          className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm"
        >
          Comando
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onGoHistory();
          }}
          className="ml-auto px-3 py-2 rounded-lg bg-gray-950 border border-gray-800 hover:border-gray-700 text-sm"
        >
          Ver historial →
        </button>
      </div>
    </div>
  );
}
