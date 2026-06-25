const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

const WELCOME_MSG = {
  id: createMessageId(),
  role: "assistant",
  content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
};

function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const justCreatedRef = useRef(false);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  const fetchSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch {
      // silencio
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const onNewSession = () => {
    if (busy) return;
    setActiveSessionId(null);
    setMessages([WELCOME_MSG]);
    setText("");
    setError("");
  };

  const onDeleteSession = async (event, sessionId) => {
    event.stopPropagation();
    if (busy) return;
    try {
      await deleteSession(sessionId);
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setMessages([WELCOME_MSG]);
      }
      await fetchSessions();
    } catch (err) {
      setError("Erro ao deletar sessao.");
    }
  };

  const onSelectSession = async (sessionId) => {
    if (busy) return;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
    setActiveSessionId(sessionId);
    setError("");
    try {
      const msgs = await getSessionMessages(sessionId);
      setMessages(
        msgs.length === 0
          ? [WELCOME_MSG]
          : msgs.map((m) => ({ id: `msg-${m.id}`, role: m.role, content: m.content }))
      );
    } catch (err) {
      setError("Erro ao carregar mensagens.");
      setMessages([WELCOME_MSG]);
    }
  };

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    setError("");

    let sessionId = activeSessionId;

    // First message in a new session: create session first
    if (sessionId === null) {
      try {
        const created = await createSession("New Chat");
        sessionId = created.id;
        setActiveSessionId(sessionId);
        justCreatedRef.current = true;
      } catch (err) {
        setError("Erro ao criar sessao.");
        return;
      }
    }

    const userMessage = { id: createMessageId(), role: "user", content: cleaned };
    const assistantMessageId = createMessageId();

    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantMessageId, role: "assistant", content: "" },
    ]);
    setText("");
    setBusy(true);
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await sendMessageStream({
        message: cleaned,
        history: chatHistory,
        session_id: sessionId,
        signal: abortController.signal,
        onDelta: (delta) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: `${msg.content}${delta}` }
                : msg
            )
          );
        },
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && !msg.content.trim()
            ? { ...msg, content: "Nao foi possivel obter resposta do modelo agora." }
            : msg
        )
      );

      // Generate title after first message in a new session
      if (justCreatedRef.current) {
        justCreatedRef.current = false;
        try {
          await generateSessionTitle(cleaned, sessionId);
          await fetchSessions();
        } catch {
          // se falhar, ignorar
        }
      }
    } catch (err) {
      const aborted = err?.name === "AbortError";
      if (!aborted) {
        setError(err.message || "Falha inesperada ao gerar resposta.");
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: msg.content.trim() ? msg.content : "Nao foi possivel obter resposta do modelo agora." }
              : msg
          )
        );
      } else {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId && !msg.content.trim()
              ? { ...msg, content: "Resposta interrompida." }
              : msg
          )
        );
      }
    } finally {
      abortControllerRef.current = null;
      setBusy(false);
      fetchSessions();
    }
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <span>Sessões</span>
          <button className="sidebar-new-btn" onClick={onNewSession} disabled={busy}>
            + Novo
          </button>
        </div>
        <div className="sidebar-list">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`sidebar-item${s.id === activeSessionId ? " active" : ""}`}
              onClick={() => onSelectSession(s.id)}
            >
              <span className="sidebar-item-title">{s.title}</span>
              <button className="sidebar-item-delete" onClick={(e) => onDeleteSession(e, s.id)} title="Deletar sessao">
                ✕
              </button>
            </div>
          ))}
        </div>
      </aside>

      <div className="main-area">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
        </header>

        <section className="messages" aria-live="polite" ref={messagesRef}>
          <div className="messages-inner">
            {messages.map((msg) => (
              <article key={msg.id} className={`bubble ${msg.role}`}>
                <MessageContent content={msg.content} />
              </article>
            ))}
          </div>
        </section>

        <Composer
          text={text}
          busy={busy}
          error={error}
          onChangeText={setText}
          onSubmit={onSubmit}
          onStop={onStop}
        />

        <div className="warning-banner">Lembre-se, voce precisa focar no experimento!!!</div>
      </div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

