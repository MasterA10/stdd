---
name: e2e-tester
description: "Executa testes end-to-end live em fluxos L3 do Draw: injeta entrada
  via curl (preferencial) ou direto no handler, encadeia ações não automáticas,
  valida pelo log do app e corrige o que falhar. Comportamento e persistência sempre
  reais; mock somente do payload de entrada quando o trigger externo não chega ao
  ambiente local."
---

# E2E Tester

Use esta skill quando o usuário pedir para executar, criar ou validar um teste
end-to-end de um fluxo L3 já implementado. Esta é uma **skill de interação comum**:
não faz parte do loop automático de backlog e não executa `looper backlog complete`.

## Objetivo

Provar que o fluxo descrito no nó L3 funciona de ponta a ponta com credenciais reais
(ou de sandbox), produzindo evidência rastreável no log do app.

## Pré-condições obrigatórias

1. **Nó L3 identificado**: O usuário deve informar o `draw_id` e o `node_id` do fluxo
   a ser testado. Se não informar, pergunte antes de prosseguir.
2. **`.env` verificado**: Confirme que `.env` existe na raiz do projeto e que está listado
   no `.gitignore`. Se `.env` não existir, liste quais variáveis são necessárias com base
   no código e interrompa até o usuário fornecê-las. **Nunca commite credenciais.**
3. **Implementação existente**: Leia os `code_refs` do nó para confirmar que os símbolos
   existem na codebase. Se ausentes, informe o bloqueio.

## Leitura do fluxo L3

1. Leia `.looper/draws/<draw_id>.json` e localize o nó L3 pelo `node_id`.
2. Extraia em **texto limpo** (não entregue o JSON bruto):
   - Sequência de passos do fluxo em ordem.
   - Entrada esperada (payload, headers, parâmetros).
   - Saída esperada (resposta HTTP, estado no banco, evento emitido).
   - Integrações externas envolvidas.
   - Caminhos de erro e fallback relevantes.
3. Leia os `code_refs` para identificar os arquivos e símbolos de entrada do fluxo.

## Fronteira do mock

```
┌─────────────────────────────────────────────────────────────────┐
│ SIMULADO (apenas quando necessário):                            │
│   - Payload de entrada (JSON que chegaria pelo webhook/evento)  │
│                                                                 │
│ SEMPRE REAL (nunca mockado):                                    │
│   - Toda a lógica de negócio                                    │
│   - Persistência (banco real com credenciais do .env)           │
│   - Integrações externas                                        │
│   - Side effects (filas, eventos, notificações)                 │
│   - Logs do app                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Estratégia de entrada (ordem de preferência)

### 1. `curl` — preferencial quando há endpoint HTTP local

Use quando o fluxo é disparado por requisição HTTP (webhook, API REST, callback)
e o servidor está rodando localmente:

```bash
curl -X POST http://localhost:<porta>/<rota> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{ ... payload do nó ... }'
```

- Identifique porta e rota no código ou no `.env`.
- Construa o payload com base nos campos do nó L3.
- Capture a resposta HTTP completa (status + body).
- **O comportamento interno (lógica, banco, integrações) roda no app real.**

### 2. Injeção direta no handler (webhook externo sem túnel)

Quando o evento vem de fora mas não pode chegar ao ambiente local (ex.: webhook de
terceiro sem túnel), **mock somente o payload de entrada** e chame o handler diretamente:

```python
# Somente o payload é simulado; lógica e banco são reais
from myapp.controllers.webhook_controller import handle_webhook
from dotenv import load_dotenv

load_dotenv()
payload = {"event": "payment.completed", "amount": 100, "user_id": "123"}
resultado = handle_webhook(payload)
print(resultado)
```

Regra: somente o payload de entrada é construído pelo teste. Todo o comportamento
interno (validações, banco, integrações externas, side effects) **roda no contexto
real do app** com as credenciais do `.env`.

### 3. Chamada direta à função (sem endpoint HTTP)

Quando a ação é disparada pela view chamando a função diretamente (sem webhook):

```python
from myapp.controllers.meu_controller import executar_fluxo
from dotenv import load_dotenv

load_dotenv()
resultado = executar_fluxo(parametro="valor_real")
print(resultado)
```

## Encadeamento de ações

Quando o fluxo L3 tiver múltiplos passos **não encadeados automaticamente**
(cada passo exige chamada separada):

1. Execute o Passo 1 e capture o resultado intermediário.
2. Use o resultado do Passo 1 como entrada do Passo 2.
3. Repita até o último passo.
4. Valide o estado final (banco, resposta, evento emitido).

Documente cada passo: `entrada enviada → resposta/resultado → log relevante`.

## Validação pelo log

Após cada chamada, colete os logs gerados pelo app e verifique:

- [ ] Handler/função de entrada chamado — aparece no log (`debug`/`info`).
- [ ] Parâmetros de entrada registrados nos logs.
- [ ] Cada integração externa: requisição enviada e resposta recebida nos logs.
- [ ] Resultado de negócio registrado (`info` de conclusão de operação).
- [ ] Nenhum `error` ou `warn` inesperado.

**`error` nos logs = bloqueio**: investigue a causa, corrija o código e re-execute
até o log estar limpo antes de declarar sucesso.

## Relatório obrigatório

Ao final do teste, produza um relatório com:

```
## Teste E2E — [nome do nó L3]

**Draw**: <draw_id> | **Nó**: <node_id>
**Data/hora**: <timestamp>
**Ambiente**: live / sandbox / injeção direta de payload

### Passos executados
1. <ação> → <status HTTP ou resultado> → <log relevante>
2. ...

### Validações de log
- [x] Handler chamado e registrado
- [x] Integração X: ciclo completo nos logs
- [ ] ❌ Erro encontrado: <descrição>

### Status final
✅ PASSOU / ❌ FALHOU

### Correções aplicadas (se houver)
- <arquivo>: <o que foi corrigido e por quê>

### O que não foi possível testar
- <item>: <motivo>
```

## Critério de conclusão

O teste E2E é válido quando:

1. O fluxo completo rodou sem `error` nos logs.
2. Cada passo produziu log rastreável de entrada e saída.
3. O estado final (resposta HTTP, banco, evento) corresponde ao esperado no nó L3.
4. Qualquer desvio foi corrigido no código e o teste re-executado com sucesso.

Registre ao final:

```bash
looper log "Teste E2E do nó <node_id> — <status>" --type teste
```
