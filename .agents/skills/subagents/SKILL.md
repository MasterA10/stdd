---
name: subagents
description: Orquestra subagentes locais em sessões tmux, com execução paralela, escolha explícita de agente e modelo, retomada de sessões e espera por barreira sem polling.
---

# Subagents

Use esta skill quando o agente principal precisar dividir uma tarefa em investigações ou execuções independentes. O agente principal define o contexto, dispara os subagentes, aguarda a barreira e só então avalia os resultados.

## Comandos oficiais

Escolha o agente e o modelo antes de iniciar. Se o usuário não informar um modelo, o agente principal deve preencher `{model}` com o modelo usado na sessão atual; não invente um modelo nem troque silenciosamente de provedor.

Codex, em modo não interativo:

```bash
codex exec --model {model} -C {workdir} --json "{prompt}"
codex exec resume {session_id} --model {model} -C {workdir} --json "{prompt}"
```

Use `--json` para eventos JSONL, `--output-last-message FILE` para a resposta final, `--sandbox read-only|workspace-write|danger-full-access` conforme a autorização e `--full-auto` somente em ambiente confiável. Reasoning é configurado pelo perfil/opções aceitos pela versão local do Codex; valide com `codex exec --help` antes de adicionar uma flag específica.

Claude Code, em modo print:

```bash
claude -p --model {model} --output-format json "{prompt}"
claude -p --resume {session_id} --model {model} --output-format json "{prompt}"
```

Use `--max-turns N`, `--permission-mode plan|acceptEdits|bypassPermissions` ou `--dangerously-skip-permissions` somente quando o escopo autorizar. Claude não possui uma flag universal chamada `reasoning`; não invente `--effort` para ele. Ajustes de esforço dependem do modelo/versão e devem ser confirmados em `claude --help`.

Agy/Antigravity, em modo headless:

```bash
agy -p "{prompt}" --model {model} --effort {reasoning}
agy -p "{prompt}" --conversation {session_id} --model {model} --effort {reasoning}
```

`--effort` aceita `low`, `medium` ou `high`; `--agent NAME` seleciona um agente listado por `agy agents`; `--dangerously-skip-permissions` libera todas as ferramentas e exige autorização explícita. O primeiro resultado JSON contém `conversation_id`, que deve ser preservado como `{session_id}` para a continuação.

Para acompanhar a execução no Terminal, prefira o formato textual padrão e não use `--output-format json`. JSON deve ser usado somente quando outro programa precisar processar eventos e metadados; ele deixa o pane visualmente mais carregado.

Os nomes e flags acima são contratos de CLI, não texto livre. Antes de executar, confirme a versão instalada com `command -v`, `--version` e `--help`; se o contrato local divergir, pare e registre a divergência.

## Orquestração

- Confirme a autorização do usuário, o escopo de cada tarefa e os limites de escrita.
- Descubra os CLIs locais com `scripts/orchestrate_subagents.py discover`. A descoberta informa disponibilidade e versão, mas não escolhe agente ou modelo.
- Use um manifesto JSON com tarefas de ID único, prompt, comando, modelo, reasoning, diretório e, para retomadas, `session_id`.
- Inicie os aguardadores antes dos agentes. Execute todas as tarefas na mesma sessão tmux, com um pane por tarefa: dois agentes ficam em dois painéis equilibrados, três em três painéis e assim sucessivamente. O helper abre um Terminal dedicado e anexa essa sessão; use `--headless` somente em CI ou ambiente sem interface gráfica.
- Comunique a conclusão por `tmux wait-for`; o helper oferece FIFO bloqueante como fallback.
- O agente principal espera bloqueado pela barreira. Não use `tmux has-session`, `sleep`, loops de consulta ou leitura periódica de logs.
- Depois que todos terminarem, leia stdout/stderr, códigos de saída e artefatos. Término do processo não significa aprovação.
- Para continuar uma sessão, preserve o mesmo `session_id`, troque o comando pelo comando de retomada e envie a nova instrução. Não crie uma sessão nova para a etapa seguinte.
- Reutilize o mesmo pane para a continuação: o processo anterior termina, mas a sessão tmux e o shell do pane permanecem abertos. Use:

```bash
python scripts/orchestrate_subagents.py continue --state results.json --task-id planner --command 'codex exec resume SESSION_ID --model MODEL "agora implemente o plano"'
```
- Em falha, timeout ou cancelamento, preserve os resultados recebidos, encerre apenas as sessões necessárias e informe a limitação.

```bash
python scripts/orchestrate_subagents.py discover
python scripts/orchestrate_subagents.py run --manifest subagents.json --output results.json
python scripts/orchestrate_subagents.py run --manifest subagents.json --output results.json --headless  # somente CI
```

O helper não escolhe modelos nem presume sintaxe específica: os comandos do manifesto usam `{prompt}`, `{model}`, `{reasoning}`, `{workdir}` e `{session_id}`. Nunca coloque segredos em prompts, manifestos ou resultados versionados.

O retorno do helper é sempre normalizado por tarefa em JSON com `id`, `status`, `response`, `session_id`, `usage` e `error`. A saída bruta de stdout/stderr é temporária e não é devolvida ao agente principal; o pane mostra somente `response` depois da conclusão.
