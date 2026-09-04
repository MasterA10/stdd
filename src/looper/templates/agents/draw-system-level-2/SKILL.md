---
name: draw-system-level-2
description: "Cria o nível 2 de um Draw System no Looper: o mapa exaustivo de jornadas, telas, views e navegação por papel. Use depois de draw-system-level-1; não use para arquitetura macro, regras internas detalhadas ou baixo nível da codebase."
---

# Draw System — Nível 2: Jornadas do usuário / View

## Responsabilidade

Construir a View do sistema sob uma raiz de nível 1. O nível 2 é normalmente o maior e mais detalhado desenho: ao lê-lo, alguém deve conseguir reconstruir aproximadamente 95% da interface do frontend, suas telas, estados e caminhos de navegação. A skill executa a parte de Views da Fase 1 e para antes de criar os subfluxos do nível 3.

Leia primeiro a raiz, a cápsula de jornadas e os descendentes relevantes. Para comportamento isolado use `$draw-feature`; para a arquitetura pai use `$draw-system-level-1`.

## Hierarquia e handoff

Crie o desenho com `hierarchy.level: 2`, `role: "journey"`, `parent_draw_ref` igual ao ID da raiz, `parent_node_id` igual ao nó-cápsula e `root_draw_ref` igual ao ID da raiz. Atualize o mesmo nó do pai com um único `draw_ref` para o filho. Todo descendente deve declarar `parent_draw_ref`, `parent_node_id` e `root_draw_ref`; o pai e o filho precisam resolver em `.looper/draws/`. Não criar órfãos, `draw_ref` quebrado ou passos do filho no pai.

## Cada tela é um nó

Modele cada tela, view, seção, área acessível ou subárea navegável como um nó distinto. Quando uma ação leva a outra tela, a tela de destino é outro nó; quando a nova tela possui opções que levam a mais telas, crie todos esses nós. Não compacte a jornada em um nó genérico.

Para cada tela, registre:

- qual papel a acessa e qual é o objetivo daquele papel;
- tela inicial, entrada, retorno, encerramento e redirecionamentos;
- para quais outras telas/views o papel pode ir, incluindo ida, volta e atalhos;
- sequência de navegação e condições que fazem opções aparecerem ou não;
- estados visíveis: loading, sucesso, erro, vazio e bloqueado;
- caminhos feliz, erro, recuperação e saída;
- opções permitidas e ações proibidas sem detalhar ainda a regra interna;
- dados e estados que o papel consegue observar;
- quais dados são fixos e quais são dinâmicos; para dados dinâmicos, registre a
  chave/caminho que a view consumirá pelo contrato `get_mock_fake` e mantenha a
  fonte em um único JSON compartilhado do projeto;
- `code_refs` dos componentes frontend/interface reais, como React, Vue, HTML, templates, views, `.tsx` e `.jsx`, quando a análise estática os comprovar.

Durante a especificação, nós de `hierarchy.level: 2` podem permanecer sem `code_refs`; não invente arquivo, função ou símbolo placeholder. Essa ausência não deve bloquear a criação ou a documentação. Depois que a implementação da task for concluída, o nó deve receber referência ao arquivo e, quando possível, à função/componente real. O `looper test` só bloqueia `draw.level2_missing_code_ref` para nós marcados como implementados no backlog.

### Exemplo de exaustividade

Em um aplicativo como Instagram, o feed é um nó; Home, Search, Reels, Shop e Profile são telas distintas. No perfil, Editar Perfil, Configurações e Posts salvos são nós adicionais. Configurações abre Privacidade, Segurança e Notificações. O nível 2 representa essa árvore para cada papel, não apenas o caminho feliz.

## O que não pertence ao nível 2

Não gravar rotas ou URLs, cores, fontes, tamanhos, CSS, aparência visual, layout, botões individuais ou regras de negócio detalhadas. O nó representa a tela e as opções de navegação; o nível 3 explica como as ações funcionam.

## Pontos de entrada

Use os pontos de entrada reais que melhor representem as jornadas:

- mobile normalmente parte de uma tela de abertura ou home;
- site normalmente parte da home, com uma segunda entrada apenas para área administrativa/painel realmente separado;
- papéis com fluxos isolados podem ter entradas separadas quando cliente e administrador não compartilham caminho;
- não criar raízes dispersas sem ponto de acesso real.

## Papéis separados

Crie caminhos separados para cliente, administrador, vendedor, operador, suporte e serviço automatizado quando objetivos, permissões, tenant, dados visíveis ou estados forem diferentes. Para cada papel, registre objetivo, ponto de entrada, opções permitidas, ações proibidas, contexto de acesso, estados observáveis e caminhos de sucesso, erro, recuperação e encerramento. Compartilhe um fluxo somente quando a regra e o estado observável forem realmente iguais, registrando os papéis autorizados. Se o papel ainda não estiver comprovado, crie `questions` em vez de inventar permissões.

## Telas que precisam de nível 3

Avalie cada nó. A maioria das telas deve apontar para um subfluxo de nível 3 quando possuir regra de negócio, decisão, autorização, validação ou detalhe de implementação relevante. Aponte no próprio nó com `draw_ref` para `$draw-system-level-3`. Se a tela ainda estiver planejada, o subfluxo pode ser gerado sem código; sua descrição deve registrar o comportamento esperado e suas perguntas abertas. Quando a implementação existir, a leitura prévia do símbolo e da referência na codebase passa a ser obrigatória para validar e enriquecer o subfluxo.

Uma tela de transição, loading, confirmação ou encaminhamento que apenas conecta estados e não tem lógica própria pode permanecer sem `draw_ref`. Essa exceção não pode esconder uma tela com comportamento real.

## Funcionalidades não implementadas

Uma opção planejada e ainda não implementada é um nó terminal: registre o estado `não implementado`, não crie continuação fictícia, não dê filhos, não aponte para nível 3 e preserve perguntas e decisões necessárias. Quando houver mistura de implementado e planejado, crie um grupo específico `Não implementado` ou `Planejado`; atribua os nós ao grupo e deixe a diferenciação visual para a paleta semântica do viewer. Nunca grave cor individual. Essa regra vale para todo fluxo e subfluxo; se não houver escopo planejado, não invente grupo.

## Convenção lógica de conexões

Toda seta usa `condition` numérico:

- `1` (`então`) é consequência certa e pode coexistir com um conjunto de `3` (`se`) ou de `2` (`ou`);
- `3` (`se`) é guarda possível. Um `se` exige pelo menos outro `se` correspondente na mesma origem;
- `2` (`ou`) é alternativa exclusiva.

Nunca misture `se` com `ou` na mesma decisão, em nenhuma direção ou rótulo. Nunca misture `ou` com `se`: são a mesma proibição vista pela outra direção. O `então` pode acompanhar ambas as famílias porque é a continuação inevitável. Use `label` e `description` para explicar a condição em linguagem natural; não use `nodes[].type` para representar decisão.

## Execução da Fase 1 — Views

1. Inspecione a raiz, stack, `.looper/config.json`, desenhos existentes, estado do Git e análise estática.
2. Crie o JSON de jornadas separadamente, preservando IDs estáveis e o vínculo pai/filho.
3. Mapeie exaustivamente todas as telas e fluxos por papel; não compactar para reduzir o tamanho.
4. Consulte análise estática para associar componentes frontend no próprio nó, marcando fatos `resolved`, `unresolved` ou pendentes sem inventar símbolos.
5. Use `groups` para fronteiras e `flows` para caminhos temporais. Não grave layout, posição, cor, data ou HTML.
6. Valide nós, relações, etapas de fluxo, grupos de não implementados, perguntas e referências hierárquicas.
7. Grave com `looper draw create --data-json '<JSON>'` e confira com `looper draw serve`.
8. Revise a árvore, folhas não implementadas e todas as telas que exigem nível 3.
9. Pare e pergunte se o usuário quer continuar para `$draw-system-level-3`; não crie comportamento antes da aprovação.

Registre a alteração:

```bash
looper log "Cria jornadas do sistema no nível 2" --type implementacao
```

Entregue raiz, ID da jornada, telas com `draw_ref`, folhas não implementadas, perguntas, arquivos alterados e o comando de revisão visual.

## Regras do ciclo interativo

Erros são consequências condicionais (`se`/`ou`), nunca sequência inevitável; valide no ponto de entrada da ação, antes de persistir ou chamar integrações. Funcionalidades planejadas ficam no grupo terminal `Não implementado`. A arquitetura é TDD: execute `backlog test` antes de produção, trate uma task por interação e conclua somente o ID recebido por `backlog complete`.
