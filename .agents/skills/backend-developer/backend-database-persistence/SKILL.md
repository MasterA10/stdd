---
name: backend-database-persistence
description: "Projeta e revisa banco de dados e persistência backend com schema consistente, queries seguras, transações, migrações e recuperação confiável."
---

# Backend Database & Persistence

Use esta skill ao criar ou alterar schema, modelos, queries, repositórios, migrações,
transações, cache persistido ou qualquer armazenamento de dados. Permaneça agnóstico ao
banco e siga o contrato e as convenções da aplicação.

## Avaliação obrigatória da stack

Antes de escolher uma solução, identifique o framework, ORM/driver, banco, mecanismo de
cache e modelo de execução realmente usados. Consulte a documentação oficial e as
convenções do próprio ecossistema para verificar a forma recomendada de configurar
conexões, migrations, transações, pooling, constraints, serialização, retries e testes.
Prefira os primitives oficiais e idiomáticos da stack; não imponha um padrão genérico se
ele contrariar garantias, lifecycle ou limites do framework. Registre a decisão e o motivo
quando houver mais de uma alternativa razoável.

## Fonte de verdade e classificação dos dados

Classifique cada dado antes de decidir onde gravá-lo:

- **Persistente e autoritativo**: informação de negócio, identidade, histórico, estado
  necessário após reinício ou dado que não pode ser recriado. Deve ser gravado em um
  armazenamento durável, com integridade, backup, controle de acesso e política de retenção.
- **Derivado e reconstruível**: resultado de consulta ou cálculo que pode ser refeito a
  partir da fonte de verdade. Pode usar cache apenas como otimização, com invalidação,
  TTL, limite de tamanho e fallback para a fonte persistente.
- **Efêmero**: estado curto de execução, lock ou coordenação. Deve ter expiração e não
  pode ser a única cópia de uma decisão ou dado de negócio.

Nunca use cache como substituto de persistência. Dados de identidade, pessoais, financeiros,
regulatórios ou necessários para auditoria não devem ser guardados em cache por padrão —
por exemplo, CPF de usuário deve permanecer em persistência segura, não em cache. Se houver
uma exceção técnica realmente justificada, ela exige decisão explícita, minimização,
criptografia, TTL curto, controle de acesso, não exposição em chaves/logs e teste de
invalidação; o cache jamais vira a fonte de verdade.

Não coloque PII, tokens, credenciais ou dados sensíveis em chaves de cache, métricas,
URLs, mensagens de erro ou fixtures. Quando possível, persista identificadores protegidos
ou referências internas, aplique criptografia/mascaramento conforme a classificação e
separe dados de autenticação, dados pessoais e dados operacionais.

## Tipos nativos e desenho eficiente de tabelas

Escolha o tipo de dado pelo significado e pelo comportamento esperado no banco, não pela
facilidade de serializar no código. Antes de criar o schema, confirme no framework/ORM o
mapeamento para o tipo nativo e valide o DDL gerado:

- Datas e horários devem usar o tipo temporal nativo apropriado (por exemplo, timestamp
  com fuso/UTC quando o banco e o domínio suportarem), nunca string para representar tempo.
  Defina explicitamente precisão, timezone e convenção de gravação; converta apenas na
  borda de apresentação.
- Valores monetários e medidas que exigem exatidão devem usar decimal/numeric com precisão
  e escala definidas, não ponto flutuante. Contagens, flags e estados devem usar tipos
  compactos e semânticos, respeitando os recursos e limitações da stack.
- Identificadores, chaves estrangeiras, códigos e versões devem ter tipos compatíveis em
  todas as tabelas. Não use texto ilimitado para tudo, nem JSON/blob para campos que são
  pesquisados, relacionados, ordenados ou sujeitos a constraint.
- Defina tamanho, nulabilidade, default e collation conscientemente. Evite defaults que
  escondam erro de aplicação, colunas sempre nulas sem justificativa e precisão maior que
  a necessária, pois largura de linha afeta armazenamento, cache e índices.

Organize tabelas para refletir entidades e relações reais: chaves primárias estáveis,
foreign keys, constraints de unicidade e índices baseados nas consultas reais. Indexe
colunas usadas em filtros, joins e ordenação quando houver benefício medido; evite excesso
de índices, índices redundantes e indexação indiscriminada de campos de baixa seletividade.
Analise planos de execução e cardinalidade em dados representativos. Não transforme um
campo estruturado em JSON ou um modelo EAV apenas para evitar desenhar o schema; use isso
somente quando a variabilidade for genuína e documente o custo de consulta e integridade.

## Modelagem

- Modele entidades, limites e relacionamentos a partir do domínio; defina chaves,
  nulabilidade, tipos, constraints e índices explicitamente.
- Preserve integridade no banco e na aplicação: chaves estrangeiras, unicidade,
  invariantes e validações não devem depender apenas da interface.
- Escolha normalização, desnormalização e cache por evidência de acesso e consistência.
  Documente trade-offs e fonte de verdade.
- Separe domínio, caso de uso e acesso a dados. Repositórios/adaptadores devem esconder
  detalhes do driver sem esconder custos, erros ou semântica de consistência.

## Queries, transações e concorrência

Use queries parametrizadas ou APIs seguras; nunca concatene entrada do usuário em SQL.
Selecione apenas os campos necessários, imponha paginação/limites, valide ordenação e
monitore consultas lentas. Defina timeout, isolamento, lock e idempotência conforme o
caso de uso. Mantenha transações curtas, com efeitos externos fora da transação ou
coordenados por um mecanismo explícito. Trate concorrência, retries e operações
parcialmente concluídas sem duplicar dados.

## Migrações, falhas e dados

Migrações devem ser versionadas, revisáveis, reversíveis quando possível e testadas em
uma cópia representativa. Planeje mudanças incompatíveis em etapas (expandir, migrar,
contrair), com backfill controlado e caminho de rollback. Nunca destrua ou reescreva
dados em produção sem confirmação e backup verificável. Não coloque credenciais em
schema, fixtures, logs ou seeds.

Defina limites de retenção, apagamento, backup, restauração e classificação de dados.
Falhas de persistência devem ser distinguíveis de “não encontrado”, ter erro observável
e não deixar estado parcialmente confirmado.

## Validação

Teste constraints, queries críticas, autorização no acesso a registros, transações,
concorrência relevante, migrações em banco limpo e existente, rollback/backfill e
falhas de conexão/timeouts. Use fixtures determinísticas e dados não sensíveis; confirme
que testes não dependem da ordem ou do estado residual de outra execução.

