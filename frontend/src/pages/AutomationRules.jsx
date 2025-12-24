import React, { useEffect, useMemo, useState } from 'react';
import {
  getAutomationRules,
  createAutomationRule,
  updateAutomationRule,
  deleteAutomationRule,
  getHosts,
  getHostActions,
} from '../api.js';

function normalizeActionsToList(raw) {
  // raw puede ser:
  // - array: ["VER_LOGS_USSD", "CONSULTAR_SALDO"]
  // - objeto: { "VER_LOGS_USSD": "desc", ... }
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.map((k) => String(k));
  if (typeof raw === 'object') return Object.keys(raw).map((k) => String(k));
  return [];
}

function RuleForm({ initial, hosts, onSave, onCancel }) {
  const [form, setForm] = useState(
    initial || {
      host_id: hosts[0]?.id || '',
      action_key: '',
      schedule: '* * * * *', // backend espera "schedule"
      enabled: true,
      timeout_seconds: 60,
      retry_enabled: false,
      retry_delay_minutes: 10,
      max_attempts: 2,
      telegram_enabled: false,
    }
  );

  const [actionsRaw, setActionsRaw] = useState(null);

  useEffect(() => {
    async function loadActions() {
      if (!form.host_id) return;
      try {
        const acts = await getHostActions(form.host_id);
        setActionsRaw(acts);
      } catch (e) {
        console.error(e);
        setActionsRaw(null);
      }
    }
    loadActions();
  }, [form.host_id]);

  const actions = useMemo(() => normalizeActionsToList(actionsRaw), [actionsRaw]);

  // Si cambias de host, y la acción actual no existe, resetea
  useEffect(() => {
    if (!form.action_key) return;
    if (actions.length > 0 && !actions.includes(form.action_key)) {
      setForm((prev) => ({ ...prev, action_key: '' }));
    }
  }, [actions, form.action_key]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;

    // Convertimos números a number desde el form para evitar strings "5"
    if (type === 'number') {
      const num = value === '' ? '' : Number(value);
      setForm((prev) => ({ ...prev, [name]: num }));
      return;
    }

    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Enviar payload ya alineado con backend
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
    <form onSubmit={handleSubmit} className="space-y-2">
      <div>
        <label className="block text-sm">Router</label>
        <select
          name="host_id"
          value={form.host_id}
          onChange={handleChange}
          className="w-full p-2 text-black"
          required
        >
          {hosts.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm">Acción</label>
        <select
          name="action_key"
          value={form.action_key}
          onChange={handleChange}
          className="w-full p-2 text-black"
          required
        >
          <option value="">Seleccione...</option>
          {actions.map((key) => (
            <option key={key} value={key}>
              {key}
            </option>
          ))}
        </select>
        {/* Debug opcional: si quieres ver el raw que llega */}
        {/* <pre className="text-xs text-gray-400">{JSON.stringify(actionsRaw, null, 2)}</pre> */}
      </div>

      <div>
        <label className="block text-sm">Schedule (crontab)</label>
        <input
          name="schedule"
          value={form.schedule}
          onChange={handleChange}
          className="w-full p-2 text-black"
          required
        />
      </div>

      <div>
        <label className="block text-sm">Timeout (segundos)</label>
        <input
          type="number"
          name="timeout_seconds"
          value={form.timeout_seconds}
          onChange={handleChange}
          className="w-full p-2 text-black"
          min="1"
        />
      </div>

      <div className="flex items-center space-x-2">
        <label>
          <input type="checkbox" name="enabled" checked={form.enabled} onChange={handleChange} /> Habilitada
        </label>
        <label>
          <input type="checkbox" name="telegram_enabled" checked={form.telegram_enabled} onChange={handleChange} /> Telegram
        </label>
      </div>

      <div className="flex space-x-2 items-center">
        <label className="flex items-center space-x-1">
          <input type="checkbox" name="retry_enabled" checked={form.retry_enabled} onChange={handleChange} />
          <span>Reintentos</span>
        </label>

        <input
          type="number"
          name="retry_delay_minutes"
          value={form.retry_delay_minutes}
          onChange={handleChange}
          className="w-20 p-2 text-black"
          min="1"
        />

        <input
          type="number"
          name="max_attempts"
          value={form.max_attempts}
          onChange={handleChange}
          className="w-20 p-2 text-black"
          min="1"
        />

        <span className="text-sm">minutos / intentos</span>
      </div>

      <div className="flex space-x-2">
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">
          Guardar
        </button>
        <button type="button" onClick={onCancel} className="px-4 py-2 bg-gray-500 text-white rounded">
          Cancelar
        </button>
      </div>
    </form>
  );
}

export default function CheckupsPage() {
  const [rules, setRules] = useState([]);
  const [hosts, setHosts] = useState([]);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editRule, setEditRule] = useState(null);

  const loadData = async () => {
    try {
      const [rulesData, hostsData] = await Promise.all([getAutomationRules(), getHosts()]);
      setRules(rulesData || []);
      setHosts(hostsData || []);
      setError(null);
    } catch (e) {
      console.error(e);
      setError('Error al cargar reglas');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSave = async (payload) => {
    try {
      if (editRule) {
        await updateAutomationRule(editRule.id, payload);
      } else {
        await createAutomationRule(payload);
      }
      setShowForm(false);
      setEditRule(null);
      await loadData();
    } catch (e) {
      console.error(e);
      setError('Error al guardar regla: ' + (e?.message || ''));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar regla?')) return;
    await deleteAutomationRule(id);
    await loadData();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Automatizaciones</h1>
        <button
          onClick={() => {
            setEditRule(null);
            setShowForm(true);
          }}
          className="px-4 py-2 bg-green-600 text-white rounded"
        >
          Añadir
        </button>
      </div>

      {error && <div className="text-red-500">{error}</div>}

      {showForm && hosts.length > 0 && (
        <RuleForm
          initial={editRule}
          hosts={hosts}
          onSave={handleSave}
          onCancel={() => {
            setShowForm(false);
            setEditRule(null);
          }}
        />
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-2 text-left">ID</th>
              <th className="px-4 py-2 text-left">Router</th>
              <th className="px-4 py-2 text-left">Acción</th>
              <th className="px-4 py-2 text-left">Schedule</th>
              <th className="px-4 py-2 text-left">Estado</th>
              <th className="px-4 py-2">Acciones</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-700">
            {rules.map((rule) => (
              <tr key={rule.id} className="hover:bg-gray-800">
                <td className="px-4 py-2">{rule.id}</td>
                <td className="px-4 py-2">{rule.host_id}</td>
                <td className="px-4 py-2">{rule.action_key}</td>
                <td className="px-4 py-2">{rule.schedule ?? rule.cron ?? '—'}</td>
                <td className="px-4 py-2">{rule.enabled ? 'On' : 'Off'}</td>
                <td className="px-4 py-2 space-x-2">
                  <button
                    onClick={() => {
                      // Adaptamos regla existente al form
                      setEditRule({
                        ...rule,
                        schedule: rule.schedule ?? rule.cron ?? '* * * * *',
                      });
                      setShowForm(true);
                    }}
                    className="px-2 py-1 bg-yellow-600 text-white rounded"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    className="px-2 py-1 bg-red-600 text-white rounded"
                  >
                    Borrar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>

        </table>
      </div>
    </div>
  );
}
