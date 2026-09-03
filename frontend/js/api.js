// Central API client — every fetch call in the app goes through here so
// auth headers and error handling stay consistent in one place.
const API_BASE = window.location.origin;

function getToken() { return localStorage.getItem("pms_token"); }
function getRole() { return localStorage.getItem("pms_role"); }
function setSession(token, role) {
  localStorage.setItem("pms_token", token);
  localStorage.setItem("pms_role", role);
}
function clearSession() {
  localStorage.removeItem("pms_token");
  localStorage.removeItem("pms_role");
}

async function api(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }

  if (!res.ok) {
    const message = (data && data.detail) ? data.detail : `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

function requireAuth(expectedRole) {
  const token = getToken();
  const role = getRole();
  if (!token || (expectedRole && role !== expectedRole)) {
    window.location.href = "index.html";
  }
}

function logout() {
  clearSession();
  window.location.href = "index.html";
}

// ---------- Toasts ----------
function toast(message, type = "success") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

function initials(name) {
  if (!name) return "?";
  return name.split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase();
}
