const { useState } = React;

function AuthPage({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const cleanedEmail = email.trim();
    const cleanedPassword = password.trim();
    if (!cleanedEmail || !cleanedPassword) return;

    setError("");
    setBusy(true);

    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/signup";
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: cleanedEmail, password: cleanedPassword }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        setError(data?.detail || "Erro de autenticacao");
        return;
      }

      onAuthenticated(data);
    } catch (e) {
      setError("Erro de conexao com o servidor");
    } finally {
      setBusy(false);
    }
  };

  const switchMode = () => {
    setMode((m) => (m === "login" ? "signup" : "login"));
    setError("");
  };

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand">ChatLLM Lab</div>
      </header>

      <div className="auth-page">
        <div className="auth-card">
          <h2>{mode === "login" ? "Entrar" : "Criar conta"}</h2>

          <form onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="auth-email">Email</label>
              <input
                id="auth-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                disabled={busy}
                autoFocus
                autoComplete="email"
              />
            </div>

            <div className="auth-field">
              <label htmlFor="auth-password">Senha</label>
              <input
                id="auth-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "signup" ? "Minimo 6 caracteres" : "Sua senha"}
                disabled={busy}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </div>

            {error && <div className="auth-error">{error}</div>}

            <button type="submit" className="auth-submit" disabled={busy || !email.trim() || !password.trim()}>
              {busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
            </button>
          </form>

          <p className="auth-switch">
            {mode === "login" ? (
              <>Nao tem conta? <button type="button" className="auth-link" onClick={switchMode}>Cadastre-se</button></>
            ) : (
              <>Ja tem conta? <button type="button" className="auth-link" onClick={switchMode}>Faca login</button></>
            )}
          </p>
        </div>
      </div>
    </main>
  );
}