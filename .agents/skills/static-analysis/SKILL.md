---
name: static-analysis
description: Implementa e conecta adaptadores agnósticos de análise estática ao STDD, produzindo fatos determinísticos sobre símbolos, dependências, complexidade, estrutura e alterações.
---

# Static Analysis Skill

## Rastreabilidade da hierarquia Draw

Os fatos estáticos devem respeitar a árvore criada pelo `$draw-system`: nível 1 fornece contexto de fronteiras, nível 2 fornece a jornada, nível 3 delimita o comportamento técnico e nível 4 pode apontar para símbolos e testes reais. Não criar ou mover `draw_ref`, `parent_draw_ref`, `parent_node_id` ou `root_draw_ref` automaticamente. O adapter fornece fatos; o agente decide as associações.

Ao produzir fatos para um desenho filho, preservar seu pai e a raiz. Reportar referências `resolved`, `unresolved` e `drift` sem tratar um fluxo órfão como resolvido. Uma folha não implementada não deve receber símbolos ou dependências como se fosse código entregue.

Esta skill orienta a criação de um adaptador específico para a stack do projeto. O adaptador implementa o contrato do STDD; ele não altera o fluxo geral do framework, não inventa fatos e não substitui os gates determinísticos.

## Objetivo

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
    "complexity": true,
    "structural_metrics": true,
    "changes": true
  },
  "symbols": [],
  "dependencies": [],
  "complexity": [],
  "structural_metrics": [],
  "quality_findings": [],
  "changes": [],
  "warnings": [],
  "errors": []
}
```

Cada item deve indicar, quando aplicável, `file`, `position`, `symbol_id` e `source`. Tipos, relações ou métricas desconhecidas devem ser marcados como `unknown` ou `unresolved`, nunca inferidos como fatos.

## Conteúdo determinístico esperado

### Símbolos

Inclua funções, métodos, classes, construtores, endpoints e handlers, com nome, nome qualificado, tipo, assinatura, visibilidade e posição. Quando existirem no projeto, inclua também procedures, funções, triggers e views do banco, handlers/consumidores RPC e contratos ou IDLs que tenham implementação rastreável. Cada símbolo deve informar `file`, `qualified_name`, `kind` e `source`; para SQL, o arquivo deve ser a migration, schema ou script que contém a definição ou implementação.

### Dependências

Inclua imports, chamadas, herança, implementação, uso de símbolos, dependentes diretos e indiretos, ciclos, fan-in e fan-out. Inclua também relações entre handler RPC e contrato/cliente, handler e procedure SQL, ou migration/schema e símbolo SQL quando observadas. Diferencie relação observada de relação apenas sugerida.

### Complexidade

Calcule a complexidade ciclomática por função ou método quando a ferramenta permitir. Registre também linhas, parâmetros, retornos, profundidade de blocos, chamadas externas e efeitos colaterais identificáveis.

### Padrões de qualidade

Use estes padrões como default quando o projeto não configurar limites próprios. O adaptador deve sempre retornar o valor observado, o limite aplicado, a unidade, o arquivo e o símbolo afetado.

| Métrica | Normal | Warning | Blocking |
| --- | ---: | ---: | ---: |
| Linhas em função de produção | até 40 | 41–100 | acima de 100 |
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
- Quando a stack possuir RPC ou banco, fixtures devem cobrir o handler/contrato e uma procedure ou função SQL com o arquivo de origem correspondente.
- Dado um diff que altera uma função, somente os símbolos afetados devem ser marcados.
- Dependências e ciclos devem ser reproduzíveis no mesmo fixture.
- A complexidade ciclomática deve ter casos com valor conhecido.
- Funções acima do limite devem gerar `long_function` com severidade e valores antes/depois do limite.
- Testes longos devem gerar `long_test` ou recomendação equivalente para marcar etapas com comentários curtos.
- Saída JSON inválida, schema incompatível ou exit code diferente de zero bloqueia o `stdd test`.
- O adaptador não pode escrever fora do diretório autorizado.
- Não inclua tokens, chaves ou credenciais no relatório, stdout ou stderr.

O relatório factual deve permanecer separado de qualquer explicação ou sugestão produzida por IA.

## Segredos hardcoded e arquivos ignorados

O `stdd test` sempre executa um scanner determinístico interno para procurar credenciais gravadas como literais no código ou em arquivos de configuração. O scanner deve reconhecer atribuições a `PASSWORD`, `PASSWD`, `SECRET`, `API_KEY`, `ACCESS_TOKEN`, `AUTH_TOKEN`, `CLIENT_SECRET` e `PRIVATE_KEY`, inclusive com prefixos como `DATABASE_PASSWORD`, além de tokens conhecidos e cabeçalhos de chaves privadas.

Leituras por ambiente (`os.getenv`, `process.env`, `${TOKEN}`), placeholders (`test`, `example`, `dummy`) e arquivos `.env` não são tratados como segredo hardcoded pelo scanner interno. O valor encontrado nunca pode aparecer no relatório: use `"[REDACTED]"`, informe arquivo, linha, tipo do achado e `severity: "blocking"`. Um achado `kind: "hardcoded_secret"` bloqueia o `stdd test`, mesmo quando não há adaptador externo configurado.

Durante `stdd init`, o framework mantém um `.gitignore` na raiz do projeto e adiciona regras idempotentes para `.env`, `.env.*`, `*.pyc`, `__pycache__/`, ambientes virtuais e `node_modules/`, preservando regras preexistentes. A exceção `!.env.example` permite versionar apenas o modelo sem credenciais. Não crie nem registre arquivos `.env` como evidência.

Além do valor literal hardcoded, compare os valores dos arquivos `.env`, `.env.local` e variantes locais com o conteúdo do código. Se um valor de ambiente aparecer no código, gere `hardcoded_env_value` com severidade `blocking`, identificando somente a chave, arquivo e linha e redigindo o valor. Se uma variável não tiver referência detectável, gere `unreferenced_env_variable` como `warning`; isso não bloqueia sozinho porque variáveis podem ser consumidas por infraestrutura, scripts ou serviços externos.
