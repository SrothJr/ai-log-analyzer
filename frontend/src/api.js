const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "The backend request failed.");
  }
  return body;
}

export function uploadLog(file) {
  const form = new FormData();
  form.append("file", file);
  return request("/api/jobs", { method: "POST", body: form });
}

export function startJob(id) {
  return request(`/api/jobs/${id}/start`, { method: "POST" });
}

export function getJob(id) {
  return request(`/api/jobs/${id}`);
}

export function getFindings(id) {
  return request(`/api/jobs/${id}/findings`);
}
