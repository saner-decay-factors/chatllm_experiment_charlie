const { useState } = React;

function Sidebar({ sessions, activeSessionId, onSelectSession, onCreateSession, onDeleteSession }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
      <div className="sidebar-header">
        <button
          className="sidebar-toggle"
          onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? "Expandir barra lateral" : "Recolher barra lateral"}
        >
          {collapsed ? (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <polyline points="7,4 13,9 7,14" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <polyline points="11,4 5,9 11,14" />
            </svg>
          )}
        </button>
        {!collapsed && <span className="sidebar-title">Sessoes</span>}
      </div>

      {!collapsed && (
        <>
          <button className="sidebar-new-chat" onClick={onCreateSession}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="8" y1="2" x2="8" y2="14" />
              <line x1="2" y1="8" x2="14" y2="8" />
            </svg>
            <span>Novo chat</span>
          </button>

          <nav className="sidebar-list" aria-label="Lista de sessoes">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`sidebar-item ${session.id === activeSessionId ? "sidebar-item--active" : ""}`}
                onClick={() => onSelectSession(session.id)}
              >
                <span className="sidebar-item-title">
                  {session.title || "Nova conversa"}
                </span>
                <button
                  className="sidebar-item-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  aria-label={`Deletar sessao ${session.title || "sem titulo"}`}
                  title="Deletar sessao"
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                    <line x1="3" y1="3" x2="11" y2="11" />
                    <line x1="11" y1="3" x2="3" y2="11" />
                  </svg>
                </button>
              </div>
            ))}
          </nav>
        </>
      )}
    </aside>
  );
}