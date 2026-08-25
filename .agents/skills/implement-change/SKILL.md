---
name: implement-change
description: Implementa em loop as changes pendentes entregues por `looper backlog change`, valida cada correção e conclui somente o ID reservado.
---

# Implement Change Agent

Executa exclusivamente o loop de alterações do Draw. Cada change é um pedido de correção ou evolução registrado em um nó, normalmente criado por revisão, interação ou manutenção do desenho. A change entregue pelo cursor é a autorização e o escopo da implementação; não buscar tasks comuns com `looper backlog task`.

## Ciclo obrigatório

1. Execute `looper backlog change`.
2. Se retornar `backlog-change-empty`, encerre o loop.
3. Se retornar uma change, use exatamente o ID entregue em `task.id` e mantenha o cursor reservado até concluir ou reportar um bloqueio real.
4. Leia o Draw e o nó indicados, o pedido da change, perguntas e respostas, `code_refs`, símbolos, arquivos, dependências e a informação crítica fornecida pelo backlog.
5. Compare o pedido com a codebase real e determine todos os pontos necessários para corrigir o comportamento, preservando contratos e evitando mudanças fora do escopo.
6. Implemente a change nos arquivos reais. Não marque a alteração como concluída apenas editando o Draw, criando um teste superficial ou descrevendo uma solução futura.
7. Extraia a alteração implementada como documentação do comportamento: crie uma pergunta objetiva sobre o que foi alterado e associe a resposta comprovada ao nó do Draw que originou a change. A pergunta e a resposta devem ser persistidas em `node.questions`, preservando o histórico e o formato do contrato (`id`, `type`, `prompt`, `answer`); não deixe essa documentação somente no código, no log ou na change.
8. Associe a pergunta ao nó mais diretamente relacionado à alteração. Se a change envolver mais de um comportamento, crie uma pergunta por decisão relevante e associe cada uma ao nó correspondente; não use um nó genérico nem duplique perguntas já existentes.
9. Valide o Draw e as referências depois de injetar a pergunta e a resposta, execute os testes aplicáveis, a análise estática e `looper test`. Trate falhas como bloqueios; não force resultados nem use asserções vazias ou valores pré-calculados.
10. Registre a implementação com `looper log "Implementa a change <task-id>" --type implementacao`.
11. Somente depois da implementação, da documentação associada ao nó e da validação, execute `looper backlog complete <task-id>` usando exatamente o ID recebido.
12. Repita a partir de `looper backlog change`.

## Camadas e ordem

`looper backlog change --frontend` e `--backend` são filtros transitórios do cursor. Use-os somente quando a solicitação determinar uma camada; eles não alteram a ordem global nem concluem as changes da outra camada.

Se houver uma change em andamento, conclua-a antes de solicitar outra. Não conclua uma change diferente por aproximação, mesmo que o Draw tenha vários pedidos no mesmo nó. Preserve o pai, o subfluxo e as referências apresentados no contexto.

## Limites

- Não implemente uma task normal, uma lacuna não registrada ou uma funcionalidade planejada sem change.
- Não invente arquivos, símbolos, endpoints, payloads ou comportamento ausente no contrato.
- Se a change exigir uma decisão de produto ou arquitetural que o pedido não define, mantenha o ID em andamento, explique o bloqueio e peça a decisão; não marque como concluída.
- Se a implementação revelar uma lacuna adicional, registre-a no ponto correto do Draw como nova change ou informe o bloqueio antes de concluir a change atual.
- Nenhuma change pode ser concluída sem a pergunta e a resposta da alteração implementada persistidas no `node.questions` do nó correspondente. A resposta deve descrever o comportamento efetivamente implementado, com evidência em arquivos, símbolos ou testes; não invente uma resposta nem marque a documentação como concluída quando a associação ao nó for ambígua.
- Preserve mudanças existentes e não use comandos destrutivos para limpar o workspace.

## Encerramento

Informe as changes implementadas, os IDs concluídos, arquivos alterados, testes e gates executados, evidências registradas e eventuais bloqueios. Quando o cursor retornar `backlog-change-empty`, informe que não restam changes pendentes.
