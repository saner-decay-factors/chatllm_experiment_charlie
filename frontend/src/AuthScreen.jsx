const { useState } = React;

function AuthScreen({ onAuthSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    const cleanedEmail = email.trim();
    if (!cleanedEmail || !password) {
      setError("Preencha todos os campos");
      return;
    }

    setLoading(true);
    try {
      if (mode === "login") {
        await loginRequest(cleanedEmail, password);
      } else {
        await registerRequest(cleanedEmail, password);
      }
      onAuthSuccess();
    } catch (err) {
      setError(err.message || "Erro inesperado");
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode(mode === "login" ? "register" : "login");
    setError("");
  };

  return (
    <div className="auth-overlay">
      <div className="auth-card">
        <h1 className="auth-title">ChatLLM Lab</h1>
        <h2 className="auth-subtitle">
          {mode === "login" ? "Entrar" : "Criar conta"}
        </h2>

        {error && <div className="note error">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            className="auth-input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            autoFocus
            disabled={loading}
            autoComplete="email"
          />
          <input
            className="auth-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Senha"
            disabled={loading}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
          <button className="auth-btn" type="submit" disabled={loading}>
            {loading
              ? "Aguarde..."
              : mode === "login"
              ? "Entrar"
              : "Criar conta"}
          </button>
        </form>

        <p className="auth-switch">
          {mode === "login" ? (
            <>
              Nao tem conta?{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); switchMode(); }}>
                Cadastre-se
              </a>
            </>
          ) : (
            <>
              Ja tem conta?{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); switchMode(); }}>
                Fazer login
              </a>
            </>
          )}
        </p>
      </div>
    </div>
  );
}