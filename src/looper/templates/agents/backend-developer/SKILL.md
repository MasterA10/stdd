---
name: backend-developer
description: "Desenvolve e revisa backend modular, observável e seguro; use para APIs, regras de negócio, jobs, integrações e persistência."
---

# Backend Developer

Use esta skill para implementar ou revisar backend, APIs, jobs, regras de negócio e
integrações. Ela não substitui o Draw, o contrato existente, a stack detectada ou as
decisões do `AGENTS.md`; leia esses artefatos antes de alterar produção.

## Roteamento obrigatório por capacidade

Consulte as skills especializadas abaixo quando a tarefa tocar a capacidade correspondente.
Elas são skills independentes, não uma hierarquia de “skills secundárias”:

- `$backend-logging` para logs, erros, observabilidade, correlação e diagnóstico.
- `$backend-database-persistence` para schema, queries, transações, migrações e persistência.
- `$backend-auth-security` para autenticação, autorização, sessões, segredos e hardening.

Quando uma mudança atravessar mais de uma capacidade, consulte todas as skills aplicáveis
antes de desenhar a solução. A skill central continua responsável pela composição do backend,
fronteiras entre camadas, integrações externas e validação ponta a ponta.

## Resultado esperado

Entregue backend observável, modular, testável e seguro. Separe entrada/controller, caso de
uso, domínio, persistência, integrações externas e infraestrutura. Evite funções ou módulos
monolíticos; prefira composição explícita e dependências injetáveis.

Evite criar ou ampliar arquivos de backend acima de 300 linhas. Isso é uma orientação de
modularidade, não um limite absoluto de qualidade nem uma validação estática aplicada pelo
`looper test`.

## Integrações e APIs externas

Encapsule SDKs e APIs externas em adaptadores orientados ao contrato. Centralize no adaptador
autenticação, endpoint, timeout, retry, backoff, idempotência, paginação, conversão de erros
e logging da chamada; o restante do sistema depende de uma interface local.

Consulte a documentação oficial atual antes de implementar. Registre em `.agents/conventions/`
o serviço, endpoint/contrato, autenticação e pré-condições. Nunca invente payloads nem confie
em resposta externa sem validação. Toda integração que participar do comportamento deve ter
teste de contrato autorizado (sandbox quando disponível); credenciais inválidas podem provar
o caminho de autenticação, mas nunca use segredos reais em testes.

## Validação

Cubra as fronteiras relevantes com testes focados, a suíte afetada e os gates do Looper.
Prove caminhos de sucesso e falha, contratos externos, limites entre camadas e as capacidades
especializadas acionadas. Não declare o backend implementado somente porque existem classes
ou endpoints: prove o caminho observável e suas falhas relevantes.
