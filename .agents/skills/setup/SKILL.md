---
name: setup
description: Descobre a stack e prepara o STDD para executar testes e análise estática reais do projeto. Usar na inicialização, reconfiguração ou diagnóstico de linguagens, frameworks, bancos, provedores de IA, runners, monorepos e ambientes de teste.
---

# Setup Agent

## Instalação do CLI

Para instalar uma versão publicada no Git e colocar `stdd` no `PATH`, usar `uv`:

```bash
uv tool install stdd --from git+https://github.com/MasterA10/stdd.git@vX.Y.Z
```

Depois inicializar o repositório pelo caminho, sem copiar o pacote para dentro dele:

```bash
stdd init my-project
cd my-project
```

O `init` é idempotente e cria os artefatos do framework em `.stdd/` e as skills em `.agents/skills/`.

As integrações podem ser instaladas explicitamente:

```bash
stdd init . --integration codex
stdd init . --integration claude --integration gemini
stdd init . --all-integrations
```

O Codex usa `.agents/skills`, o Claude usa `.claude/skills` e o Gemini usa `.gemini/skills`. A instalação é local e idempotente; não instala o agente nem dependências da aplicação. O CLI pode ser instalado remotamente com `uv tool install stdd --from git+https://github.com/MasterA10/stdd.git@vX.Y.Z`.

Depois do init, executar `stdd setup`. Essa etapa descobre a linguagem e gera comandos específicos, como `npm test`, `go test ./...`, `cargo test`, `dotnet test`, `mvn test` ou `python -m pytest` somente quando a evidência local indicar essa stack. O núcleo não assume Python para projetos de outras linguagens.

## Responsabilidade

Mapear a codebase e configurar capacidades comprovadas para `stdd test`. Detectar em vez de presumir. Criar adapters e scripts específicos da stack somente quando necessários e testá-los antes da ativação. Não alterar regras de negócio da aplicação.

## Descoberta

Inspecionar, com evidência:

- linguagens e aplicações de um monorepo;
- framework principal e bibliotecas relevantes;
- runners de teste, build, lint e tipagem;
- PostgreSQL ou outros bancos, migrations e ferramentas de teste;
- filas, caches, APIs, storage e serviços externos;
- SDKs e provedores de inteligência artificial;
- agente local e executáveis disponíveis;
- configuração atual em `.stdd/config.json`.

Registrar capacidade como `available` somente após localizar e validar o comando. Usar `unavailable` ou `detected` quando a execução ainda não foi comprovada. Nunca ler ou persistir valores de credenciais; registrar apenas nomes de variáveis.

O setup também constrói e revisa o `.gitignore` da raiz. Deve preservar regras existentes e manter `.env`, `.env.*`, `*.pyc`, `__pycache__/`, `.cache/`, `**/.cache/`, `*.cache`, `.coverage`, `coverage/`, ambientes virtuais e caches de ferramentas. A exceção `!.env.example` é permitida. Não criar arquivos de credencial nem copiar valores de `.env` para relatórios.

## Configuração dos runners

Configurar `.stdd/config.json` com arrays de argumentos, sem shell concatenado:

```json
{
  "test_commands": [
    {"name": "unit", "command": ["python", "-m", "pytest", "tests/unit", "-q"]},
    {"name": "integration", "command": ["python", "-m", "pytest", "tests/integration", "-q"]}
  ]
}
```

Preservar comandos existentes até provar que estão obsoletos. Para suites que exigem serviço, credencial ou autorização, criar um runner seguro que reporte `not_executed` com motivo quando a pré-condição faltar. Não apresentar suíte ausente como aprovada.

### Alias global

Tratar `stdd test` como o alias global canônico. Todas as suítes aplicáveis, existentes e configuradas em `test_commands` devem ser executadas uma vez na mesma chamada. Isso pode incluir unitários, integração, contrato, banco, end-to-end, segurança, performance e teste live quando a superfície e a política justificarem. Não criar ou exigir suíte para cada arquivo: frontend visual normalmente usa revisão humana, e Markdown puramente documental não precisa de teste. Uma falha não interrompe as suítes seguintes: o alias termina todas as execuções e devolve resultado consolidado com status, duração e exit code por suíte.

Cada runner encapsula seu próprio ciclo de vida. Um runner de banco deve criar ou selecionar o banco isolado, aplicar migrations, preparar dados quando necessário, executar os testes e realizar cleanup mesmo após falha. O alias global apenas orquestra esses runners; não deve reproduzir comandos internos nem apontar para produção.

### Perfis e aprovação

Usar o perfil `mvp` para permitir cobertura proporcional à vida útil e ao risco do produto. Configurar por suíte `enabled`, `profiles`, `required` e `requires_approval`. O usuário pode selecionar com `--suite`, remover com `--exclude`, trocar o perfil com `--profile` e liberar ações controladas com `--approve-actions`. Suíte pulada deve aparecer como `not_executed` com motivo.

Antes de instalar pacote ou blocker, baixar ferramenta ou imagem, iniciar ou recriar container, criar banco, aplicar migrations fora de ambiente efêmero, alterar serviço local ou realizar ação cara, solicitar aprovação explícita ao usuário e apresentar comando, objetivo, impacto e alternativa. Não executar primeiro para perguntar depois. Ausência de autorização mantém a capacidade como `not_executed` ou `unavailable`.

Exemplo de suíte controlada:

```json
{"name":"database","command":[".stdd/adapters/tests/run-database"],"profiles":["product","critical"],"requires_approval":true,"required":false}
```

Manter scripts gerados pelo framework dentro de `.stdd/adapters/` ou outro diretório explicitamente autorizado. Todo adapter deve possuir teste determinístico, timeout, comandos conhecidos, stdout estruturado e stderr para diagnóstico.

## Matriz mínima de descoberta de testes

Procurar e classificar quando a superfície existir e o risco justificar:

- unitários;
- integração;
- contrato e fixtures;
- regressão;
- end-to-end;
- banco e migration;
- performance, benchmark e carga;
- segurança;
- isolamento e concorrência;
- pentest;
- teste live de IA ou outro provedor externo.

Adicionar também `revisão visual` para frontend e `revisão documental` para Markdown. Não criar todas as categorias por obrigação. Para frontend, automatizar somente lógica crítica; para renderização, registrar revisão visual humana. Para Markdown simples, registrar `not_applicable` quando não houver comportamento executável. Registrar lacunas relevantes para produção.

## Contrato de inferência e teste live

Ao detectar chamada de inteligência artificial:

1. identificar SDK, endpoint lógico, modelo configurável e variáveis de credencial;
2. configurar testes unitários com mock, sem rede;
3. configurar contrato offline com resposta real sanitizada;
4. configurar teste live opt-in que chama o provedor real;
5. separar avaliação semântica probabilística dos validadores determinísticos.

O teste live deve enviar entrada pequena, usar timeout, limite de chamadas e custo, validar HTTP, JSON, schema e resposta normalizada. Credencial ausente produz `not_executed`. Nunca imprimir chave, token, prompt privado ou payload sensível. Não usar igualdade exata para texto probabilístico.

## PostgreSQL e pgTAP

Quando PostgreSQL estiver presente, detectar pgTAP e `pg_prove`. Configurar banco exclusivo de teste ou container efêmero, aplicar migrations, executar testes de schema, constraints, índices, funções, triggers, roles e RLS, e realizar cleanup. Bloquear URL de produção por padrão. Se pgTAP não estiver instalado, registrar a capacidade como `unavailable` e indicar a instalação necessária; não simular sucesso.

## Testes não funcionais

### Performance

Definir comando reproduzível, dataset, aquecimento, repetições, duração, concorrência, métricas e limites. Evitar benchmark instável no gate rápido; suites caras podem ser separadas para CI ou execução agendada.

### Segurança

Configurar, quando aplicável, scanner de segredos, análise de dependências, validação de entrada, autenticação, autorização e testes de falha segura. Sanitizar toda evidência.

### Isolamento

Validar separação entre tenants, bancos, schemas, filas, caches, processos, arquivos temporários e testes paralelos. Cada teste deve preparar e limpar o próprio estado.

### Pentest

Configurar somente contra alvo local ou ambiente explicitamente autorizado. Definir escopo, intensidade, timeout e cleanup. Nunca inferir permissão para testar produção.

## Análise estática

Detectar a melhor ferramenta da linguagem e conectar um adapter ao contrato `static_analysis` do STDD. Validar símbolos, dependências, complexidade, funções longas e mudanças antes de habilitar o comando. Sem adapter, manter `status = unavailable`.

## Validação do setup

1. Executar cada runner específico em ambiente seguro.
2. Registrar comando, versão, duração, exit code e status.
3. Executar `stdd test` por último.
4. Gravar diagnóstico em `.stdd/test-discovery.md`, sem segredos.
5. Distinguir `passed`, `failed`, `blocked` e `not_executed`.

## Clareza e logs

Testes novos seguem o padrão da stack. Em Python, cada função de teste deve ter docstring de exatamente duas linhas curtas. Testes longos ou end-to-end devem usar comentários breves para separar etapas.

Registrar testes e configuração separadamente quando forem trabalhos distintos:

```bash
stdd log "Configura runners detectados" --impl
stdd log "Adiciona validações da stack" --test
```

Usar `--refactor` para retrabalho ou falta de planejamento prévio. Não combinar WorkTypes por conveniência. Ao concluir, informar capacidades disponíveis, indisponíveis, comandos configurados, evidências e pré-condições externas.
