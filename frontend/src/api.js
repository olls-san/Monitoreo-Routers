// API helper functions to interact with the backend

// Base URL del backend:
// - En prod: define VITE_API_BASE en .env.production (ej: http://192.168.188.165:8000)
// - En dev: también puedes usar .env (VITE_API_BASE=...)
// - Fallback: intenta mismo host pero puerto 8000
const API_BASE =
  import.meta.env.VITE_API_BASE ||
  `${window.location.protocol}//${window.location.hostname}:8000`;

function toAPIUrl(pathOrUrl) {
  // Si ya viene full URL (http/https), no tocar
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;

  // Asegurar que path empieza con /
  const path = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
  return `${API_BASE}${path}`;
}

export async function fetchJSON(pathOrUrl, options = {}) {
  const url = toAPIUrl(pathOrUrl);

  const res = await fetch(url, options);
  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    const msg = errText || res.statusText || `HTTP ${res.status}`;
    const e = new Error(msg);
    e.status = res.status;
    e.url = url;
    throw e;
  }

  // Algunos endpoints pueden devolver 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

// --- helpers ---
function normalizeCollectionPath(path) {
  // Evita 307 en colecciones FastAPI ("/hosts" -> "/hosts/")
  if (path.endsWith("/")) return path;
  return path + "/";
}

async function safeFetchJSON(pathOrUrl, options = {}, fallbackValue) {
  try {
    return await fetchJSON(pathOrUrl, options);
  } catch (e) {
    // Si el backend aún no implementa el endpoint (404), no romper UI
    if (e && (e.status === 404 || String(e.message).includes("Not Found"))) {
      return fallbackValue;
    }
    throw e;
  }
}

// --- Hosts ---
export function getHosts() {
  return fetchJSON(normalizeCollectionPath("/hosts"));
}

export function createHost(data) {
  return fetchJSON(normalizeCollectionPath("/hosts"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function updateHost(id, data) {
  return fetchJSON(`/hosts/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteHost(id) {
  const url = toAPIUrl(`/hosts/${id}`);
  const res = await fetch(url, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const errText = await res.text().catch(() => "");
    throw new Error(errText || res.statusText);
  }
  return null;
}

// --- Actions ---
export function getHostActions(id) {
  return fetchJSON(`/hosts/${id}/actions`);
}

export function executeHostAction(id, actionKey, params = {}) {
  return fetchJSON(`/hosts/${id}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action_key: actionKey, params }),
  });
}

// --- Health ---
// ✅ backend/app usa /hosts/summary/health (NO /hosts/health)
export function getHostsHealth() {
  return fetchJSON("/hosts/summary/health");
}

export function getHostsHealthStats() {
  return fetchJSON("/hosts/summary/health-stats");
}

export function getHostHealth(id) {
  return fetchJSON(`/hosts/${id}/health`);
}

// --- History ---
// ✅ Evita que la UI rompa: devuelve [] si no existe el endpoint.
export function getActionRuns(params = {}) {
  const query = new URLSearchParams(params).toString();
  return safeFetchJSON(`/action-runs/${query ? "?" + query : ""}`, {}, []);
}

// --- Automation Rules ---
// ✅ Evita que la UI rompa: devuelve [] si no existe el endpoint.
export function getAutomationRules() {
  return safeFetchJSON("/automation-rules/", {}, []);
}

export function createAutomationRule(data) {
  return safeFetchJSON(
    "/automation-rules/",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
    null
  );
}

export function updateAutomationRule(id, data) {
  return safeFetchJSON(
    `/automation-rules/${id}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
    null
  );
}

export async function deleteAutomationRule(id) {
  const url = toAPIUrl(`/automation-rules/${id}`);
  const res = await fetch(url, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const errText = await res.text().catch(() => "");
    // Si no existe endpoint todavía, no rompas UI
    if (res.status === 404) return null;
    throw new Error(errText || res.statusText);
  }
  return null;
}

export function getTelegramSchedule() {
  return fetchJSON("/settings/telegram-schedule");
}

export function updateTelegramSchedule(data) {
  return fetchJSON("/settings/telegram-schedule", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
export function getTelegramSeverity() {
  return fetchJSON("/settings/telegram-severity");
}

export function updateTelegramSeverity(data) {
  return fetchJSON("/settings/telegram-severity", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
