const API_BASE = window.location.origin;

async function sendMessageStream({ message, history, sessionKey, onDelta, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, session_key: sessionKey }),
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body?.detail || "Erro ao enviar mensagem para o servidor.";
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("Streaming nao suportado no ambiente atual.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const rawEvent of events) {
      const line = rawEvent
        .split("\n")
        .find((part) => part.startsWith("data:"));
      if (!line) continue;

      const payloadText = line.slice(5).trim();
      if (!payloadText) continue;

      let payload;
      try {
        payload = JSON.parse(payloadText);
      } catch {
        continue;
      }

      if (payload.error) {
        throw new Error(payload.error);
      }

      if (payload.delta) {
        onDelta(payload.delta);
      }
    }
  }
}

async function fetchSessions() {
  const response = await fetch(`${API_BASE}/api/sessions`);
  if (!response.ok) throw new Error("Erro ao listar sessoes");
  return response.json();
}

async function createSession() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Erro ao criar sessao");
  return response.json();
}

async function deleteSession(sessionKey) {
  const response = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionKey)}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Erro ao deletar sessao");
}

async function fetchSessionMessages(sessionKey) {
  const response = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionKey)}/messages`);
  if (!response.ok) throw new Error("Erro ao carregar mensagens");
  return response.json();
}

async function generateSessionTitle(sessionKey, message) {
  const response = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionKey)}/generate-title`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) throw new Error("Erro ao gerar titulo");
  return response.json();
}

// ---- Auth API ----

function extractErrorDetail(body) {
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((d) => d.msg || String(d)).join("; ");
  }
  return null;
}

let _authToken = localStorage.getItem("auth_token") || null;

function getAuthToken() {
  return _authToken;
}

function setAuthToken(token) {
  _authToken = token;
  if (token) {
    localStorage.setItem("auth_token", token);
  } else {
    localStorage.removeItem("auth_token");
  }
}

async function registerRequest(email, password) {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = extractErrorDetail(body);
    throw new Error(detail || "Erro ao cadastrar");
  }
  const data = await response.json();
  setAuthToken(data.access_token);
  return data;
}

async function loginRequest(email, password) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = extractErrorDetail(body);
    throw new Error(detail || "Erro ao fazer login");
  }
  const data = await response.json();
  setAuthToken(data.access_token);
  return data;
}

async function logoutRequest() {
  if (!_authToken) return;
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${_authToken}`,
    },
  }).catch(() => {});
  setAuthToken(null);
}

async function fetchMe() {
  if (!_authToken) return null;
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${_authToken}` },
  });
  if (!response.ok) {
    setAuthToken(null);
    return null;
  }
  return response.json();
}

function authFetch(url, options = {}) {
  const headers = { ...options.headers };
  if (_authToken) {
    headers["Authorization"] = `Bearer ${_authToken}`;
  }
  return fetch(url, { ...options, headers });
}
