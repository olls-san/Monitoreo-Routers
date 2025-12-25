import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import AutomationRules from "./AutomationRules.jsx";
import HostManager from "./HostManager.jsx";

const TABS = [
  { key: "system", label: "Sistema" },
  { key: "hosts", label: "Gestionar routers" },
  { key: "automation", label: "Automatizaciones" },
];

function TabButton({ active, children, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-2 rounded-lg text-sm border transition ${
        active
          ? "border-blue-700 bg-blue-900/20 text-blue-200"
          : "border-gray-800 bg-gray-900 text-gray-300 hover:bg-gray-800"
      }`}
    >
      {children}
    </button>
  );
}

export default function SettingsPage() {
  const [sp, setSp] = useSearchParams();
  const tab = sp.get("tab") || "system";
  const hostIdParam = sp.get("hostId");

  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadConfig() {
      try {
        const res = await fetch("/config/");
        if (!res.ok) throw new Error("Failed to load");
        setConfig(await res.json());
      } catch (e) {
        setError("Error al cargar configuración");
      }
    }
    loadConfig();
  }, []);

  const subtitle = useMemo(() => {
    if (tab === "hosts") return "Alta / edición / desactivación de routers.";
    if (tab === "automation") return "Reglas programadas por router (filtrables).";
    return "Estado e ideas para organizar configuraciones.";
  }, [tab]);

  const setTab = (t) => {
    const next = new URLSearchParams(sp);
    next.set("tab", t);
    // Mantén hostId solo para automation
    if (t !== "automation") next.delete("hostId");
    setSp(next);
  };

  return (
    <div className="space-y-4">
      <div>
        <div className="text-2xl font-bold">Configuración</div>
        <div className="text-sm text-gray-400 mt-1">{subtitle}</div>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <TabButton key={t.key} active={tab === t.key} onClick={() => setTab(t.key)}>
            {t.label}
          </TabButton>
        ))}
      </div>

      {error && <div className="text-red-400">{error}</div>}

      {tab === "system" && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
            <div className="font-semibold mb-2">Estado del sistema</div>
            {config ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
                  <div className="text-xs text-gray-500">Scheduler TZ</div>
                  <div className="mt-1 text-gray-200">{config.scheduler_timezone}</div>
                </div>
                <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
                  <div className="text-xs text-gray-500">Timeout</div>
                  <div className="mt-1 text-gray-200">{config.request_timeout} s</div>
                </div>
                <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
                  <div className="text-xs text-gray-500">Telegram</div>
                  <div className="mt-1 text-gray-200">{config.telegram_configured ? "Configurado" : "No configurado"}</div>
                </div>
              </div>
            ) : (
              !error && <div className="text-gray-300">Cargando...</div>
            )}
          </div>

          <div className="rounded-2xl border border-gray-800 bg-gray-950 p-4">
            <div className="font-semibold mb-2">Ideas para organizar Configuraciones</div>
            <ul className="text-sm text-gray-300 space-y-2 list-disc pl-5">
              <li><span className="text-gray-200">Sistema</span>: estado backend, scheduler, logs globales, backups DB.</li>
              <li><span className="text-gray-200">Red / VPN</span>: WireGuard (IP, peers), rutas, puertos expuestos.</li>
              <li><span className="text-gray-200">Alertas</span>: Telegram (chatId, reglas), umbrales (offline, latencia).</li>
              <li><span className="text-gray-200">Seguridad</span>: credenciales cifradas, rotación, roles (futuro).</li>
              <li><span className="text-gray-200">Automatizaciones</span>: plantillas de cron, reintentos, límites.</li>
            </ul>
          </div>
        </div>
      )}

      {tab === "hosts" && (
        <div className="space-y-4">
          <HostManager />
        </div>
      )}

      {tab === "automation" && (
        <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
          <AutomationRules initialHostId={hostIdParam ? String(hostIdParam) : null} />
        </div>
      )}
    </div>
  );
}
