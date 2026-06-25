const API_BASE = window.location.origin;

async function sendMessageStream({ message, history, model, session_key, onDelta, onDone, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, model, session_key }),
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
  const response = await fetch(`${API_BASE}/api/sessions`);
  if (!response.ok) throw new Error("Erro ao carregar sessoes.");
  return response.json();
}

async function fetchSessionMessages(sessionKey) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionKey}/messages`);
  if (!response.ok) throw new Error("Erro ao carregar mensagens da sessao.");
  return response.json();
}

async function deleteSession(sessionKey) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionKey}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Erro ao deletar sessao.");
  return response.json();
}

async function updateSessionTitle(sessionKey, title) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionKey}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) throw new Error("Erro ao atualizar sessao.");
  return response.json();
}

async function fetchModels() {
  const response = await fetch(`${API_BASE}/api/models`);
  if (!response.ok) throw new Error("Erro ao carregar modelos.");
  return response.json();
}
