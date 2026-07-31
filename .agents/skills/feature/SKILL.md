---
name: feature
description: Especifica funcionalidades por testes executáveis no STDD sem alterar código de produção. Usar ao transformar pedidos, desenhos, contratos de API, integrações de IA, regras de banco ou requisitos de segurança e desempenho em cenários verificáveis.
---

# Feature Agent

## Responsabilidade

Transformar intenção em comportamento observável e testes que falhem pelo motivo esperado. Tratar testes como documentação executável. Não implementar código de produção, não enfraquecer testes existentes e não duplicar a especificação em arquivos Markdown intermediários.

## Fontes de verdade

Ler somente o contexto necessário:

- solicitação atual e critérios aceitos pelo usuário;
- `.stdd/config.json` e capacidades realmente configuradas;
- testes, contratos, schemas e fixtures existentes;
- código relacionado, apenas para entender interfaces e efeitos atuais;
- `.stdd/draws/<draw-id>.json` quando a solicitação partir de um desenho;
- `draw_ref` apenas quando o subfluxo fizer parte do escopo.

Não converter Draw em documentação duplicada. O JSON e os testes permanecem fontes diretas.

## Preflight

1. Conferir o estado do Git e preservar alterações do usuário.
2. Localizar testes e símbolos relacionados.
3. Identificar linguagem, framework de teste, banco e integrações externas.
4. Confirmar quais runners estão realmente disponíveis; capacidade não confirmada é `unavailable`.
5. Definir comportamento de sucesso, erros, limites, efeitos colaterais e riscos.
6. Escolher as categorias de teste proporcionais ao risco.

## Contrato de testes

Não limitar a estratégia a testes funcionais. Avaliar explicitamente:

| Categoria | Exigir quando |
| --- | --- |
| Unitário | regra isolável, transformação, validação ou erro local |
| Integração | dois componentes reais precisam colaborar |
| Contrato | API, evento, schema, SDK ou resposta externa possui formato estável |
| Regressão | existe bug ou comportamento anterior que não pode retornar |
| End-to-end | o valor depende de várias etapas do sistema |
| Banco | migrations, constraints, funções, triggers, RLS ou transações importam |
| Performance | latência, throughput, memória ou volume possui objetivo mensurável |
| Segurança | autenticação, autorização, entrada hostil, segredo ou exposição de dados muda |
| Isolamento | tenants, testes paralelos, dados, processos ou integrações não podem vazar estado |
| Pentest | há superfície atacável e ambiente explicitamente autorizado |
| Teste live | uma integração com IA ou serviço externo precisa provar o contrato real |

### Teste live de inteligência artificial

Para código que chama um provedor de IA, planejar camadas separadas:

1. unitário sem rede, com mock do transporte;
2. contrato offline com fixture real sanitizada;
3. teste live opt-in, chamando o provedor real;
4. avaliação semântica probabilística, quando relevante, separada do contrato determinístico.

O teste live deve usar entrada pequena, timeout, limite de chamadas e credencial somente por variável de ambiente. Validar transporte, status, JSON, schema, normalização, campos obrigatórios e limites; não exigir igualdade exata de texto livre. Ausência de credencial ou rede deve produzir `not_executed` com motivo, nunca `passed`. Não registrar prompt privado, token, chave ou resposta sensível.

### Banco de dados e pgTAP

Em PostgreSQL, considerar pgTAP para validar schema, constraints, índices, funções, triggers, permissões e RLS. Executar em banco isolado de teste após migrations e antes do cleanup. Nunca apontar para produção. Se pgTAP ou o banco não estiver disponível, registrar `not_executed` e a pré-condição ausente.

### Testes não funcionais

- Performance: definir baseline, carga, aquecimento, repetições, percentil e limite antes de executar.
- Segurança: testar autorização negativa, validação de entrada, segredos, dependências e falha segura.
- Isolamento: provar ausência de vazamento entre tenants, casos, workers e execuções paralelas.
- Pentest: executar somente em alvo local ou ambiente autorizado, com escopo, intensidade e cleanup definidos.

## Fluxo de especificação

1. Escrever uma matriz curta de comportamento no raciocínio de trabalho: cenário, entrada, resultado, erro e efeito.
2. Reutilizar o padrão de testes da stack; não criar framework paralelo.
3. Criar primeiro os testes de sucesso, erro, limites e falha segura aplicáveis.
4. Usar fakes ou fixtures para serviços externos na suíte determinística.
5. Separar testes caros ou online em suíte identificável.
6. Executar os testes novos e confirmar estado vermelho pelo motivo correto.
7. Executar testes relacionados para distinguir falha nova de baseline preexistente.
8. Não alterar produção para fazer o teste passar.

Usar `stdd test` como alias global para confirmar que todas as suítes configuradas continuam executáveis. Uma feature pode começar pelos testes relacionados, mas não deve ser apresentada como validada globalmente sem essa execução agregada.

## Clareza dos testes

- Nomear cada teste pelo comportamento observável.
- Em Python, usar docstring de exatamente duas linhas curtas: o que é testado e como o cenário é exercitado.
- Em testes longos ou end-to-end, inserir comentários breves de etapa antes de grupos coerentes de ações e asserções.
- Não comentar detalhes óbvios nem documentar cada chamada.
- Não exigir docstrings em funções de produção.

## Evidência e encerramento

Registrar para cada suíte: comando, ambiente, status, duração, exit code e falha relevante. Usar apenas `passed`, `failed`, `blocked` ou `not_executed`. Não tratar teste ausente ou não executado como sucesso.

Ao alterar testes, registrar separadamente:

```bash
stdd log "Especifica comportamento da feature" --test
```

Não combinar esse log com implementação. Informar arquivos de teste criados, comandos executados, resultado vermelho esperado, suítes ainda não executadas e pré-condições externas.
