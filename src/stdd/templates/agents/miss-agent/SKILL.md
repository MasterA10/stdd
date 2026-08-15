---
name: miss-agent
description: Executa tasks pendentes do backlog hierárquico, usando perguntas, respostas, símbolos e dependências reais do nó.
---

# Miss Agent

Executa o backlog uma task por vez até que o comando retorne `backlog-empty`.

## Ciclo obrigatório

1. Execute `stdd backlog task`.
2. Se a resposta for `backlog-test-required`, execute `stdd backlog test`, crie os testes do nó de nível 2 e de todos os seus subfluxos ou marque manualmente no viewer um fluxo de sistema já existente; a análise estática é opcional para essa marcação.
3. Se a resposta for `backlog-empty`, encerre o ciclo.
4. Leia o nó, suas perguntas e respostas, os símbolos, arquivos, dependências e o subfluxo relacionado.
5. Faça somente o trabalho descrito pela fase atual: testes durante `backlog test`, produção durante `backlog task`.
6. Execute os testes aplicáveis.
7. Execute `stdd backlog complete <task-id>` usando exatamente o ID retornado.
8. Repita o ciclo.

Quando a resposta trouxer `parent_task` e `subtask`, mantenha o pai no contexto da execução e marque cada ID separadamente. O checklist de teste vem antes do checklist de implementação; desmarcação feita no viewer deve ser tratada como bloqueio real.

Não conclua tasks fora de ordem, não invente símbolos ou arquivos e não marque uma task como concluída quando houver bloqueio real. Preserve respostas existentes, inclusive `false`, `0` e texto vazio. Se a task depender de uma decisão ausente, informe o bloqueio e mantenha a task em andamento.
