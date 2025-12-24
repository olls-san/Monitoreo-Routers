import React, { useEffect } from "react";
import { useHost } from "../contexts/HostContext.jsx";

export default function HostPicker({ hosts }) {
  const { selectedHostId, setSelectedHostId } = useHost();

  // Si no hay host seleccionado, elige el primero automáticamente cuando carguen.
  useEffect(() => {
    if (!hosts || hosts.length === 0) return;
    if (selectedHostId) return;
    setSelectedHostId(String(hosts[0].id));
  }, [hosts, selectedHostId, setSelectedHostId]);

  return (
    <div className="flex items-center gap-3">
      <div className="text-sm text-gray-300">Host activo</div>
      <select
        value={selectedHostId}
        onChange={(e) => setSelectedHostId(e.target.value)}
        className="px-3 py-2 rounded-lg bg-gray-800 text-gray-100 border border-gray-700"
      >
        {(!hosts || hosts.length === 0) && <option value="">—</option>}
        {hosts?.map((h) => (
          <option key={h.id} value={String(h.id)}>
            {h.name}
          </option>
        ))}
      </select>
    </div>
  );
}
