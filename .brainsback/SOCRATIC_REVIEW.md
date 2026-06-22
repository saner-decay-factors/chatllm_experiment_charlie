# Socratic Review Record

> AI-generated. Humans must not edit this file.

## Question 1 — Fluxo de criação de sessão

**Q:** A função `_get_or_create_session` cria uma sessão nova se o `session_key` não for encontrado. Se a sessão já existe, ela é retornada diretamente, independente de quem a criou. Agora que temos autenticação com `user_id`, em que cenário isso poderia causar um problema de segurança? Como você impediria que um usuário acesse a sessão de outro?

**A (developer):** poderia causar um problema de segurança caso um usuario forcasse entrar em um chat_id de outra pessoa por exemplo, o que da pra fazer para mitigar isso é colocar mais uma validação, do tipo, aquele usuario, com aquele token, realmente pertence aquele chat_id?

## Question 2 — Fallback de título vs API externa

**Q:** O título é gerado de duas formas: primeiro tenta uma chamada extra ao OpenRouter com `generate_title()`, e se falhar, usa fallback com as primeiras palavras da mensagem do usuário. O fallback local não gasta tokens nem adiciona latência, mas pode gerar títulos genéricos. Já a chamada extra consome tempo (~1-2s) e tokens. Por que você optou por fazer uma chamada extra especificamente pra gerar o título, em vez de instruir o próprio modelo da conversa a já retornar um título embutido na resposta principal?

**A (developer):** pensando bem, faz mais sentido a forma que voce propos agora, instruir atraves do prompt enviado em toda primeira mensagem de um chat, ao modelo enviar no final de cada resposta, o titulo para aquela conversa, isso faz bastante sentido, até pensei nisso, mas pensei que mandar um prompt especializado para isso fosse mais seguro do modelo enviar o titulo sempre em um mesmo padrao, sem ficar enviesado com respostas e temas e contextos especificos, mas faz mais sentido sim da forma que voce falou, reduz latencia de fato

## Question 3 — Geração de título no stream vs endpoint síncrono

**Q:** Tanto o endpoint `/api/chat` quanto o `/api/chat/stream` geram o título automático. No stream, o título só é gerado depois que a resposta completa já foi enviada pro frontend. Você pensou em alternativa pra exibir o título mais cedo, talvez antes do streaming terminar?

**A (developer):** a forma de exibir um titulo mais cedo que eu pensei antes de pensar implementar dessa forma, foi de, ao inves de criar o titulo com a resposta do modelo, criar o titulo com a mensagem do usuario, ou seja, o usuario manda a mensagem, e antes de a mensagem ser enviada ao modelo, acontece uma chamada extra para colocar o titulo, dai, o titulo ja seria criado antes mesmo do modelo responder, mas nao gostei dessa forma que eu pensei pois vai aumentar o acoplamento temporal do request de envio de mensagem, e geralmente quando um usuario envia a mensagem ele quer a resposta mais rapido do que o titulo sendo criado, adicionar uma chamada externa antes mesmo da resposta ser enviada, se tornou uma escolha ruim no meu entendimento por conta disso, mas é um tradeoff interessante para alguns casos

## Question 4 — Paginação de mensagens

**Q:** A paginação de mensagens usa offset e limit no SQLite. Em chats com centenas de mensagens, o OFFSET pode ficar lento. Você considerou usar cursor-based pagination como alternativa?

**A (developer):** para um projeto com usuarios com muitas e muitas conversas, realmente a paginação por cursor seria mais interessante, mas pensei exatamente no que voce falou no final, no prompt enviado para a IA fazer essa feature eu nao especifiquei se queria por cursor ou nao, justamente por nao importar tanto considerando o volume desse projeto simples de teste

## Question 5 — Segurança da SECRET_KEY

**Q:** A SECRET_KEY no config.py tem um valor hardcoded como fallback. Se alguém fizer deploy sem configurar a variável de ambiente, qualquer pessoa que ler o código consegue forjar JWTs. Como mitigar esse risco?

**A (developer):** colocando CI/CD para poder impedir que isso seja feito, basicamente assim

## Question 6 — Tratamento de erro no hash de senha

**Q:** O hash_password usa bcrypt diretamente, que rejeita senhas > 72 bytes. Hoje isso geraria um 500 sem mensagem clara. Como tratar?

**A (developer):** acho que seria possivel limitar a quantidade de caracteres que o usuario pode criar a senha por exemplo deixar um range de sei la, de 8 a 20

## Question 7 — Logout no frontend

**Q:** O logout atual só limpa o localStorage. O token JWT continua válido até expirar (24h). Você considerou blacklist de tokens ou rotação?

**A (developer):** nao considere esse tipo de estratégia, mais por ser um projeto mais objetivo, mas acho que nesse caso se fosse ter usuarios reais e tudo mais, usaria blacklist que ja sei mais ou menos como funciona e faz sentido para esses casos

## Question 8 — Proteção de sessões entre usuários

**Q:** O endpoint GET /api/sessions/{session_key}/messages não verifica se a sessão pertence ao usuário atual via user_id. Como implementaria essa verificação?

**A (developer):** chat session tem user_id, entao caso um usuario que nao seja aquele userid, tente entrar naquela conversa, o sistema deve bloquear isso, seria basicamente essa condição, o usuario so consegue enviar mensagens para os chats nos quais ele tem a relação FK atraves de user_id

## Question 9 — Sessões órfãs

**Q:** O list_sessions() inclui sessões sem user_id com `user_id.is_(None)` pra compatibilidade. Qual o comportamento esperado pra essas sessões órfãs?

**A (developer):** nesse caso eu cometi um erro, nao deve ser acessivel para todos os usuarios, nao tinha visto esse filter, isso nao é uma boa prática e nao é bom para UX, se ChatSession.user_id for none, entao ele nao aparece pra ninguem, enquanto o user_id for none