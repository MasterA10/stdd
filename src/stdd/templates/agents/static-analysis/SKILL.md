---
name: static-analysis
description: Implementa e conecta adaptadores agnósticos de análise estática ao STDD, produzindo fatos determinísticos sobre símbolos, dependências, complexidade, estrutura e alterações.
---

# Static Analysis Skill

## Rastreabilidade da hierarquia Draw

Os fatos estáticos devem respeitar a árvore criada pelas skills `$draw-system-level-1` a `$draw-system-level-4`: nível 1 fornece contexto de fronteiras, nível 2 fornece a jornada, nível 3 delimita o comportamento em linguagem simples e nível 4 aprofunda os símbolos e testes reais. Todos os níveis podem ter `code_refs` no próprio nó quando houver símbolo comprovado: nível 1 para configuração/infraestrutura, nível 2 para frontend/interface, nível 3 para funções/handlers que executam a tarefa e nível 4 para detalhes internos, SQL, procedures, RPCs, migrations e testes. Não criar ou mover `draw_ref`, `parent_draw_ref`, `parent_node_id` ou `root_draw_ref` automaticamente. O adapter fornece fatos; o agente decide as associações.

Ao produzir fatos para um desenho filho, preservar seu pai e a raiz. Reportar referências `resolved`, `unresolved` e `drift` sem tratar um fluxo órfão como resolvido. Uma folha não implementada não deve receber símbolos ou dependências como se fosse código entregue.

### Qualidade estrutural dos subfluxos de nível 3

Ao analisar os desenhos em `.stdd/draws/`, aplicar uma verificação específica aos documentos com `hierarchy.level: 3`, isto é, aos filhos dos desenhos de jornada de nível 2. Emitir apenas warnings quando o subfluxo tiver menos de quatro nós (`draw.level3_min_nodes`) ou quando qualquer nó tiver `description` ausente, não textual ou com menos de 80 caracteres (`draw.level3_short_description`). O finding deve apontar o arquivo, o ID do nó quando aplicável, o valor observado, o limite e a evidência. Esses achados são informativos e nunca bloqueiam `stdd draw create` ou `stdd test`; não criar nós decorativos nem aprovar lacunas sem evidência.

Para documentos com `hierarchy.level: 2`, `3` ou `4`, emitir `draw.level2_missing_code_ref`, `draw.level3_missing_code_ref` ou `draw.level4_missing_code_ref` como bloqueio para cada nó sem pelo menos um `code_refs` com símbolo válido. Além disso, emitir `draw.empty_node_symbol` como bloqueio quando um nó contiver símbolo ausente, vazio ou genérico (ex: `unnamed`, `(sem nome)`, `placeholder`) e `draw.duplicate_node_symbol` como warning quando o mesmo símbolo for reutilizado mais de 4 vezes no mesmo desenho. O finding deve apontar o arquivo do desenho, os nós afetados, o valor observado, o limite (4) e a evidência. Esses achados aparecem durante `stdd draw create`, mas somente `stdd test` aplica o bloqueio ao exit code.

Esta skill orienta a criação de um adaptador específico para a stack do projeto. O adaptador implementa o contrato do STDD; ele não altera o fluxo geral do framework, não inventa fatos e não substitui os gates determinísticos. Quando houver rastreabilidade de autorização, preservar como dependências os símbolos reais de middleware, policies, guards, handlers ou casos de uso; não inferir que cliente e administrador têm as mesmas permissões.

## Objetivo

Para verificar exclusivamente a rastreabilidade dos Draws, use `stdd draw symbols`. O comando lista os símbolos associados e os nós sem símbolo, sem executar suítes de teste, contrato, backlog ou adapter; a análise estática completa continua integrada ao `stdd test`.

Conectar um analisador local ao comando `stdd test` para que a execução produza, quando houver capacidade disponível:

- símbolos e assinaturas;
- handlers e consumidores de RPC, contratos/IDLs rastreáveis e símbolos de procedure, função, trigger ou view SQL quando a stack os utilizar;
- imports, chamadas e dependências;
- dependentes diretos e indiretos;
- ciclos, fan-in e fan-out;
- complexidade ciclomática;
- linhas, parâmetros, retornos e profundidade de blocos;
- métricas estruturais de arquivos, módulos e classes;
- alterações de símbolos entre estados.
- tecnologias e plataformas detectadas, como Supabase, provedores de banco, frameworks de back-end e serviços externos;
- locais reais onde a lógica pode estar implementada: aplicação, banco, RPC, procedure, função SQL, trigger, view, serviço externo ou contrato remoto;
- regras de negócio e dependências que atravessam a linguagem principal, o banco ou outro back-end.

O agente deve usar a melhor ferramenta da stack, como AST nativo, compiler API ou parser especializado. A skill não presume uma linguagem específica.

## Conexão com o STDD

1. Detecte a linguagem e as ferramentas sem afirmar capacidades não confirmadas.
2. Crie um comando executável no diretório autorizado pelo projeto.
3. Configure o comando em `.stdd/config.json`:

```json
{
  "static_analysis": {
    "enabled": true,
    "adapter_command": ["python", "-m", "project_static_adapter"]
  }
}
```

4. O STDD enviará JSON via stdin ao comando:

```json
{
  "contract_version": "1",
  "execution_id": "id-da-execucao",
  "project_path": "/caminho/do/projeto",
  "changed_files": ["src/example.ext"],
  "mode": "incremental"
}
```

5. O adaptador deve escrever somente o relatório JSON no stdout. Mensagens de diagnóstico devem ir para stderr.
6. O agente deve executar os testes próprios do adaptador antes de habilitá-lo no fluxo principal.

Sem adaptador, o STDD registra `static_analysis.status = "unavailable"`. Não simule uma análise para obter aprovação.

## Relatório obrigatório

O stdout do adaptador deve conter um objeto com estes campos:

```json
{
  "contract_version": "1",
  "status": "passed",
  "capabilities": {
    "symbols": true,
    "dependencies": true,
    "technologies": true,
    "external_logic": true,
    "complexity": true,
    "structural_metrics": true,
    "changes": true
  },
  "symbols": [],
  "dependencies": [],
  "technologies": [],
  "external_logic": [],
  "complexity": [],
  "structural_metrics": [],
  "quality_findings": [],
  "changes": [],
  "warnings": [],
  "errors": []
}
```

Cada item deve indicar, quando aplicável, `file`, `position`, `symbol_id` e `source`. Tipos, relações ou métricas desconhecidas devem ser marcados como `unknown` ou `unresolved`, nunca inferidos como fatos.

## Descoberta de plataforma e localização da regra

A análise não pode presumir que toda regra de negócio está em arquivos da linguagem principal. Antes de associar um nó do Draw a um símbolo, investigar a arquitetura executável completa:

- detectar Supabase por configuração, URLs, dependências, migrations, policies, funções Edge, chamadas ao cliente e referências ao banco; registrar a evidência e distinguir Auth, Database, Storage, Realtime e Edge Functions;
- detectar back-end próprio ou framework por manifests, servidores, rotas, handlers, controllers, workers, jobs e clientes HTTP;
- detectar RPC por contratos, clientes, handlers, endpoints, chamadas remotas e consumidores; ligar contrato, handler e consumidor quando existirem;
- detectar lógica em SQL, procedure, função, trigger, view, policy, migration ou schema, preservando o arquivo de origem e o símbolo qualificado;
- detectar funções externas e serviços remotos por SDKs, URLs, contratos, webhooks, filas e chamadas observáveis, sem tratar apenas o nome de um pacote como prova de execução;
- detectar regras divididas entre aplicação, banco e serviço externo, mantendo cada localização como fato separado e as dependências entre elas como relações observadas.

O relatório deve expor essas descobertas em estruturas determinísticas, por exemplo:

```json
{
  "technologies": [
    {"name": "supabase", "kind": "backend_platform", "components": ["auth", "database"], "evidence": [{"file": "supabase/config.toml", "source": "config"}]}
  ],
  "external_logic": [
    {"kind": "sql_procedure", "qualified_name": "public.create_order", "file": "supabase/migrations/001_orders.sql", "source": "sql_ast"},
    {"kind": "rpc_handler", "qualified_name": "orders.create", "file": "src/orders/rpc.ts", "source": "typescript_ast"}
  ]
}
```

Cada tecnologia ou localização deve conter evidência rastreável (`file`, `source`, posição ou símbolo quando disponível). Não afirmar Supabase, RPC, back-end ou regra externa somente por semelhança textual. Se a capacidade não existir para a stack, usar `unavailable` ou `unresolved` e explicar a limitação.

## Conteúdo determinístico esperado

### Símbolos

Inclua funções, métodos, classes, construtores, endpoints e handlers, com nome, nome qualificado, tipo, assinatura, visibilidade e posição. Quando existirem no projeto, inclua também procedures, funções, triggers, views e policies do banco, funções Edge, handlers/consumidores RPC, contratos/IDLs e serviços externos que tenham implementação ou chamada rastreável. Cada símbolo deve informar `file`, `qualified_name`, `kind` e `source`; para SQL, o arquivo deve ser a migration, schema ou script que contém a definição ou implementação. Classifique `kind` para distinguir `backend_endpoint`, `rpc_handler`, `rpc_consumer`, `sql_procedure`, `sql_function`, `sql_trigger`, `sql_view`, `sql_policy`, `edge_function`, `external_service` e símbolos da aplicação.

### Dependências

Inclua imports, chamadas, herança, implementação, uso de símbolos, dependentes diretos e indiretos, ciclos, fan-in e fan-out. Inclua também relações entre cliente e plataforma Supabase, handler RPC e contrato/cliente, handler e procedure/função SQL, policy e tabela, migration/schema e símbolo SQL, aplicação e serviço externo, quando observadas. Diferencie relação observada de relação apenas sugerida e informe a localização da regra de negócio atravessada.

### Complexidade

Calcule a complexidade ciclomática por função ou método quando a ferramenta permitir. Registre também linhas, parâmetros, retornos, profundidade de blocos, chamadas externas e efeitos colaterais identificáveis.

### Padrões de qualidade

Use estes padrões como default quando o projeto não configurar limites próprios. O adaptador deve sempre retornar o valor observado, o limite aplicado, a unidade, o arquivo e o símbolo afetado.

| Métrica | Normal | Warning | Blocking |
| --- | ---: | ---: | ---: |
| Linhas em função de produção | até 100 | 101–150 | acima de 150 |
| Complexidade ciclomática | até 10 | 11–25 | acima de 25 |
| Parâmetros por função | até 5 | 6–9 | acima de 9 |
| Profundidade máxima de blocos | até 4 | 5–6 | acima de 6 |
| Linhas em teste | até 80 | 81–160 | acima de 160 |
| Asserções em um teste | até 8 | 9–15 | acima de 15 |
| Dependências diretas de um módulo | até 10 | 11–20 | acima de 20 |

Esses limites são sinais de risco, não uma medição de valor humano. Um projeto pode sobrescrevê-los em `.stdd/config.json`, mas o relatório deve registrar os limites efetivamente usados.

Achados obrigatórios em `quality_findings`:

- `long_function` para funções acima do limite de linhas;
- `high_complexity` para complexidade acima do limite;
- `too_many_parameters` para excesso de parâmetros;
- `deep_nesting` para profundidade excessiva;
- `long_test` para testes acima do limite de linhas ou asserções;
- `high_fan_out` para módulos com dependências diretas excessivas;
- `god_class_candidate` para classes que atendam aos critérios abaixo.

Cada achado deve conter `kind`, `severity`, `file`, `symbol_id` quando existir, `value`, `limit` e `evidence`.

### Classe Deus

Não classifique uma classe como Deus apenas por linhas. Primeiro calcule estes sinais determinísticos:

- pelo menos 20 métodos;
- pelo menos 1.000 linhas;
- pelo menos 10 campos ou estado interno relevante;
- pelo menos 15 dependências externas;
- complexidade ciclomática agregada acima de 50;
- acesso a pelo menos 4 domínios ou módulos semanticamente distintos;
- fan-out acima de 20;
- fan-in acima de 25, que indica centralidade, mas não prova classe Deus isoladamente.

Classifique como `god_class_candidate` em nível `warning` quando houver pelo menos 3 sinais, incluindo um sinal de responsabilidade ou dependência. Use `blocking` somente quando houver pelo menos 4 sinais e também um indicador grave: 1.000 linhas, 20 métodos, 15 dependências externas ou complexidade agregada acima de 50.

O relatório deve listar os sinais que justificaram a classificação. A IA poderá interpretar se os sinais representam responsabilidades distintas e sugerir uma divisão, mas não poderá alterar os fatos ou transformar uma hipótese em métrica.

### Testes longos e etapas

Considere um teste longo quando ele tiver mais de 80 linhas, mais de 8 asserções ou mais de 2 etapas externas. Para esses testes, gere `long_test` como `warning` e recomende comentários curtos de etapa, por exemplo:

```python
# Etapa 1: cria o pedido e autentica o usuário.
# Etapa 2: executa o fluxo de pagamento.
# Etapa 3: verifica persistência e notificação.
```

Os comentários explicam a sequência do cenário; não devem substituir as asserções nem descrever detalhes óbvios da implementação.

### Estrutura

Registre tamanho de arquivos, métodos e campos por classe, imports por módulo, módulos centrais, acoplamento, duplicações detectáveis e sinais objetivos de classe Deus. A classificação semântica final pode ser feita por IA, mas os números devem vir do adaptador.

### Alterações

Classifique símbolos criados, removidos, alterados, movidos, assinaturas alteradas, corpos alterados e comentários alterados. Renomeações devem ser hipóteses com evidência, não fatos automáticos.

## Validação e falha segura

- O adaptador deve possuir testes determinísticos para cada capacidade declarada.
- Dado um arquivo de exemplo, a contagem de símbolos deve ser exata.
- Quando a stack possuir Supabase, RPC, back-end externo ou banco, fixtures devem cobrir a detecção da plataforma, o handler/contrato e uma procedure, função, trigger, view ou policy SQL com o arquivo de origem correspondente.
- Dado um diff que altera uma função, somente os símbolos afetados devem ser marcados.
- Dependências e ciclos devem ser reproduzíveis no mesmo fixture.
- A complexidade ciclomática deve ter casos com valor conhecido.
- Funções acima do limite devem gerar `long_function` com severidade e valores antes/depois do limite.
- Testes longos devem gerar `long_test` ou recomendação equivalente para marcar etapas com comentários curtos.
- Saída JSON inválida, schema incompatível ou exit code diferente de zero bloqueia o `stdd test`.
- O adaptador não pode escrever fora do diretório autorizado.
- Não inclua tokens, chaves ou credenciais no relatório, stdout ou stderr.

O relatório factual deve permanecer separado de qualquer explicação ou sugestão produzida por IA.

## Exceções controladas

O projeto pode aceitar um achado específico sem desligar a análise inteira. Configure `static_analysis.exceptions` em `.stdd/config.json`:

```json
{
  "static_analysis": {
    "exceptions": [
      {
        "rule": "long_function",
        "file": "src/services/legacy.py",
        "action": "warning",
        "reason": "Refatoração planejada para o próximo ciclo.",
        "expires": "2027-01-01"
      }
    ]
  }
}
```

Cada exceção deve indicar exatamente uma regra e um alvo (`file`, `symbol_id` ou intervalo `lines`), além de `reason` e `expires`. `warning` mantém o achado visível sem bloquear; `ignore` remove o achado dos indicadores ativos, mas deixa evidência da exceção aplicada. Exceções expiradas bloqueiam a análise até serem revisadas. Não usar curingas implícitos.

Adapters podem reconhecer marcadores inline equivalentes à linguagem (`// stdd:ignore`, `<!-- stdd:ignore -->` ou `/* stdd:ignore */`), sempre exigindo regra, motivo e validade. Exceções não podem ignorar falha de contrato, saída inválida, parser quebrado ou achados de segredo hardcoded.

## Segredos hardcoded e arquivos ignorados

O `stdd test` sempre executa um scanner determinístico interno para procurar credenciais gravadas como literais no código ou em arquivos de configuração. O scanner deve reconhecer atribuições a `PASSWORD`, `PASSWD`, `SECRET`, `API_KEY`, `ACCESS_TOKEN`, `AUTH_TOKEN`, `CLIENT_SECRET` e `PRIVATE_KEY`, inclusive com prefixos como `DATABASE_PASSWORD`, além de tokens conhecidos e cabeçalhos de chaves privadas.

Leituras por ambiente (`os.getenv`, `process.env`, `${TOKEN}`), placeholders (`test`, `example`, `dummy`) e arquivos `.env` não são tratados como segredo hardcoded pelo scanner interno. O valor encontrado nunca pode aparecer no relatório: use `"[REDACTED]"`, informe arquivo, linha, tipo do achado e `severity: "blocking"`. Um achado `kind: "hardcoded_secret"` bloqueia o `stdd test`, mesmo quando não há adaptador externo configurado.

Durante `stdd init`, o framework mantém um `.gitignore` na raiz do projeto e adiciona regras idempotentes para `.env`, `.env.*`, `*.pyc`, `__pycache__/`, ambientes virtuais e `node_modules/`, preservando regras preexistentes. A exceção `!.env.example` permite versionar apenas o modelo sem credenciais. Não crie nem registre arquivos `.env` como evidência.

Além do valor literal hardcoded, compare os valores dos arquivos `.env`, `.env.local` e variantes locais com o conteúdo do código. Se um valor de ambiente aparecer no código, gere `hardcoded_env_value` com severidade `blocking`, identificando somente a chave, arquivo e linha e redigindo o valor. Se uma variável não tiver referência detectável, gere `unreferenced_env_variable` como `warning`; isso não bloqueia sozinho porque variáveis podem ser consumidas por infraestrutura, scripts ou serviços externos.

### Credenciais fictícias em testes

Fixtures de teste podem conter credenciais sintéticas, CEDs, INVs ou tokens de integração que parecem reais para o scanner. Para permitir conscientemente uma ocorrência específica, marque a própria linha da fixture — ou a linha imediatamente anterior — com:

```python
PASSWORD = "ced-ficticia"  # stdd:allow-credential
```

O marcador só funciona em arquivos reconhecidos como teste (`test`, `tests`, `spec`, `specs` ou `fixtures`). A ocorrência continua no relatório como `hardcoded_secret` ou `hardcoded_env_value`, com `severity: "warning"`, `value: "[REDACTED]"` e `exception: "explicit_test_credential_allowlist"`; ela não bloqueia o `stdd test`. O mesmo marcador em código de produção continua `blocking`.

O projeto pode impor a política rígida em `.stdd/config.json`:

```json
{
  "static_analysis": {
    "allow_marked_test_credentials": false
  }
}
```

O padrão é `true` para permitir fixtures explicitamente marcadas, nunca para liberar credenciais silenciosamente. Não colocar valores reais em uma lista de exceções, no relatório ou no log.
