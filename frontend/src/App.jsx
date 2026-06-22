const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionKey, setCurrentSessionKey] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState([
    {
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  // Carregar sessoes ao iniciar
  useEffect(() => {
    fetchSessions().then((data) => {
      setSessions(data.sessions);
      if (data.sessions.length > 0) {
        const latest = data.sessions[0];
        setCurrentSessionKey(latest.session_key);
        loadSessionMessages(latest.session_key);
      }
    }).catch(() => {});
  }, []);

  const loadSessionMessages = async (sessionKey) => {
    try {
      const data = await fetchSessionMessages(sessionKey);
      const msgs = data.messages.map((m) => ({
        id: createMessageId(),
        role: m.role,
        content: m.content,
      }));
      if (msgs.length === 0) {
        msgs.push({
          id: createMessageId(),
          role: "assistant",
          content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
        });
      }
      setMessages(msgs);
    } catch {
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
    }
  };

  const refreshSessions = useCallback(() => {
    fetchSessions().then((data) => setSessions(data.sessions)).catch(() => {});
  }, []);

  const switchSession = async (sessionKey) => {
    if (busy) return;
    setCurrentSessionKey(sessionKey);
    setError("");
    await loadSessionMessages(sessionKey);
  };

  const newSession = async () => {
    if (busy) return;
    try {
      const data = await createSession();
      setCurrentSessionKey(data.session_key);
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
      setError("");
      refreshSessions();
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

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
        session_key: currentSessionKey,
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
        onDone: (sessionKey) => {
          if (sessionKey) setCurrentSessionKey(sessionKey);
          refreshSessions();
        },
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && !msg.content.trim()
            ? { ...msg, content: "Nao foi possivel obter resposta do modelo agora." }
            : msg
        )
      );
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
      refreshSessions();
    }
  };

  return (
    <main className="app-shell">
      <header className="app-header">
        <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Alternar sidebar">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <rect x="2" y="4" width="16" height="2" rx="1" />
            <rect x="2" y="9" width="16" height="2" rx="1" />
            <rect x="2" y="14" width="16" height="2" rx="1" />
          </svg>
        </button>
        <div className="brand">ChatLLM Lab</div>
      </header>

      <div className="app-body">
        {sidebarOpen && (
          <aside className="sidebar">
            <button className="sidebar-new-btn" onClick={newSession} disabled={busy}>
              + Nova conversa
            </button>
            <div className="sidebar-sessions">
              {sessions.length === 0 && (
                <div className="sidebar-empty">Nenhuma conversa ainda</div>
              )}
              {sessions.map((s) => (
                <button
                  key={s.session_key}
                  className={`sidebar-item ${s.session_key === currentSessionKey ? "active" : ""}`}
                  onClick={() => switchSession(s.session_key)}
                  disabled={busy}
                  title={s.title || "Conversa sem titulo"}
                >
                  {s.title || "Nova conversa"}
                </button>
              ))}
            </div>
          </aside>
        )}

        <div className="chat-area">
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
        </div>
      </div>

      <div className="warning-banner">Lembre-se, voce precisa focar no experimento!!!</div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

