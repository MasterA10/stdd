---
name: implement-backend
description: "Desenvolve e implementa regras de negócio, controllers, models, APIs, persistência e integrações (Nível 3) no backlog Looper; use para tasks de backend liberadas por looper backlog backend ou looper backlog task --backend."
---

# Implement Backend Agent

Esta skill pertence exclusivamente ao loop de implementação backend do backlog (Nível 3 — Controllers, Models, Regras de Negócio e Integrações).
Leia-a quando `looper backlog backend` ou `looper backlog task --backend` entregar uma task de Nível 3 (`backlog-task` ou `backlog-verification-task`).
Não leia esta skill para edições comuns, perguntas, medições, refatorações livres ou qualquer pedido que não tenha sido entregue pelo cursor do backlog.

Se `.looper/config.json` tiver `backlog.test_loop_enabled: false`, esta skill não depende de um loop prévio de testes: o projeto optou pelo loop somente de implementação. A cobertura transversal pode ser conduzida separadamente por `$test-application`.

## Objetivo

Percorrer o backlog de regras e backend (L3) até a conclusão da camada backend:

```text
looper backlog backend
  -> ler o contexto da regra L3 (e da tela L2 pai no 1º nó L3)
  -> consultar $backend-developer e contratos da aplicação
  -> implementar controller, model, validações, persistência e integrações
  -> executar testes de backend e looper test
  -> associar referências de código (looper draw associate-reference)
  -> looper backlog complete <task-id>
  -> repetir até backlog-layer-empty
```

## Contexto da Tela L2 Pai

- Ao receber o **primeiro nó L3** de uma tela, o backlog injetará automaticamente o bloco `parent_screen_context` (dados da tela L2 pai, sua descrição, entradas de navegação e símbolos).
- Utilize esse contexto para entender como a regra se acopla à view/tela construída na fase frontend.
- Nos nós L3 seguintes da mesma tela, o contexto de tela não é repetido para manter o foco na lógica específica da etapa.

## Regras de Engenharia Backend Obrigatórias

Ao implementar regras, APIs e integrações de backend:
1. **`$backend-developer` (`.agents/skills/backend-developer/SKILL.md`)**:
   - **Logging Transversal e Incondicional**: Registre eventos nos quatro níveis operacionais (`error`, `warn`, `info`, `debug`). Erros devem ser capturados e registrados incondicionalmente em qualquer ambiente, sem mascarar ou resumir exceções.
   - **Sem Truncamento Arbitrário e Redaction Cirúrgico**: Nunca aplique redaction genérico que esconda payloads úteis para depuração.
   - **Testes de Contrato para APIs Externas**: Toda integração externa deve ter teste de contrato executando endpoint real com credenciais deliberadamente inválidas para comprovar conexão e transporte.
   - **Modularidade**: Separe controllers, casos de uso, repositórios e adaptadores.

## Regras do loop

1. Execute `looper backlog backend` (ou `looper backlog task --backend`) para obter a próxima task.
2. Se a resposta for `kind: "backlog-bootstrap-task"`, prepare somente a estrutura mínima do projeto com as evidências locais; não implemente funcionalidade de produto.
3. Implemente apenas a task recebida, preservando contratos, autorização, dados e alterações locais do usuário.
4. Execute o teste mais específico, as suítes afetadas e `looper test`. Falha é bloqueio; não execute `backlog complete` para avançar com validação quebrada.
5. Se houver bloqueio, deixe a task aberta e informe o motivo, a evidência e a ação necessária.

## Verificação intermediária da implementação

Quando `looper backlog backend` entregar uma task de verificação criada por
`verification_interval` (ou `l2_verification_interval`), ela é uma auditoria obrigatória do comportamento já
implementado. O agente não pode concluir essa task apenas porque a task anterior está
`done`, existem arquivos, há símbolos associados ou algum teste superficial passa.

Para cada nó listado em `Alvos da verificação`:

1. Leia o Draw, as decisões respondidas, o nó L2 e todos os subfluxos relacionados.
2. Use as referências de código fornecidas para localizar os arquivos e símbolos reais.
3. Carregue esses arquivos no contexto e leia o código relevante antes de formar uma conclusão; não presuma o conteúdo a partir do nome do arquivo ou do símbolo.
4. Compare a implementação com a especificação completa: tela alcançável, regras de negócio, estados, validações, endpoints/handlers, persistência, integrações, permissões e efeitos observáveis.
5. Execute os testes aplicáveis e confirme que o caminho funciona de fato, incluindo as falhas e estados relevantes quando fizerem parte do Draw.
6. Só conclua pelo `backlog complete` quando houver evidência de conformidade no código e de funcionamento real. Se a implementação estiver ausente, parcial, desconectada, simulada ou quebrada, deixe a task de verificação aberta e relate os arquivos, símbolos, testes e lacunas encontrados.

A verificação não implementa uma aprovação automática: ela deve produzir uma conclusão
auditável, distinguindo `implementado`, `parcial`, `ausente` e `bloqueado`, com evidências
concretas para cada resultado.

## Escopo e Draws

- Leia o Draw relacionado e seus subfluxos apenas na medida necessária para a task.
- Não implemente folhas do grupo de funcionalidades não implementadas sem escopo aprovado.
- Não invente símbolos, referências, respostas ou continuação de fluxo.
- A associação não é automática. Em todo loop, antes de concluir, associe explicitamente cada nó entregue (o L2 e todos os L3 incluídos pelo `task_delivery_scope`) aos arquivos e símbolos reais criados ou alterados nessa fase.
- Para associar cada nó, use o símbolo de produção real e os símbolos de teste como dependências; arquivo sem `qualified_name` não é evidência.
- Preserve `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`.

### Rastreabilidade obrigatória em cada loop

Depois de criar ou alterar os artefatos e antes de `backlog complete`:

1. Identifique, no contexto da task, o `draw_id`, o `node_id` e todos os nós cobertos pelo escopo.
2. Execute `looper test` para atualizar os fatos estáticos e confirme na codebase/fatos o caminho do arquivo e o `qualified_name` real de cada símbolo; nunca invente um nome nem trate o arquivo como associação implícita.
3. Para cada nó coberto, execute `looper draw associate-reference` com o símbolo real e suas dependências reais. Inclua os símbolos de teste relacionados como `--source-dependency` para manter a ligação entre implementação e teste.
   ```bash
   looper draw associate-reference --draw-id <draw-id> --node-id <node-id> \
     --qualified-name '<símbolo-real>' --source-dependency '<símbolo-de-teste>'
   ```
4. Execute `looper draw symbols` e confira que as associações foram gravadas no nó correto e resolvem para os arquivos esperados. Se alguma associação estiver ausente, vazia ou não puder ser comprovada, deixe a task aberta e informe o bloqueio.

Na fase de implementação, `--qualified-name` deve apontar para o símbolo de produção real;
os testes vinculados entram como dependências reais. Se a fase só produzir uma estrutura
de bootstrap, associe o símbolo real dessa fase ao nó, sem fabricar um símbolo de produção.
O `backlog complete <task-id>` só pode ser o último comando do loop, depois dessa
associação e verificação.

Para tasks originadas de `$draw-system-level-1` a `$draw-system-level-4`, ler o Draw pai e
o filho, preservar `parent_draw_ref`, `parent_node_id`, `root_draw_ref` e `draw_ref`, e
interromper diante de fluxo órfão. Antes de declarar que não há mudança, confira
`git diff -- .looper/draws` e `git diff --cached -- .looper/draws`, liste os arquivos não rastreados
e faça ler o JSON atual completo. O diff de desenho é entrada de implementação:
diante de um pedido explícito de implementar, fazer uma mudança coerente antes de concluir.

## Memória contextual seletiva

Antes de `backlog complete`, verifique se a implementação confirmou uma regra reutilizável.
Registre contratos, arquitetura, operação, limites e escopo no `AGENTS.md`; registre
tipografia, cores, espaçamento, estados, animações e interações no `.looper/design.md`.
Atualize somente decisões aceitas ou padrões comprovados, consolidando duplicatas e
removendo detalhes temporários. Não registre hipóteses, IDs de execução, segredos ou
detalhes de implementação que não orientem trabalhos futuros. Relate qualquer atualização
de contexto junto dos arquivos, testes e limitações da task.

## Implementação e validação

- Entregue a melhor mudança coerente, eficiente e segura dentro do escopo pedido, buscando a melhor experiência sem inventar escopo.
- Valide entradas antes de efeitos e mantenha falhas seguras.
- Não edite testes aprovados para obter verde nem contorne gates.
- Não adicione dependências ou mude contratos sem necessidade comprovada e escopo aprovado.
- Não grave segredos em código, Draws, logs ou evidências.

Antes de implementar, inspecione os Draws de nível 2 e 3 da task e identifique as camadas
exigidas: lógica de negócio, apresentação, integração com o framework, assets e
configuração. A implementação deve entregar todas as camadas necessárias para tornar a
feature alcançável, não apenas o trecho exercitado pelo teste mais direto.

Antes de concluir, registre testes executados, falhas preexistentes ou pré-condições
ausentes, Draws e referências atualizados, limitações e camadas entregues. O gate inclui
`draw.level2_missing_code_ref`, `draw.level3_missing_code_ref`,
`draw.level4_missing_code_ref` e `draw.empty_node_symbol`.

Use cobertura proporcional também para frontend e markdown quando fizerem parte do
escopo. Teste live, pgTAP, performance, segurança, isolamento e pentest só são exigidos
quando aplicáveis. Ausência de runner ou pré-condição deve ser `not_executed`, nunca
sucesso. Em perfil MVP, qualquer instalação, download, criação de banco ou container
exige aprovação explícita do usuário. Não instalar, baixar, criar banco ou iniciar
container sem essa aprovação.

### Uso da análise estática para refatoração segura

Use a análise estática para refatoração segura, comparando valores antes/depois sem
esconder achados. Funções entre 101–150 linhas são manutenção; findings bloqueantes
exigem escopo e evidência antes de uma mudança maior.

### Critério de conclusão

Testes verdes são condição necessária, não suficiente. Verifique também que:

1. a feature é alcançável pelo caminho descrito no Draw;
2. todas as camadas exigidas foram entregues (incluindo todos os subfluxos internos quando aplicável);
3. os `code_refs` apontam para os artefatos relevantes;
4. `looper test` passou;
5. o cursor foi avançado pelo ID correto.

Registre cada trabalho concluído separadamente:

```bash
looper log "Implementa comportamento da task <task-id>" --type implementacao
```

Só reporte sucesso quando o diff estiver dentro do escopo, a validação passar e o
`backlog complete` tiver sido executado pelo ID recebido.
