---
name: backend-developer
description: "Desenvolve e revisa backend modular com logging transversal, destinos configuráveis e integrações externas encapsuladas; use para tasks de backend, APIs, persistência e regras de negócio."
---

# Backend Developer

Use esta skill para implementar ou revisar backend, APIs, persistência, jobs e regras de
negócio. Ela não substitui o Draw, o contrato existente, a stack detectada ou as decisões
do `AGENTS.md`; leia esses artefatos antes de alterar produção.

## Resultado esperado

Entregue backend observável, modular e testável. Cada responsabilidade deve ter uma
fronteira clara: entrada/controller, caso de uso, domínio, persistência, integrações
externas e infraestrutura não devem virar uma função ou módulo monolítico.

## Logging transversal e global

O logging é uma capacidade de infraestrutura essencial e transversal disponível para qualquer
módulo, request, job, callback, integração e handler de erro. Não espalhe `print`, `console.log`
ad-hoc, acesso direto a arquivo ou SQL de log disperso pela aplicação.

Há exatamente quatro níveis operacionais:

- `error`: falha, exceção ou condição que exige investigação imediata ou diagnóstica.
  Registrado de forma **incondicional** em qualquer ambiente (produção, staging e dev),
  independentemente de flags de debug estarem ligadas ou desligadas. Preserve o tipo, a mensagem
  crua sem maquiagem, stack trace completo, operação, módulo, payload e contexto de correlação.
- `warn`: condição anormal ou degradação recuperável que não interrompeu o fluxo, mas
  exige acompanhamento. Inclua a causa, o fallback usado e o impacto esperado.
- `info`: evento operacional relevante, mudança de estado ou conclusão de uma operação de negócio;
  não use para despejar detalhes de cada linha ou dumps volumosos de payload.
- `debug`: diagnóstico técnico detalhado do fluxo, ciclo de vida e payloads. Deve registrar
  payloads completos de entrada e saída, variáveis de contexto e respostas brutas para permitir
  depuração precisa sem mascarar informações úteis. Deve poder ser habilitado ou reduzido
  por configuração sem alterar o código de negócio.

Não crie níveis adicionais como `trace`, `verbose` ou níveis específicos de domínio para
contornar essa regra.

Modele o logger como uma fachada/contrato único e configure os destinos de forma independente:

- console do navegador em interfaces web;
- arquivo;
- banco de dados.

Um evento pode ser enviado a mais de um destino. Os destinos devem ser adaptadores
substituíveis, com configuração explícita, e uma falha no destino de log não pode causar
recursão infinita nem ocultar a falha original. Se o banco falhar, use uma degradação
segura para outro destino disponível e preserve a evidência do erro sem tentar registrar
o erro do logger no mesmo destino quebrado.

### Regras fundamentais de observabilidade agnóstica

1. **Erros são incondicionais (proibido desligar logs de erro)**: Flags de configuração de
   debug/verbose controlam apenas a verbosidade de `info` e `debug`. Eventos `error`, exceções não
   tratadas, erros fatais de encerramento do processo e falhas de integração externa devem ser
   gravados **sempre**, mesmo com o modo debug desativado.
2. **Separação estrita entre resposta ao cliente e log técnico**: Mensagens amigáveis, tratadas
   e sanitizadas pertencem exclusivamente à camada de apresentação/resposta ao cliente (frontend/API).
   No log técnico interno, **nunca mascare, resuma, engula ou converta erros em mensagens genéricas**.
   Se uma biblioteca, banco ou API externa cuspir um erro, capture a mensagem exata, código e corpo cru.
3. **Entrada e saída completas em requisições e integrações**: Todo adaptador ou cliente HTTP/RPC
   deve registrar o ciclo completo:
   - **Na saída (Request)**: método, URL/endpoint com parâmetros, headers permitidos e body/payload enviado.
   - **No retorno (Response)**: status HTTP, latência/tempo de resposta, headers úteis e body/resposta recebida na íntegra.
   - **Na falha**: status retornado, body bruto retornado pela API externa (com mensagens e detalhes de validação), payload enviado e mensagem da exceção.
4. **Redaction cirúrgico (proibido mascarar payloads e campos de negócio)**: A ocultação de dados
   sensíveis deve ser estrita e pontual em credenciais e segredos reais (`password`, `token`,
   `access_token`, `refresh_token`, `secret`, `api_key`, `authorization`, `cookie`, `bearer`, `cvv`, `private_key`).
   É expressamente proibido aplicar filtros genéricos que mascarem palavras como `body`, `payload`,
   `data`, `response`, `params`, `details`, `email`, `chat_id` ou atributos de negócio, destruindo a
   capacidade de diagnosticar falhas.
5. **Introspecção automática de pilha sem repetição de código**: O logger deve aproveitar os
   recursos de runtime da stack (ex: call stack inspection, backtrace, stack trace de exceptions)
   para extrair automaticamente arquivo, linha e método de origem, sem obrigar o desenvolvedor a
   passar manualmente parâmetros de localização em cada invocação de log.
6. **Sem truncamento arbitrário de mensagens e payloads**: Não corte mensagens de erro, respostas de
   APIs ou stack traces com limites curtos arbitrários (como 100-240 caracteres) que eliminem detalhes
   essenciais de diagnóstico.
7. **Captura global nos limites da aplicação**: Instale interceptadores nas bordas da stack:
   exceções não tratadas, handlers de encerramento fatal (shutdown/uncaught), middleware de request,
   jobs em background, callbacks assíncronos e adaptadores de integração. A captura global deve
   gravar o erro completo com correlation ID e delegar o fluxo para o mecanismo normal de erro ou status HTTP.

## Modularidade e tamanho das funções

Separe composição, validação, regra, persistência e efeitos externos. Prefira funções
curtas com uma responsabilidade observável e classes pequenas quando houver estado ou
contrato explícito. Extraia módulos por capacidade/coeso domínio, não apenas por
quantidade de linhas. Quando uma função começa a decidir, persistir, logar e chamar uma
API ao mesmo tempo, divida-a e injete as dependências.

## APIs e serviços externos

Integrações externas geralmente devem ser classes/adaptadores com métodos orientados ao
contrato do serviço. O restante do backend depende de uma interface local, não do SDK ou
payload espalhado pela aplicação. Centralize autenticação, endpoint, timeout, retry,
backoff, idempotência, paginação, conversão de erro e logging da chamada no adaptador.
Nas chamadas e integrações externas, o log deve ser completo em ambas as pontas: registre
exatamente o que foi enviado (requisição, parâmetros e body) e o que retornou (status e
resposta recebida), permitindo auditoria ponta a ponta sem expor dados sensíveis.

Consulte a documentação oficial atual do serviço antes de implementar e registre em
`.agents/conventions/` o endpoint/contrato, autenticação e pré-condições quando a
integração entrar no projeto. Mantenha no `AGENTS.md` somente a visão geral e as regras
operacionais do projeto. Nunca invente payloads ou trate resposta externa como confiável
sem validação.

Toda API externa que participa do comportamento implementado deve ter pelo menos um
teste de contrato que execute a chamada real em endpoint de sandbox/teste ou ambiente
explicitamente autorizado. Esse teste deve usar credenciais deliberadamente inválidas,
nunca segredos reais, e confirmar o erro de autenticação documentado pelo serviço
(normalmente `401` ou `403`). O objetivo é provar que transporte, endpoint, autenticação
e formato básico da requisição estão realmente conectados. Qualquer resposta diferente
do erro de credencial esperado — inclusive sucesso, `404`, erro de método ou erro de
validação de payload — é bloqueio para a task: revise endpoint, método, headers,
autenticação e payload antes de concluir. Mocks podem complementar os testes, mas não
substituem essa chamada de contrato.

## Validação

Antes de concluir uma task, cubra as fronteiras relevantes com testes: níveis `error`,
`warn`, `info` e `debug`, seleção independente de console/arquivo/banco, redaction, correlation ID,
captura global, falha de destino sem recursão e comportamento dos adaptadores externos.
Execute testes focados, a suíte afetada e os gates do Looper. Não declare backend
implementado somente porque existem classes ou endpoints; prove o caminho observável e
suas falhas relevantes.
