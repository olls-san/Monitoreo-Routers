import React, { useEffect, useState } from "react";
import AutomationRules from "./AutomationRules.jsx";
import HostManager from "./HostManager.jsx";

export default function SettingsPage() {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadConfig() {
      try {
        const res = await fetch("/config");
        if (!res.ok) throw new Error("Failed to load");
        setConfig(await res.json());
      } catch (e) {
        setError("Error al cargar configuración");
      }
    }
    loadConfig();
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <div className="text-2xl font-bold">Configuración</div>
        <div className="text-sm text-gray-400 mt-1">
          Config general + gestión de routers y automatizaciones (solo UI, sin cambiar lógica).
        </div>
      </div>

      {error && <div className="text-red-400">{error}</div>}

      <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
        <div className="font-semibold mb-2">Estado del sistema</div>
        {config ? (
          <div className="space-y-2 text-sm text-gray-200">
            <div>Zona horaria scheduler: {config.scheduler_timezone}</div>
            <div>Timeout de peticiones: {config.request_timeout} s</div>
            <div>Telegram configurado: {config.telegram_configured ? "Sí" : "No"}</div>
          </div>
        ) : (
          !error && <div className="text-gray-300">Cargando...</div>
        )}
      </div>

      <HostManager />

      {/* Aquí reusamos tu pantalla original de automatizaciones sin tocar lógica */}
      <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
        <AutomationRules />
      </div>
    </div>
  );
}
