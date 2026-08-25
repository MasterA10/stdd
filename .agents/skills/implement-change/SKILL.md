---
name: implement-change
description: Implementa em loop as changes pendentes entregues por `looper backlog change`, reconcilia o Draw com a implementação real e conclui somente o ID reservado.
---

# Implement Change Agent

Executa exclusivamente o loop de alterações do Draw. Cada change é um pedido de correção ou evolução registrado em um nó, normalmente criado por revisão, interação ou manutenção do desenho. A change entregue pelo cursor é a autorização e o escopo da implementação; não buscar tasks comuns com `looper backlog task`.

O objetivo da skill não é apenas alterar arquivos: é deixar a implementação e o desenho consistentes depois da change. O Draw é uma representação executável da arquitetura e do comportamento; portanto, uma alteração que torne nós, conexões, referências ou subfluxos incompatíveis exige a reconciliação do desenho no mesmo ciclo.

## Ciclo obrigatório

1. Execute `looper backlog change`.
2. Se retornar `backlog-change-empty`, encerre o loop.
3. Se retornar uma change, use exatamente o ID entregue em `task.id` e mantenha o cursor reservado até concluir ou reportar um bloqueio real.
4. Leia o Draw e o nó indicados, o pedido da change, perguntas e respostas, `code_refs`, símbolos, arquivos, dependências e a informação crítica fornecida pelo backlog.
5. Compare o pedido com a codebase real e determine todos os pontos necessários para corrigir o comportamento, preservando contratos e evitando mudanças fora do escopo.
6. Implemente a change nos arquivos reais. Não marque a alteração como concluída apenas editando o Draw, criando um teste superficial ou descrevendo uma solução futura.
7. Faça a reconciliação do Draw após a implementação:
   - verifique se cada nó afetado continua compatível com a change, com os nós vizinhos, com o pai, com os subfluxos, com as referências e com o comportamento implementado;
   - crie os nós necessários quando a implementação introduzir uma etapa, decisão, integração, estado ou responsabilidade que o fluxo precisa representar;
   - desconecte e remova nós, conexões ou referências que se tornarem obsoletos, contraditórios ou sem função. Preserve o histórico somente quando o schema do Draw tiver um local explícito para isso;
   - ajuste grupos, terminais, entradas, saídas e navegação para que o fluxo continue válido e compreensível. Nós planejados e não implementados devem seguir as regras de grupo e terminal do projeto;
   - não use uma mudança cosmética no Draw para mascarar uma incompatibilidade da implementação, nem altere nós genéricos quando houver um nó específico mais adequado.
8. Releia o fluxo completo afetado de ponta a ponta e confirme que, depois da change, não há nó isolado indevidamente, conexão apontando para nó inexistente, referência quebrada, caminho impossível, duplicação contraditória ou descrição que promete comportamento ausente. Se a mudança exigir uma decisão não definida, trate como bloqueio.
9. Execute os testes aplicáveis, a análise estática e `looper test`. Trate falhas como bloqueios; não force resultados nem use asserções vazias ou valores pré-calculados.
10. Registre a implementação e a reconciliação com `looper log "Implementa e reconcilia a change <task-id>" --type implementacao`.
11. Somente depois da validação, execute `looper backlog complete <task-id>` usando exatamente o ID recebido.
12. Repita a partir de `looper backlog change`.

## Camadas e ordem

`looper backlog change --frontend` e `--backend` são filtros transitórios do cursor. Use-os somente quando a solicitação determinar uma camada; eles não alteram a ordem global nem concluem as changes da outra camada.

Se houver uma change em andamento, conclua-a antes de solicitar outra. Não conclua uma change diferente por aproximação, mesmo que o Draw tenha vários pedidos no mesmo nó. Preserve o pai, o subfluxo e as referências apresentados no contexto.

## Limites

- Não implemente uma task normal, uma lacuna não registrada ou uma funcionalidade planejada sem change.
- Não invente arquivos, símbolos, endpoints, payloads ou comportamento ausente no contrato.
- Não conclua a change se o Draw continuar incompatível com a implementação. A change pode exigir criar, reconectar, desconectar ou apagar nós, arestas, grupos e referências; faça somente os ajustes necessários e rastreáveis ao pedido.
- Se a change exigir uma decisão de produto ou arquitetural que o pedido não define, mantenha o ID em andamento, explique o bloqueio e peça a decisão; não marque como concluída.
- Se a implementação revelar uma lacuna adicional, registre-a no ponto correto do Draw como nova change ou informe o bloqueio antes de concluir a change atual.
- Preserve mudanças existentes e não use comandos destrutivos para limpar o workspace.

## Encerramento

Informe as changes implementadas, os IDs concluídos, arquivos alterados, testes e gates executados, evidências registradas e eventuais bloqueios. Quando o cursor retornar `backlog-change-empty`, informe que não restam changes pendentes.
