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

O logging é uma capacidade de infraestrutura disponível para qualquer módulo, request,
job, callback, integração e handler de erro. Não espalhe `print`, acesso direto a arquivo
ou SQL de log pela aplicação.

Há exatamente quatro níveis operacionais:

- `error`: falha, exceção ou condição que exige investigação. Preserve tipo, mensagem,
  stack trace, operação, módulo e contexto de correlação.
- `warn`: condição anormal ou degradação recuperável que não interrompeu o fluxo, mas
  exige acompanhamento. Inclua a causa, o fallback usado e o impacto esperado.
- `info`: evento operacional relevante, mudança de estado ou conclusão de uma operação;
  não use para despejar detalhes de cada linha ou payload.
- `debug`: diagnóstico detalhado do fluxo e dos dados não sensíveis. Deve poder ser
  habilitado ou reduzido por configuração sem alterar o código de negócio.

Não crie níveis adicionais como `trace`, `verbose` ou níveis específicos de domínio para
contornar essa regra.

Modele o logger como uma fachada/contrato único e configure os destinos de forma
independente:

- console do navegador em interfaces web;
- arquivo;
- banco de dados.

Um evento pode ser enviado a mais de um destino. Os destinos devem ser adaptadores
substituíveis, com configuração explícita, e uma falha no destino de log não pode causar
recursão infinita nem ocultar a falha original. Se o banco falhar, use uma degradação
segura para outro destino disponível e preserve a evidência do erro sem tentar registrar
o erro do logger no mesmo destino quebrado.

Todo evento estruturado deve carregar, quando disponível, timestamp, nível, mensagem,
request/correlation ID, módulo, operação, ambiente, identificador da entidade, metadados
úteis e erro serializado. Redija tokens, senhas, cookies, chaves, dados pessoais e
payloads sensíveis antes de qualquer destino. Nunca registre um segredo para facilitar
debug.

Instale captura global nos limites corretos da stack: exceções não tratadas, middleware
de request, jobs/background workers, callbacks assíncronos e falhas de integração. A
captura global deve registrar a exceção uma vez e devolvê-la ao mecanismo normal de erro;
não transforme logging em tratamento silencioso. Logs de debug não devem serializar
objetos enormes nem alterar o resultado do caso de uso.

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

Consulte a documentação oficial atual do serviço antes de implementar e registre no
`AGENTS.md` o endpoint/contrato, autenticação e pré-condições quando a integração entrar
no projeto. Nunca invente payloads ou trate resposta externa como confiável sem validação.

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
