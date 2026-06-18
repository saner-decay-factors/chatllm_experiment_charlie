const { useState } = React;

function Sidebar({ sessions, activeSessionKey, onSelectSession, onCreateSession, onDeleteSession, sidebarOpen }) {
  const [deleting, setDeleting] = useState(null);

  const handleDelete = async (event, sessionKey) => {
    event.stopPropagation();
    setDeleting(sessionKey);
    try {
      await onDeleteSession(sessionKey);
    } finally {
      setDeleting(null);
    }
  };

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("pt-BR", { month: "short", day: "numeric" });
  };

  return (
    <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onCreateSession} title="Nova conversa">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="8" y1="1" x2="8" y2="15" />
            <line x1="1" y1="8" x2="15" y2="8" />
          </svg>
          Nova conversa
        </button>
      </div>

      <nav className="sidebar-nav">
        {sessions.map((session) => (
          <div
            key={session.session_key}
            className={`session-item ${session.session_key === activeSessionKey ? "active" : ""}`}
            onClick={() => onSelectSession(session.session_key)}
          >
            <span className="session-title" title={session.title}>
              {session.title}
            </span>
            <span className="session-date">{formatDate(session.updated_at)}</span>
            <button
              className="session-delete-btn"
              onClick={(e) => handleDelete(e, session.session_key)}
              disabled={deleting === session.session_key}
              title="Deletar conversa"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                <line x1="1" y1="1" x2="11" y2="11" />
                <line x1="11" y1="1" x2="1" y2="11" />
              </svg>
            </button>
          </div>
        ))}
      </nav>
    </aside>
  );
}