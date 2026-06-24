const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await authUser(mode === "login" ? "login" : "register", email, password);
      onAuth();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1>ChatLLM Lab</h1>
        <h2>{mode === "login" ? "Entrar" : "Cadastrar"}</h2>
        {error && <div className="auth-error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={busy}
            autoFocus
          />
          <input
            type="password"
            placeholder="Senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            disabled={busy}
          />
          <button type="submit" disabled={busy || !email.trim() || !password}>
            {busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>
        <p className="auth-toggle">
          {mode === "login" ? (
            <>Nao tem conta? <a href="#" onClick={(e) => { e.preventDefault(); setMode("register"); setError(""); }}>Cadastre-se</a></>
          ) : (
            <>Ja tem conta? <a href="#" onClick={(e) => { e.preventDefault(); setMode("login"); setError(""); }}>Faca login</a></>
          )}
        </p>
      </div>
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const currentSessionIdRef = useRef(null);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  // Verificar autenticacao ao montar
  useEffect(() => {
    checkAuth().then((u) => {
      if (u) setUser(u);
      setAuthChecked(true);
    });
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

  useEffect(() => {
    if (user) loadSessions();
  }, [user]);

  const loadSessions = async () => {
    try {
      const list = await listSessions();
      setSessions(list);
    } catch {
      // ignora
    }
  };

  const loadSessionMessages = useCallback(async (sessionId) => {
    try {
      const data = await getSessionMessages(sessionId);
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
      setActiveSessionId(sessionId);
      currentSessionIdRef.current = sessionId;
    } catch {
      // ignora
    }
  }, []);

  const handleNewSession = async () => {
    try {
      const session = await createSession();
      setActiveSessionId(session.id);
      currentSessionIdRef.current = session.id;
      setMessages([
        {
          id: createMessageId(),
          role: "assistant",
          content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
        },
      ]);
      await loadSessions();
    } catch {
      // ignora
    }
  };

  const handleSelectSession = (sessionId) => {
    if (busy) return;
    loadSessionMessages(sessionId);
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (busy) return;
    try {
      await deleteSession(sessionId);
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        currentSessionIdRef.current = null;
        setMessages([
          {
            id: createMessageId(),
            role: "assistant",
            content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
          },
        ]);
      }
      await loadSessions();
    } catch {
      // ignora
    }
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch { /* ignora */ }
    setUser(null);
    setSessions([]);
    setActiveSessionId(null);
    currentSessionIdRef.current = null;
    setMessages([
      {
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      },
    ]);
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
        sessionId: currentSessionIdRef.current,
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
        onSessionId: (sid) => {
          if (!currentSessionIdRef.current) {
            currentSessionIdRef.current = sid;
            setActiveSessionId(sid);
            loadSessions();
          }
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
    }
  };

  if (!authChecked) return null;

  if (!user) {
    return <AuthScreen onAuth={() => checkAuth().then(setUser)} />;
  }

  return (
    <div className="app-layout">
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={handleNewSession} disabled={busy}>
            + Nova conversa
          </button>
        </div>
        <nav className="sidebar-list">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`sidebar-item ${s.id === activeSessionId ? 'active' : ''}`}
              onClick={() => handleSelectSession(s.id)}
            >
              <span className="sidebar-item-title">
                {s.title || 'Nova conversa'}
              </span>
              <button
                className="sidebar-item-delete"
                onClick={(e) => handleDeleteSession(e, s.id)}
                title="Excluir sessao"
              >
                &times;
              </button>
            </div>
          ))}
        </nav>
      </aside>

      <main className="app-shell">
        <header className="app-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label="Alternar barra lateral"
          >
            {'\u2630'}
          </button>
          <div className="brand">ChatLLM Lab</div>
          <div className="user-info">
            <span className="user-email">{user?.email}</span>
            <button className="logout-btn" onClick={handleLogout} title="Sair">
              Sair
            </button>
          </div>
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

