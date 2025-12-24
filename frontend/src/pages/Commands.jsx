import React, { useEffect, useMemo, useState } from "react";
import { getHosts, getHostActions, executeHostAction } from "../api.js";
import { useHost } from "../contexts/HostContext.jsx";
import HostPicker from "../components/HostPicker.jsx";
import HostLogsPanel from "../components/HostLogsPanel.jsx";

export default function CommandsPage() {
  const { selectedHostId } = useHost();
  const [hosts, setHosts] = useState([]);
  const [actionsRaw, setActionsRaw] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loadingActions, setLoadingActions] = useState(false);

  useEffect(() => {
    async function loadHosts() {
      try {
        setHosts(await getHosts());
      } catch (e) {
        console.error(e);
        setError("Error al cargar routers");
      }
    }
    loadHosts();
  }, []);

  useEffect(() => {
    async function loadActions() {
      if (!selectedHostId) {
        setActionsRaw([]);
        return;
      }

      setLoadingActions(true);
      setError(null);

      try {
        const data = await getHostActions(selectedHostId);
        setActionsRaw(data);
      } catch (e) {
        console.error(e);
        setError("Error al obtener acciones");
        setActionsRaw([]);
      } finally {
        setLoadingActions(false);
      }
    }

    loadActions();
  }, [selectedHostId]);

  const actionsList = useMemo(() => {
    if (!actionsRaw) return [];
    if (Array.isArray(actionsRaw)) return actionsRaw.map((key) => ({ key, desc: "" }));
    if (typeof actionsRaw === "object")
      return Object.entries(actionsRaw).map(([key, desc]) => ({
        key,
        desc: typeof desc === "string" ? desc : "",
      }));
    return [];
  }, [actionsRaw]);

  const handleExecute = async (actionKey) => {
    setResult(null);
    setError(null);

    if (!selectedHostId) {
      setError("Seleccione un router primero");
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
        <div className="text-2xl font-bold">Comandos</div>
        <div className="text-sm text-gray-400 mt-1">
          Ejecuta acciones del backend sobre el host activo (sin cambiar lógica).
        </div>
      </div>

      <HostPicker hosts={hosts} />

      <div className="flex gap-4">
        {/* izquierda */}
        <div className="flex-[2] space-y-3">
          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
            <div className="font-semibold">Acciones soportadas</div>

            {loadingActions ? (
              <div className="text-gray-300 mt-3">Cargando acciones...</div>
            ) : actionsList.length === 0 ? (
              <div className="text-gray-400 mt-3">No hay acciones disponibles</div>
            ) : (
              <ul className="space-y-2 mt-3">
                {actionsList.map(({ key, desc }) => (
                  <li key={key} className="flex items-center justify-between bg-gray-950 p-3 rounded-xl border border-gray-800">
                    <div className="min-w-0">
                      <div className="font-mono text-sm">{key}</div>
                      {desc ? <div className="text-xs text-gray-500 mt-1">{desc}</div> : null}
                    </div>
                    <button
                      onClick={() => handleExecute(key)}
                      className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm"
                    >
                      Ejecutar
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {error && <div className="text-red-400">{error}</div>}

          <div className="rounded-2xl border border-gray-800 bg-gray-950 p-4">
            <div className="font-semibold mb-2">Salida</div>
            <pre className="text-sm font-mono whitespace-pre-wrap">
              {result ? JSON.stringify(result, null, 2) : "—"}
            </pre>
          </div>
        </div>

        {/* derecha */}
        <div className="flex-[1]">
          <HostLogsPanel title="Logs relacionados a comandos" logs={null} />
        </div>
      </div>
    </div>
  );
}
