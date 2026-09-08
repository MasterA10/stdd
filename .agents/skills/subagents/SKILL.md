---
name: subagents
description: Orquestra subagentes locais no Herdr, com escolha de agente e modelo, modo nativo de agentes, retomada de sessões e espera sem polling.
---

# Subagents

Use esta skill quando o agente principal precisar dividir uma tarefa em investigações ou execuções independentes. O agente principal define o contexto, dispara os subagentes, aguarda a barreira e só então avalia os resultados.

## Comandos oficiais

Escolha o agente e o modelo antes de iniciar. Quando o usuário não informar outro modelo, use `gpt-5.6-luna` (Luna Medium) para Codex. Para Gemini, use o CLI `agy` com `--model gemini-3.8-flash --effort low`. Para os demais agentes, mantenha o modelo explicitamente configurado ou remova a opção conforme o contrato local; não troque silenciosamente de provedor.

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
agy -p "{prompt}" --model {model} --effort {reasoning} --dangerously-skip-permissions
agy -p "{prompt}" --conversation {session_id} --model {model} --effort {reasoning} --dangerously-skip-permissions
```

`--effort` aceita `low`, `medium` ou `high`; `--agent NAME` seleciona um agente listado por `agy agents`; `--dangerously-skip-permissions` libera todas as ferramentas e exige autorização explícita. O primeiro resultado JSON contém `conversation_id`, que deve ser preservado como `{session_id}` para a continuação.

Para acompanhar a execução no Terminal, prefira o formato textual padrão e não use `--output-format json`. JSON deve ser usado somente quando outro programa precisar processar eventos e metadados; ele deixa o pane visualmente mais carregado.

Os nomes e flags acima são contratos de CLI, não texto livre. Antes de executar, confirme a versão instalada com `command -v`, `--version` e `--help`; se o contrato local divergir, pare e registre a divergência.

## Orquestração nativa com Herdr

O Herdr é o gerenciador de workspace e terminal padrão para subagentes. Não são necessários scripts intermediários nem barreiras manuais: o Herdr oferece controle de painéis, detecção de ciclo de vida de agentes e sincronização bloqueante nativa.

### 1. Inspecionar o ambiente
Antes de disparar subagentes, confirme o status do Herdr e os agentes em execução:
```bash
herdr status
herdr agent list
```

### 2. Criar painel dedicado (sem roubar foco)
Crie um painel preservando o diretório de trabalho e mantendo o foco do usuário inalterado:
```bash
herdr pane split --current --direction right --cwd "$PWD" --no-focus
```
> O comando retorna um JSON contendo `.result.pane.pane_id` (por exemplo, `"w1:p2"`).

### 3. Iniciar o subagente no modo nativo
Inicie o agente suportado (`agy`, `codex`, `claude` ou `gemini`) no painel criado com um nome único:
```bash
herdr agent start worker1 --kind agy --pane <pane-id>
```
Para passar flags ou parâmetros nativos específicos (como modelo e esforço), adicione-os após `--`:
```bash
herdr agent start worker1 --kind agy --pane <pane-id> -- --model gemini-3.8-flash --effort low
```
O comando aguarda o subagente estar interativo e pronto para receber entrada (`interactive_ready`).

### 4. Submeter a tarefa com espera bloqueante (sem polling)
Envie o prompt com a flag `--wait`:
```bash
herdr agent prompt worker1 "Investigue a falha X e reporte as causas e os arquivos afetados." --wait --timeout 120000
```
O Herdr aguarda nativamente até que o agente atinja o estado `idle`, `done` ou `blocked`, sem necessidade de loops de consulta ou polling.

### 5. Ler o resultado limpo
Obtenha a resposta limpa e formatada do agente:
```bash
herdr agent read worker1 --source recent-unwrapped --lines 150
```

### 6. Continuar a sessão
Para continuar a conversa ou enviar novas instruções no mesmo contexto:
```bash
herdr agent prompt worker1 "Com base nessa análise, elabore o plano de ação." --wait --timeout 120000
```
Para controle de teclas no terminal:
```bash
herdr agent send-keys worker1 ctrl+c
```

### 7. Encerrar e limpar o painel
Ao término da tarefa, encerre o painel descartável:
```bash
herdr pane close <pane-id>
```

Em falha, timeout ou cancelamento, inspecione a saída com `herdr agent read`, feche apenas os painéis concluídos e relate as evidências ao usuário.
