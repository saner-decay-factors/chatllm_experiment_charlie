const { useState } = React;

const STORAGE_TOKEN_KEY = "chatllm_auth_token";

function getStoredToken() {
  return localStorage.getItem(STORAGE_TOKEN_KEY);
}

function storeToken(token) {
  if (token) {
    localStorage.setItem(STORAGE_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(STORAGE_TOKEN_KEY);
  }
}

function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    const cleanedEmail = email.trim();
    if (!cleanedEmail || !password) {
      setError("Preencha todos os campos.");
      return;
    }

    if (!cleanedEmail.includes("@") || !cleanedEmail.includes(".")) {
      setError("Insira um email valido.");
      return;
    }

    setLoading(true);
    try {
      let result;
      if (mode === "signup") {
        result = await authSignup(cleanedEmail, password);
      } else {
        result = await authLogin(cleanedEmail, password);
      }
      storeToken(result.token);
      onAuth({ token: result.token, email: result.email, userId: result.user_id });
    } catch (err) {
      setError(err.message || "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setMode(mode === "login" ? "signup" : "login");
    setError("");
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-brand">ChatLLM Lab</div>
        <h2 className="auth-title">{mode === "login" ? "Entrar" : "Cadastrar"}</h2>

        {error && <div className="auth-error">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            type="email"
            className="auth-input"
            placeholder="Seu email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            autoFocus
          />
          <input
            type="password"
            className="auth-input"
            placeholder="Senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>

        <div className="auth-toggle">
          {mode === "login" ? (
            <span>
              Nao tem conta?{" "}
              <button className="auth-link-btn" onClick={toggleMode} disabled={loading}>
                Cadastre-se
              </button>
            </span>
          ) : (
            <span>
              Ja tem conta?{" "}
              <button className="auth-link-btn" onClick={toggleMode} disabled={loading}>
                Entrar
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}