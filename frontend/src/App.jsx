const { useEffect, useMemo, useRef, useState, useCallback } = React;

const AUTH_TOKEN_KEY = "chatllm_auth_token";

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function setAuthToken(token) {
  if (token) localStorage.setItem(AUTH_TOKEN_KEY, token);
  else localStorage.removeItem(AUTH_TOKEN_KEY);
}

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);
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
  const [currentModel, setCurrentModel] = useState("Gemma");
  const [models, setModels] = useState(["Gemma", "ChatGPT", "Gemini", "Claude"]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionKey, setCurrentSessionKey] = useState(null);
  const [showSessionDropdown, setShowSessionDropdown] = useState(false);
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const sessionDropdownRef = useRef(null);
  const modelDropdownRef = useRef(null);
  const initialLoadRef = useRef(true);
  const sessionJustChangedRef = useRef(false);

  // Check stored auth on mount
  useEffect(() => {
    const storedToken = getAuthToken();
    if (storedToken) {
      authMe(storedToken).then((data) => {
        if (data) {
          setUser({ token: storedToken, email: data.email, userId: data.user_id });
        } else {
          setAuthToken(null);
        }
        setAuthReady(true);
      }).catch(() => {
        setAuthToken(null);
        setAuthReady(true);
      });
    } else {
      setAuthReady(true);
    }
  }, []);

  const handleAuth = useCallback((userData) => {
    setUser(userData);
  }, []);

  const handleLogout = useCallback(() => {
    const token = getAuthToken();
    if (token) {
      authLogout(token).catch(() => {});
    }
    setAuthToken(null);
    setUser(null);
    setMessages([{
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    }]);
    setCurrentSessionKey(null);
    setSessions([]);
  }, []);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  // Load sessions and models on mount
  useEffect(() => {
    if (!user) return;
    fetchModels().then((data) => {
      if (data.models && data.models.length) {
        // Merge API models with defaults, ensuring Gemma is always present
        const allModels = [...new Set([...data.models, "ChatGPT", "Gemini", "Claude", "Gemma"])];
        setModels(allModels);
      }
    }).catch(() => {});
    loadSessions();
  }, [user]);

  const loadSessions = useCallback(() => {
    const token = getAuthToken();
    if (!token) return;
    fetchSessions(token).then((data) => {
      setSessions(data);
      if (initialLoadRef.current && data.length > 0) {
        // Load the most recent session
        const mostRecent = data[0];
        setCurrentSessionKey(mostRecent.session_key);
        fetchSessionMessages(mostRecent.session_key, token).then((msgs) => {
          if (msgs.length > 0) {
            setMessages(msgs.map((m) => ({
              id: createMessageId(),
              role: m.role,
              content: m.content,
            })));
          } else {
            setMessages([{
              id: createMessageId(),
              role: "assistant",
              content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
            }]);
          }
        }).catch(() => {});
        initialLoadRef.current = false;
      } else if (data.length === 0) {
        initialLoadRef.current = false;
      }
    }).catch(() => {});
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

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (sessionDropdownRef.current && !sessionDropdownRef.current.contains(e.target)) {
        setShowSessionDropdown(false);
      }
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target)) {
        setShowModelDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleNewSession = useCallback(() => {
    setCurrentSessionKey(null);
    setMessages([{
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    }]);
    setShowSessionDropdown(false);
  }, []);

  const handleSelectSession = useCallback(async (sessionKey) => {
    if (busy) return;
    const token = getAuthToken();
    setShowSessionDropdown(false);
    setCurrentSessionKey(sessionKey);
    sessionJustChangedRef.current = true;
    try {
      const msgs = await fetchSessionMessages(sessionKey, token);
      setMessages(msgs.length > 0
        ? msgs.map((m) => ({
            id: createMessageId(),
            role: m.role,
            content: m.content,
          }))
        : [{
            id: createMessageId(),
            role: "assistant",
            content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
          }]
      );
    } catch {
      setError("Erro ao carregar conversa.");
    }
  }, [busy]);

  const handleDeleteSession = useCallback(async (e, sessionKey) => {
    e.stopPropagation();
    const token = getAuthToken();
    try {
      await deleteSession(sessionKey, token);
      // Reload sessions and reset if current session was deleted
      const data = await fetchSessions(token);
      setSessions(data);
      if (currentSessionKey === sessionKey) {
        handleNewSession();
      }
    } catch {
      setError("Erro ao deletar conversa.");
    }
  }, [currentSessionKey, handleNewSession]);

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

    // Store session_key from what we know before the stream completes
    const currentKeySnapshot = currentSessionKey;

    try {
      await sendMessageStream({
        message: cleaned,
        model: currentModel,
        session_key: currentSessionKey,
        token: getAuthToken(),
        history: chatHistory,
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
        onDone: (newSessionKey) => {
          if (newSessionKey && newSessionKey !== currentKeySnapshot) {
            setCurrentSessionKey(newSessionKey);
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
      loadSessions();
    }
  };

  const currentSession = sessions.find((s) => s.session_key === currentSessionKey);

  if (!authReady) {
    return null;
  }

  if (!user) {
    return <AuthScreen onAuth={handleAuth} />;
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand">ChatLLM Lab</div>
        <div className="header-center">
          <span className="header-user">{user.email}</span>
          <button className="logout-btn" onClick={handleLogout} title="Sair">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">
              <path d="M5 1H3a1 1 0 00-1 1v10a1 1 0 001 1h2M9 10l3-3-3-3M12 7H5" stroke="currentColor" strokeWidth="1.5" fill="none"/>
            </svg>
            Sair
          </button>
        </div>
        <div className="header-right" ref={sessionDropdownRef}>
          <button
            className="dropdown-btn session-btn"
            onClick={() => setShowSessionDropdown(!showSessionDropdown)}
            title="Selecionar conversa"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M2 2.5A1.5 1.5 0 013.5 1h5a1.5 1.5 0 011.5 1.5V3h2.5A1.5 1.5 0 0114 4.5v7a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 012 11.5v-9zM3.5 2a.5.5 0 00-.5.5v9a.5.5 0 00.5.5h9a.5.5 0 00.5-.5v-7a.5.5 0 00-.5-.5H10V4.5A1.5 1.5 0 008.5 3h-5z"/>
            </svg>
            <span className="dropdown-label">
              {currentSession ? currentSession.title : "Nova conversa"}
            </span>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
              <path d="M3 4.5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" fill="none"/>
            </svg>
          </button>
          {showSessionDropdown && (
            <div className="dropdown-menu session-menu">
              <button className="dropdown-item new-session-item" onClick={handleNewSession}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">
                  <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="2" fill="none"/>
                </svg>
                Nova conversa
              </button>
              <div className="dropdown-divider"></div>
              {sessions.length === 0 && (
                <div className="dropdown-empty">Nenhuma conversa salva</div>
              )}
              {sessions.map((s) => (
                <div
                  key={s.session_key}
                  className={`dropdown-item session-item ${s.session_key === currentSessionKey ? "active" : ""}`}
                  onClick={() => handleSelectSession(s.session_key)}
                >
                  <div className="session-item-content">
                    <div className="session-item-title">{s.title}</div>
                    <div className="session-item-meta">
                      {s.message_count} mensagens
                    </div>
                  </div>
                  <button
                    className="session-delete-btn"
                    onClick={(e) => handleDeleteSession(e, s.session_key)}
                    title="Deletar conversa"
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
                      <path d="M2 3h8M4.5 3V2a.5.5 0 01.5-.5h2a.5.5 0 01.5.5v1M3 3v7a1 1 0 001 1h4a1 1 0 001-1V3" stroke="currentColor" strokeWidth="1.2" fill="none"/>
                    </svg>
                  </button>
                </div>
              ))}
              <div className="dropdown-divider"></div>
              <button className="dropdown-item logout-item" onClick={handleLogout}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">
                  <path d="M5 1H3a1 1 0 00-1 1v10a1 1 0 001 1h2M9 10l3-3-3-3M12 7H5" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                </svg>
                Sair
              </button>
            </div>
          )}
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

      <div className="composer-area" ref={modelDropdownRef}>
        <div className="model-selector">
          <button
            className="dropdown-btn model-btn"
            onClick={() => setShowModelDropdown(!showModelDropdown)}
            title="Selecionar modelo"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">
              <path d="M7 0a7 7 0 100 14A7 7 0 007 0zM5.5 4.5l4 2.5-4 2.5v-5z"/>
            </svg>
            <span>{currentModel}</span>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
              <path d="M3 4.5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" fill="none"/>
            </svg>
          </button>
          {showModelDropdown && (
            <div className="dropdown-menu model-menu">
              {models.map((m) => (
                <div
                  key={m}
                  className={`dropdown-item ${m === currentModel ? "active" : ""}`}
                  onClick={() => { setCurrentModel(m); setShowModelDropdown(false); }}
                >
                  {m}
                </div>
              ))}
            </div>
          )}
        </div>

        <Composer
          text={text}
          busy={busy}
          error={error}
          onChangeText={setText}
          onSubmit={onSubmit}
          onStop={onStop}
        />
      </div>

      <div className="warning-banner">Lembre-se, você precisa focar no experimento!!!</div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

