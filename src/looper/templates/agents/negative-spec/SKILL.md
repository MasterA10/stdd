---
name: negative-spec
description: "Lê o contexto completo do sistema e revisa todos os Draws L3 para definir condições de não aceite e presunções que não podem ser assumidas."
---

# Negative Spec

Use esta skill para revisar ou completar Draws de nível 3 antes da implementação ou da
validação final. O resultado de cada nó é somente um `negative_spec`: condições objetivas
de não aceite e presunções proibidas. Não crie critérios de sucesso, aceite ou aprovação.

## Contexto obrigatório antes da revisão

Antes de navegar qualquer nó L3, leia o contexto estruturado completo da aplicação:

```bash
looper draw context
```

Execute o comando sem `--draw`, `--level` ou `--node`. Esse contexto global é obrigatório:
inclui arquitetura, jornadas, conexões, perguntas, respostas, símbolos, dependências e
metadados necessários para interpretar cada task sem isolá-la do sistema. Só depois dessa
leitura navegue os Draws L3 relacionados, usando filtros quando ajudarem a examinar cada
desenho em detalhe:

```bash
looper draw context --level 3
looper draw context --node <node-id>
```

Não conclua a análise de um L3 apenas pela descrição do próprio nó. Compare-o com o contexto
L1/L2, seus pais, irmãos, conexões, contratos e fronteiras do sistema inteiro.

## Objetivo

Percorra todos os Draws L3 vinculados às jornadas e avalie cada nó e conexão com o contexto
global. Identifique lacunas pequenas mas relevantes: estados não tratados, autorização
ausente, persistência incorreta, dados em cache indevido, tipos inadequados, validação
faltante, erro engolido, efeito duplicado, contrato externo inventado, retry inseguro,
ausência de idempotência ou saída que não corresponde ao fluxo.

A revisão também deve identificar **presunções que não podem ser assumidas**. Considere
proibida qualquer conclusão que não esteja definida ou comprovada pelo contexto completo,
pelo Draw correspondente, por uma convenção técnica oficial ou pelo código lido. Exemplos:

- não presumir que o usuário está autenticado, autorizado, no tenant correto ou usando uma
  sessão válida;
- não presumir que um dado existe, está atualizado, é único, está persistido ou pode ser
  recuperado do cache;
- não presumir que uma API externa responde, que o payload é válido, que a rede é confiável
  ou que retry é seguro/idempotente;
- não presumir que campos omitidos, permissões, timezone, locale, ordenação, paginação,
  concorrência ou estado anterior têm um valor padrão;
- não presumir que a existência de endpoint, classe, migration, teste ou resposta HTTP prova
  o comportamento ponta a ponta;
- não presumir que uma lacuna do Draw é uma decisão de produto ou autorização para inventar
  regra, dado, arquivo, endpoint, dependência ou fluxo.

Transforme cada lacuna ou presunção insegura em uma condição verificável de não aceite.
+
## Invariantes implícitos e perguntas abertas

Durante a leitura, procure padrões operacionais comuns ao domínio e ao tipo de recurso:
limites de estoque ou ingressos, encerramento de vendas, expiração, duplicidade, cancelamento,
conflitos de concorrência, estados terminais, retenção e recuperação. A ausência de uma regra
óbvia no texto é uma lacuna a ser analisada, não uma autorização para inventá-la.

Use esta decisão para cada padrão encontrado:

1. Se o contexto global, o L1/L2, as decisões respondidas, as conexões e as dependências
   permitirem concluir claramente que a regra é uma verdade do sistema, registre-a como
   `negative_spec` no nó aplicável. Exemplo: “Não aceitar se a venda continuar depois que a
   quantidade disponível atingir zero”, somente quando o contexto realmente definir limite,
   disponibilidade e encerramento da venda.
2. Se o contexto não permitir afirmar a regra com segurança, crie no próprio nó a pergunta
   aberta que falta, usando o contrato de perguntas do Draw: `type: "open"`, `answer: null`
   e um `prompt` específico sobre a decisão. Exemplo: “Quando a quantidade de ingressos
   atingir zero, a venda deve ser encerrada, entrar em lista de espera ou seguir outro fluxo?”.
3. Não transforme uma pergunta aberta em `negative_spec`, não escolha a resposta pelo usuário
   e não use uma convenção genérica do domínio como se fosse decisão confirmada. A pergunta
   deve permanecer visível para ser respondida por uma pessoa responsável.

A pergunta deve ser criada no nó mais diretamente afetado e explicar o impacto da resposta
sobre o comportamento, as permissões, os estados, a persistência ou as saídas. Antes de criar
uma nova pergunta, verifique perguntas existentes e não duplique uma decisão já respondida.


## Forma do Negative Spec

O Negative Spec deve combinar, quando aplicável:

- **Condição de não aceite**: “Não aceitar se ...”.
- **Presunção proibida**: “Não presumir que ...; exigir evidência de ...”.

Se a presunção proibida impedir uma decisão técnica, registre também uma pergunta aberta em
`questions`. Não transforme ausência de definição em um valor padrão inventado.

## Regras

- O Negative Spec deve ser específico ao nó, ao papel, à entrada, à regra e ao efeito
  observável; não use frases genéricas como “não pode ter bugs”.
- Escreva condições falsificáveis: deve ser possível testar ou inspecionar se ocorreram.
- Não invente comportamento para preencher lacunas. Se a evidência não bastar, registre a
  dúvida em `questions` e mantenha a condição limitada ao que o contexto sustenta.
- Cubra sucesso aparente que ainda seria incompleto: código existente não prova persistência,
  autorização, transação, contrato, recuperação ou experiência ponta a ponta.
- Preserve a separação entre fato implementado e comportamento planejado. O Negative Spec
  descreve a barreira de conclusão, não altera o comportamento do sistema.
- Para dados sensíveis, segurança, persistência e integrações, seja explícito sobre perda,
  exposição, inconsistência, duplicidade, bypass e falha silenciosa.
- Remova qualquer `success_criteria` ou `failure_criteria` do resultado e use somente
  `negative_spec`.

## Processo

1. Execute `looper draw context` sem filtros e leia o contexto completo do sistema.
2. Navegue todos os Draws L3 e confirme pais, conexões, grupos, ações, decisões, saídas e
   dependências comparando-os com L1 e L2.
3. Liste os caminhos críticos de cada nó L3: entrada, pré-condição, autorização, validação,
   regra, persistência, integração, resposta, erro, retry e recuperação.
4. Para cada caminho, pergunte: “O que provaria que esta task ainda não foi feita?” e “O que
   alguém poderia presumir sem que o contexto autorize?”.
5. Grave no campo `negative_spec` as condições de não aceite e as presunções proibidas,
   sem apagar a descrição técnica nem criar critérios positivos.
6. Registre em `questions` toda decisão ausente que impeça validar a não aceitação; não
   silencie a lacuna nem a resolva por conveniência.
7. Revise o L3 completo para garantir que todos os nós foram avaliados, inclusive terminais,
   decisões, erros e estados de recuperação; reporte lacunas e perguntas abertas.
8. Valide o JSON e registre a alteração com `looper log`. Entregue os IDs revisados, as
   condições adicionadas, as presunções proibidas, as perguntas sem resposta, as lacunas
   não resolvidas e as limitações.

## Contrato do loop

A task não está concluída quando qualquer condição do `negative_spec` ocorrer ou quando uma
presunção proibida for usada sem evidência. O agente deve demonstrar evidências objetivas de
que cada condição aplicável não ocorreu e de que decisões críticas não foram assumidas. A
simples existência de endpoint, classe, migration ou teste superficial não é evidência
suficiente. O Negative Spec não autoriza inventar testes, APIs, dados, permissões ou regras
que não estejam definidos no contexto completo, no Draw ou nas convenções oficiais consultadas.
