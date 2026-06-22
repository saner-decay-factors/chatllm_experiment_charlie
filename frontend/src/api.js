const API_BASE = window.location.origin;

// --- Token management ---
function getToken() {
  return localStorage.getItem("chatllm_token");
}

function setToken(token) {
  localStorage.setItem("chatllm_token", token);
}

function clearToken() {
  localStorage.removeItem("chatllm_token");
  localStorage.removeItem("chatllm_user");
}

function getUser() {
  const raw = localStorage.getItem("chatllm_user");
  return raw ? JSON.parse(raw) : null;
}

function setUser(user) {
  localStorage.setItem("chatllm_user", JSON.stringify(user));
}

function authHeaders() {
  const token = getToken();
  return token ? { "Authorization": `Bearer ${token}` } : {};
}

// --- Auth API ---
async function registerUser({ email, nome, sobrenome, idade, password }) {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, nome, sobrenome, idade, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Erro ao cadastrar.");
  }
  return response.json();
}

async function loginUser({ email, password }) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Erro ao fazer login.");
  }
  return response.json();
}

async function fetchMe() {
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) return null;
  return response.json();
}

// --- Chat API (with auth) ---
async function sendMessageStream({ message, history, session_key, onDelta, onDone, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message, history, session_key }),
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

      if (payload.done && onDone) {
        onDone(payload.session_key);
      }
    }
  }
}

async function fetchSessions() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    headers: { ...authHeaders() },
  });
  if (!response.ok) throw new Error("Erro ao carregar sessoes.");
  return response.json();
}

async function fetchSessionMessages(sessionKey, page = 1, pageSize = 200) {
  const response = await fetch(
    `${API_BASE}/api/sessions/${encodeURIComponent(sessionKey)}/messages?page=${page}&page_size=${pageSize}`,
    { headers: { ...authHeaders() } }
  );
  if (!response.ok) throw new Error("Erro ao carregar mensagens da sessao.");
  return response.json();
}

async function createSession() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  if (!response.ok) throw new Error("Erro ao criar sessao.");
  return response.json();
}
