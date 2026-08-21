---
name: implement-frontend
description: "Desenvolve e implementa telas, layouts, componentes e transições de navegação (Nível 2) no backlog Looper; use para tasks de frontend liberadas por looper backlog frontend ou looper backlog task --frontend."
---

# Implement Frontend Agent

Esta skill pertence exclusivamente ao loop de implementação frontend do backlog (Nível 2 — Telas e Views).
Leia-a quando `looper backlog frontend` ou `looper backlog task --frontend` entregar uma task de Nível 2 (`backlog-task` ou `backlog-bootstrap-task`).
Não leia esta skill para edições comuns, perguntas, medições, refatorações livres ou qualquer pedido que não tenha sido entregue pelo cursor do backlog.

## Objetivo

Percorrer o backlog de telas (L2) até a conclusão da camada frontend, uma tela por vez:

```text
looper backlog frontend
  -> ler o contexto da tela L2
  -> consultar .looper/design.md, $open-design e $modern-web-guidance
  -> implementar a tela, seus estados visuais e os links/navegação de saída
  -> executar testes de interface/validações locais e looper test
  -> associar referências de código (looper draw associate-reference)
  -> looper backlog complete <task-id>
  -> repetir até backlog-layer-empty
```

## Escopo Estrito do Nível 2 (Frontend)

- **O que implementar**:
  1. A view/tela completa: layout, componentes visuais, tipografia, cores, espaçamento e acessibilidade.
  2. Estados de interface: carregamento, vazio, preenchido, sucesso, erro visual e desabilitado.
  3. Validação de formulários no cliente (inputs, máscaras, feedback visual imediato).
  4. Transições e navegação entre telas: links, rotas e redirecionamentos descritos no grafo de navegação do Draw.
- **O que NÃO implementar nesta fase**:
  - Não implementar controllers de backend, models, ORMs, regras de negócio complexas de servidor, persistência em banco de dados ou integrações com APIs externas.
  - Essas responsabilidades pertencem exclusivamente à fase de backend (Nível 3).

## Recursos de Design e Frontend Obrigatórios

Ao construir, refinar ou revisar telas e componentes:
1. **`.looper/design.md`**: Consulte e respeite obrigatoriamente identidade visual, tipografia, paleta de cores, espaçamentos, estados e contraste definidos no projeto.
2. **`$open-design` (`.agents/skills/open-design/SKILL.md`)**: Consulte padrões de componentes, acessibilidade (ARIA), hierarquia visual e design tokens.
3. **`$modern-web-guidance` (`.agents/skills/modern-web-guidance/SKILL.md`)**: Consulte padrões e APIs web modernas, layouts responsivos, diálogos, View Transitions e performance de carregamento.

Você pode adicionar novos guias ou recursos complementares de frontend na pasta `.agents/skills/` sem alterar as regras fundamentais.

## Escopo, Draws e Rastreabilidade

- Leia o Draw relacionado e seus subfluxos apenas na medida necessária para a task.
- Não implemente folhas do grupo de funcionalidades não implementadas sem escopo aprovado.
- Preserve `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`. Trate fluxo órfão como bloqueio em árvores `$draw-system-level-1` a `$draw-system-level-4`.
- A associação não é automática. Em todo loop, antes de `backlog complete`, associe explicitamente cada nó entregue aos arquivos e símbolos (`qualified_name`) reais da interface em `code_refs`.
- Para associar cada nó, use o símbolo de tela/componente real:
  ```bash
  looper draw associate-reference --draw-id <draw-id> --node-id <node-id> \
    --qualified-name '<símbolo-real>' --source-dependency '<dependência-opcional>'
  ```
- Execute `looper draw symbols` e confira que a associação foi gravada no nó correto. Se estiver ausente ou vazia, deixe a task aberta.
- O `backlog complete <task-id>` só pode ser o último comando do loop.
- O gate `looper test` valida `draw.level2_missing_code_ref` e `draw.empty_node_symbol`.

## Memória contextual seletiva

Antes de `backlog complete`, verifique se a implementação confirmou uma regra reutilizável. Registre tipografia, cores, espaçamento, estados, animações e interações no `.looper/design.md`; registre contratos gerais no `AGENTS.md`. Não registre hipóteses ou segredos.

## Cursor e Conclusão

1. Execute `looper backlog frontend` para receber a próxima tela.
2. Cada task frontend entrega **exatamente 1 tela por vez** (`batch_size = 1`).
3. Após implementar e validar a tela com `looper test`, execute `looper backlog complete <task-id>`.
4. Registre o trabalho com:
   ```bash
   looper log "Implementa tela da task <task-id>" --type implementacao
   ```
5. Repita até receber `kind: "backlog-layer-empty"` com `layer: "frontend"`.
