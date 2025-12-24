import React, { useEffect, useMemo, useState } from "react";
import { getHosts, getHostActions, executeHostAction } from "../api.js";
import { useHost } from "../contexts/HostContext.jsx";
import HostPicker from "../components/HostPicker.jsx";
import HostLogsPanel from "../components/HostLogsPanel.jsx";

function normalizeActionsToList(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.map((k) => String(k));
  if (typeof raw === "object") return Object.keys(raw).map((k) => String(k));
  return [];
}

// Intenta mapear “rápidos” a keys existentes SIN inventar endpoints ni cambiar lógica.
// Si no encuentra match, no ejecuta y muestra lista real.
function findKey(actions, candidates) {
  const upper = actions.map((a) => a.toUpperCase());
  for (const c of candidates) {
    const idx = upper.findIndex((a) => a.includes(c));
    if (idx >= 0) return actions[idx];
  }
  return null;
}

export default function CheckupsPage() {
  const { selectedHostId } = useHost();
  const [hosts, setHosts] = useState([]);
  const [actionsRaw, setActionsRaw] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loadingActions, setLoadingActions] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setHosts(await getHosts());
      } catch (e) {
        setError("Error al cargar routers");
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      if (!selectedHostId) return;
      setLoadingActions(true);
      setError(null);
      try {
        const data = await getHostActions(selectedHostId);
        setActionsRaw(data);
      } catch (e) {
        setActionsRaw(null);
        setError("Error al obtener acciones");
      } finally {
        setLoadingActions(false);
      }
    })();
  }, [selectedHostId]);

  const actions = useMemo(() => normalizeActionsToList(actionsRaw), [actionsRaw]);

  const quick = useMemo(() => {
    return [
      { label: "Ping", key: findKey(actions, ["PING"]) },
      { label: "USSD saldo", key: findKey(actions, ["SALDO", "USSD"]) },
      { label: "Revisar LTE", key: findKey(actions, ["LTE"]) },
      { label: "Estado interface", key: findKey(actions, ["INTERFACE"]) },
    ];
  }, [actions]);

  const run = async (actionKey) => {
    setResult(null);
    setError(null);
    if (!selectedHostId) {
      setError("Seleccione un host");
      return;
    }
    if (!actionKey) {
      setError("Este chequeo rápido no tiene acción compatible en este host.");
      return;
    }
    try {
      const res = await executeHostAction(selectedHostId, actionKey, {});
      setResult(res);
    } catch (e) {
      setError("Error al ejecutar acción: " + (e?.message || ""));
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <div className="text-2xl font-bold">Chequeos</div>
        <div className="text-sm text-gray-400 mt-1">
          Ejecuta chequeos sobre el host activo. (No cambia lógica, solo UI)
        </div>
      </div>

      <HostPicker hosts={hosts} />

      <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
        <div className="font-semibold">Chequeos rápidos</div>
        <div className="text-sm text-gray-400 mt-1">
          Se habilitan solo si existe una acción compatible en el backend para ese host.
        </div>

        {loadingActions ? (
          <div className="mt-3 text-gray-300">Cargando acciones...</div>
        ) : (
          <div className="mt-4 flex flex-wrap gap-2">
            {quick.map((q) => (
              <button
                key={q.label}
                onClick={() => run(q.key)}
                className={`px-3 py-2 rounded-lg text-sm border ${
                  q.key
                    ? "border-gray-700 bg-gray-800 hover:bg-gray-700"
                    : "border-gray-800 bg-gray-950 text-gray-500 cursor-not-allowed"
                }`}
                title={q.key ? `Acción: ${q.key}` : "No hay acción compatible"}
              >
                {q.label}
              </button>
            ))}
          </div>
        )}

        {/* Si no hay mapping exacto, igual mostramos lista real disponible */}
        <div className="mt-5">
          <div className="text-sm font-semibold text-gray-200">Acciones disponibles (reales)</div>
          {actions.length === 0 ? (
            <div className="text-sm text-gray-500 mt-2">—</div>
          ) : (
            <div className="mt-2 flex flex-wrap gap-2">
              {actions.map((k) => (
                <button
                  key={k}
                  onClick={() => run(k)}
                  className="px-3 py-2 rounded-lg text-sm border border-gray-800 bg-gray-950 hover:border-gray-700"
                >
                  {k}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {error && <div className="text-red-400">{error}</div>}

      {result && (
        <div className="rounded-2xl border border-gray-800 bg-gray-950 p-4">
          <div className="font-semibold mb-2">Salida</div>
          <pre className="text-sm font-mono whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}

      <HostLogsPanel title="Logs relacionados a chequeos" logs={null} />
    </div>
  );
}
