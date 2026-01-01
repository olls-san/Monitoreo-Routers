import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import AutomationRules from "./AutomationRules.jsx";
import HostManager from "./HostManager.jsx";
import {
  getTelegramSchedule,
  updateTelegramSchedule,
  getTelegramSeverity,
  updateTelegramSeverity,
} from "../api.js";

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

  // Telegram schedule
  const [tgSched, setTgSched] = useState(null);
  const [tgSaving, setTgSaving] = useState(false);
  const [tgMsg, setTgMsg] = useState(null);

  // Telegram severity
  const [sevCfg, setSevCfg] = useState(null);
  const [sevSaving, setSevSaving] = useState(false);
  const [sevMsg, setSevMsg] = useState(null);

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

  useEffect(() => {
    async function loadSchedule() {
      try {
        const s = await getTelegramSchedule();
        setTgSched(s);
      } catch (e) {
        setTgSched(null);
      }
    }
    loadSchedule();
  }, []);

  useEffect(() => {
    async function loadSeverity() {
      try {
        const s = await getTelegramSeverity();
        setSevCfg(s);
      } catch (e) {
        setSevCfg(null);
      }
    }
    loadSeverity();
  }, []);

  const subtitle = useMemo(() => {
    if (tab === "hosts") return "Alta / edición / desactivación de routers.";
    if (tab === "automation") return "Reglas programadas por router (filtrables).";
    return "Estado e ideas para organizar configuraciones.";
  }, [tab]);

  const setTab = (t) => {
    const next = new URLSearchParams(sp);
    next.set("tab", t);
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
          {/* Estado del sistema */}
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
                  <div className="mt-1 text-gray-200">
                    {config.telegram_configured ? "Configurado" : "No configurado"}
                  </div>
                </div>
              </div>
            ) : (
              !error && <div className="text-gray-300">Cargando...</div>
            )}
          </div>

          {/* Telegram – Resumen diario */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
            <div className="font-semibold mb-2">Telegram – Resumen diario</div>

            {!tgSched ? (
              <div className="text-gray-300 text-sm">Cargando configuración...</div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={!!tgSched.enabled}
                    onChange={(e) => setTgSched({ ...tgSched, enabled: e.target.checked })}
                  />
                  <div className="text-sm text-gray-200">Habilitado</div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
                    <div className="text-xs text-gray-500">Hora</div>
                    <input
                      className="mt-2 w-full rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-sm text-gray-200"
                      type="number"
                      min={0}
                      max={23}
                      value={tgSched.hour ?? 0}
                      onChange={(e) => setTgSched({ ...tgSched, hour: Number(e.target.value) })}
                    />
                  </div>

                  <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
                    <div className="text-xs text-gray-500">Minuto</div>
                    <input
                      className="mt-2 w-full rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-sm text-gray-200"
                      type="number"
                      min={0}
                      max={59}
                      value={tgSched.minute ?? 0}
                      onChange={(e) => setTgSched({ ...tgSched, minute: Number(e.target.value) })}
                    />
                  </div>

                  <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
                    <div className="text-xs text-gray-500">Timezone</div>
                    <select
                      className="mt-2 w-full rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-sm text-gray-200"
                      value={tgSched.timezone ?? "UTC"}
                      onChange={(e) => setTgSched({ ...tgSched, timezone: e.target.value })}
                    >
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">America/New_York</option>
                      <option value="America/Havana">America/Havana</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    disabled={tgSaving}
                    onClick={async () => {
                      setTgSaving(true);
                      setTgMsg(null);
                      try {
                        const saved = await updateTelegramSchedule(tgSched);
                        setTgSched(saved);
                        setTgMsg("Guardado y reprogramado.");
                      } catch (e) {
                        setTgMsg("Error guardando la configuración.");
                      } finally {
                        setTgSaving(false);
                      }
                    }}
                    className="px-3 py-2 rounded-lg text-sm border border-gray-700 bg-gray-950 text-gray-200 hover:bg-gray-800 disabled:opacity-60"
                  >
                    Guardar
                  </button>

                  {tgMsg && <div className="text-sm text-gray-300">{tgMsg}</div>}
                </div>
              </div>
            )}
          </div>

          {/* Telegram – Severidad (umbrales) */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
            <div className="font-semibold mb-2">Telegram – Severidad (umbrales)</div>

            {!sevCfg ? (
              <div className="text-gray-300 text-sm">Cargando configuración...</div>
            ) : (
              <div className="space-y-4">
                {[
                  { key: "critical", label: "CRÍTICO" },
                  { key: "high", label: "ALTA" },
                  { key: "medium", label: "MEDIA" },
                ].map(({ key, label }) => (
                  <div key={key} className="rounded-xl border border-gray-800 bg-gray-950 p-3">
                    <div className="text-sm text-gray-200 mb-2">{label}</div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <div className="text-xs text-gray-500">Días (validos_dias ≤)</div>
                        <input
                          className="mt-2 w-full rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-sm text-gray-200"
                          type="number"
                          min={0}
                          value={sevCfg?.[key]?.days ?? 0}
                          onChange={(e) =>
                            setSevCfg({
                              ...sevCfg,
                              [key]: { ...sevCfg[key], days: Number(e.target.value) },
                            })
                          }
                        />
                      </div>

                      <div>
                        <div className="text-xs text-gray-500">Datos MB (datos_mb &lt;)</div>
                        <input
                          className="mt-2 w-full rounded-lg bg-gray-900 border border-gray-700 px-3 py-2 text-sm text-gray-200"
                          type="number"
                          min={0}
                          value={sevCfg?.[key]?.data_mb ?? 0}
                          onChange={(e) =>
                            setSevCfg({
                              ...sevCfg,
                              [key]: { ...sevCfg[key], data_mb: Number(e.target.value) },
                            })
                          }
                        />
                      </div>
                    </div>
                  </div>
                ))}

                <div className="flex items-center gap-3">
                  <button
                    disabled={sevSaving}
                    onClick={async () => {
                      setSevSaving(true);
                      setSevMsg(null);
                      try {
                        const saved = await updateTelegramSeverity(sevCfg);
                        setSevCfg(saved);
                        setSevMsg("Guardado.");
                      } catch (e) {
                        setSevMsg("Error guardando la configuración.");
                      } finally {
                        setSevSaving(false);
                      }
                    }}
                    className="px-3 py-2 rounded-lg text-sm border border-gray-700 bg-gray-950 text-gray-200 hover:bg-gray-800 disabled:opacity-60"
                  >
                    Guardar
                  </button>

                  {sevMsg && <div className="text-sm text-gray-300">{sevMsg}</div>}
                </div>
              </div>
            )}
          </div>

          {/* Ideas */}
          <div className="rounded-2xl border border-gray-800 bg-gray-950 p-4">
            <div className="font-semibold mb-2">Ideas para organizar Configuraciones</div>
            <ul className="text-sm text-gray-300 space-y-2 list-disc pl-5">
              <li>
                <span className="text-gray-200">Sistema</span>: estado backend, scheduler, logs globales, backups DB.
              </li>
              <li>
                <span className="text-gray-200">Red / VPN</span>: WireGuard (IP, peers), rutas, puertos expuestos.
              </li>
              <li>
                <span className="text-gray-200">Alertas</span>: Telegram (chatId, reglas), umbrales (offline, latencia).
              </li>
              <li>
                <span className="text-gray-200">Seguridad</span>: credenciales cifradas, rotación, roles (futuro).
              </li>
              <li>
                <span className="text-gray-200">Automatizaciones</span>: plantillas de cron, reintentos, límites.
              </li>
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
