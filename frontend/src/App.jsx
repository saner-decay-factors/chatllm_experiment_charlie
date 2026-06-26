const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [user, setUser] = useState(null); // { user_id, email, token } | null
  const [authChecked, setAuthChecked] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const initializedRef = useRef(false);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Check for saved token on mount
  useEffect(() => {
    if (authChecked) return;
    (async () => {
      const savedToken = localStorage.getItem("auth_token");
      if (savedToken) {
        setAuthToken(savedToken);
        const me = await authGetMe();
        if (me) {
          setUser(me);
        } else {
          localStorage.removeItem("auth_token");
          clearAuthToken();
        }
      }
      setAuthChecked(true);
    })();
  }, [authChecked]);

  // Load sessions when user is known
  useEffect(() => {
    if (!authChecked) return;
    if (initializedRef.current) return;
    initializedRef.current = true;

    (async () => {
      try {
        const list = await fetchSessions();
        setSessions(list);
        if (list.length > 0) {
          setActiveSessionId(list[0].id);
          const msgs = await fetchSessionMessages(list[0].id);
          setMessages(msgs.map((m) => ({
            id: createMessageId(),
            role: m.role,
            content: m.content,
          })));
        } else {
          const created = await createSession();
          setSessions([created]);
          setActiveSessionId(created.id);
        }
      } catch (e) {
        setError("Falha ao carregar sessoes: " + e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [authChecked, user]);

  const switchSession = useCallback(async (sessionId) => {
    if (sessionId === activeSessionId) return;
    setActiveSessionId(sessionId);
    setMessages([]);
    setError("");
    try {
      const msgs = await fetchSessionMessages(sessionId);
      setMessages(msgs.map((m) => ({
        id: createMessageId(),
        role: m.role,
        content: m.content,
      })));
    } catch (e) {
      setError("Falha ao carregar mensagens: " + e.message);
    }
  }, [activeSessionId]);

  const handleCreateSession = useCallback(async () => {
    try {
      const created = await createSession();
      setSessions((prev) => [created, ...prev]);
      setActiveSessionId(created.id);
      setMessages([]);
      setError("");
    } catch (e) {
      setError("Falha ao criar sessao: " + e.message);
    }
  }, []);

  const handleDeleteSession = useCallback(async (sessionId) => {
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter((s) => s.id !== sessionId);
        if (remaining.length > 0) {
          const next = remaining[0];
          setActiveSessionId(next.id);
          const msgs = await fetchSessionMessages(next.id);
          setMessages(msgs.map((m) => ({
            id: createMessageId(),
            role: m.role,
            content: m.content,
          })));
        } else {
          const created = await createSession();
          setSessions([created]);
          setActiveSessionId(created.id);
          setMessages([]);
        }
      }
    } catch (e) {
      setError("Falha ao deletar sessao: " + e.message);
    }
  }, [activeSessionId, sessions]);

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const refreshSessions = useCallback(async () => {
    try {
      const list = await fetchSessions();
      setSessions(list);
    } catch {
      // silent
    }
  }, []);

  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    setError("");
    const userMessage = { id: createMessageId(), role: "user", content: cleaned };
    const assistantMessageId = createMessageId();
    const currentSessionId = activeSessionId;

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
        session_id: currentSessionId,
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
      refreshSessions();
    }
  };

  const handleAuthenticated = (data) => {
    localStorage.setItem("auth_token", data.token);
    setAuthToken(data.token);
    setUser({ user_id: data.user_id, email: data.email });
    // Reset session state
    initializedRef.current = false;
    setLoading(true);
    setSessions([]);
    setActiveSessionId(null);
    setMessages([]);
  };

  const handleLogout = async () => {
    try {
      await authLogout();
    } catch {
      // ignore
    }
    localStorage.removeItem("auth_token");
    clearAuthToken();
    setUser(null);
    setSessions([]);
    setActiveSessionId(null);
    setMessages([]);
    initializedRef.current = false;
    setLoading(true);
  };

  // Not authenticated yet
  if (!authChecked) {
    return (
      <main className="app-shell">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
        </header>
        <div className="loading-indicator">Carregando...</div>
      </main>
    );
  }

  if (user === null) {
    return <AuthPage onAuthenticated={handleAuthenticated} />;
  }

  if (loading) {
    return (
      <main className="app-shell">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
        </header>
        <div className="loading-indicator">Carregando...</div>
      </main>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={switchSession}
        onCreateSession={handleCreateSession}
        onDeleteSession={handleDeleteSession}
        onLogout={handleLogout}
        userEmail={user.email}
      />

      <main className="app-shell">
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
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

