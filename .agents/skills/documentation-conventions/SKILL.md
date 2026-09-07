---
name: documentation-conventions
description: "Valida contratos técnicos e estabelece padrões antes da escrita do Draw Nível 3: analisa requisitos do Nível 2, consulta documentação oficial de APIs integradas, compila convenções com header YAML em .agents/conventions e pausa para decisão humana explícita diante de múltiplos caminhos arquiteturais."
---

# Documentation & Conventions

Use esta skill para validar contratos técnicos, consultar documentações oficiais de APIs e SDKs integradas e estabelecer padrões arquiteturais antes da escrita do Draw Nível 3 (Tasks de Implementação).

## Gatilho de Execução

Esta skill deve ser disparada **imediatamente antes da montagem das tasks do Draw Nível 3**, logo após a conclusão e consolidação das jornadas, telas e views do Draw Nível 2:

- Garante que nenhuma task de código ou endpoint de Nível 3 seja desenhado com base em suposições arbitrárias, contratos inventados ou padrões divergentes.
- Serve de fundação técnica oficial para que o Draw Nível 3 atue como plano de execução cirúrgico com endpoints, rotas, payloads e plataformas explícitas.

## Leitura e Varredura Técnica

A skill executa uma varredura rigorosa e documenta convenções reutilizáveis:

1. **Análise dos Requisitos do Nível 2**:
   - Mapeia todas as telas, formulários, ações de usuário, eventos, integrações externas e estados previstos nas jornadas L2.
   - Identifica cada dependência técnica necessária: serviços de mensageria, gateways de pagamento, autenticação, bancos de dados, filas e serviços de terceiros.

2. **Consulta Obrigatória à Documentação Oficial**:
   - É estritamente proibido inventar payloads, parâmetros, rotas, cabeçalhos de autenticação ou fluxos de integração.
   - Consulta a documentação oficial atualizada de cada API/SDK envolvida (ex.: Stripe, WhatsApp Cloud API, SendGrid, Auth0, AWS S3).
   - Extrai contratos oficiais: URLs base, métodos HTTP, parâmetros de rota/query, schemas de request/response em JSON, códigos de status e regras de webhook (assinaturas, idempotência e ativação).

3. **Compilação de Convenções de Projeto**:
   - Registra cada padrão como um arquivo Markdown individual na pasta `.agents/conventions/<assunto>.md`.
   - **Cabeçalho Obrigatório**: Conforme exigido pelo gate do Looper, todo arquivo em `.agents/conventions/` (exceto o índice `README.md`) deve obrigatoriamente possuir frontmatter YAML com `name` e `description` não vazios:
     ```yaml
     ---
     name: <identificador-ou-nome>
     description: <descricao-curta-e-clara>
     ---
     ```
   - Compila padrões técnicos essenciais do projeto:
     - **Estruturas de pastas**: Organização de diretórios e divisão modular (ex.: controllers, use cases, models, repositories, adapters).
     - **Padrões de nomenclatura**: Convenções de casing e prefixação/sufixação para arquivos, classes, funções, tabelas de banco, variáveis e rotas.
     - **Arquitetura de componentes e regras**: Padrões de separação de responsabilidades, injeção de dependências e tratamento global de erros e logs.
     - **Contratos de integração externa**: Documentação de cada serviço externo com credenciais necessárias, fluxo de chamadas, endpoints, payload esperado e pré-condições.
   - Atualiza o índice `.agents/conventions/README.md` e o catálogo de convenções no `AGENTS.md`.

## Parada para Decisão Arquitetural

Caso a documentação técnica ou a API consultada apresente múltiplos caminhos ou alternativas operacionais para atender a uma mesma funcionalidade e a especificação de UI/requisitos não deixar claro qual deve ser utilizado:

- **Exemplos de bifurcação arquitetural**:
  - Checkout/Pagamento: Redirecionamento para checkout hospedado vs. QR Code estático/dinâmico no próprio app vs. link de pagamento avulso.
  - Autenticação: Fluxo OAuth2 Authorization Code com PKCE vs. Magic Link por e-mail vs. credenciais diretas com JWT.
  - Notificações em tempo real: WebSockets bidirecional vs. Server-Sent Events (SSE) vs. polling HTTP regular.
  - Upload de arquivos: Upload direto multipart para a API vs. URL pré-assinada (Presigned URL) para storage/bucket.
- **Instrução Mandatória de Pausa**:
  - A skill é expressamente instruída a **pausar a execução imediatamente**.
  - Não tome decisões arquiteturais ambíguas nem assuma uma alternativa por conta própria sem evidência explícita.
  - Apresente de forma clara ao usuário:
    1. O nó/funcionalidade do Nível 2 em questão;
    2. Os caminhos técnicos viáveis identificados na documentação;
    3. Os prós, contras e impactos de cada opção na arquitetura e na experiência;
    4. Solicite uma definição humana explícita antes de prosseguir.
- **Registro da Decisão**:
  - Assim que a decisão for confirmada pelo usuário, registre a escolha na convenção correspondente em `.agents/conventions/`.
  - Só então libere o avanço para a elaboração das tasks do Draw Nível 3 com `$draw-system-level-3`.

## Relação com o Draw Nível 3

Após a execução da skill e validação das convenções:
- O gerador do Draw Nível 3 (`$draw-system-level-3`) consome as convenções geradas em `.agents/conventions/` e o contexto global (`looper draw context`).
- As tasks de implementação do Nível 3 passam a referenciar os contratos exatos documentados (rotas, métodos HTTP, parâmetros e payloads), eliminando qualquer instrução genérica.
