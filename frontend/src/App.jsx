const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

const WELCOME_MESSAGE = {
  id: createMessageId(),
  role: "assistant",
  content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
};

function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionKey, setActiveSessionKey] = useState(null);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [initializing, setInitializing] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const titleGeneratedRef = useRef({});

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  const loadSessions = useCallback(async () => {
    try {
      const data = await fetchSessions();
      setSessions(data);
      return data;
    } catch {
      return [];
    }
  }, []);

  const loadMessages = useCallback(async (sessionKey) => {
    try {
      const data = await fetchSessionMessages(sessionKey);
      if (data && data.length > 0) {
        setMessages(
          data.map((m) => ({ id: createMessageId(), role: m.role, content: m.content }))
        );
      } else {
        setMessages([WELCOME_MESSAGE]);
      }
    } catch {
      setMessages([WELCOME_MESSAGE]);
    }
  }, []);

  // Initialize: load sessions, create one if none exist
  useEffect(() => {
    (async () => {
      setInitializing(true);
      let data = await loadSessions();
      if (data.length === 0) {
        const newSession = await createSession();
        data = [newSession];
        setSessions(data);
      }
      const target = data[0];
      setActiveSessionKey(target.session_key);
      await loadMessages(target.session_key);
      setInitializing(false);
    })();
  }, []);

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

  const handleCreateSession = async () => {
    const newSession = await createSession();
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionKey(newSession.session_key);
    setMessages([WELCOME_MESSAGE]);
    titleGeneratedRef.current[newSession.session_key] = false;
  };

  const handleSelectSession = async (sessionKey) => {
    if (sessionKey === activeSessionKey) return;
    abortControllerRef.current?.abort();
    setBusy(false);
    setError("");
    setActiveSessionKey(sessionKey);
    await loadMessages(sessionKey);
  };

  const handleDeleteSession = async (sessionKey) => {
    await deleteSession(sessionKey);
    const remaining = sessions.filter((s) => s.session_key !== sessionKey);
    setSessions(remaining);
    if (remaining.length > 0) {
      const target = remaining[0];
      setActiveSessionKey(target.session_key);
      await loadMessages(target.session_key);
    } else {
      const newSession = await createSession();
      setSessions([newSession]);
      setActiveSessionKey(newSession.session_key);
      setMessages([WELCOME_MESSAGE]);
    }
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

    const currentSessionKey = activeSessionKey;
    if (!titleGeneratedRef.current[currentSessionKey]) {
      titleGeneratedRef.current[currentSessionKey] = true;
    }

    try {
      await sendMessageStream({
        message: cleaned,
        history: chatHistory,
        sessionKey: currentSessionKey,
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
      // Refresh sessions to update ordering
      loadSessions().then((data) => setSessions(data));
    }
  };

  if (initializing) {
    return (
      <main className="app-shell">
        <div className="loading-screen">Carregando...</div>
      </main>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        activeSessionKey={activeSessionKey}
        onSelectSession={handleSelectSession}
        onCreateSession={handleCreateSession}
        onDeleteSession={handleDeleteSession}
        sidebarOpen={sidebarOpen}
      />

      <main className="app-shell">
        <header className="app-header">
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} title="Alternar barra lateral">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="4" x2="15" y2="4" />
              <line x1="3" y1="9" x2="15" y2="9" />
              <line x1="3" y1="14" x2="15" y2="14" />
            </svg>
          </button>
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
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

