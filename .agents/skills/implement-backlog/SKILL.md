---
name: implement-backlog
description: "Percorre exclusivamente o loop de implementação do backlog STDD: recebe uma task liberada por stdd backlog task, implementa apenas o escopo recebido, valida, audita quando exigido e conclui pelo backlog complete."
---

# Implement Backlog Agent

Esta skill pertence exclusivamente ao loop de implementação do backlog. Leia-a somente
quando `stdd backlog task` entregar uma resposta acionável (`backlog-task`,
`backlog-bootstrap-task` ou `backlog-verification-task`). Não leia esta skill para edições comuns, perguntas, medições, revisões livres ou qualquer pedido que não tenha
sido entregue pelo comando `stdd backlog task`.

## Objetivo

Percorrer o backlog até o terminal, uma task por vez. O loop é:

```text
stdd backlog task
  -> ler o contexto da task
  -> implementar somente essa task
  -> executar testes focados e o gate global
  -> stdd backlog complete <task-id>
  -> repetir até backlog-empty
```

Não declarar conclusão no meio do loop. `backlog-empty` é o único sinal de que não há
outra task de implementação.

Se `.stdd/config.json` tiver `backlog.test_loop_enabled: false`, a fase de testes está
intencionalmente desabilitada: não execute `$create-tests-backlog` nem trate
`backlog-test-required` como bloqueio. Use diretamente `stdd backlog task` e percorra
somente o loop de implementação.

## Cursor obrigatório

O cursor do backlog é a fonte de verdade da ordem de execução. Nunca escolha uma task
manualmente, pule a task retornada ou avance pelo arquivo JSON.

1. Execute `stdd backlog task` e trabalhe exatamente na task e no `task-id` retornados.
2. Retome a task que o cursor indicar como `in_progress` antes de buscar qualquer outra.
3. Depois de implementar e validar a task, execute obrigatoriamente `stdd backlog complete <task-id>` usando o mesmo ID recebido.
4. Só procure a próxima task depois que o `backlog complete` terminar com sucesso; esse comando libera e avança o cursor.
5. Repita o ciclo. Termine somente quando `stdd backlog task` retornar `kind: "backlog-empty"`.

Concluir o código ou passar nos testes não conclui a task operacionalmente. Sem
`backlog complete`, a task continua aberta no cursor.

## Escopo de entrega

Leia `backlog.task_delivery_scope` em `.stdd/config.json`:

- `task`: implemente somente o ID recebido; os subfluxos serão entregues em chamadas posteriores.
- `node`: implemente o nó pai e os subfluxos listados no mesmo contexto; conclua o conjunto usando o ID do nó pai.

Essa configuração é a mesma usada por `stdd backlog test`. Em qualquer modo, siga o
cursor e não escolha IDs manualmente.

## Regras do loop

1. Leia a resposta em linguagem natural de `stdd backlog task`, incluindo task, ID, predecessor, condição, pai, subfluxos, perguntas respondidas, símbolos e testes entregues pelo comando.
2. Se a resposta for `kind: "backlog-test-required"`, não implemente: volte para `$create-tests-backlog`/`stdd backlog test`.
3. Se a resposta for `kind: "backlog-bootstrap-task"`, prepare somente a estrutura mínima do projeto com as evidências locais; não implemente funcionalidade de produto.
4. Implemente apenas a task recebida, preservando contratos, autorização, dados e alterações locais do usuário.
5. Execute o teste mais específico, as suítes afetadas e `stdd test`. Falha é bloqueio; não execute `backlog complete` para avançar com validação quebrada.
6. Se houver bloqueio, deixe a task aberta e informe o motivo, a evidência e a ação necessária.

## Verificação intermediária da implementação

Quando `stdd backlog task` entregar uma task de verificação criada por
`l2_verification_interval`, ela é uma auditoria obrigatória do comportamento já
implementado. O agente não pode concluir essa task apenas porque a task anterior está
`done`, existem arquivos, há símbolos associados ou algum teste superficial passa.

Para cada nó listado em `Alvos da verificação`:

1. Leia o Draw, as decisões respondidas, o nó L2 e todos os subfluxos relacionados.
2. Use as referências de código fornecidas para localizar os arquivos e símbolos reais.
3. Carregue esses arquivos no contexto e leia o código relevante antes de formar uma conclusão; não presuma o conteúdo a partir do nome do arquivo ou do símbolo.
4. Compare a implementação com a especificação completa: tela alcançável, regras de negócio, estados, validações, persistência, integrações, permissões e efeitos observáveis.
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
2. Execute `stdd test` para atualizar os fatos estáticos e confirme na codebase/fatos o caminho do arquivo e o `qualified_name` real de cada símbolo; nunca invente um nome nem trate o arquivo como associação implícita.
3. Para cada nó coberto, execute `stdd draw associate-reference` com o símbolo real e suas dependências reais. Inclua os símbolos de teste relacionados como `--source-dependency` para manter a ligação entre implementação e teste.
   ```bash
   stdd draw associate-reference --draw-id <draw-id> --node-id <node-id> \
     --qualified-name '<símbolo-real>' --source-dependency '<símbolo-de-teste>'
   ```
4. Execute `stdd draw symbols` e confira que as associações foram gravadas no nó correto e resolvem para os arquivos esperados. Se alguma associação estiver ausente, vazia ou não puder ser comprovada, deixe a task aberta e informe o bloqueio.

Na fase de implementação, `--qualified-name` deve apontar para o símbolo de produção real;
os testes vinculados entram como dependências reais. Se a fase só produzir uma estrutura
de bootstrap, associe o símbolo real dessa fase ao nó, sem fabricar um símbolo de produção.
O `backlog complete <task-id>` só pode ser o último comando do loop, depois dessa
associação e verificação.

Para tasks originadas de `$draw-system-level-1` a `$draw-system-level-4`, ler o Draw pai e
o filho, preservar `parent_draw_ref`, `parent_node_id`, `root_draw_ref` e `draw_ref`, e
interromper diante de fluxo órfão. Antes de declarar que não há mudança, confira
`git diff -- .stdd/draws` e `git diff --cached -- .stdd/draws`, liste os arquivos não rastreados
e faça ler o JSON atual completo. O diff de desenho é entrada de implementação:
diante de um pedido explícito de implementar, fazer uma mudança coerente antes de concluir.

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
2. todas as camadas exigidas foram entregues;
3. os `code_refs` apontam para os artefatos relevantes;
4. `stdd test` passou;
5. o cursor foi avançado pelo ID correto.

Registre cada trabalho concluído separadamente:

```bash
stdd log "Implementa comportamento da task <task-id>" --type implementacao
```

Só reporte sucesso quando o diff estiver dentro do escopo, a validação passar e o
`backlog complete` tiver sido executado pelo ID recebido.
