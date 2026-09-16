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
registro `looper log` do tipo `bug`. O subagente executa o trabalho ponta a ponta:
pesquisa, investiga, reproduz, corrige e testa o bug. Ao terminar, grava um
relatório Markdown temporário; o agente orquestrador lê somente esse relatório
final e o apaga imediatamente. Não considere uma alteração concluída apenas
porque o subagente editou arquivos.

O orquestrador pode usar um único subagente para executar a correção, mas o
subagente recebido é a folha terminal desta execução: ele deve resolver o bug
ponta a ponta sozinho e não pode criar, invocar, delegar ou solicitar outro
subagente, worker do Herdr ou mecanismo equivalente. É proibido iniciar nesting
ou recursão de subagentes, mesmo quando a investigação parecer paralelizável;
se precisar de uma etapa adicional, execute-a na própria sessão e registre o
resultado no relatório final.

## Princípio de modularização, centralização e reutilização

Durante a investigação e a correção, se uma regra, validação, transformação, consulta,
instrumentação ou outro trecho puder ser reaproveitado, extraia-o para um módulo, serviço ou
adaptador com interface clara, centralize sua implementação e reutilize-o em todos os
consumidores. Antes de criar um helper ou workaround, procure uma implementação compartilhada
existente; não duplique lógica para resolver apenas um caminho do bug. Mantenha a correção
focada no defeito e faça a modularização somente no escopo necessário para eliminar a
duplicação.

## Fluxo obrigatório com subagente

O usuário autoriza o uso de subagente ao solicitar esta skill. Execute todo subagente
via `herdr` (modo nativo de agentes); não use outro mecanismo de delegação. Preserve o workspace e
não faça commit ou push como parte desta skill. O subagente é responsável pela
investigação e pela correção, não apenas por sugerir um plano.
Essa é a única delegação permitida: depois de iniciado, o subagente não deve
iniciar ou pedir qualquer subdelegação, outro worker do Herdr ou outro mecanismo
de agentes.

> **Padrão de modo**: Execute por padrão com a TUI nativa do Herdr dentro de uma pane visível, usando os próprios agentes, hooks e ciclo de vida. O agente principal não deve ler `herdr agent read`, `pane read`, scrollback ou output intermediário. Instrua o subagente a gravar o diagnóstico/plano final em um arquivo Markdown e leia somente esse artefato após o estado final.
> 1. **Modo Interativo (Janela interativa / TUI completa, padrão)**: Inicia o agente no pane com a TUI viva (`herdr agent start ... -- <flags-yolo>`), permitindo acompanhar o processo e usar os hooks nativos sem importar o contexto interno para a sessão principal.
> 2. **Modo Direto / Resposta Limpa (Headless no Pane, exceção)**: Só use quando o usuário ou o contrato pedir headless; execute `agy -p ... --dangerously-skip-permissions` ou `codex exec ...` na pane e grave a resposta final em arquivo.
>
> Em ambos os modos, nunca esqueça de rodar em modo YOLO (`--yolo` no Codex, `--dangerously-skip-permissions` no Agy).

1. Faça uma triagem curta: reproduza ou confirme o sintoma, leia o contexto do Draw
   relacionado (`looper draw context`) e localize arquivos e símbolos reais. Se o
   pedido for vago, registre o que foi observado e a pré-condição ausente.
2. Crie um caminho único e exclusivo para o relatório temporário, por exemplo
   `.looper/runs/<run-id>/resolve-bug-report.md`, e passe esse caminho no prompt.
   O prompt único deve declarar expressamente que o subagente é terminal e não
   pode criar, invocar, delegar ou solicitar subagentes. O subagente deve pesquisar a documentação necessária, ler arquivos, reproduzir
   o sintoma, investigar a stack trace e a observabilidade, corrigir o bug, atualizar
   os Draws antes de mudanças de comportamento, associar os símbolos reais e
   executar os testes aplicáveis. Toda pesquisa, leitura de arquivos, scripts
   internos e raciocínio detalhado devem permanecer na sessão do subagente; ele não
   deve despejar resumos na conversa ou na pane.
3. Se o bug não for rastreável, o subagente deve fazer a instrumentação diagnóstica
   necessária e conferir se eventos, entradas,
   saídas, falhas e correlação necessários estão registrados. Quando faltarem
   evidências, amplie a instrumentação somente no caminho relacionado, com logs
   claros nos quatro níveis operacionais definidos por `$backend-developer`:
   `error`, `warn`, `info` e `debug`. `error` deve ser incondicional e preservar
   mensagem, tipo e stack trace; `debug` pode ser controlado por configuração. Não
   mascare payloads de negócio, não trunque stack traces e não crie níveis
   adicionais. Só mantenha logs novos que sejam claros, úteis e relacionados ao
   caminho do bug.
4. O subagente deve escrever o relatório final no caminho informado, mesmo quando
   ficar bloqueado. O relatório deve conter sintoma, passos de reprodução,
   evidência da causa-raiz, arquivos e `qualified_name` afetados, logs relevantes,
   correção aplicada ou bloqueio, testes executados e resultados, impactos nos
   Draws e avaliação de convenção reutilizável. Não use o texto da resposta do
   agente como relatório substituto.
5. Aguarde somente o estado de ciclo de vida do Herdr, sem ler output incremental.
   Depois de `idle`, `done` ou `blocked`, confirme que o arquivo existe e leia-o uma
   única vez. Em seguida, remova somente esse arquivo temporário pelo caminho exato:

   ```bash
   report_file=".looper/runs/<run-id>/resolve-bug-report.md"
   test -s "$report_file"
   sed -n '1,260p' "$report_file"
   rm -f -- "$report_file"
   ```

   Nunca leia `herdr agent read`, `pane read`, scrollback ou output intermediário
   para completar o relatório. Se o arquivo não existir ou estiver vazio, trate a
   entrega como bloqueada e não tente reconstruir o contexto pela pane.
6. Revise o diff produzido, confira se não há mudanças fora do escopo, confirme a
   correção no caminho real e execute a suíte mais específica, a análise estática
   aplicável e `looper test`. Falhas são bloqueios; não force resultados nem edite
   testes aprovados apenas para obter verde.

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
