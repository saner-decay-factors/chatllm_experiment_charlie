# Relatório de Implementação

## Resumo
- **Alteração 1**: Sistema de sessões de chat (múltiplas conversas) e seletor de modelos LLM.
- **Alteração 2**: Sistema de autenticação de usuários (cadastro/login/logout) com persistência em SQLite.
- **Status**: Completo

## Alterações Realizadas

### Backend — Sessões e Modelos

1. **`backend/config.py`** — Adicionado dicionário `MODEL_OPTIONS` mapeando nomes amigáveis ("ChatGPT", "Gemini", "Claude", "Gemma") para slugs do OpenRouter.

2. **`backend/models.py`** — Criada entidade `ChatSession`. Adicionado campo `session_id` (FK) em `ChatMessage`.

3. **`backend/schemas/chat.py`** — Adicionado campo opcional `session_key` em `ChatRequest`. Schemas `SessionOut` e `MessageOut`.

4. **`backend/routers/chat.py`** — Endpoints de CRUD de sessões e rota `GET /api/models`.

5. **`backend/main.py`** — Migração automática (ALTER TABLE) para colunas `session_id` e `session_key`.

### Backend — Autenticação

6. **`backend/models.py`** — Novas entidades `User` (id, email, password_hash) e `AuthToken` (id, user_id, token) com hash via `pbkdf2_sha256`.

7. **`backend/schemas/chat.py`** — Novos schemas `AuthSignup`, `AuthLogin`, `AuthResponse`.

8. **`backend/routers/auth.py`** (novo) — Endpoints:
   - `POST /api/auth/signup` — Cadastro com email (valida formato) + senha.
   - `POST /api/auth/login` — Login, retorna token de sessão.
   - `POST /api/auth/logout` — Invalida token.
   - `GET /api/auth/me` — Verifica token e retorna dados do usuário.

9. **`backend/main.py`** — Router de auth registrado.

### Frontend — Autenticação

10. **`frontend/src/api.js`** — Funções `authSignup`, `authLogin`, `authLogout`, `authMe`.

11. **`frontend/src/AuthScreen.jsx`** (novo) — Tela de login/cadastro com alternância entre modos, validação de email e senha, armazenamento do token em `localStorage`.

12. **`frontend/src/App.jsx`** — App verifica token salvo ao montar. Se não autenticado, renderiza `<AuthScreen>`. Se autenticado, mostra o chat com email do usuário no topo e opção de logout no dropdown de sessões.

13. **`frontend/index.html`** — CSS da tela de autenticação e registro do script `AuthScreen.jsx`.

## Estratégia de Testes
- 41 testes existentes passam (pytest).
- Senhas hasheadas com `pbkdf2_sha256` (bcrypt não necessário).
- Tokens de 64 caracteres hex gerados com `secrets.token_hex(32)`.

## Riscos e Acompanhamento
- [ ] Banco SQLite existente pode precisar ser recriado se as migrações falharem.
- [ ] Sessões de chat não estão vinculadas a usuários específicos (qualquer usuário vê todas as sessões). Melhoria futura.
- [ ] Token armazenado em `localStorage` (não `httpOnly cookie`). Adequado para experimento local.

---
**Nota**: Preenchido pelo agente.
