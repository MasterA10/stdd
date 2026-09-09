---
name: backend-auth-security
description: "Projeta e revisa autenticação, autorização, sessões, segredos e controles de segurança backend por padrão seguro e menor privilégio."
---

# Backend Authentication & Security

Use esta skill quando a funcionalidade envolver identidade, login, tokens, sessões,
permissões, dados sensíveis, endpoints expostos ou fronteiras de confiança. Consulte a
documentação oficial dos protocolos, frameworks e provedores escolhidos; não invente
fluxos criptográficos nem payloads.

## Identidade e acesso

- Diferencie autenticação (quem é), autorização (o que pode fazer) e auditoria (o que
  aconteceu). Faça autorização no servidor, em toda operação protegida e sobre o
  recurso/tenant correto; nunca confie em IDs, roles ou flags enviados pelo cliente.
- Aplique menor privilégio, deny-by-default, escopos explícitos e separação de funções.
  Padronize respostas e controle de timing quando isso reduzir enumeração de contas.
- Valide entrada, método, origem, conteúdo e tamanho em cada fronteira. Use proteção
  contra replay, CSRF, brute force, abuso e excesso de requisições quando aplicável.
- Para sessões e tokens, defina expiração, renovação, revogação, rotação, armazenamento,
  audience/issuer e clock skew. Não persista tokens em texto aberto quando o desenho
  puder usar hash ou armazenamento protegido.

## Criptografia e segredos

Use bibliotecas maduras e primitivas recomendadas pela plataforma; não implemente
criptografia, hashing de senha ou geração de tokens manualmente. Hash de senha deve usar
um algoritmo adaptativo aprovado e parâmetros revisáveis. Segredos vêm de secret manager
ou configuração segura, nunca do código, repositório, URL, fixture ou log. Redija
passwords, tokens, cookies, chaves e material privado antes de observabilidade, traces
ou mensagens de erro.

Proteja transporte, cookies e headers de segurança conforme o contexto. Diferencie
dados públicos, internos, confidenciais e altamente sensíveis; minimize coleta,
exposição, retenção e privilégio de leitura. Erros para o cliente devem ser úteis sem
revelar stack, credenciais, existência indevida de conta ou detalhes de infraestrutura.

## Mudanças e validação

Faça threat modeling proporcional ao risco e registre decisões, dependências e
pré-condições em `.agents/conventions/`. Revise dependências e defaults seguros antes
de liberar. Teste login/logout, expiração e revogação, autorização positiva e negativa,
isolamento entre usuários/tenants, entradas malformadas, rate limiting, CSRF quando
aplicável, rotação de segredos e respostas de erro. Inclua testes de regressão para cada
falha de segurança corrigida; nunca use credenciais reais.


