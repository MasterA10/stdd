---
name: backend-logging
description: "Projeta e revisa logging e observabilidade de backend com eventos estruturados, correlação, diagnóstico completo e redaction segura."
---

# Backend Logging

Use esta skill quando a implementação criar, alterar ou depurar logs, erros, requests,
jobs, callbacks ou integrações. Logging é uma capacidade de infraestrutura crítica e
transversal: deve tornar o comportamento explicável e não pode ser tratado como decoração.

## Contrato mínimo

- Use uma fachada/contrato único de logger; não espalhe `print`, `console.log`, SQL ou
  escrita direta em arquivo pela aplicação.
- Mantenha exatamente quatro níveis: `error`, `warn`, `info` e `debug`.
  `error` é sempre registrado, em qualquer ambiente; configuração de verbosidade só
  controla `info` e `debug`.
- Prefira eventos estruturados com timestamp, nível, evento, operação, módulo,
  correlation ID, duração, resultado e erro tipado. Extraia arquivo, linha e método da
  stack automaticamente quando a runtime permitir.
- Capture exceções não tratadas, falhas fatais, requests, jobs, callbacks assíncronos e
  adaptadores externos nos limites da aplicação. Preserve stack trace completo e causa.
- Em integrações, registre request e response completos o suficiente para reproduzir o
  diagnóstico: método, endpoint, parâmetros, headers permitidos, payload, status,
  latência e corpo retornado. Não trunque arbitrariamente evidências importantes.
- Separe mensagem sanitizada para o cliente do diagnóstico técnico interno. Nunca engula,
  resuma ou substitua a causa original no log técnico.

## Segurança e operação

Redija apenas segredos e credenciais reais (`password`, tokens, chaves, cookies,
authorization, bearer, CVV e chaves privadas). Não aplique redaction ampla a `body`,
`payload`, `data`, `response`, `details` ou campos de negócio, pois isso destrói o
diagnóstico. Quando um campo puder conter segredo, redija-o por nome/caminho explícito e
teste essa regra.

Configure destinos (console, arquivo, coletor ou banco) como adaptadores substituíveis e
independentes. Um destino indisponível deve degradar para outro destino seguro sem recursão,
sem esconder a falha original e sem tentar registrar o erro no destino quebrado. Defina
retenção, acesso, rotação e volume conforme o ambiente; não registre dados só porque estão
disponíveis.

## Validação

Teste os quatro níveis, logs de erro com debug desligado, correlation ID, captura global,
payloads de integração, redaction pontual, destinos independentes, fallback e ausência de
recursão. Verifique também que logs não alteram a resposta ou a transação principal.


