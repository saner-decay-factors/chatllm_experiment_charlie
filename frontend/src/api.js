const API_BASE = window.location.origin;

async function sendMessageStream({ message, history, session_id, onDelta, signal }) {
  const body = { message, history };
  if (session_id) {
    body.session_id = session_id;
  }

  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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
  const resp = await fetch(`${API_BASE}/api/sessions`);
  if (!resp.ok) throw new Error("Falha ao carregar sessoes");
  return resp.json();
}

async function createSession() {
  const resp = await fetch(`${API_BASE}/api/sessions`, { method: "POST" });
  if (!resp.ok) throw new Error("Falha ao criar sessao");
  return resp.json();
}

async function deleteSession(sessionId) {
  const resp = await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: "DELETE" });
  if (!resp.ok) throw new Error("Falha ao deletar sessao");
  return resp.json();
}

async function fetchSessionMessages(sessionId) {
  const resp = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`);
  if (!resp.ok) throw new Error("Falha ao carregar mensagens da sessao");
  return resp.json();
}
