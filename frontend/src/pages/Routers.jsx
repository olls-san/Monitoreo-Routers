import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getHosts, getHostsHealth } from "../api.js";
import { useHost } from "../contexts/HostContext.jsx";
import HostPicker from "../components/HostPicker.jsx";
import HostCard from "../components/HostCard.jsx";

export default function RoutersPage() {
  const navigate = useNavigate();
  const { selectedHostId, setSelectedHostId } = useHost();

  const [hosts, setHosts] = useState([]);
  const [healthMap, setHealthMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      const [hostsData, healthData] = await Promise.all([getHosts(), getHostsHealth()]);
      setHosts(hostsData);

      const map = {};
      healthData.forEach((h) => (map[h.host_id] = h));
      setHealthMap(map);

      setError(null);
    } catch (e) {
      console.error(e);
      setError("Error al cargar hosts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let alive = true;
    loadData();

    const interval = setInterval(async () => {
      try {
        const healthData = await getHostsHealth();
        if (!alive) return;
        const map = {};
        healthData.forEach((h) => (map[h.host_id] = h));
        setHealthMap(map);
      } catch (e) {
        console.error("Health refresh failed:", e);
      }
    }, 5000);

    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, []);

  const filteredHosts = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return hosts;
    return hosts.filter((h) => {
      const hay = `${h.name} ${h.ip} ${h.router_type || ""}`.toLowerCase();
      return hay.includes(q);
    });
  }, [hosts, query]);

  return (
    <div className="space-y-4">
      <div>
        <div className="text-2xl font-bold">Routers</div>
        <div className="text-sm text-gray-400 mt-1">
          Todo lo que ejecutes en Historial / Chequeos / Comandos se aplica al host seleccionado.
        </div>
      </div>

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3 flex-1">
          <HostPicker hosts={hosts} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar router (nombre / IP / tipo)"
            className="w-full md:max-w-[420px] px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-sm text-gray-200 placeholder:text-gray-500"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate("/settings?tab=hosts")}
            className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm"
          >
            Gestionar routers
          </button>
          <button
            onClick={() => navigate("/settings?tab=automation")}
            className="px-3 py-2 rounded-lg bg-gray-950 border border-gray-800 hover:border-gray-700 text-sm"
          >
            Automatizaciones
          </button>
        </div>
      </div>

      {error && <div className="text-red-400">{error}</div>}

      {loading ? (
        <div className="text-gray-300">Cargando...</div>
      ) : (
        <div
          className="grid gap-4"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}
        >
          {filteredHosts.map((host) => {
            const health = healthMap[host.id] || {};
            return (
              <HostCard
                key={host.id}
                host={host}
                health={health}
                selected={String(selectedHostId) === String(host.id)}
                onSelect={() => setSelectedHostId(String(host.id))}
                onGoCheckups={() => {
                  setSelectedHostId(String(host.id));
                  navigate("/checkups");
                }}
                onGoCommands={() => {
                  setSelectedHostId(String(host.id));
                  navigate("/commands");
                }}
                onGoHistory={() => {
                  setSelectedHostId(String(host.id));
                  navigate("/history");
                }}
                onGoAutomations={() => {
                  setSelectedHostId(String(host.id));
                  navigate(`/settings?tab=automation&hostId=${encodeURIComponent(String(host.id))}`);
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
