import React, { useEffect, useMemo, useState } from "react";
import { getActionRuns, getHosts } from "../api.js";
import { useHost } from "../contexts/HostContext.jsx";
import HostPicker from "../components/HostPicker.jsx";

function badge(status) {
  if (status === "SUCCESS") return "bg-green-900/30 text-green-300 border-green-800";
  if (status === "RUNNING") return "bg-blue-900/30 text-blue-200 border-blue-800";
  return "bg-red-900/20 text-red-300 border-red-800";
}

export default function HistoryPage() {
  const { selectedHostId } = useHost();

  const [hosts, setHosts] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setHosts(await getHosts());
      } catch (e) {
        console.error(e);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const params = {};
        if (selectedHostId) params.host_id = selectedHostId;
        const data = await getActionRuns(params);
        setRuns(data || []);
        setError(null);
        // si cambia el host, selecciona el primer run
        setSelectedRunId((prev) => (prev ? prev : (data?.[0]?.id ?? null)));
      } catch (e) {
        setError("Error al cargar historial");
      }
    })();
  }, [selectedHostId]);

  const selectedRun = useMemo(
    () => runs.find((r) => r.id === selectedRunId) || null,
    [runs, selectedRunId]
  );

  const hostName = useMemo(() => {
    const h = hosts.find((x) => String(x.id) === String(selectedHostId));
    return h ? h.name : (selectedHostId ? String(selectedHostId) : "—");
  }, [hosts, selectedHostId]);

  return (
    <div className="space-y-4">
      <div>
        <div className="text-2xl font-bold">Historial</div>
        <div className="text-sm text-gray-400 mt-1">
          Ejecuciones registradas para el host activo.
        </div>
      </div>

      <HostPicker hosts={hosts} />

      {error && <div className="text-red-400">{error}</div>}

      <div className="flex gap-4">
        {/* izquierda */}
        <div className="flex-[2] rounded-2xl border border-gray-800 bg-gray-900 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 font-semibold">
            Acciones
          </div>

          <div className="overflow-auto">
            <table className="min-w-full divide-y divide-gray-800">
              <thead className="bg-gray-950">
                <tr>
                  <th className="px-4 py-2 text-left text-sm text-gray-300">Acción</th>
                  <th className="px-4 py-2 text-left text-sm text-gray-300">Estado</th>
                  <th className="px-4 py-2 text-left text-sm text-gray-300">Hora</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {runs.map((r) => {
                  const active = r.id === selectedRunId;
                  return (
                    <tr
                      key={r.id}
                      onClick={() => setSelectedRunId(r.id)}
                      className={`cursor-pointer ${
                        active ? "bg-blue-900/20" : "hover:bg-gray-950"
                      }`}
                    >
                      <td className="px-4 py-2">
                        <div className="font-mono text-sm">{r.action_key}</div>
                        <div className="text-xs text-gray-500">
                          {r.summary || "—"}
                        </div>
                      </td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 text-xs rounded-lg border ${badge(r.status)}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-300">
                        {r.executed_at ? new Date(r.executed_at).toLocaleString() : "—"}
                      </td>
                    </tr>
                  );
                })}
                {runs.length === 0 && (
                  <tr>
                    <td className="px-4 py-4 text-gray-500" colSpan={3}>
                      No hay runs (o endpoint no implementado).
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* derecha */}
        <div className="flex-[1] space-y-3">
          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
            <div className="text-sm text-gray-400">Host</div>
            <div className="text-lg font-semibold">{hostName}</div>

            <div className="mt-3 text-sm text-gray-400">Acción</div>
            <div className="font-mono">{selectedRun?.action_key || "—"}</div>

            {selectedRun?.status && (
              <div className="mt-3">
                <span className={`px-2 py-1 text-xs rounded-lg border ${badge(selectedRun.status)}`}>
                  {selectedRun.status}
                </span>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-gray-800 bg-gray-950 p-4">
            <div className="font-semibold mb-2">Detalle</div>

            {/* Si no hay stdout/stderr en la API, mostramos JSON como placeholder */}
            <pre className="text-sm font-mono whitespace-pre-wrap">
              {selectedRun ? JSON.stringify(selectedRun, null, 2) : "Seleccione una ejecución"}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
