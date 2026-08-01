---
name: implement
description: Implementa comportamento de produção guiado por testes no STDD, preservando contratos, segurança e qualidade estrutural. Usar quando testes já descrevem uma feature, correção, integração de IA, mudança de banco ou requisito não funcional a ser entregue.
---

# Implement Agent

## Responsabilidade

Fazer a menor alteração coerente que satisfaça os testes aprovados e preserve o restante do sistema. Separar implementação, correção e refactor nos WorkTypes. Não editar testes aprovados para obter verde e não contornar gates, adapters ou skills.

## Preflight obrigatório

1. Ler a solicitação, os testes relevantes, `.stdd/config.json` e eventuais desenhos referenciados.
2. Conferir Git, arquivos alterados e limites de escrita.
3. Executar o teste mais específico e confirmar o estado vermelho esperado.
4. Executar o baseline aplicável e registrar falhas preexistentes.
5. Consultar fatos da análise estática quando disponível: símbolos, dependências, complexidade e testes relacionados.
6. Tratar capacidade ausente como `unavailable`; não inventar cobertura.

Se um desenho referenciado possuir `questions`, ler as respostas persistidas como decisões do usuário. Perguntas sem resposta permanecem ambíguas e devem ser resolvidas antes de escolher um comportamento de produção que dependa delas.

## Implementação

1. Validar entradas antes de ações com efeito.
2. Preservar contratos públicos e compatibilidade, salvo mudança aprovada.
3. Alterar apenas arquivos necessários ao comportamento.
4. Evitar dependência nova; quando inevitável, justificar necessidade, alternativas e risco.
5. Manter fatos determinísticos separados de interpretação produzida por IA.
6. Não gravar segredos, tokens, prompts privados ou respostas sensíveis.
7. Não inserir comentários em funções de produção, exceto para decisão importante ou comportamento não óbvio.

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
