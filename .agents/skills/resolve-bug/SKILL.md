---
name: resolve-bug
description: "Investiga e corrige bugs com análise e execução delegadas a um subagente, validação do plano, testes, atualização dos Draws e registro de convenções reutilizáveis."
---

# Resolve Bug

Use esta skill para bugs de uma interação comum ou de manutenção. Ela não substitui
`$implement-change` quando o backlog entregar uma change com ID reservado.

## Resultado esperado

Entregue uma correção reproduzível, com causa-raiz evidenciada, testes que falham
antes e passam depois quando possível, Draws correspondentes atualizados e um
registro `looper log` do tipo `bug`. Não considere uma alteração concluída apenas
porque o subagente editou arquivos.

## Fluxo obrigatório com subagente

O usuário autoriza o uso de subagente ao solicitar esta skill. Execute todo subagente
via `herdr` (modo nativo de agentes); não use outro mecanismo de delegação. Preserve o workspace e
não faça commit ou push como parte desta skill.

> **Padrão de modo**: Execute por padrão com a TUI nativa do Herdr dentro de uma pane visível, usando os próprios agentes, hooks e ciclo de vida. O agente principal não deve ler `herdr agent read`, `pane read`, scrollback ou output intermediário. Instrua o subagente a gravar o diagnóstico/plano final em um arquivo Markdown e leia somente esse artefato após o estado final.
> 1. **Modo Interativo (Janela interativa / TUI completa, padrão)**: Inicia o agente no pane com a TUI viva (`herdr agent start ... -- <flags-yolo>`), permitindo acompanhar o processo e usar os hooks nativos sem importar o contexto interno para a sessão principal.
> 2. **Modo Direto / Resposta Limpa (Headless no Pane, exceção)**: Só use quando o usuário ou o contrato pedir headless; execute `agy -p ... --dangerously-skip-permissions` ou `codex exec ...` na pane e grave a resposta final em arquivo.
>
> Em ambos os modos, nunca esqueça de rodar em modo YOLO (`--yolo` no Codex, `--dangerously-skip-permissions` no Agy).

1. Faça uma triagem curta: reproduza ou confirme o sintoma, leia o contexto do Draw
   relacionado (`looper draw context`) e localize arquivos e símbolos reais. Se o
   pedido for vago, registre o que foi observado e a pré-condição ausente.
2. Delegue ao subagente a investigação inicial e a avaliação da observabilidade.
   Instrua-o a manter leituras e pesquisas dentro da própria sessão e a não
   despejar resumos na conversa; o resultado dessa etapa deve ser salvo em um
   Markdown final para leitura única do agente principal.
   Se o bug não for
   rastreável, identifique as funções envolvidas e a stack trace percorrida e confira
   se os eventos, entradas, saídas, falhas e correlação necessários estão sendo
   registrados. Quando faltarem evidências, peça ao subagente para ampliar a
   instrumentação somente no caminho relacionado ao bug, com logs claros nos quatro
   níveis operacionais definidos por `$backend-developer`: `error`, `warn`, `info` e
   `debug`. `error` deve ser incondicional e preservar mensagem, tipo e stack trace;
   `debug` pode ser controlado por configuração. Não mascare payloads de negócio,
   não trunque stack traces e não crie níveis adicionais. O subagente deve propor
   essa instrumentação como uma etapa diagnóstica separada, sem corrigir o bug ainda.
   Se os logs já explicam o caminho e a falha, não os altere apenas por formalidade.
3. Valide no agente principal o escopo da instrumentação diagnóstica. Quando
   aprovada, delegue ao subagente sua execução, reproduza o bug, examine os eventos
   gerados e peça a atualização da análise. Só mantenha logs novos que sejam claros,
   úteis e relacionados ao caminho do bug.
4. Delegue ao subagente a análise consolidada e a criação do plano de correção,
   exigindo um arquivo Markdown final. O relatório deve conter sintoma, passos de reprodução, evidência da causa-raiz,
   arquivos e `qualified_name` afetados, logs relevantes, correção mínima, testes,
   impactos nos Draws e uma avaliação de possível convenção reutilizável. O
   subagente não deve implementar a correção nesta fase.
5. Valide o plano no agente principal contra o código, os testes, os contratos e o
   Draw. O plano só está aprovado se explicar a causa, cobrir os estados relevantes,
   incluir a instrumentação necessária quando a observabilidade foi insuficiente,
   não ampliar o escopo sem justificativa e tiver uma verificação observável. Se
   houver lacunas, devolva-o ao subagente para revisão; não autorize implementação
   com hipótese não confirmada.
6. Delegue ao subagente a execução do plano aprovado, explicitando o escopo e os
   critérios de aceite. A execução deve alterar código e testes reais quando
   aplicável, atualizar o Draw antes de uma mudança de comportamento conforme as
   regras do projeto e associar os símbolos reais aos nós afetados.
6. Aguarde somente o estado de ciclo de vida do Herdr, sem ler output incremental.
   Leia o arquivo Markdown final uma única vez, revise o diff produzido, confira
   se não há mudanças fora do escopo, confirme a correção no caminho real e
   execute a suíte mais específica, análise estática aplicável e `looper test`.
   Falhas são bloqueios; não force resultados nem edite testes aprovados apenas
   para obter verde.

## Draws e convenções

- Identifique todos os Draws, nós, conexões e níveis afetados. Se a correção mudar
  comportamento documentado, atualize a especificação e as conexões necessárias
  antes de liberar o código; ao final confirme a descrição, referências e símbolos
  reais (`arquivo` e `qualified_name`).
- Detalhes sem mudança de comportamento podem ser registrados como pergunta e
  resposta no nó correto. Não crie um nó genérico nem invente símbolos ou fluxo.
- Só crie ou altere arquivo em `.agents/conventions/` quando a investigação confirmar
  um padrão técnico difícil, não pontual e reproduzível em trabalhos futuros. Dê um
  assunto específico, inclua frontmatter `name` e `description`, atualize o índice e
  não registre hipótese, workaround temporário, segredo ou ID de execução.

## Encerramento

Depois de toda a validação, registre separadamente:

```bash
looper log "Corrige <resumo curto do bug>" --type bug
```

Relate causa-raiz, correção, arquivos e símbolos alterados, Draws e convenções
atualizados, testes e evidências. Se a reprodução, a execução do subagente ou uma
pré-condição necessária estiver indisponível, informe o bloqueio e não declare o bug
resolvido.
