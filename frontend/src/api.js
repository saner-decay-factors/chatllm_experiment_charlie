const API_BASE = window.location.origin;

function getAuthHeaders() {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function sendMessageStream({ message, history, sessionId, onDelta, onSessionId, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, session_id: sessionId }),
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

      if (payload.session_id && onSessionId) {
        onSessionId(payload.session_id);
      }

      if (payload.delta) {
        onDelta(payload.delta);
      }
    }
  }
}

async function listSessions() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Erro ao listar sessoes");
  const data = await response.json();
  return data.sessions;
}

async function createSession() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
    body: "{}",
  });
  if (!response.ok) throw new Error("Erro ao criar sessao");
  return response.json();
}

async function deleteSession(sessionId) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Erro ao deletar sessao");
}

async function getSessionMessages(sessionId) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Erro ao carregar mensagens");
  return response.json();
}

// --- Auth ---

async function authUser(endpoint, email, password) {
  const response = await fetch(`${API_BASE}/api/auth/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
    throw new Error(detail || "Erro de autenticacao");
  }
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("user_email", data.email);
  return data;
}

async function logoutUser() {
  const response = await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
  });
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_email");
  if (!response.ok && response.status !== 401) {
    throw new Error("Erro ao fazer logout");
  }
}

async function checkAuth() {
  const token = localStorage.getItem("access_token");
  if (!token) return null;
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_email");
    return null;
  }
  return response.json();
}
