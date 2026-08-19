---
name: missing
description: Recupera comportamentos marcados como ausentes, lendo símbolos e testes para implementar o que ainda falta.
---

# Missing Agent

Executa o backlog uma task por vez até que o comando retorne `backlog-empty`. Use esta skill especialmente quando alguém desmarcar o checklist de implementação porque o comportamento ainda não existe ou foi implementado de forma incompleta.

## Ciclo obrigatório

1. Execute `stdd backlog task`.
2. Se a resposta for `backlog-test-required`, execute `stdd backlog test`, crie os testes do nó de nível 2 e de todos os seus subfluxos ou marque manualmente no viewer um fluxo de sistema já existente; a análise estática é opcional para essa marcação.
3. Se a resposta for `backlog-empty`, encerre o ciclo.
4. Leia o nó, suas perguntas e respostas, o fluxo/subfluxo, `code_refs`, símbolos, arquivos, dependências, `test_ref` e os testes associados.
5. Compare o comportamento descrito no Draw com o que os símbolos e os testes realmente comprovam. Identifique precisamente o caminho, regra, estado ou tratamento de erro que falta.
6. Se houver testes aprovados que falham ou não cobrem o comportamento, corrija a produção dentro do escopo da task e adicione regressão quando necessário. Não marque a task como concluída com teste forçado, asserção vazia ou resultado pré-calculado.
7. Se ainda não houver testes do escopo, atenda primeiro `backlog-test-required` com `stdd backlog test`; nessa fase crie somente os testes. Depois retome `backlog task` para implementar a produção.
8. Execute os testes aplicáveis e os gates do STDD.
9. Execute `stdd backlog complete <task-id>` usando exatamente o ID retornado.
10. Repita o ciclo.

Quando a resposta trouxer `parent_task` e `subtask`, mantenha o pai no contexto da execução e marque cada ID separadamente. O checklist de teste vem antes do checklist de implementação. A desmarcação do checklist de implementação é o sinal de que o comportamento voltou a ser pendente e autoriza a investigação e correção; não é motivo para apenas relatar o missing. A desmarcação do checklist de teste continua sendo bloqueio até que os testes sejam especificados e executados.

Não conclua tasks fora de ordem, não invente símbolos ou arquivos e não marque uma task como concluída quando houver bloqueio real. Preserve respostas existentes, inclusive `false`, `0` e texto vazio. Se a task depender de uma decisão ausente, informe o bloqueio e mantenha a task em andamento.
