# Backlog Completo de Implementação

## CLI de Preservação Comportamental e Desenvolvimento Assistido por IA

---

# Como utilizar este backlog

Cada tarefa possui:

* **Objetivo:** resultado esperado.
* **Implementação:** atividades que devem ser realizadas.
* **Entregáveis:** arquivos, comandos ou componentes produzidos.
* **Critérios de aceite:** evidências necessárias para concluir a tarefa.
* **Dependências:** tarefas que precisam estar concluídas anteriormente.

O agente deverá:

1. executar as tarefas na ordem indicada;
2. não iniciar uma fase com dependências pendentes;
3. criar testes antes ou junto da implementação;
4. registrar decisões arquiteturais relevantes;
5. executar os critérios de aceite;
6. não marcar tarefas como concluídas apenas porque o código compila;
7. produzir um relatório resumido ao final de cada fase.

---

# Fase 0 — Fundação do projeto

## Tarefa 0.1 — Criar o repositório principal

### Objetivo

Criar a estrutura inicial da CLI e preparar o projeto para desenvolvimento incremental.

### Implementação

* Criar o repositório Git.
* Definir a linguagem do núcleo da CLI.
* Utilizar TypeScript como implementação inicial recomendada.
* Configurar Node.js em versão LTS.
* Escolher um gerenciador de pacotes.
* Configurar TypeScript em modo estrito.
* Configurar lint.
* Configurar formatter.
* Configurar testes.
* Configurar build.
* Configurar execução local da CLI.
* Configurar commits convencionais, se desejado.
* Criar `.gitignore`.
* Criar licença.
* Criar README inicial.

### Entregáveis

```text
package.json
tsconfig.json
src/
tests/
README.md
LICENSE
.gitignore
```

### Critérios de aceite

* O projeto instala sem erros.
* O TypeScript compila.
* O lint executa.
* A suíte de testes executa.
* Um comando inicial da CLI responde no terminal.

### Dependências

Nenhuma.

---

## Tarefa 0.2 — Definir princípios arquiteturais

### Objetivo

Registrar as regras que todas as implementações futuras deverão respeitar.

### Implementação

Criar documentos de decisão contendo:

* scripts comprovam fatos;
* agentes interpretam significado;
* testes preservam comportamento;
* humanos aprovam intenção;
* saídas probabilísticas nunca são tratadas como fatos exatos;
* chaves e segredos nunca são armazenados no projeto;
* o framework não suporta todas as linguagens antecipadamente;
* adaptadores são criados para a stack do projeto;
* o CLI é a interface pública principal;
* código legado pode utilizar baseline;
* novas alterações não devem piorar silenciosamente a estrutura.

### Entregáveis

```text
docs/architecture/principles.md
docs/architecture/decisions/
```

### Critérios de aceite

* Os princípios estão versionados.
* Todas as futuras decisões podem referenciar esses documentos.
* Existe uma definição clara de operações determinísticas, probabilísticas e híbridas.

### Dependências

Tarefa 0.1.

---

## Tarefa 0.3 — Definir convenções internas

### Objetivo

Padronizar nomes, schemas, erros e resultados.

### Implementação

Definir:

* formato dos comandos;
* nomenclatura dos módulos;
* formato de erros;
* estrutura dos logs;
* exit codes;
* formato das respostas JSON;
* IDs estáveis;
* versão dos schemas;
* convenção de diretórios internos.

### Entregáveis

```text
docs/architecture/conventions.md
src/core/errors/
src/core/result/
src/core/schemas/
```

### Critérios de aceite

* Todos os comandos podem retornar saída humana e saída JSON.
* Erros possuem códigos estáveis.
* Exit codes estão documentados.
* Schemas possuem versão.

### Dependências

Tarefa 0.2.

---

# Fase 1 — Núcleo da CLI

## Tarefa 1.1 — Criar o parser de comandos

### Objetivo

Disponibilizar a estrutura principal da CLI.

### Implementação

Criar a estrutura dos comandos CLI públicos e registrar os agentes suportados:

```text
stdd init (CLI: instala a estrutura .stdd/ e as skills dos agentes em .agents/skills/)
stdd test (CLI: valida contratos e roda a suíte de testes configurada no terminal)

Agentes/Skills (em .agents/skills/):
- setup     (Agente: responsável pela varredura da codebase, diagnósticos, mapeamento e alinhamento de testes)
- feature   (Agente: traduz solicitações em cenários e testes executáveis)
- implement (Agente: guia a implementação de produção pelos testes)
```

Adicionar:

* `--help`;
* `--version`;
* `--json`;
* `--verbose`;
* `--quiet`;
* `--no-color`;
* `--ci`.

### Entregáveis

```text
src/cli/
src/commands/
```

### Critérios de aceite

* Todos os comandos aparecem no help.
* Comandos desconhecidos retornam erro consistente.
* A saída JSON é válida.
* O exit code é previsível.

### Dependências

Fase 0.

---

## Tarefa 1.2 — Criar sistema de configuração

### Objetivo

Permitir configuração global e por projeto.

### Implementação

Suportar:

* `framework.yml`;
* `.framework/project/stack.yml`;
* configurações padrão;
* sobrescrita por flags;
* sobrescrita por variáveis de ambiente;
* validação por schema;
* versionamento da configuração;
* migração futura de versões.

### Entregáveis

```text
src/config/
schemas/framework-config.schema.json
```

### Critérios de aceite

* Configuração inválida é rejeitada.
* Mensagens indicam o campo incorreto.
* Valores padrão são aplicados.
* Segredos não são aceitos diretamente no arquivo.

### Dependências

Tarefa 1.1.

---

## Tarefa 1.3 — Criar executor de processos

### Objetivo

Executar ferramentas externas de forma segura e observável.

### Implementação

Adicionar:

* execução de subprocessos;
* timeout;
* captura de stdout;
* captura de stderr;
* exit code;
* cancelamento;
* diretório de execução;
* variáveis permitidas;
* sanitização de logs;
* suporte a streaming;
* modo silencioso;
* modo CI.

### Entregáveis

```text
src/execution/process-runner.ts
```

### Critérios de aceite

* Comandos com sucesso são capturados corretamente.
* Falhas retornam erro estruturado.
* Timeouts encerram o processo.
* Segredos conhecidos são mascarados.
* Processos filhos são encerrados no cancelamento.

### Dependências

Tarefa 1.2.

---

## Tarefa 1.4 — Criar sistema de logs

### Objetivo

Registrar operações sem expor informações sensíveis.

### Implementação

Criar níveis:

* debug;
* info;
* warning;
* error;
* audit.

Registrar:

* comando;
* duração;
* status;
* arquivos afetados;
* scripts executados;
* agentes utilizados;
* resultados de validação.

### Entregáveis

```text
src/logging/
.framework/logs/
```

### Critérios de aceite

* Nenhuma chave aparece nos logs.
* O modo JSON produz eventos válidos.
* Logs de auditoria são separados dos logs de interface.
* Cada execução possui identificador único.

### Dependências

Tarefa 1.3.

---

# Fase 2 — Estado local e banco de dados

## Tarefa 2.1 — Criar banco SQLite

### Objetivo

Criar a memória estrutural e comportamental do projeto.

### Implementação

Criar tabelas para:

* projetos;
* aplicações;
* stacks;
* símbolos;
* descrições;
* testes;
* relações;
* comportamentos;
* alterações;
* bugs;
* métricas;
* agentes;
* inferências;
* contratos;
* execuções;
* hooks;
* harnesses.

### Entregáveis

```text
src/database/
src/database/migrations/
.framework/index/framework.db
```

### Critérios de aceite

* Banco é criado automaticamente.
* Migrations são versionadas.
* Migrations podem ser reaplicadas em banco vazio.
* Operações possuem transações.
* Dados podem ser exportados para JSON.

### Dependências

Fase 1.

---

## Tarefa 2.2 — Implementar repositórios internos

### Objetivo

Evitar que comandos manipulem SQL diretamente.

### Implementação

Criar repositórios para:

* símbolos;
* testes;
* relações;
* descrições;
* mudanças;
* bugs;
* execuções;
* configurações de inferência;
* harnesses.

### Entregáveis

```text
src/database/repositories/
```

### Critérios de aceite

* Repositórios possuem testes.
* Nenhuma camada de comando executa SQL diretamente.
* Operações de escrita são transacionais.

### Dependências

Tarefa 2.1.

---

## Tarefa 2.3 — Criar sistema de snapshots

### Objetivo

Registrar o estado antes e depois de alterações.

### Implementação

Capturar:

* commit atual;
* Git status;
* hashes;
* símbolos;
* testes;
* métricas;
* dependências;
* arquivos modificados.

### Entregáveis

```text
src/snapshots/
.framework/snapshots/
```

### Critérios de aceite

* Um snapshot pode ser comparado com outro.
* O snapshot não duplica a codebase inteira desnecessariamente.
* Arquivos sensíveis são ignorados.

### Dependências

Tarefa 2.2.

---

# Fase 3 — Descoberta da codebase

## Tarefa 3.1 — Implementar `framework init`

### Objetivo

Inicializar projetos novos ou existentes.

### Implementação

Detectar se o diretório:

* está vazio;
* possui codebase;
* é monorepo;
* possui configuração anterior.

Para projeto vazio:

* perguntar linguagem;
* framework;
* banco;
* framework de testes;
* perfil;
* agente;
* harness.

Para codebase existente:

* iniciar análise automática;
* apresentar resultado;
* permitir correção;
* salvar somente após aprovação.

### Entregáveis

```text
src/commands/init/
```

### Critérios de aceite

* Projeto novo pode ser configurado.
* Projeto existente pode ser detectado.
* Nenhuma configuração ambígua é salva sem indicação.
* O comando pode ser reexecutado sem destruir dados.

### Dependências

Fase 2.

---

## Tarefa 3.2 — Detectar linguagens

### Objetivo

Identificar linguagens utilizadas no projeto.

### Implementação

Analisar:

* extensões;
* manifests;
* diretórios;
* arquivos de build;
* lockfiles;
* containers.

Registrar:

* linguagem;
* caminho;
* evidência;
* nível de confiança.

### Entregáveis

```text
src/discovery/languages/
```

### Critérios de aceite

* Projetos com uma ou múltiplas linguagens são identificados.
* O relatório mostra evidências.
* Inferências incertas são marcadas como inferidas.

### Dependências

Tarefa 3.1.

---

## Tarefa 3.3 — Detectar frameworks e ferramentas

### Objetivo

Descobrir frameworks, test runners, ORMs, builds e linters.

### Implementação

Analisar:

* dependências;
* scripts;
* configurações;
* imports;
* containers.

### Critérios de aceite

* Framework principal é detectado.
* Test runners existentes são detectados.
* Ferramentas de lint e tipagem são registradas.
* O usuário pode corrigir o resultado.

### Dependências

Tarefa 3.2.

---

## Tarefa 3.4 — Detectar bancos e serviços externos

### Objetivo

Identificar persistência e integrações relevantes.

### Implementação

Detectar:

* PostgreSQL;
* MySQL;
* MariaDB;
* SQLite;
* MongoDB;
* Redis;
* filas;
* serviços HTTP;
* SDKs de IA;
* serviços de arquivos.

Não ler valores secretos.

### Critérios de aceite

* Apenas nomes de variáveis de ambiente são registrados.
* Nenhuma credencial aparece no banco ou logs.
* Serviços incertos são sinalizados.

### Dependências

Tarefa 3.3.

---

## Tarefa 3.5 — Implementar `framework scan`

### Objetivo

Reanalisar a stack após mudanças.

### Implementação

Produzir diff da stack:

* linguagem adicionada;
* framework removido;
* banco alterado;
* novo serviço;
* nova suíte de testes.

### Critérios de aceite

* Nenhuma alteração é aplicada sem relatório.
* O usuário pode aceitar ou rejeitar mudanças.
* Execução em CI pode usar política automática.

### Dependências

Tarefas 3.2 a 3.4.

---

## Tarefa 3.6 — Implementar `framework doctor`

### Objetivo

Diagnosticar o ambiente.

### Implementação

Verificar:

* runtimes;
* versões;
* package managers;
* test runners;
* containers;
* banco de testes;
* permissões;
* scripts;
* agentes;
* harnesses;
* configuração de inferência.

### Critérios de aceite

* Problemas possuem instrução objetiva.
* Credenciais são exibidas apenas como disponíveis ou ausentes.
* O comando não modifica o ambiente.

### Dependências

Tarefa 3.5.

---

# Fase 4 — Contratos de adaptadores

## Tarefa 4.1 — Criar contrato de linguagem

### Objetivo

Definir o que um adaptador de linguagem deve implementar.

### Implementação

A interface deve incluir:

```text
detect
parse
extractSymbols
extractTypes
extractRelations
detectChangedSymbols
measureComplexity
formatGeneratedComment
validateSyntax
```

### Critérios de aceite

* O contrato não depende de uma linguagem específica.
* Entradas e saídas possuem schemas.
* Erros são padronizados.

### Dependências

Fase 3.

---

## Tarefa 4.2 — Criar contrato de test runner

### Objetivo

Padronizar execução e leitura dos testes.

### Implementação

A interface deve incluir:

```text
detect
listSuites
listTests
run
parseResults
extractCases
identifyUsedSymbols
```

### Critérios de aceite

* Resultados de frameworks diferentes podem ser normalizados.
* Categorias de testes são suportadas.
* Exit code e falhas são preservados.

### Dependências

Tarefa 4.1.

---

## Tarefa 4.3 — Criar contrato de banco

### Objetivo

Padronizar testes de banco e preparação de ambiente.

### Implementação

Incluir:

* detecção;
* inicialização de ambiente de teste;
* migrations;
* seed;
* cleanup;
* execução de testes;
* desligamento.

### Critérios de aceite

* O contrato não assume um banco específico.
* O ambiente de teste pode ser isolado.
* Produção nunca é utilizada por padrão.

### Dependências

Tarefa 4.2.

---

## Tarefa 4.4 — Criar contrato de inferência

### Objetivo

Padronizar integrações com modelos de IA.

### Implementação

Incluir:

```text
detectConfiguration
validateCredentials
buildRequest
invoke
normalizeResponse
validateContract
```

### Critérios de aceite

* O contrato não expõe chave.
* Respostas são normalizadas.
* Schemas podem ser validados fora do modelo.

### Dependências

Tarefa 4.3.

---

## Tarefa 4.5 — Criar contrato de harness

### Objetivo

Padronizar integração com ambientes de agentes.

### Implementação

Incluir:

```text
detect
inspectCapabilities
installIntegration
registerHook
installSubagent
execute
collectEvidence
uninstall
```

### Critérios de aceite

* O contrato suporta hooks nativos e wrapper externo.
* Capacidades são detectadas, não presumidas.
* Adaptadores podem declarar limitações.

### Dependências

Tarefa 4.4.

---

# Fase 5 — Geração de adaptadores por agentes

## Tarefa 5.1 — Criar o Adapter Agent

### Objetivo

Permitir que o agente local implemente adaptadores para a stack detectada.

### Implementação

O agente deverá receber:

* contrato;
* stack;
* estrutura do projeto;
* ferramentas disponíveis;
* diretórios permitidos;
* testes obrigatórios;
* schemas esperados.

### Entregáveis

```text
.framework/agents/adapter/
```

### Critérios de aceite

* O agente só escreve em diretórios autorizados.
* A resposta segue schema.
* O agente não altera o núcleo da CLI.

### Dependências

Fase 4.

---

## Tarefa 5.2 — Criar gerador de testes para adaptadores

### Objetivo

Validar adaptadores antes da ativação.

### Implementação

Gerar testes como:

* extrair funções;
* extrair classes;
* detectar função modificada;
* identificar tipos;
* inserir comentário;
* executar test runner;
* normalizar resultado.

### Critérios de aceite

* Adaptador não é ativado com testes falhando.
* Casos de erro são testados.
* O adaptador não pode retornar dados fora do schema.

### Dependências

Tarefa 5.1.

---

## Tarefa 5.3 — Criar sandbox de adaptadores

### Objetivo

Impedir que scripts gerados façam operações não autorizadas.

### Implementação

Aplicar:

* diretórios permitidos;
* comandos permitidos;
* timeout;
* restrição de rede;
* variáveis autorizadas;
* logs;
* hashes.

### Critérios de aceite

* Tentativa de acesso proibido é bloqueada.
* Falhas são registradas.
* O adaptador não recebe segredos desnecessários.

### Dependências

Tarefa 5.2.

---

## Tarefa 5.4 — Implementar primeiro adaptador real

### Objetivo

Provar o fluxo em uma única stack.

### Implementação sugerida

Escolher uma combinação:

```text
TypeScript + Vitest
```

ou:

```text
Python + Pytest
```

Implementar:

* AST;
* tipos;
* imports;
* chamadas;
* comentários;
* test runner;
* complexidade.

### Critérios de aceite

* O fluxo completo funciona em um projeto de exemplo.
* Símbolos e testes são indexados.
* Funções alteradas são detectadas.

### Dependências

Tarefa 5.3.

---

# Fase 6 — Análise estática

## Tarefa 6.1 — Criar modelo de símbolos

### Objetivo

Representar funções, métodos, classes e outros elementos.

### Implementação

Campos mínimos:

```text
stable_id
name
qualified_name
kind
language
file
position
signature
types
visibility
content_hash
```

### Critérios de aceite

* IDs permanecem estáveis em alterações simples.
* Símbolos podem ser atualizados incrementalmente.
* Símbolos removidos são registrados.

### Dependências

Fase 5.

---

## Tarefa 6.2 — Implementar extração de símbolos

### Objetivo

Extrair elementos estruturais da codebase.

### Implementação

Extrair:

* funções;
* métodos;
* classes;
* componentes;
* endpoints;
* handlers;
* construtores.

### Critérios de aceite

* O resultado corresponde ao código analisado.
* Arquivos inválidos geram erro controlado.
* O índice é atualizado.

### Dependências

Tarefa 6.1.

---

## Tarefa 6.3 — Implementar tipos e assinaturas

### Objetivo

Registrar entradas e saídas exatas quando disponíveis.

### Implementação

Capturar:

* parâmetros;
* tipos;
* opcionais;
* generics;
* retorno;
* overload usado;
* tipos não resolvidos.

### Critérios de aceite

* Tipos nunca são inventados.
* Tipos desconhecidos são marcados.
* A origem da informação é registrada.

### Dependências

Tarefa 6.2.

---

## Tarefa 6.4 — Implementar grafo estrutural

### Objetivo

Registrar relações entre símbolos.

### Implementação

Criar relações:

* chama;
* importa;
* herda;
* implementa;
* utiliza;
* testa;
* acessa tabela;
* publica evento;
* consome evento.

### Critérios de aceite

* Relações possuem origem e confiança.
* O grafo pode responder dependentes diretos.
* O grafo pode responder dependentes indiretos.

### Dependências

Tarefa 6.3.

---

## Tarefa 6.5 — Implementar diff de símbolos

### Objetivo

Identificar exatamente o que mudou.

### Implementação

Classificar:

* criado;
* removido;
* alterado;
* movido;
* renomeado;
* assinatura alterada;
* corpo alterado;
* comentário alterado.

### Critérios de aceite

* Alteração apenas de comentário não é classificada como mudança funcional automática.
* Renomeações prováveis são registradas como hipótese.
* Ambiguidades podem ser enviadas a um agente.

### Dependências

Tarefa 6.4.

---

## Tarefa 6.6 — Implementar atualização incremental

### Objetivo

Evitar nova análise completa a cada alteração.

### Implementação

* Reanalisar somente arquivos modificados.
* Atualizar relações afetadas.
* Invalidar caches.
* Atualizar métricas.
* Registrar mudança.

### Critérios de aceite

* Arquivos não alterados não são analisados novamente sem necessidade.
* O índice permanece consistente.
* Existe comando de rebuild completo.

### Dependências

Tarefa 6.5.

---

# Fase 7 — Qualidade estrutural

## Tarefa 7.1 — Medir funções

### Objetivo

Identificar funções difíceis de manter.

### Implementação

Calcular:

* linhas;
* linhas lógicas;
* complexidade ciclomática;
* complexidade cognitiva;
* parâmetros;
* profundidade;
* retornos;
* dependências;
* efeitos colaterais detectáveis.

### Critérios de aceite

* Métricas são reproduzíveis.
* Ferramenta e versão são registradas.
* Limites podem ser configurados.

### Dependências

Fase 6.

---

## Tarefa 7.2 — Medir classes

### Objetivo

Identificar classes excessivamente complexas.

### Implementação

Calcular:

* métodos;
* campos;
* dependências;
* complexidade;
* fan-in;
* fan-out;
* coesão;
* módulos acessados.

### Critérios de aceite

* Classe Deus não é identificada apenas pelo número de linhas.
* O relatório separa métricas de interpretação.

### Dependências

Tarefa 7.1.

---

## Tarefa 7.3 — Medir módulos e arquitetura

### Objetivo

Detectar acoplamento estrutural problemático.

### Implementação

Detectar:

* ciclos;
* centralidade;
* profundidade;
* quantidade de exports;
* acoplamento aferente;
* acoplamento eferente;
* dependências entre domínios.

### Critérios de aceite

* Novos ciclos podem ser bloqueados.
* O sistema diferencia dívida anterior de regressão nova.

### Dependências

Tarefa 7.2.

---

## Tarefa 7.4 — Criar baseline estrutural

### Objetivo

Permitir adoção em codebases legadas.

### Implementação

Registrar estado atual:

* violações;
* métricas;
* dependências;
* ciclos;
* funções longas;
* classes complexas.

### Critérios de aceite

* Dívida existente não bloqueia automaticamente o projeto.
* Piora em código modificado é detectada.
* Novas violações podem ser bloqueadas.

### Dependências

Tarefa 7.3.

---

## Tarefa 7.5 — Criar Code Quality Agent

### Objetivo

Interpretar métricas estruturais.

### Implementação

O agente poderá:

* identificar responsabilidades distintas;
* sugerir divisão de funções;
* sugerir divisão de classes;
* apontar abstração prematura;
* sugerir redução de dependências.

### Critérios de aceite

* O agente não calcula métricas.
* O relatório separa fatos e sugestões.
* Nenhuma refatoração é aplicada automaticamente.

### Dependências

Tarefa 7.4.

---

# Fase 8 — Índice comportamental

## Tarefa 8.1 — Criar modelo de comportamento

### Objetivo

Representar comportamentos protegidos por testes.

### Implementação

Campos:

```text
id
description
origin_test
related_symbols
inputs
outputs
errors
effects
status
source
review_status
```

### Critérios de aceite

* Um comportamento pode existir independentemente do nome atual da função.
* Comportamentos podem ser vinculados a múltiplos símbolos.

### Dependências

Fase 7.

---

## Tarefa 8.2 — Vincular testes e símbolos

### Objetivo

Saber quais testes protegem quais funções.

### Implementação

Utilizar:

* imports;
* chamadas;
* fixtures;
* mocks;
* execução, quando necessário.

### Critérios de aceite

* Relações diretas são identificadas.
* Relações inferidas são marcadas.
* Um teste pode proteger múltiplas funções.

### Dependências

Tarefa 8.1.

---

## Tarefa 8.3 — Registrar mudanças comportamentais

### Objetivo

Preservar histórico sem poluir comentários.

### Implementação

Registrar:

* comportamento anterior;
* comportamento novo;
* testes;
* símbolos;
* bug ou feature;
* responsável;
* origem da análise;
* aprovação.

### Critérios de aceite

* O comentário da função contém apenas comportamento atual.
* O histórico fica no índice e arquivos de histórico.

### Dependências

Tarefa 8.2.

---

# Fase 9 — Runtime de agentes

## Tarefa 9.1 — Criar contrato de agentes

### Objetivo

Padronizar execução dos subagentes.

### Implementação

Definir:

* input schema;
* output schema;
* permissões;
* diretórios;
* ferramentas;
* timeout;
* limite de ciclos;
* preflight;
* postflight.

### Critérios de aceite

* Respostas inválidas são rejeitadas.
* O agente não pode aumentar seu próprio escopo.
* Toda execução possui ID.

### Dependências

Fase 8.

---

## Tarefa 9.2 — Criar registro de origem e confiança

### Objetivo

Distinguir fatos e inferências.

### Implementação

Suportar:

```text
exact
inferred
ai_generated
human_approved
runtime_verified
unknown
```

### Critérios de aceite

* Toda descrição possui origem.
* Toda conclusão semântica registra o agente.
* A interface diferencia comprovado de sugerido.

### Dependências

Tarefa 9.1.

---

## Tarefa 9.3 — Criar Explain Agent

### Objetivo

Explicar funções e classes.

### Implementação

Fornecer ao agente:

* assinatura;
* tipos;
* corpo;
* chamadas;
* testes;
* módulo;
* diff.

Exigir resposta estruturada:

* resumo;
* entradas;
* saída;
* efeitos;
* erros;
* confiança.

### Critérios de aceite

* O agente não inventa tipos.
* Tipos são fornecidos pela análise estática.
* Descrições podem ser aprovadas pelo usuário.

### Dependências

Tarefa 9.2.

---

## Tarefa 9.4 — Criar Create Tests Agent

### Objetivo

Transformar uma descrição de feature em testes.

### Implementação

O agente deverá:

* localizar funções relacionadas;
* criar testes;
* não implementar;
* considerar casos extremos;
* respeitar o perfil do projeto.

### Critérios de aceite

* O código de produção não é alterado.
* O teste falha pelo motivo esperado.
* O teste pode ser apresentado para aprovação.

### Dependências

Tarefa 9.3.

---

## Tarefa 9.5 — Criar Implement Agent

### Objetivo

Implementar testes aprovados.

### Implementação

O agente deverá:

* confirmar teste;
* confirmar estado vermelho;
* preservar testes aprovados;
* fazer mudança mínima;
* executar testes relacionados;
* atualizar funções alteradas.

### Critérios de aceite

* Testes aprovados não são modificados.
* Todas as alterações passam por análise pós-mudança.
* Dependências novas são registradas.

### Dependências

Tarefa 9.4.

---

## Tarefa 9.6 — Criar Fix Agent

### Objetivo

Corrigir bugs com teste de regressão.

### Implementação

Fluxo:

* interpretar bug;
* localizar contexto;
* criar reprodução;
* confirmar falha;
* corrigir;
* executar regressão;
* registrar mudança.

### Critérios de aceite

* Todo bug corrigido possui teste de regressão.
* O bug é vinculado aos símbolos alterados.
* O comportamento anterior e novo são registrados.

### Dependências

Tarefa 9.5.

---

## Tarefa 9.7 — Criar Trade-off Agent

### Objetivo

Comparar alternativas sem modificar código.

### Implementação

Avaliar:

* complexidade;
* custo;
* manutenção;
* desempenho;
* segurança;
* testes;
* estágio do projeto;
* dependências;
* lock-in.

### Critérios de aceite

* O agente opera somente em leitura.
* A recomendação informa condições para reavaliação.

### Dependências

Tarefa 9.6.

---

## Tarefa 9.8 — Criar Review Agent

### Objetivo

Explicar mudanças por comportamento.

### Implementação

Receber:

* diff;
* símbolos;
* métricas;
* testes;
* contratos;
* dependências;
* resultados.

### Critérios de aceite

* Fatos e interpretações aparecem separados.
* O agente não modifica código.
* Pontos sem teste são informados.

### Dependências

Tarefa 9.7.

---

## Tarefa 9.9 — Criar Refactor Agent

### Objetivo

Executar refatorações controladas.

### Implementação

* gerar plano;
* apresentar mapa antes e depois;
* preservar comportamento;
* executar testes;
* registrar símbolos movidos ou divididos.

### Critérios de aceite

* Refatoração não começa sem snapshot.
* Mudanças funcionais são destacadas.
* Testes relacionados são executados.

### Dependências

Tarefa 9.8.

---

## Tarefa 9.10 — Criar Migration Agent

### Objetivo

Apoiar migração de linguagem ou tecnologia.

### Implementação

* exportar comportamentos;
* traduzir testes;
* mapear tipos;
* mapear erros;
* mapear efeitos;
* comparar resultados.

### Critérios de aceite

* Migração não é considerada concluída apenas porque compila.
* Testes equivalentes passam na nova stack.
* Divergências são registradas.

### Dependências

Tarefa 9.9.

---

# Fase 10 — Documentação automática

## Tarefa 10.1 — Gerar descrições de funções

### Objetivo

Criar descrição mínima de cada função relevante.

### Implementação

* Recuperar tipos pela análise estática.
* Solicitar descrição ao Explain Agent.
* Salvar descrição no índice.
* Inserir comentário de acordo com a linguagem.
* Registrar origem.

### Critérios de aceite

* Comentários explicam função, entrada e saída.
* Não incluem histórico.
* Não repetem detalhes óbvios de implementação.
* Comentários são atualizados somente quando necessário.

### Dependências

Fase 9.

---

## Tarefa 10.2 — Implementar `framework test explain`

### Objetivo

Explicar todos os símbolos utilizados no teste.

### Implementação

* Extrair funções e métodos.
* Resolver imports.
* Incluir funções internas, externas e helpers.
* Deduplicar símbolos.
* Recuperar descrição.
* Gerar descrição ausente.
* Inserir um único cabeçalho.

### Critérios de aceite

* Cada símbolo aparece uma vez por arquivo.
* Tipos são apresentados.
* O teste permanece válido.
* O bloco gerado pode ser atualizado.

### Dependências

Tarefa 10.1.

---

## Tarefa 10.3 — Suportar modos de explicação

### Objetivo

Permitir diferentes estratégias.

### Implementação

Suportar:

```text
header
first-use
virtual
```

### Critérios de aceite

* `header` insere cabeçalho.
* `first-use` comenta antes da primeira utilização.
* `virtual` não modifica arquivos.
* A configuração escolhe o padrão.

### Dependências

Tarefa 10.2.

---

## Tarefa 10.4 — Implementar `framework sync`

### Objetivo

Manter índice e documentação sincronizados.

### Implementação

* Atualizar assinaturas.
* Atualizar tipos.
* Atualizar descrições alteradas.
* Adicionar símbolos novos.
* Remover símbolos ausentes.
* Atualizar cabeçalhos.
* Atualizar hashes.

### Critérios de aceite

* O comando é idempotente.
* Não modifica código fora de regiões controladas.
* Blocos manuais são preservados.

### Dependências

Tarefa 10.3.

---

# Fase 11 — Orquestração de testes

## Tarefa 11.1 — Criar modelo unificado de suítes

### Objetivo

Representar diferentes runners.

### Implementação

Categorias:

* unit;
* integration;
* database;
* contract;
* end-to-end;
* regression;
* security;
* benchmark;
* performance;
* load;
* migration;
* inference.

### Critérios de aceite

* Cada suíte possui comando, diretório, timeout e política.
* Resultados são normalizados.

### Dependências

Fase 10.

---

## Tarefa 11.2 — Implementar `framework test`

### Objetivo

Executar as suítes configuradas por um único comando.

### Implementação

Suportar:

```text
framework test
framework test --unit
framework test --integration
framework test --database
framework test --security
framework test --performance
framework test --changed
framework test --all
framework test caminho/do/teste
```

### Critérios de aceite

* Resultados são consolidados.
* Um único exit code é retornado.
* Falhas mostram a suíte de origem.
* O comando funciona em CI.

### Dependências

Tarefa 11.1.

---

## Tarefa 11.3 — Selecionar testes relacionados

### Objetivo

Executar testes impactados por mudanças.

### Implementação

Camadas:

1. testes diretamente vinculados;
2. testes dos dependentes;
3. testes semanticamente sugeridos.

### Critérios de aceite

* Camadas são exibidas separadamente.
* Testes obrigatórios nunca dependem apenas de IA.
* O perfil decide quais camadas executar.

### Dependências

Tarefa 11.2.

---

## Tarefa 11.4 — Implementar aprovação de testes

### Objetivo

Proteger comportamentos validados.

### Implementação

Comando:

```text
framework test approve
```

Registrar:

* hash;
* data;
* teste;
* comportamento;
* perfil;
* aprovador.

### Critérios de aceite

* Alteração do teste invalida a aprovação.
* Agentes não podem alterar teste aprovado silenciosamente.

### Dependências

Tarefa 11.3.

---

# Fase 12 — Fluxos principais

## Tarefa 12.1 — Implementar `framework feature`

### Objetivo

Criar o fluxo de feature orientado por testes.

### Pipeline

* snapshot;
* recuperação de contexto;
* criação de teste;
* explicação;
* execução;
* estado vermelho;
* apresentação;
* aprovação.

### Critérios de aceite

* Nenhuma implementação é feita.
* A falha ocorre pelo motivo esperado.
* O usuário pode revisar o teste.

### Dependências

Fase 11.

---

## Tarefa 12.2 — Implementar `framework implement`

### Objetivo

Implementar comportamento aprovado.

### Pipeline

* validar aprovação;
* validar estado vermelho;
* executar agente;
* analisar diff;
* atualizar símbolos;
* executar análise estrutural;
* selecionar testes;
* executar testes;
* atualizar descrições;
* gerar relatório.

### Critérios de aceite

* Testes aprovados permanecem inalterados.
* Regressões estruturais são detectadas.
* O índice é atualizado.

### Dependências

Tarefa 12.1.

---

## Tarefa 12.3 — Implementar `framework fix`

### Objetivo

Corrigir bugs com rastreabilidade.

### Pipeline

* interpretar bug;
* criar reprodução;
* confirmar falha;
* aprovar reprodução;
* corrigir;
* executar regressões;
* registrar bug;
* atualizar descrições.

### Critérios de aceite

* Bug possui ID.
* Teste de regressão permanece na suíte.
* Funções alteradas ficam vinculadas ao bug.

### Dependências

Tarefa 12.2.

---

## Tarefa 12.4 — Implementar `framework tradeoff`

### Objetivo

Analisar decisões arquiteturais.

### Critérios de aceite

* Não modifica código.
* Considera perfil atual.
* Informa vantagens, desvantagens, recomendação e condição de revisão.

### Dependências

Tarefa 12.3.

---

## Tarefa 12.5 — Implementar `framework review`

### Objetivo

Revisar alterações por comportamento.

### Implementação

Exibir:

* funções criadas;
* funções alteradas;
* assinaturas;
* comportamentos;
* testes;
* dependências;
* banco;
* inferências;
* riscos;
* lacunas.

### Critérios de aceite

* Fatos e análises da IA estão separados.
* Pontos de revisão humana são destacados.

### Dependências

Tarefa 12.4.

---

## Tarefa 12.6 — Implementar `framework impact`

### Objetivo

Analisar impacto estrutural e semântico.

### Implementação

Exibir:

* dependentes diretos;
* indiretos;
* testes;
* endpoints;
* tabelas;
* eventos;
* riscos sugeridos.

### Critérios de aceite

* Impacto estrutural é determinístico.
* Impacto semântico é rotulado como sugestão.

### Dependências

Tarefa 12.5.

---

## Tarefa 12.7 — Implementar `framework inspect`

### Objetivo

Consultar qualquer símbolo ou comportamento.

### Implementação

Exibir:

* descrição;
* assinatura;
* tipos;
* testes;
* bugs;
* dependências;
* mudanças;
* métricas;
* origem das informações.

### Critérios de aceite

* Consulta pode ser feita por ID ou nome.
* Informações não resolvidas são indicadas.

### Dependências

Tarefa 12.6.

---

## Tarefa 12.8 — Implementar `framework refactor`

### Objetivo

Orquestrar refatoração visível.

### Subcomandos

```text
framework refactor inspect
framework refactor plan
framework refactor apply
```

### Critérios de aceite

* Plano é separado da execução.
* Snapshot é obrigatório.
* Comportamentos preservados são verificados.
* Diferenças funcionais são destacadas.

### Dependências

Tarefa 12.7.

---

# Fase 13 — Integrações de inferência

## Tarefa 13.1 — Implementar configuração de inferência

### Objetivo

Configurar provedor sem salvar credenciais.

### Comando

```text
framework inference configure
```

### Implementação

Registrar:

* nome lógico;
* modelo;
* variável da chave;
* variável de URL;
* timeout;
* limites;
* política de testes.

### Critérios de aceite

* Nenhum valor secreto é salvo.
* Configuração pode usar endpoint próprio.
* Variáveis ausentes são informadas.

### Dependências

Fase 12.

---

## Tarefa 13.2 — Implementar `framework inference doctor`

### Objetivo

Validar disponibilidade da integração.

### Implementação

Verificar:

* adaptador;
* agente;
* variável da chave;
* endpoint;
* modelo;
* limite;
* conectividade opcional.

### Critérios de aceite

* Valor da chave nunca é exibido.
* Falhas possuem diagnóstico objetivo.
* O comando pode operar sem realizar inferência.

### Dependências

Tarefa 13.1.

---

## Tarefa 13.3 — Criar normalização de respostas

### Objetivo

Reduzir acoplamento com fornecedores.

### Implementação

Formato interno:

```text
provider
model
text
structuredOutput
toolCalls
usage
finishReason
requestId
latency
```

### Critérios de aceite

* Testes da aplicação podem depender do formato normalizado.
* Campos ausentes são tratados.
* Resposta original pode ser descartada ou sanitizada.

### Dependências

Tarefa 13.2.

---

## Tarefa 13.4 — Criar contratos JSON de inferência

### Objetivo

Validar entrada e saída deterministicamente.

### Implementação

* Schema de entrada.
* Schema de saída.
* Campos obrigatórios.
* Tipos.
* Enumerações.
* Versão.

### Critérios de aceite

* O modelo não valida seu próprio JSON.
* Resposta inválida falha no validador.
* Schemas são versionados.

### Dependências

Tarefa 13.3.

---

## Tarefa 13.5 — Criar testes unitários com mocks

### Objetivo

Testar código sem chamada externa.

### Implementação

Testar:

* prompt;
* request;
* transformação;
* parse;
* fallback;
* timeout;
* erro;
* schema inválido.

### Critérios de aceite

* Testes são rápidos e determinísticos.
* Nenhuma rede é utilizada.

### Dependências

Tarefa 13.4.

---

## Tarefa 13.6 — Criar testes de contrato com fixtures

### Objetivo

Proteger compatibilidade com respostas reais.

### Implementação

* Gravar resposta sanitizada.
* Validar schema.
* Validar normalização.
* Remover dados sensíveis.

### Critérios de aceite

* Fixture não contém segredo.
* Fixture pode ser utilizada offline.
* Mudança de contrato é detectada.

### Dependências

Tarefa 13.5.

---

## Tarefa 13.7 — Implementar teste online mínimo

### Objetivo

Executar pelo menos uma inferência real.

### Comando

```text
framework inference test
```

### Implementação

* Ler chave pelo ambiente.
* Verificar limite.
* Enviar entrada pequena.
* Validar HTTP.
* Validar JSON.
* Validar schema.
* Normalizar.
* Registrar metadados.

### Critérios de aceite

* Uma chamada real é executada quando configurada.
* Ausência de chave produz `not_executed`.
* Nunca produz falso sucesso.
* Nenhum segredo é registrado.

### Dependências

Tarefa 13.6.

---

## Tarefa 13.8 — Criar testes semânticos probabilísticos

### Objetivo

Avaliar qualidade aproximada.

### Implementação

Suportar:

* rubricas;
* exemplos;
* propriedades;
* thresholds;
* avaliador;
* revisão humana.

### Critérios de aceite

* Igualdade exata de texto não é exigida.
* Resultado probabilístico é identificado.
* Teste semântico não substitui schema ou contrato.

### Dependências

Tarefa 13.7.

---

## Tarefa 13.9 — Implementar limites de custo

### Objetivo

Evitar inferências inesperadas.

### Implementação

Configurar:

* máximo de chamadas;
* tokens;
* custo estimado;
* timeout;
* confirmação;
* política de CI.

### Critérios de aceite

* Limites são verificados antes da chamada.
* CI não depende de confirmação interativa.
* Excesso bloqueia a execução.

### Dependências

Tarefa 13.8.

---

# Fase 14 — Prompts e skills

## Tarefa 14.1 — Versionar prompts

### Objetivo

Tratar prompts como código.

### Implementação

Criar:

```text
.framework/prompts/
```

Prompts:

* explain-function;
* create-test;
* implement;
* fix;
* tradeoff;
* review;
* refactor;
* migrate;
* evaluate-inference.

### Critérios de aceite

* Cada prompt possui versão.
* Inputs e outputs possuem schema.
* Mudanças podem disparar testes.

### Dependências

Fase 13.

---

## Tarefa 14.2 — Criar formato canônico de skill

### Objetivo

Manter skills independentes do harness.

### Implementação

Cada skill deve possuir:

```text
SKILL.md
instructions.md
permissions.yml
input.schema.json
output.schema.json
preflight
postflight
references/
```

### Critérios de aceite

* Skills podem ser projetadas para diferentes harnesses.
* Permissões são explícitas.
* Scripts não dependem de raciocínio do agente.

### Dependências

Tarefa 14.1.

---

# Fase 15 — Harness Control Layer

## Tarefa 15.1 — Criar modelo de capacidades

### Objetivo

Descrever o que cada harness suporta.

### Implementação

Capacidades:

* hooks nativos;
* hooks de ferramentas;
* hooks de arquivo;
* hooks de sessão;
* subagentes;
* saída estruturada;
* permissões;
* sandbox;
* MCP;
* execução por terminal.

### Critérios de aceite

* Capacidades são detectadas.
* O sistema não presume suporte por nome do produto.

### Dependências

Fase 14.

---

## Tarefa 15.2 — Implementar `framework harness detect`

### Objetivo

Descobrir harnesses disponíveis.

### Implementação

Verificar:

* executáveis;
* versões;
* configs;
* diretórios;
* comandos;
* recursos disponíveis.

### Critérios de aceite

* Codex, Claude Code e outros harnesses podem ser representados.
* Produto desconhecido ainda pode usar wrapper externo.

### Dependências

Tarefa 15.1.

---

## Tarefa 15.3 — Criar hooks canônicos

### Objetivo

Definir eventos independentes do fornecedor.

### Eventos

```text
SessionStart
SessionStop
TaskReceived
TaskPlanned
BeforeImplementation
AfterImplementation
BeforeToolCall
AfterToolCall
BeforeFileWrite
AfterFileWrite
BeforeCommand
AfterCommand
SubagentStart
SubagentStop
TaskCompleted
TaskFailed
```

### Critérios de aceite

* Payloads possuem schema.
* Hooks podem ser informativos ou bloqueantes.
* Nem todo harness precisa suportar todos os eventos.

### Dependências

Tarefa 15.2.

---

## Tarefa 15.4 — Criar wrapper universal

### Objetivo

Controlar qualquer harness executável por terminal.

### Pipeline

* preflight;
* snapshot;
* execução;
* captura de saída;
* diff;
* AST;
* testes;
* postflight;
* relatório.

### Critérios de aceite

* Funciona sem hooks nativos.
* Exit code do harness é preservado.
* Falhas posteriores podem bloquear conclusão.

### Dependências

Tarefa 15.3.

---

## Tarefa 15.5 — Criar Harness Discovery Agent

### Objetivo

Interpretar capacidades ambíguas.

### Critérios de aceite

* Não modifica a aplicação.
* Produz relatório de capacidades.
* Sugere integração nativa ou wrapper.

### Dependências

Tarefa 15.4.

---

## Tarefa 15.6 — Criar Harness Adapter Agent

### Objetivo

Gerar adaptadores para o harness disponível.

### Critérios de aceite

* Só escreve em diretórios autorizados.
* Gera testes de compatibilidade.
* Não altera políticas centrais.

### Dependências

Tarefa 15.5.

---

## Tarefa 15.7 — Criar Hook Design Agent

### Objetivo

Planejar quais hooks serão usados.

### Critérios de aceite

* Define eventos, modos e pipelines.
* Não instala diretamente.
* Considera impacto de desempenho.

### Dependências

Tarefa 15.6.

---

## Tarefa 15.8 — Criar Hook Installer Agent

### Objetivo

Instalar hooks no harness.

### Implementação

* Backup.
* Conversão do manifesto.
* Instalação.
* Validação.
* Teste.
* Rollback.

### Critérios de aceite

* Configuração existente é preservada.
* Instalação inválida é revertida.
* Hooks são testados.

### Dependências

Tarefa 15.7.

---

## Tarefa 15.9 — Implementar hook `BeforeFileWrite`

### Objetivo

Bloquear alterações proibidas.

### Verificações

* arquivo no escopo;
* permissão;
* teste aprovado;
* arquivo protegido;
* arquivo gerado;
* segredo;
* justificativa da tarefa.

### Critérios de aceite

* Tentativas proibidas são bloqueadas.
* O agente recebe motivo estruturado.

### Dependências

Tarefa 15.8.

---

## Tarefa 15.10 — Implementar hook `AfterFileWrite`

### Objetivo

Analisar alteração incrementalmente.

### Pipeline

* sintaxe;
* format;
* AST;
* símbolos;
* grafo;
* métricas;
* testes relacionados;
* índice temporário.

### Critérios de aceite

* Não executa suíte completa após cada edição.
* Regressões críticas são informadas.

### Dependências

Tarefa 15.9.

---

## Tarefa 15.11 — Criar Dependency Review Agent

### Objetivo

Analisar novas dependências.

### Implementação

Responder:

* é necessária;
* já existe alternativa;
* biblioteca padrão resolve;
* cria duplicação;
* adiciona risco;
* aumenta lock-in.

### Critérios de aceite

* O agente recebe fatos do diff.
* Dependências não utilizadas são bloqueadas deterministicamente.

### Dependências

Tarefa 15.10.

---

## Tarefa 15.12 — Criar Test Expansion Agent

### Objetivo

Ampliar cobertura com base em alterações.

### Implementação

Sugerir:

* unitário;
* integração;
* regressão;
* segurança;
* benchmark;
* inference;
* end-to-end.

### Critérios de aceite

* Testes obrigatórios e sugeridos são separados.
* O agente não remove testes existentes.

### Dependências

Tarefa 15.11.

---

## Tarefa 15.13 — Implementar Completion Gate

### Objetivo

Impedir conclusão sem evidências.

### Verificações

* testes;
* sintaxe;
* tipos;
* contratos;
* estrutura;
* dependências;
* documentação;
* inferência;
* índice;
* testes aprovados.

### Critérios de aceite

* O agente não pode declarar sucesso antes do gate.
* Falhas retornam instruções acionáveis.
* O gate informa o que foi comprovado e inferido.

### Dependências

Tarefa 15.12.

---

## Tarefa 15.14 — Limitar ciclos corretivos

### Objetivo

Evitar loops infinitos.

### Implementação

Configurar:

* máximo de tentativas;
* bloqueio por erro repetido;
* revisão humana após limite.

### Critérios de aceite

* O agente para após o limite.
* O relatório preserva tentativas e erros.

### Dependências

Tarefa 15.13.

---

## Tarefa 15.15 — Proteger políticas e hooks

### Objetivo

Impedir que agentes removam os próprios controles.

### Implementação

Proteger:

```text
.framework/policies/
.framework/hooks/
.framework/gates/
.framework/adapters/harnesses/
```

### Critérios de aceite

* Agente de implementação não pode editar esses diretórios.
* Alterações exigem comando administrativo.
* Hashes detectam manipulação.

### Dependências

Tarefa 15.14.

---

## Tarefa 15.16 — Implementar `framework harness test`

### Objetivo

Testar integração do harness.

### Simulação

* iniciar sessão;
* iniciar subagente;
* criar arquivo temporário;
* disparar hooks;
* simular bloqueio;
* executar cleanup.

### Critérios de aceite

* Todos os eventos suportados são validados.
* Arquivos temporários são removidos.
* Incompatibilidades são relatadas.

### Dependências

Tarefa 15.15.

---

# Fase 16 — Quality Gates

## Tarefa 16.1 — Criar engine de gates

### Objetivo

Executar regras conforme perfil.

### Implementação

Tipos:

* deterministic;
* probabilistic;
* hybrid.

Modos:

* observe;
* warn;
* block;
* repair.

### Critérios de aceite

* Gates possuem ID.
* Resultado possui evidência.
* Gates probabilísticos não parecem fatos.

### Dependências

Fase 15.

---

## Tarefa 16.2 — Criar gates determinísticos

### Gates iniciais

* teste falhando;
* sintaxe inválida;
* tipo inválido;
* teste aprovado alterado;
* função nova sem índice;
* documentação desatualizada;
* dependência circular;
* complexidade crítica;
* dependência não utilizada;
* schema inválido;
* inferência online obrigatória não executada.

### Critérios de aceite

* Todos possuem testes.
* Falhas retornam evidências.

### Dependências

Tarefa 16.1.

---

## Tarefa 16.3 — Criar gates probabilísticos

### Gates iniciais

* mudança funcional suspeita;
* descrição possivelmente desatualizada;
* teste incompleto;
* classe Deus;
* abstração prematura;
* dependência injustificada;
* caso extremo ausente.

### Critérios de aceite

* Resultado registra agente e confiança.
* Perfil padrão usa aviso.
* Bloqueio exige configuração explícita.

### Dependências

Tarefa 16.2.

---

## Tarefa 16.4 — Implementar perfis

### Perfis

```text
experiment
mvp
product
critical
```

### Critérios de aceite

* Cada perfil possui regras documentadas.
* Projeto pode mudar de perfil.
* Baseline é respeitado.

### Dependências

Tarefa 16.3.

---

## Tarefa 16.5 — Implementar `framework check`

### Objetivo

Executar todos os gates aplicáveis.

### Critérios de aceite

* Saída humana e JSON.
* Exit code compatível com CI.
* Gates não executados são indicados.
* Nenhum teste ausente é tratado como sucesso.

### Dependências

Tarefa 16.4.

---

# Fase 17 — Busca e navegação

## Tarefa 17.1 — Implementar busca textual

### Objetivo

Localizar funções, testes e comportamentos.

### Implementação

Buscar por:

* nome;
* assinatura;
* descrição;
* arquivo;
* bug;
* teste.

### Critérios de aceite

* Funciona sem embeddings.
* Resultados mostram origem.

### Dependências

Fase 16.

---

## Tarefa 17.2 — Implementar busca semântica opcional

### Objetivo

Pesquisar por significado.

### Implementação

* gerar embeddings;
* armazenar vetores;
* combinar busca textual, estrutural e vetorial;
* permitir execução local ou externa.

### Critérios de aceite

* Busca funciona sem tornar o banco vetorial obrigatório.
* Resultado semântico é identificado como aproximação.

### Dependências

Tarefa 17.1.

---

# Fase 18 — Migração de linguagem

## Tarefa 18.1 — Exportar pacote comportamental

### Objetivo

Criar pacote independente da implementação.

### Conteúdo

* testes;
* comportamentos;
* tipos;
* contratos;
* fixtures;
* erros;
* efeitos;
* schemas;
* integrações;
* metadados.

### Critérios de aceite

* O pacote não depende do código original para ser compreendido.
* Segredos não são exportados.

### Dependências

Fase 17.

---

## Tarefa 18.2 — Implementar `framework migrate`

### Objetivo

Orquestrar troca de linguagem ou stack.

### Pipeline

* congelar suíte;
* exportar comportamento;
* mapear tipos;
* traduzir testes;
* criar adaptadores novos;
* implementar;
* executar testes;
* comparar;
* registrar divergências.

### Critérios de aceite

* A migração não é concluída sem testes equivalentes.
* Particularidades da nova linguagem são documentadas.
* Divergências precisam de aprovação.

### Dependências

Tarefa 18.1.

---

# Fase 19 — CI/CD

## Tarefa 19.1 — Criar integração básica de CI

### Objetivo

Executar validações em pull requests.

### Pipeline mínimo

* build;
* lint;
* type checking;
* análise estática;
* testes unitários;
* testes de contrato;
* testes relacionados;
* schemas;
* check.

### Critérios de aceite

* Falha bloqueia o pipeline.
* Saídas podem ser anexadas ao pull request.

### Dependências

Fase 18.

---

## Tarefa 19.2 — Criar pipeline online

### Objetivo

Validar integrações externas.

### Implementação

* secrets do CI;
* inferência mínima;
* banco;
* APIs;
* contratos;
* timeout;
* limites.

### Critérios de aceite

* Chaves não aparecem em logs.
* Falta de secret produz estado explícito.
* Política decide bloquear ou pular.

### Dependências

Tarefa 19.1.

---

## Tarefa 19.3 — Criar pipeline nightly

### Objetivo

Executar verificações mais caras.

### Testes

* suíte completa;
* benchmarks;
* segurança;
* semânticos;
* dependências;
* carga reduzida.

### Critérios de aceite

* Resultados históricos são preservados.
* Regressões são comparadas com baseline.

### Dependências

Tarefa 19.2.

---

## Tarefa 19.4 — Criar pipeline de release

### Objetivo

Validar versão final.

### Verificações

* todos os gates;
* testes online;
* contratos;
* segurança;
* benchmark;
* migrations;
* aprovação.

### Critérios de aceite

* Release falha quando gate crítico falha.
* Artefatos são reproduzíveis.

### Dependências

Tarefa 19.3.

---

# Fase 20 — Segurança

## Tarefa 20.1 — Criar gestão segura de credenciais

### Objetivo

Garantir que chaves nunca sejam armazenadas.

### Implementação

Suportar:

* environment;
* secret store;
* CI secrets;
* tokens temporários;
* autenticação oficial do provedor.

### Critérios de aceite

* Scanner confirma ausência de segredos.
* Logs são mascarados.
* Prompts não recebem credenciais.

### Dependências

Fase 19.

---

## Tarefa 20.2 — Criar scanner de segredos

### Objetivo

Bloquear inclusão acidental de chaves.

### Critérios de aceite

* Arquivos modificados são analisados.
* Falsos positivos podem ser justificados.
* Segredo crítico bloqueia imediatamente.

### Dependências

Tarefa 20.1.

---

## Tarefa 20.3 — Validar scripts e hooks

### Objetivo

Impedir execução insegura.

### Implementação

* sanitização de argumentos;
* allowlist de comandos;
* hashes;
* diretórios;
* rede;
* timeout;
* shell escaping.

### Critérios de aceite

* Entradas não são concatenadas diretamente em shell.
* Alteração de hook é detectada.
* Falha crítica é fail-closed.

### Dependências

Tarefa 20.2.

---

# Fase 21 — Observabilidade

## Tarefa 21.1 — Registrar execuções

### Objetivo

Criar trilha auditável.

### Estrutura

```text
.framework/runs/<execution-id>/
```

Conteúdo:

* request;
* harness;
* eventos;
* diff;
* análise estática;
* testes;
* análise de agentes;
* relatório final.

### Critérios de aceite

* Segredos não são armazenados.
* Execuções podem ser consultadas.

### Dependências

Fase 20.

---

## Tarefa 21.2 — Criar relatórios comparativos

### Objetivo

Comparar antes e depois.

### Implementação

Comparar:

* complexidade;
* dependências;
* testes;
* comportamento;
* performance;
* inferências;
* cobertura.

### Critérios de aceite

* Regressões são destacadas.
* Baseline é respeitado.

### Dependências

Tarefa 21.1.

---

# Fase 22 — Experiência de uso

## Tarefa 22.1 — Refinar mensagens do CLI

### Objetivo

Tornar resultados compreensíveis para pessoas que não dominam a linguagem.

### Implementação

* títulos claros;
* separação entre fatos e inferências;
* sugestões acionáveis;
* resumo final;
* códigos de erro;
* exemplos de correção.

### Critérios de aceite

* Nenhuma falha retorna apenas stack trace.
* O usuário sabe o próximo passo.

### Dependências

Fase 21.

---

## Tarefa 22.2 — Criar modo interativo

### Objetivo

Guiar inicialização e aprovação.

### Implementação

Usar perguntas para:

* validar stack;
* escolher perfil;
* selecionar agente;
* aprovar teste;
* aprovar mudança funcional;
* aceitar trade-off.

### Critérios de aceite

* CI pode desativar interação.
* Valores padrão são seguros.

### Dependências

Tarefa 22.1.

---

## Tarefa 22.3 — Criar modo não interativo

### Objetivo

Permitir automação completa.

### Implementação

Flags, arquivos e políticas devem substituir perguntas.

### Critérios de aceite

* Nenhum comando fica bloqueado esperando entrada em CI.
* Ausência de decisão obrigatória produz erro explícito.

### Dependências

Tarefa 22.2.

---

# Fase 23 — Testes do próprio framework

## Tarefa 23.1 — Criar testes unitários do core

### Cobertura

* configuração;
* schemas;
* banco;
* processos;
* logs;
* resultados;
* gates;
* policies.

### Critérios de aceite

* Componentes críticos possuem testes.
* Testes não dependem de rede.

### Dependências

Fase 22.

---

## Tarefa 23.2 — Criar projetos fixture

### Objetivo

Testar stacks reais.

### Fixtures iniciais

* TypeScript com Vitest;
* Python com Pytest;
* projeto com banco;
* projeto com IA;
* monorepo;
* codebase legada.

### Critérios de aceite

* Fixtures são pequenas.
* Cada fixture demonstra cenário específico.

### Dependências

Tarefa 23.1.

---

## Tarefa 23.3 — Criar teste end-to-end de feature

### Fluxo

```text
init
feature
test explain
test
approve
implement
review
check
```

### Critérios de aceite

* Todo o ciclo funciona sem intervenção manual não planejada.
* O índice é atualizado.
* Testes aprovados são protegidos.

### Dependências

Tarefa 23.2.

---

## Tarefa 23.4 — Criar teste end-to-end de bug

### Fluxo

```text
fix
reprodução
correção
regressão
review
check
```

### Critérios de aceite

* Bug é registrado.
* Teste de regressão permanece.
* Descrição atual é atualizada quando necessário.

### Dependências

Tarefa 23.3.

---

## Tarefa 23.5 — Criar teste end-to-end de inferência

### Fluxo

* mock;
* fixture;
* chamada real;
* schema;
* normalização;
* semântico.

### Critérios de aceite

* Cada camada é reportada separadamente.
* Ausência de chave não produz falso sucesso.

### Dependências

Tarefa 23.4.

---

## Tarefa 23.6 — Criar teste end-to-end de harness

### Fluxo

* detectar harness;
* instalar integração;
* executar subagente;
* disparar hooks;
* bloquear ação;
* completion gate;
* cleanup.

### Critérios de aceite

* Wrapper universal funciona.
* Hooks nativos são testados quando disponíveis.

### Dependências

Tarefa 23.5.

---

## Tarefa 23.7 — Criar teste de refatoração

### Objetivo

Validar preservação de comportamento.

### Implementação

* dividir função;
* mover arquivo;
* renomear símbolo;
* atualizar grafo;
* executar testes.

### Critérios de aceite

* Símbolos anteriores e novos são relacionados.
* O comportamento permanece protegido.
* Refatoração é registrada.

### Dependências

Tarefa 23.6.

---

## Tarefa 23.8 — Criar teste de migração

### Objetivo

Validar reimplementação em outra linguagem.

### Implementação

* exportar pacote;
* traduzir testes;
* implementar versão mínima;
* comparar resultados.

### Critérios de aceite

* Entradas equivalentes produzem saídas equivalentes.
* Divergências são registradas.

### Dependências

Tarefa 23.7.

---

# Fase 24 — Documentação do produto

## Tarefa 24.1 — Criar documentação de instalação

### Conteúdo

* requisitos;
* instalação;
* inicialização;
* configuração;
* primeiro projeto.

### Dependências

Fase 23.

---

## Tarefa 24.2 — Criar documentação de comandos

### Conteúdo

Todos os comandos, flags, exemplos e exit codes.

### Dependências

Tarefa 24.1.

---

## Tarefa 24.3 — Criar documentação arquitetural

### Conteúdo

* determinístico versus probabilístico;
* agentes;
* scripts;
* adaptadores;
* índice;
* inferência;
* harness;
* segurança.

### Dependências

Tarefa 24.2.

---

## Tarefa 24.4 — Criar guia de desenvolvimento de adaptadores

### Conteúdo

* contratos;
* schemas;
* testes;
* permissões;
* sandbox;
* exemplos.

### Dependências

Tarefa 24.3.

---

## Tarefa 24.5 — Criar guia de criação de agentes

### Conteúdo

* papel;
* permissões;
* input;
* output;
* preflight;
* postflight;
* limites.

### Dependências

Tarefa 24.4.

---

## Tarefa 24.6 — Criar guia de segurança

### Conteúdo

* credenciais;
* secrets;
* logs;
* hooks;
* scripts;
* APIs;
* inferência;
* CI.

### Dependências

Tarefa 24.5.

---

# Fase 25 — Empacotamento e distribuição

## Tarefa 25.1 — Criar build distribuível

### Objetivo

Permitir instalação simples.

### Implementação

* build;
* binário ou pacote;
* versionamento;
* checksums;
* release notes.

### Critérios de aceite

* Instalação funciona em ambiente limpo.
* `framework --version` funciona.

### Dependências

Fase 24.

---

## Tarefa 25.2 — Criar atualização segura

### Objetivo

Atualizar CLI, schemas e templates.

### Implementação

* detectar versão;
* executar migrations;
* preservar configuração;
* backup;
* rollback.

### Critérios de aceite

* Atualização não perde índice.
* Configurações antigas são migradas.

### Dependências

Tarefa 25.1.

---

# Fase 26 — Validação final

## Tarefa 26.1 — Executar cenário completo em projeto novo

### Fluxo obrigatório

```text
framework init
framework doctor
framework feature
framework test explain
framework test
framework test approve
framework tradeoff
framework implement
framework review
framework check
```

### Critérios de aceite

* Todas as etapas funcionam.
* O usuário entende o comportamento sem ler toda a implementação.

### Dependências

Fase 25.

---

## Tarefa 26.2 — Executar cenário em codebase existente

### Objetivo

Validar adoção progressiva.

### Critérios de aceite

* Stack é detectada.
* Baseline é criado.
* Código legado não bloqueia imediatamente.
* Novas regressões são detectadas.

### Dependências

Tarefa 26.1.

---

## Tarefa 26.3 — Executar cenário com modelo menor

### Objetivo

Provar que o contexto reduz dependência de modelos avançados.

### Implementação

Dar ao agente:

* testes;
* descrições;
* tipos;
* grafo;
* histórico;
* gates.

### Critérios de aceite

* O modelo completa uma feature sem quebrar testes existentes.
* O completion gate detecta falhas quando necessário.

### Dependências

Tarefa 26.2.

---

## Tarefa 26.4 — Executar cenário de inferência externa

### Critérios de aceite

* Mock funciona.
* Fixture funciona.
* Inferência real funciona.
* JSON é validado.
* Resposta é normalizada.
* Teste semântico é separado.
* Nenhuma chave é armazenada.

### Dependências

Tarefa 26.3.

---

## Tarefa 26.5 — Executar cenário com harness controlado

### Critérios de aceite

* Harness é detectado.
* Hooks ou wrapper são instalados.
* Alteração proibida é bloqueada.
* Regressão estrutural é detectada.
* Dependência desnecessária é questionada.
* Completion gate impede conclusão inválida.

### Dependências

Tarefa 26.4.

---

## Tarefa 26.6 — Executar cenário de migração

### Critérios de aceite

* Comportamentos são exportados.
* Testes são recriados.
* Nova implementação passa.
* Diferenças de linguagem são registradas.

### Dependências

Tarefa 26.5.

---

# Definition of Done do produto

O projeto será considerado concluído quando:

* a CLI descobrir ou receber a stack;
* adaptadores específicos puderem ser gerados e testados;
* funções e classes forem extraídas por análise estática;
* tipos e assinaturas forem registrados sem invenção;
* descrições funcionais puderem ser geradas por IA;
* testes puderem receber explicações automáticas;
* testes puderem ser executados por um comando unificado;
* features começarem por testes;
* bugs produzirem testes de regressão;
* alterações forem analisadas por diff e AST;
* funções longas e classes Deus forem detectadas;
* dependências complexas e ciclos forem identificados;
* análises determinísticas e probabilísticas estiverem separadas;
* inferências reais puderem ser testadas com credenciais seguras;
* JSON de APIs externas for validado por schema;
* harnesses puderem ser controlados por hooks ou wrapper;
* subagentes possuírem escopo e permissões;
* completion gates impedirem conclusão sem evidência;
* refatorações forem permitidas, mas nunca invisíveis;
* o índice preservar comportamentos e histórico;
* o framework funcionar com projetos novos e existentes;
* a codebase puder ser reimplementada em outra linguagem com base nos testes e contratos.

---

# Ordem resumida de implementação

```text
Fundação
→ Núcleo da CLI
→ Configuração
→ Banco local
→ Descoberta da stack
→ Contratos de adaptadores
→ Geração de adaptadores
→ Análise estática
→ Métricas estruturais
→ Índice comportamental
→ Runtime de agentes
→ Documentação de funções
→ Explicação de testes
→ Execução unificada
→ Feature
→ Implement
→ Fix
→ Review
→ Inferência
→ Skills
→ Harness Control
→ Quality Gates
→ Busca
→ Migração
→ CI/CD
→ Segurança
→ Observabilidade
→ Testes end-to-end
→ Documentação
→ Distribuição
→ Validação final
```
