# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
Estou desenvolvendo um ChatLLM utilizando React + FastAPI + OpenRouter. Não está implementado a funcionalidade de sessões de chat, para que o usuário não seja forçado a deixar toda sua conversa em um único chat. Por isso, é necessário a criação de um novo botão dropdown que permite o usuário alternar entre conversas e modelos de LLM. As opções de conversas disponíveis no dropdown de conversa deve conter uma lista de todas as conversas já criadas. Dentre as opções disponíveis, é obrigatório as opções "ChatGPT", "Gemini", e "Claude".

## Steps
- [ ] Ler todos os arquivos presentes nas pastas "backend" e a pasta "frontend"
- [ ] Identificar pontos de inserção no frontend para inserção de novos elementos de tela
- [ ] Inserir novo dropdown no canto inferior direto da tela a respeito da mudança de modelos
- [ ] Identificar pontos de inserção no backend para reaproveitamento da estrutura do OpenRouter
- [ ] Modificar método já utilizado pelo backend para que comporte outro modelo além do definido na .env 
- [ ] Fazer com que, ao selecionar uma das opções de modelo disponíveis, este será o modelo a ser usado para gerar texto
- [ ] Inserir novo dropdown no canto superior direito a respeito da mudança de contexto da conversa
- [ ] Identificar no backend se já existe alguma implementação de banco de dados ou algo para salvar o contexto pré-existente
- [ ] Reaproveitar ou criar estrutura de dados para salvar a conversa atual
- [ ] Fazer com que, ao selecionar uma das opções de conversas disponíveis, toda a conversa seja carregada na interface


## Success Looks Like

- [ ] A interface exibe no canto superior direito um dropdown que permite a troca de conversa.
- [ ] A interface exibe no canto inferior direito um dropdown que permite a troca de modelos.


---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
