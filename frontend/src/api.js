// API helper functions to interact with the backend

export async function fetchJSON(url, options = {}) {
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

async function safeFetchJSON(url, options = {}, fallbackValue) {
  try {
    return await fetchJSON(url, options);
  } catch (e) {
    // Si el backend/app aún no implementa el endpoint (404), no romper UI
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
  const res = await fetch(`/hosts/${id}`, { method: "DELETE" });
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

// --- History (no implementado aún en backend/app) ---
// ✅ Evita que la UI rompa: devuelve [] si no existe el endpoint.
export function getActionRuns(params = {}) {
  const query = new URLSearchParams(params).toString();
  return safeFetchJSON(`/action-runs${query ? "?" + query : ""}`, {}, []);
}

// --- Automation Rules (no implementado aún en backend/app) ---
// ✅ Evita que la UI rompa: devuelve [] si no existe el endpoint.
export function getAutomationRules() {
  return safeFetchJSON("/automation-rules", {}, []);
}

export function createAutomationRule(data) {
  return safeFetchJSON(
    "/automation-rules",
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
  const res = await fetch(`/automation-rules/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const errText = await res.text().catch(() => "");
    // Si no existe endpoint todavía, no rompas UI
    if (res.status === 404) return null;
    throw new Error(errText || res.statusText);
  }
  return null;
}
