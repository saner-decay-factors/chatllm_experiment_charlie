# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
atualmente o sistema nao tem sessoes de chat com base no historico e titulo automatico em uma barra lateral, o usuario ainda nao consegue criar em alternar sessoes atraves de uma barra lateral, o que é fundamental para uma plataforma que tem chats LLMs, alem disso o usuario pode querer entrar em uma sessao que ele ja criou para continuar sua conversa. Além disso, outra funcionalidade que falta seria a de titulo automatico baseado em contexto, quando um usuario inicia uma conversa, a ferramenta deveria preencher automaticamente um titulo baseado no contexto do prompt que ele enviou.

## Steps
- Implementação das sessoes de chat: Primeiramente, devem ser criados os Models necessários para salvar no banco de dados de forma padronizada as conversas, esse salvamento deve ocorrer apos o envio de uma mensagem valida pelo usuário, e penso em cada mensagem ter um chat ou algo do tipo como FK da entidade Chat. Essa primeira parte da implementação é relativamente simples e serve como inicio da implementação da feature de sessões de chat
- Implementação das sessoes de chat(parte 2): Depois de ter implementado a primeira parte, e garantir atraves de testes que teve sucesso na implementação, precisamos agora partir para os endpoints que o frontend vai chamar para essa funcionalidade, deve existir entao uma rota GET para o frontend chamar e carregar os titulos de cada conversa na barra lateral que posteriormente vamos criar no frontend, a partir dai, o usuario pode entrar em uma conversa clicando nos titulos que estarão listados na barra lateral, e isso faz com que ele entre naquele chat, e para isso devemos criar outro endpoint GET para carregar todas as mensagens que tem aquele chat como chat_id, esse endpoint pode te paginação para não ser uma consulta muito pesada em casos de chats cheios. Além desses endpoints, deve ter os outros CRUD mais simples de post para mensagem em uma conversa, caso eu tenha esquecido alguma coisa importante em relação a essa parte, pode complementar implementando algo que acabei nao menionando e que pode ser fundamental para essa funcionalidade
- Implementação das sessoes de chat(parte 3): Depois de terminar a implementação do backend, pode partir para o frontend, que deve chamar o que foi criado no backend e fazer o uma barra lateral simples com os titulos das conversas que foram criados como botoes para serem clicaveis e ter como acessar as conversas, carregando elas paginadas atraves do endpoint criado.
- Título automatico: o backend deve ser capaz de criar titulos automaticos com base no contexto da conversa, se a sessao ainda nao tiver titulo, o titulo deve ser definido automaticamente com base no contexto **possivel ja na primeira resposta do modelo**. Ou seja, na primeira mensagemm, quando o usuario ainda nao enviou nenhuma mensagem valida e envia sua primeira, na resposta do modelo, já é possivel ter um contexto e criar um titulo automatico. Esse titulo automatico deve ser criado enviando um prompt otimizado para uma chamada extra no openrouter, que faz uma chamada especifica passando a resposta da LLM, e um prompt para que essa chamada retorne um texto para aquele chat, sempre com base na reposta que a llm. Esse titulo deve preencher a tabela criada nas etapas anteriores, deve preencher o tituo da conversa que foi criada com o envio da primeira mensage, ja que o titulo fica vazio de inicio

## Success Looks Like
- o sucesso deve ser medido a partir de testes para casos possiveis de chamadas, e qualuer caso que envolva as novas features criadas
## Notes
- 

---

