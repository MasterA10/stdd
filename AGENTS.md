# Agent Guide — Harness Control Layer

## Missão

Implementar a Harness Control Layer descrita em [`general-plan.md`](general-plan.md), transformando cada item do plano em código testado, evidência reproduzível e uma decisão clara de aprovação ou bloqueio.

O agente pode escolher a implementação, mas não pode concluir uma tarefa sem provar que ela está dentro do escopo, testada, documentada e aprovada pelos gates.

## Fonte de verdade

Antes de trabalhar:

1. Leia este arquivo.
2. Leia [`general-plan.md`](general-plan.md) integralmente.
3. Inspecione o estado atual do repositório, testes, configuração e Git.
4. Escolha a primeira etapa incompleta do plano.

Não invente uma etapa paralela para evitar uma etapa bloqueada. Se uma dependência estiver ausente, registre o bloqueio e implemente o máximo seguro com fakes, testes condicionais ou documentação.

## Regras obrigatórias

- Trabalhe somente na tarefa e nos diretórios autorizados.
- Preserve alterações existentes feitas pelo usuário.
- Não altere testes aprovados para fazer a implementação passar.
- Não modifique este arquivo nem os próprios gates para contornar uma falha.
- Não adicione dependências sem justificar necessidade, alternativas e trade-offs.
- Não use shell concatenado quando uma lista de argumentos for suficiente.
- Nunca registre segredos, tokens, credenciais, prompts privados ou raciocínio interno.
- Todo código novo ou alterado deve ter testes proporcionais ao risco.
- Toda função nova ou alterada deve possuir uma descrição curta, conforme o contrato do projeto.
- Mudanças em `.framework/policies/`, `.framework/hooks/`, `.framework/gates/` e adaptadores protegidos exigem validação adicional.
- Se a capacidade de um harness não for confirmada, trate-a como `detected`, não como disponível.

## Ciclo de trabalho

Para cada item do `general-plan.md`, siga exatamente este ciclo:

### 1. Preparar

- [ ] Identificar a fase, item e critério de aceite.
- [ ] Listar arquivos que serão criados ou alterados.
- [ ] Verificar dependências e pré-condições.
- [ ] Executar o baseline aplicável antes da alteração.
- [ ] Registrar falhas preexistentes, sem corrigi-las silenciosamente.

### 2. Especificar por teste

- [ ] Escrever primeiro testes de sucesso, erro, limites e falha segura.
- [ ] Para integração com harness, usar fake ou diretório temporário quando possível.
- [ ] Marcar testes que exigem executável ou serviço externo.
- [ ] Definir a evidência que provará o critério de aceite.

### 3. Implementar

- [ ] Fazer a menor implementação coerente com o contrato canônico.
- [ ] Preservar compatibilidade com `stdd init` e `stdd test`.
- [ ] Validar entradas antes de executar ações bloqueantes.
- [ ] Manter fatos determinísticos separados de análise probabilística da IA.
- [ ] Produzir mensagens de erro acionáveis.

### 4. Validar

Execute, nesta ordem, os testes mais específicos e depois os mais amplos:

```bash
python3 -m pytest tests/<area-da-mudanca> -q
python3 -m pytest -q
stdd test
```

Se `pytest` ou `stdd` não estiver instalado:

- [ ] Verificar se existe um ambiente virtual ou comando equivalente.
- [ ] Não declarar sucesso por não conseguir executar o teste.
- [ ] Registrar exatamente o comando ausente e o que foi validado alternativamente.

Também execute quando aplicável:

```bash
python3 -m compileall -q src tests
stdd harness detect --json
stdd harness doctor
stdd harness test <harness>
```

### 5. Revisar

- [ ] Conferir diff e arquivos fora do escopo.
- [ ] Conferir documentação curta das funções.
- [ ] Conferir ausência de segredos nas evidências.
- [ ] Conferir que novos arquivos estão incluídos nos testes e no relatório.
- [ ] Atualizar o checkbox correspondente em `general-plan.md` somente após a evidência passar.
- [ ] Não marcar uma fase como concluída se houver teste crítico ausente ou não executado.

## Ordem de implementação

Siga esta sequência, salvo dependência explícita:

1. Modelo canônico: capacidades, eventos, payloads, hooks, schemas e políticas.
2. Contrato comum de adaptadores e fake de testes.
3. Descoberta e comandos da CLI.
4. Wrapper universal com preflight, snapshot, execução, postflight e evidências.
5. Diff, escopo, arquivos protegidos e detecção de segredos.
6. Análise AST, símbolos, grafo e métricas incrementais.
7. Políticas estruturais e revisão de dependências.
8. Seleção e expansão de testes.
9. Hooks de arquivo, comando, ferramenta, sessão e conclusão.
10. Agentes especializados.
11. Primeiro adaptador real, escolhido somente entre harnesses detectados.
12. Completion gate e respostas estruturadas de bloqueio.
13. Segurança, simulação, observabilidade e verificação ponta a ponta.

Não implemente adaptadores fictícios apenas para preencher a lista. Um adaptador real só pode ser considerado compatível depois de passar por detecção, instalação, execução, teste de hooks e coleta de evidências.

## Contratos de comportamento

### Detecção

A detecção deve informar executável, versão, configurações localizadas e capacidades observadas. Ausência ou incompatibilidade deve produzir diagnóstico, não traceback opaco.

### Execução

Toda execução deve ter:

- `execution_id`;
- request sanitizado;
- harness e capacidades;
- snapshot inicial e final;
- stdout, stderr e exit code;
- eventos emitidos;
- diff textual e estrutural;
- testes executados;
- decisão final.

### Bloqueio

Use uma resposta estruturada como:

```json
{
  "status": "blocked",
  "reason": "nome_da_regra",
  "evidence": {},
  "required_action": []
}
```

Inclua valores antes/depois, limite, arquivo ou símbolo afetado e a ação necessária. Não use mensagens vagas como “melhore o código”.

### Falha segura

Em ações críticas, erro interno de validação deve bloquear ou interromper a execução. Nunca transforme uma falha do gate em aprovação silenciosa.

## Permissões por agente

| Agente | Pode escrever | Não pode fazer |
|---|---|---|
| Discovery | relatórios temporários | alterar a aplicação |
| Adapter | `.framework/adapters/harnesses/`, `.framework/generated/harnesses/` | modificar regras de segurança |
| Hook Design | plano estruturado | instalar hooks |
| Hook Installer | arquivos de integração autorizados, com backup | apagar configuração existente |
| Code Quality | relatório de análise | substituir métricas determinísticas |
| Test Expansion | testes autorizados e relatório | remover testes aprovados |
| Dependency Review | relatório e justificativas | adicionar dependências sozinho |
| Implementação | arquivos da feature autorizada | alterar gates, políticas ou suas próprias skills |

## Critérios de conclusão de uma tarefa

Só declare a tarefa concluída quando:

- [ ] o diff estiver dentro do escopo;
- [ ] os testes relacionados passarem;
- [ ] o contrato de documentação passar;
- [ ] a sintaxe estiver válida;
- [ ] não houver regressão estrutural não justificada;
- [ ] dependências novas estiverem justificadas e usadas;
- [ ] testes aprovados não tiverem sido alterados sem autorização;
- [ ] evidências e relatórios tiverem sido gravados sem segredos;
- [ ] o completion gate tiver sido executado;
- [ ] limitações restantes estiverem explicitamente registradas.

Se qualquer item não puder ser verificado, o estado correto é `blocked` ou `failed`, nunca `passed`.

## Formato obrigatório de encerramento

Ao terminar uma etapa, informe:

```text
Etapa:
Status: passed | blocked | failed

Arquivos criados/alterados:
- ...

Testes executados:
- comando: ...
  resultado: ...

Evidências:
- ...

Limitações ou bloqueios:
- ...

Próxima etapa:
- ...
```

Nunca diga apenas “feito”. O encerramento precisa permitir que outra pessoa reproduza a decisão.

## Definição final de pronto

A Harness Control Layer está pronta somente quando o checklist final de `general-plan.md` estiver completo e houver uma execução ponta a ponta demonstrando: detecção, execução, observação, análise incremental, seleção de testes, bloqueio de violações, conclusão aprovada e trilha de evidências reproduzível.
