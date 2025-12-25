import React, { useEffect, useMemo, useState } from "react";
import {
  getAutomationRules,
  createAutomationRule,
  updateAutomationRule,
  deleteAutomationRule,
  getHosts,
  getHostActions,
} from "../api.js";

function normalizeActionsToList(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.map((k) => String(k));
  if (typeof raw === "object") return Object.keys(raw).map((k) => String(k));
  return [];
}

function Label({ children }) {
  return <div className="text-xs text-gray-500">{children}</div>;
}

function RuleForm({ initial, hosts, defaultHostId, onSave, onCancel }) {
  const [form, setForm] = useState(() => {
    const base = {
      host_id: defaultHostId || hosts[0]?.id || "",
      action_key: "",
      schedule: "*/10 * * * *",
      enabled: true,
      timeout_seconds: 60,
      retry_enabled: true,
      retry_delay_minutes: 10,
      max_attempts: 2,
      telegram_enabled: false,
    };
    return initial ? { ...base, ...initial } : base;
  });

  const [actionsRaw, setActionsRaw] = useState(null);
  useEffect(() => {
    (async () => {
      if (!form.host_id) return;
      try {
        setActionsRaw(await getHostActions(form.host_id));
      } catch {
        setActionsRaw(null);
      }
    })();
  }, [form.host_id]);

  const actions = useMemo(() => normalizeActionsToList(actionsRaw), [actionsRaw]);

  useEffect(() => {
    if (!form.action_key) return;
    if (actions.length > 0 && !actions.includes(form.action_key)) {
      setForm((p) => ({ ...p, action_key: "" }));
    }
  }, [actions, form.action_key]);

  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    const payload = {
      host_id: Number(form.host_id),
      action_key: String(form.action_key),
      schedule: String(form.schedule),
      enabled: Boolean(form.enabled),
      timeout_seconds: Number(form.timeout_seconds ?? 60),
      retry_enabled: Boolean(form.retry_enabled),
      retry_delay_minutes: Number(form.retry_delay_minutes ?? 10),
      max_attempts: Number(form.max_attempts ?? 2),
      telegram_enabled: Boolean(form.telegram_enabled),
    };
    await onSave(payload);
  };

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
          <Label>Router</Label>
          <select
            value={form.host_id}
            onChange={(e) => set("host_id", e.target.value)}
            className="mt-2 w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-200 text-sm"
            required
          >
            {hosts.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
          <Label>Acción</Label>
          <select
            value={form.action_key}
            onChange={(e) => set("action_key", e.target.value)}
            className="mt-2 w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-200 text-sm"
            required
          >
            <option value="">Seleccione…</option>
            {actions.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="rounded-xl border border-gray-800 bg-gray-950 p-3 md:col-span-2">
          <Label>Schedule (crontab)</Label>
          <input
            value={form.schedule}
            onChange={(e) => set("schedule", e.target.value)}
            className="mt-2 w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-200 text-sm font-mono"
            required
          />
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
          <Label>Timeout (s)</Label>
          <input
            type="number"
            min={1}
            value={form.timeout_seconds}
            onChange={(e) => set("timeout_seconds", e.target.value === "" ? "" : Number(e.target.value))}
            className="mt-2 w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-200 text-sm"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
          <Label>Estado</Label>
          <div className="mt-2 flex flex-wrap gap-3 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.enabled} onChange={(e) => set("enabled", e.target.checked)} />
              <span>Habilitada</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.telegram_enabled}
                onChange={(e) => set("telegram_enabled", e.target.checked)}
              />
              <span>Telegram</span>
            </label>
          </div>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-950 p-3">
          <Label>Reintentos</Label>
          <div className="mt-2 flex items-center gap-3 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.retry_enabled}
                onChange={(e) => set("retry_enabled", e.target.checked)}
              />
              <span>Activar</span>
            </label>
            <input
              type="number"
              min={1}
              value={form.retry_delay_minutes}
              onChange={(e) => set("retry_delay_minutes", e.target.value === "" ? "" : Number(e.target.value))}
              className="w-24 px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-200 text-sm"
              title="Minutos"
            />
            <input
              type="number"
              min={1}
              value={form.max_attempts}
              onChange={(e) => set("max_attempts", e.target.value === "" ? "" : Number(e.target.value))}
              className="w-24 px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-200 text-sm"
              title="Intentos"
            />
            <span className="text-gray-500">min / intentos</span>
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        <button type="submit" className="px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm">
          Guardar
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

export default function AutomationRules({ initialHostId = null }) {
  const [rules, setRules] = useState([]);
  const [hosts, setHosts] = useState([]);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editRule, setEditRule] = useState(null);
  const [filterHostId, setFilterHostId] = useState(initialHostId || "ALL");
  const [q, setQ] = useState("");

  const hostNameById = useMemo(() => {
    const m = new Map();
    (hosts || []).forEach((h) => m.set(String(h.id), h.name));
    return m;
  }, [hosts]);

  const loadData = async () => {
    try {
      const [rulesData, hostsData] = await Promise.all([getAutomationRules(), getHosts()]);
      setRules(Array.isArray(rulesData) ? rulesData : []);
      setHosts(Array.isArray(hostsData) ? hostsData : []);
      setError(null);
    } catch (e) {
      console.error(e);
      setError("Error al cargar reglas");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    // If opened from a router card, lock initial filter
    if (initialHostId) setFilterHostId(String(initialHostId));
  }, [initialHostId]);

  const filteredRules = useMemo(() => {
    let arr = Array.isArray(rules) ? [...rules] : [];
    if (filterHostId && filterHostId !== "ALL") {
      arr = arr.filter((r) => String(r.host_id) === String(filterHostId));
    }
    const qq = q.trim().toLowerCase();
    if (qq) {
      arr = arr.filter((r) => {
        const hn = hostNameById.get(String(r.host_id)) || String(r.host_id);
        const hay = `${hn} ${r.action_key} ${r.schedule || r.cron || ""}`.toLowerCase();
        return hay.includes(qq);
      });
    }
    arr.sort((a, b) => (b.id || 0) - (a.id || 0));
    return arr;
  }, [rules, filterHostId, q, hostNameById]);

  const save = async (payload) => {
    try {
      if (editRule) await updateAutomationRule(editRule.id, payload);
      else await createAutomationRule(payload);
      setShowForm(false);
      setEditRule(null);
      await loadData();
    } catch (e) {
      console.error(e);
      setError("Error al guardar regla: " + (e?.message || ""));
    }
  };

  const del = async (id) => {
    if (!window.confirm("¿Eliminar regla?")) return;
    await deleteAutomationRule(id);
    await loadData();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="text-xl font-bold">Automatizaciones</div>
          <div className="text-sm text-gray-400 mt-1">
            Filtra por router y gestiona reglas programadas.
          </div>
        </div>

        <button
          onClick={() => {
            setEditRule(null);
            setShowForm(true);
          }}
          className="px-3 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm"
        >
          Añadir regla
        </button>
      </div>

      {error && <div className="text-red-400">{error}</div>}

      <div className="flex flex-col md:flex-row gap-3 md:items-center">
        <select
          value={filterHostId}
          onChange={(e) => setFilterHostId(e.target.value)}
          className="px-3 py-2 rounded-lg bg-gray-950 border border-gray-800 text-gray-200 text-sm"
        >
          <option value="ALL">Todos los routers</option>
          {(hosts || []).map((h) => (
            <option key={h.id} value={String(h.id)}>
              {h.name}
            </option>
          ))}
        </select>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar (acción, cron, router)"
          className="flex-1 px-3 py-2 rounded-lg bg-gray-950 border border-gray-800 text-gray-200 text-sm placeholder:text-gray-500"
        />
      </div>

      {showForm && hosts.length > 0 && (
        <div className="rounded-2xl border border-gray-800 bg-gray-950 p-4">
          <div className="font-semibold mb-3">{editRule ? "Editar regla" : "Nueva regla"}</div>
          <RuleForm
            initial={editRule}
            hosts={hosts}
            defaultHostId={filterHostId !== "ALL" ? filterHostId : initialHostId}
            onSave={save}
            onCancel={() => {
              setShowForm(false);
              setEditRule(null);
            }}
          />
        </div>
      )}

      <div className="overflow-auto rounded-2xl border border-gray-800 bg-gray-950">
        <table className="min-w-full divide-y divide-gray-800">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-xs text-gray-300">ID</th>
              <th className="px-4 py-3 text-left text-xs text-gray-300">Router</th>
              <th className="px-4 py-3 text-left text-xs text-gray-300">Acción</th>
              <th className="px-4 py-3 text-left text-xs text-gray-300">Schedule</th>
              <th className="px-4 py-3 text-left text-xs text-gray-300">Estado</th>
              <th className="px-4 py-3 text-right text-xs text-gray-300">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {filteredRules.map((r) => (
              <tr key={r.id} className="hover:bg-gray-900/60">
                <td className="px-4 py-3 text-sm text-gray-300">{r.id}</td>
                <td className="px-4 py-3 text-sm text-gray-200">
                  {hostNameById.get(String(r.host_id)) || r.host_id}
                </td>
                <td className="px-4 py-3 text-sm font-mono text-gray-200">{r.action_key}</td>
                <td className="px-4 py-3 text-sm font-mono text-gray-300">{r.schedule ?? r.cron ?? "—"}</td>
                <td className="px-4 py-3 text-sm">
                  <span
                    className={`px-2 py-1 rounded-lg border text-xs ${
                      r.enabled
                        ? "border-green-800 bg-green-900/20 text-green-200"
                        : "border-gray-800 bg-gray-900 text-gray-400"
                    }`}
                  >
                    {r.enabled ? "ON" : "OFF"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="inline-flex gap-2">
                    <button
                      onClick={() => {
                        setEditRule({ ...r, schedule: r.schedule ?? r.cron ?? "*/10 * * * *" });
                        setShowForm(true);
                      }}
                      className="px-2 py-1 rounded-lg bg-gray-900 border border-gray-800 hover:bg-gray-800 text-gray-200 text-xs"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => del(r.id)}
                      className="px-2 py-1 rounded-lg bg-red-900/20 border border-red-800 hover:bg-red-900/30 text-red-200 text-xs"
                    >
                      Borrar
                    </button>
                  </div>
                </td>
              </tr>
            ))}

            {filteredRules.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-sm text-gray-500">
                  No hay reglas para este filtro.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
