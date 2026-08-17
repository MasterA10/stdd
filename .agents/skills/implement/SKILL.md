---
name: implement
description: Implementa comportamento de produção guiado por testes no STDD, preservando contratos, segurança e qualidade estrutural. Usar quando testes já descrevem uma feature, correção, integração de IA, mudança de banco ou requisito não funcional a ser entregue.
---

# Implement Agent

## Responsabilidade

Fazer a menor alteração coerente que satisfaça os testes aprovados e preserve o restante do sistema. Separar implementação, correção e refactor nos WorkTypes. Não editar testes aprovados para obter verde e não contornar gates, adapters ou skills.

## Usuários, papéis e autorização

Ao implementar uma jornada, confirmar o papel do usuário e aplicar a autorização correspondente. Cliente e administrador não são intercambiáveis: quando seus objetivos, permissões, tenant, dados visíveis ou caminhos diferirem, preservar fronteiras e testes separados. Rejeitar acesso não autorizado de forma segura e não ampliar permissões apenas para satisfazer um caminho feliz. Se a regra de autorização não estiver definida no Draw ou nos testes, parar e registrar a decisão pendente.

## Hierarquia como contrato de implementação

Quando houver um desenho criado por `$draw-system-level-1` a `$draw-system-level-4`, ler a cadeia completa do nó de nível 2 até o nível 3 e, se existir, o nível 4. O nível 1 orienta fronteiras e escolhas de infraestrutura; o nível 2 define o comportamento do cliente; o nível 3 define o comportamento técnico a implementar; o nível 4 fornece referências verificáveis da codebase. Preservar `draw_ref`, `parent_draw_ref`, `parent_node_id` e `root_draw_ref`.

Não implementar uma folha marcada como não implementada sem escopo aprovado. Se houver fluxo órfão, referência quebrada, pai que duplica o filho ou conflito entre níveis, parar antes de alterar produção e reportar a inconsistência. A implementação deve permanecer dentro da cápsula do desenho filho e não mover detalhes de nível 3 para o pai de nível 2.

## Preflight obrigatório

1. Ler a solicitação, os testes relevantes, `.stdd/config.json` e eventuais desenhos referenciados.
2. Conferir Git, arquivos alterados e limites de escrita.
3. Executar o teste mais específico e confirmar o estado vermelho esperado.
4. Executar o baseline aplicável e registrar falhas preexistentes.
5. Consultar fatos da análise estática quando disponível: símbolos, dependências, complexidade e testes relacionados.
6. Revisar a consistência dos desenhos associados antes de alterar produção.
7. Tratar capacidade ausente como `unavailable`; não inventar cobertura.

## Associação obrigatória de símbolos

Antes de implementar, localizar no Draw o nó e associar a ele o símbolo real que executa o comportamento. Todo nó implementado ou alterado deve ter, no próprio nó, pelo menos um `code_refs` com `symbol` ou `qualified_name` comprovado pela análise estática; usar `code_refs` de outro nó, `unnamed`, `placeholder` ou nome inventado é inválido. Atualizar também dependências e `test_ref`/`test_refs` quando esses fatos estiverem disponíveis.

Toda associação de símbolo deve ser feita pela linha de comando. Executar `stdd draw symbols` para localizar o símbolo real e seu `qualified_name`, e então usar `stdd draw associate-reference --draw-id <draw-id> --node-id <node-id> --qualified-name <qualified-name>` (ou `--batch-json` para várias associações) para gravá-la. Usar exatamente o símbolo retornado pela análise estática; não editar `code_refs` manualmente no JSON nem usar a interface para criar associações. `stdd draw symbols` apenas consulta e valida as associações existentes.

Ao finalizar, executar `stdd test` e ler os achados de análise estática. O comando bloqueia nós de níveis 2, 3 e 4 sem símbolo (`draw.level2_missing_code_ref`, `draw.level3_missing_code_ref`, `draw.level4_missing_code_ref` ou `draw.empty_node_symbol`). Não declarar sucesso enquanto houver um desses achados: corrigir a associação no nó mais relacionado e repetir o gate. Para uma funcionalidade planejada e não implementada, não inventar símbolo nem continuação; mantê-la terminal no grupo de não implementados e relatar a limitação.

Para uma conferência rápida antes do gate final, executar `stdd draw symbols`. Ele lista somente os símbolos dos nós e as associações ausentes, sem executar as suítes do projeto, o contrato, o backlog ou o adapter de análise completa.

## Ordem do backlog

Antes de executar `stdd backlog task`, verificar se a resposta é `kind: "backlog-test-required"`. Nesse caso, não alterar produção: executar ou retomar `stdd backlog test`, criar os testes do nó de nível 2 e de todos os seus subfluxos ou marcar manualmente o fluxo já existente no viewer. `test_ref` e análise estática são evidências complementares, não uma pré-condição para o checklist. Só depois a mesma task pode ser implementada e concluída.

A saída padrão de `stdd backlog task` é resumida e humana. Quando for necessário consultar campos estruturados como `kind`, `parent_task`, `subtask` ou `subtasks`, repetir com `stdd backlog task --json`.

Quando a resposta trouxer `parent_task`, `subtask` e `subtasks`, preservar o pai como contexto e concluir pai e subtasks por seus próprios IDs. O checklist de implementação só pode ser marcado depois que `phase_checklists.test` do nó e dos subfluxos estiver concluído.

### Tasks Operacionais Injetadas (Bootstrap, Verificação e Encerramento)

O cursor do backlog pode injetar tasks operacionais especiais durante a jornada:

1. **`task:bootstrap`**: O agente deve verificar se dependências, `.env`, arquivos de configuração ou referências da stack precisam ser preparados antes de iniciar o desenvolvimento.
2. **`task:verify:...` (Verificação da Implementação de Nós L2)**: O agente deve auditar o código implementado em relação à especificação do Draw. **Não altere nem questione o desenho/fluxo**: o objetivo exclusivo é conferir se o código de produção cumpre com precisão as regras, validações de entrada, persistência real e integrações descritas nas telas e subfluxos, corrigindo eventuais falhas ou lacunas de implementação antes de avançar.
3. **`task:final:verification`**: O agente deve auditar a aplicação completa de ponta a ponta, garantir que a suíte de testes passa 100% e confirmar a associação de símbolos reais (`code_refs`) e testes a todos os nós L2 e L3.

### Uso da análise estática para refatoração segura

Quando houver relatório de `static_analysis`, o agente deve usá-lo como evidência de risco, não como ordem automática de reescrita. Para cada `quality_finding` relevante:

1. localizar o `file`, `symbol_id`, `qualified_name`, `value`, `limit` e `evidence` no código;
2. confirmar que o adapter realmente suporta aquela métrica para a linguagem da codebase;
3. ler o símbolo completo, seus chamadores, dependências, testes relacionados e referências dos Draws;
4. classificar o achado como correção necessária, refatoração segura, dívida técnica ou falso positivo justificado;
5. escolher a menor divisão coerente de responsabilidades, preservando entrada, saída, efeitos, transações, autorização e tratamento de erros;
6. criar ou confirmar um teste de regressão antes da refatoração quando o comportamento ainda não estiver protegido;
7. fazer a mudança em passos pequenos, executando a suíte específica após cada passo;
8. executar novamente o adapter e comparar `value`/`limit` antes e depois, sem esconder o achado alterando o limite apenas para obter aprovação.

Para funções de produção, considerar como padrão: até 100 linhas é normal, 101–150 é warning de manutenção e acima de 150 é bloqueante. Uma função acima do limite não deve ser dividida mecanicamente; investigar primeiro coesão, dependências, fronteiras de domínio, efeitos colaterais e pontos de decisão. Preferir extrair funções com nomes comportamentais, manter uma sequência principal legível e preservar as identidades públicas quando o contrato não tiver autorizado renomeação.

Para `high_complexity`, reduzir decisões aninhadas e caminhos implícitos apenas quando isso preservar a semântica. Para `too_many_parameters`, avaliar objeto de parâmetros ou agregação de dados somente quando houver coesão real; não agrupar argumentos arbitrariamente. Para `deep_nesting`, usar guard clauses ou extrair políticas quando os caminhos de erro continuarem equivalentes. Para `god_class_candidate` e `high_fan_out`, mapear responsabilidades e dependências antes de mover código.

Warnings não são falhas automáticas e findings bloqueantes não autorizam uma grande refatoração sem escopo. Se o risco ou a mudança de contrato for maior que o pedido, parar e informar a decisão necessária. Se o achado for falso positivo, documentar a evidência e ajustar o adapter/fixture na camada correta, nunca silenciar o relatório no código de produção.

Ao concluir, informar quais achados foram resolvidos, quais permaneceram, os valores antes/depois, testes executados e limitações da análise estática.

### Verificação do desenho antes de implementar

Antes de escrever código, confirmar que o desenho, os testes e os contratos descrevem a mesma intenção. Comparar o fluxo principal, subfluxos, grupos, relações, condições, entradas, saídas, erros, perguntas respondidas e referências de símbolos.

Se existir uma inconsistência real — por exemplo, o desenho manda persistir em um lugar e o contrato manda persistir em outro, um teste exige um comportamento diferente, uma referência aponta para símbolo incorreto ou falta uma decisão necessária para escolher a implementação — não iniciar a implementação. Informar o conflito, apontar os nós/arquivos envolvidos e pedir a correção ou decisão do usuário. Não resolver uma contradição arquitetural silenciosamente no código.

Se o desenho estiver consistente, registrar essa conclusão no raciocínio de implementação e usar suas referências como escopo. Perguntas já respondidas são decisões documentais; não tratá-las como pendências.

### Triagem obrigatória do diff

Antes de decidir o escopo ou concluir que nada precisa ser feito, avaliar o estado completo do Git:

- `git status --short`, `git diff` e `git diff --cached`;
- arquivos não rastreados, especialmente `.stdd/draws/`;
- `git diff -- .stdd/draws` e `git diff --cached -- .stdd/draws`;
- para cada desenho alterado, criado ou removido, ler o JSON atual completo e comparar a intenção do patch, incluindo nós, relações, `draw_ref`, fluxos, perguntas e respostas.

O diff de desenho é entrada de implementação, não apenas evidência auxiliar. Não concluir que não há mudança só porque o diff de produção está vazio ou porque os testes atuais já passam. Ao receber um pedido explícito de implementar, assumir que existe comportamento pendente: localizar a alteração correspondente no diff, nos desenhos e nos contratos, fazer uma mudança coerente e validar seus efeitos. Só encerrar sem alteração quando houver um bloqueio externo explícito e documentado.

Se um desenho referenciado possuir `questions`, ler as respostas persistidas como decisões do usuário. Perguntas sem resposta permanecem ambíguas e devem ser resolvidas antes de escolher um comportamento de produção que dependa delas.

## Implementação

1. Validar entradas antes de ações com efeito.
2. Preservar contratos públicos e compatibilidade, salvo mudança aprovada.
3. Alterar apenas arquivos necessários ao comportamento.
4. Evitar dependência nova; quando inevitável, justificar necessidade, alternativas e risco.
5. Manter fatos determinísticos separados de interpretação produzida por IA.
6. Não gravar segredos, tokens, prompts privados ou respostas sensíveis.
7. Não inserir comentários em funções de produção, exceto para decisão importante ou comportamento não óbvio.

## Ciclo de Vida e Tasks do Backlog

O desenvolvimento pelo backlog obedece fases bem definidas. O agente DEVE executar estritamente UMA task por vez e chamar `stdd backlog test` ou `stdd backlog task` ANTES de avançar. Ao receber uma task, o parser de contexto deve considerar não apenas o nó atual, mas também o nó de origem (nó anterior ou tela de entrada) e o tipo de conexão.

### Bootstrap Task (primeira task de cada ciclo)
Toda inicialização de fluxo de desenvolvimento DEVE iniciar com uma task padrão de infraestrutura que envolva:
- Configurar variáveis de ambiente (`.env`), bibliotecas centrais e arquivos raiz.
- Consolidar o `design.md` e a documentação visual.
- Incluir no `AGENTS.md` as APIs externas a serem consumidas.

### Task Final de Cada Nó L2 (Verificação & Associação)
Ao concluir os subfluxos de um nó, o ciclo deve disparar uma task de encerramento contendo:
1. Verificação funcional completa: telas não devem ser "vazios visuais"; elas devem persistir dados, validar inputs e disparar requisições reais.
2. Associação explícita de arquivos, testes e views ao nó do fluxo correspondente (usando a linha de comando do Draw).

### Task Final do Backlog Geral
Ao final do backlog geral, realiza-se uma etapa final de qualidade:
- Verificação end-to-end do MVP completo.
- Caso falte alguma dependência ou o aplicativo não inicialize, aplicar as correções finais antes de concluir a entrega.

### Execução por backlog

Quando houver um backlog gerado, o `$implement` deve executar o ciclo operacional até não haver mais tasks:

1. executar `stdd backlog task`;
2. encerrar com `backlog-empty` somente quando o comando indicar que não há tasks restantes;
3. ler perguntas, respostas, símbolos, dependências e subfluxo da task;
4. implementar somente a task retornada;
5. executar os testes específicos e os gates aplicáveis;
6. executar `stdd backlog complete <task-id>` com o ID exato recebido;
7. repetir `stdd backlog task`.

Uma task `in_progress` deve ser retomada antes de qualquer outra. Não concluir uma task fora de ordem nem fabricar símbolos, arquivos ou respostas. Se houver bloqueio, preservar a task sem executar `backlog complete` e relatar o motivo.

## Seleção proporcional de testes

Testes protegem comportamento relevante, não cada arquivo alterado. Escolher a menor evidência suficiente para o risco real:

- backend, scripts, regras de negócio, contratos, dados e segurança: testes automatizados são esperados quando a superfície tem comportamento observável;
- frontend: testar automaticamente somente lógica de negócio, transformações de dados, estados críticos, acessibilidade, segurança ou fluxos cuja falha tenha impacto relevante;
- renderização visual, layout, interação comum e acabamento: validar com revisão humana no viewer, screenshots ou inspeção manual reproduzível; não criar testes automatizados apenas para provar que uma tela renderiza;
- Markdown e documentação: não testar automaticamente, salvo quando o arquivo contém comandos executáveis, schema, contrato gerado ou outra regra que realmente possa quebrar;
- mudança sem comportamento relevante: registrar a análise e executar apenas sintaxe, build ou lint aplicável.

Não transformar a ausência de teste de uma superfície não aplicável em bloqueio. Registrar a justificativa e a evidência alternativa, como `visual_review`.

### Categorias aplicáveis

Executar testes funcionais e não funcionais somente quando a categoria for justificada pelo risco:

- regra local: unitários e regressão;
- integração entre módulos: integração e contrato;
- fluxo completo: end-to-end;
- schema ou lógica PostgreSQL: testes de banco e pgTAP;
- chamada de IA: mock, fixture contratual, teste live e, se necessário, avaliação semântica;
- autenticação, autorização ou entrada externa: segurança e isolamento;
- superfície atacável: pentest autorizado;
- caminho crítico ou volume: performance, benchmark ou carga;
- migration: ida, rollback quando suportado e compatibilidade de dados.

### Teste live de inteligência artificial

Quando a alteração integra um provedor real, manter quatro evidências distintas:

1. unidade determinística sem rede;
2. contrato com fixture sanitizada;
3. teste live opt-in contra o provedor;
4. avaliação probabilística rotulada, sem substituir schema e contrato.

No teste live, ler credencial do ambiente, limitar chamadas e custo, aplicar timeout e validar status, JSON, schema, normalização e campos obrigatórios. Não comparar texto livre por igualdade exata. Sem credencial, registrar `not_executed`; nunca converter ausência em `passed`. Sanitizar logs.

### Banco e pgTAP

Para PostgreSQL, usar pgTAP quando houver contrato de schema, constraint, função, trigger, role ou RLS. Preparar banco efêmero ou dedicado a testes, aplicar migrations, executar pgTAP e limpar o ambiente. Bloquear imediatamente qualquer configuração que aponte para produção. Ausência do runner deve aparecer como `not_executed` ou `blocked`, conforme a política do projeto.

### Performance, segurança, isolamento e pentest

- Performance: comparar com baseline sob carga reproduzível; registrar p50/p95 quando aplicável, repetições e tolerância.
- Segurança: testar caminhos negativos, privilégios mínimos, validação de entrada, segredos e comportamento fail-closed.
- Isolamento: executar casos concorrentes e provar separação entre tenants, bancos, filas, caches e arquivos temporários.
- Pentest: executar somente em ambiente autorizado, com alvo e intensidade limitados; nunca iniciar contra produção por inferência.

## Ordem de validação

1. teste diretamente relacionado;
2. suíte da área alterada;
3. análise sintática, lint e tipagem disponíveis;
4. análise estática integrada;
5. suítes de contrato, banco, segurança ou performance exigidas pelo risco;
6. `stdd test` como gate agregado.

`stdd test` é o alias global: deve executar todas as suítes configuradas, mesmo que uma anterior falhe, e consolidar o resultado. Runners especializados são responsáveis por setup e cleanup próprios; no banco, isso inclui ambiente isolado, migrations, testes e limpeza.

Em perfil `mvp`, respeitar a cobertura escolhida pelo usuário. Usar `--suite`, `--exclude` e `--profile` para controlar a execução; usar `--approve-actions` somente depois de obter aprovação explícita. Antes de instalar dependência ou blocker, baixar ferramenta ou imagem, iniciar ou recriar container, criar banco, aplicar migrations fora de ambiente efêmero ou acionar serviço pago, apresentar impacto e pedir autorização. Sem autorização, registrar `not_executed` e continuar apenas com o trabalho seguro.

Falha de ferramenta obrigatória é `blocked` ou `failed`, não sucesso. Teste live, pentest ou banco não configurado deve ser `not_executed` com ação necessária.

## Revisão obrigatória dos desenhos após implementar

Depois que o código e os testes estiverem validados, revisar novamente todos os desenhos associados ao comportamento implementado. Essa revisão confirma se o código entregue continua consistente com a intenção que foi validada antes da implementação.

Executar a revisão nesta ordem:

1. localizar os desenhos associados pelos `code_refs`, `qualified_name`, `source_dependencies`, `draw_ref` e pelos fatos em `.stdd/facts/*.facts.json`;
2. ler o desenho principal completo e todos os subfluxos relacionados, não somente o nó alterado;
3. comparar nós, relações, estados, nomes, condições, erros, entradas, saídas, perguntas e respostas com o comportamento realmente implementado;
4. verificar referências `resolved`, `unresolved` e `drift`, além de arquivos, funções e testes retornados pela análise estática;
5. se aparecer uma inconsistência real, não alterar silenciosamente o desenho: informar o conflito, os elementos afetados e a decisão necessária;
6. se não houver inconsistência, enriquecer a documentação sem mudar a intenção do desenho: corrigir apenas referências factuais, adicionar detalhes, perguntas já respondidas, grupos ou subfluxos explicativos quando forem complementares ao comportamento entregue;
7. reler o desenho inteiro após qualquer enriquecimento e confirmar que o fluxo principal, os subfluxos e as conexões continuam coerentes.

Não limitar a revisão ao nó que originou a implementação. Se uma mudança alterou uma condição, contrato, dependência, tratamento de erro ou sequência, verificar todos os elementos afetados. Só atualizar o desenho automaticamente quando a alteração for um enriquecimento compatível com a intenção já aprovada; mudança de escopo, fluxo ou decisão arquitetural exige aviso ao usuário.

### Documentação rápida com perguntas respondidas

Não tratar perguntas pendentes como requisito para concluir a implementação. Quando a implementação revelar uma decisão já tomada, regra implícita, risco ou detalhe que vale preservar, criar uma pergunta no nó ou subfluxo e gravar imediatamente a resposta correspondente como documentação rápida. Essas perguntas devem documentar o que foi feito, não abrir uma nova pendência.

Usar perguntas respondidas para registrar, por exemplo:

- por que uma dependência foi escolhida;
- qual é a fronteira entre fluxo principal e subfluxo;
- o que acontece em timeout, erro, retry ou resposta inválida;
- qual símbolo, teste ou contrato deve ser revisado quando o nó mudar;
- qual limitação ou decisão de segurança foi aplicada.

As perguntas devem ser curtas, específicas e verificáveis. Em perguntas de múltipla escolha, colocar `(sugestao)` na alternativa da resposta recomendada, nunca no texto da pergunta. A resposta deve refletir o código realmente implementado; não usar perguntas respondidas para esconder uma incerteza que ainda exige decisão do usuário.

Se o comportamento novo exigir uma sequência independente, uma integração ou um caminho de erro que complemente o nó atual sem mudar sua intenção, criar um subfluxo e conectá-lo ao ponto correto do fluxo principal. Se isso mudar o escopo ou introduzir uma decisão arquitetural nova, parar e avisar o usuário antes de alterar o desenho. Associar os novos nós aos símbolos e testes correspondentes quando esses fatos estiverem disponíveis.

Ao concluir, informar quais desenhos foram revisados, quais vínculos foram atualizados, quais detalhes ou subfluxos foram inseridos e quais associações permanecem `unresolved` ou `drift`. O resultado só pode ser declarado completo quando código, testes, referências e desenhos estiverem consistentes.

## Testes legíveis

Se for necessário adicionar teste de regressão durante a implementação:

- usar nome comportamental;
- em Python, escrever docstring de exatamente duas linhas curtas;
- marcar etapas de testes longos e end-to-end com comentários breves;
- registrar teste e implementação em logs separados.

## WorkTypes e logs

Usar o tipo pela natureza real do trabalho:

- `--impl`: comportamento novo planejado;
- `--bug`: correção de defeito com regressão;
- `--test`: criação ou alteração de teste;
- `--refactor`: retrabalho, falta de planejamento prévio ou reorganização sem nova regra de negócio.

O framework marca automaticamente como `refactor` apenas substituições extremas de pelo menos 500 linhas adicionadas e 500 removidas. Abaixo disso, avaliar intenção e contexto. Preferir um tipo por registro e criar logs progressivos por etapa concluída.

```bash
stdd log "Implementa comportamento aprovado" --impl
```

## Conclusão

Declarar sucesso somente com diff dentro do escopo, testes relevantes passando, sintaxe válida, nenhuma regressão estrutural injustificada e limitações explícitas. Informar arquivos alterados, comandos e resultados, evidências, testes `not_executed` e próxima ação necessária.
