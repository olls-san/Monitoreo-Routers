import React, { useEffect, useState } from "react";
import { getHosts, createHost, updateHost, deleteHost } from "../api.js";

function HostForm({ initial, onSave, onCancel }) {
  const [form, setForm] = useState(
    initial
      ? { name: initial.name, ip: initial.ip, type: initial.type, username: initial.username, password: "" }
      : { name: "", ip: "", type: "mikrotik", username: "", password: "" }
  );

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await onSave(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div>
        <label className="block text-sm">Nombre</label>
        <input name="name" value={form.name} onChange={handleChange} className="w-full p-2 text-black" required />
      </div>
      <div>
        <label className="block text-sm">IP</label>
        <input name="ip" value={form.ip} onChange={handleChange} className="w-full p-2 text-black" required />
      </div>
      <div>
        <label className="block text-sm">Tipo</label>
        <select name="type" value={form.type} onChange={handleChange} className="w-full p-2 text-black">
          <option value="mikrotik">MikroTik</option>
        </select>
      </div>
      <div>
        <label className="block text-sm">Usuario</label>
        <input name="username" value={form.username} onChange={handleChange} className="w-full p-2 text-black" required />
      </div>
      <div>
        <label className="block text-sm">Contraseña</label>
        <input name="password" type="password" value={form.password} onChange={handleChange} className="w-full p-2 text-black" required />
      </div>

      <div className="flex space-x-2">
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">Guardar</button>
        <button type="button" onClick={onCancel} className="px-4 py-2 bg-gray-500 text-white rounded-lg">Cancelar</button>
      </div>
    </form>
  );
}

export default function HostManager() {
  const [hosts, setHosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editHost, setEditHost] = useState(null);
  const [error, setError] = useState(null);

  const loadHosts = async () => {
    setLoading(true);
    try {
      const data = await getHosts();
      setHosts(data || []);
      setError(null);
    } catch (e) {
      console.error(e);
      setError("Error al cargar hosts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHosts();
  }, []);

  const handleSave = async (data) => {
    try {
      if (editHost) await updateHost(editHost.id, data);
      else await createHost(data);
      setShowForm(false);
      setEditHost(null);
      await loadHosts();
    } catch (e) {
      setError("Error al guardar host: " + (e?.message || ""));
    }
  };

  const handleDelete = async (host) => {
    if (!window.confirm("¿Eliminar host?")) return;
    await deleteHost(host.id);
    await loadHosts();
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <div className="font-semibold">Gestionar routers</div>
        <button
          onClick={() => {
            setEditHost(null);
            setShowForm(true);
          }}
          className="px-3 py-2 bg-green-600 text-white rounded-lg text-sm"
        >
          Añadir
        </button>
      </div>

      {error && <div className="text-red-400">{error}</div>}

      {showForm && (
        <div className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
          <HostForm
            initial={editHost}
            onSave={handleSave}
            onCancel={() => {
              setShowForm(false);
              setEditHost(null);
            }}
          />
        </div>
      )}

      {loading ? (
        <div className="text-gray-300">Cargando...</div>
      ) : (
        <div className="rounded-2xl border border-gray-800 bg-gray-900 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-800">
            <thead className="bg-gray-950">
              <tr>
                <th className="px-4 py-2 text-left text-sm text-gray-300">Nombre</th>
                <th className="px-4 py-2 text-left text-sm text-gray-300">IP</th>
                <th className="px-4 py-2 text-left text-sm text-gray-300">Tipo</th>
                <th className="px-4 py-2 text-right text-sm text-gray-300">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {hosts.map((host) => (
                <tr key={host.id} className="hover:bg-gray-950">
                  <td className="px-4 py-2">{host.name}</td>
                  <td className="px-4 py-2">{host.ip}</td>
                  <td className="px-4 py-2">{host.type}</td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <button
                      onClick={() => {
                        setEditHost(host);
                        setShowForm(true);
                      }}
                      className="px-2 py-1 bg-yellow-600 text-white rounded"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => handleDelete(host)}
                      className="px-2 py-1 bg-red-600 text-white rounded"
                    >
                      Borrar
                    </button>
                  </td>
                </tr>
              ))}
              {hosts.length === 0 && (
                <tr>
                  <td className="px-4 py-4 text-gray-500" colSpan={4}>
                    No hay hosts.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
