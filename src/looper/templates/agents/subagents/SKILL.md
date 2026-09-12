---
name: subagents
description: Orquestra subagentes locais no Herdr, com escolha de agente e modelo, modo nativo de agentes, retomada de sessões e espera sem polling.
---

# Subagents

Use esta skill quando o agente principal precisar dividir uma tarefa em investigações ou execuções independentes. O agente principal define o contexto, dispara os subagentes, aguarda a barreira e só então avalia os resultados.

## Modos de Execução: Headless no Pane vs Interativo

O modo padrão é headless em uma pane visível. Crie a pane com
`herdr pane split` e execute nela o comando direto do agente (`codex exec`,
`agy -p` ou equivalente), sem iniciar a TUI. Quando a resposta final precisar
ser consumida pelo agente principal, prefira `--output-last-message FILE` no
Codex ou um arquivo equivalente e leia somente esse artefato; a saída completa
do processo pode continuar visível na pane para acompanhamento.

Use o modo interativo/TUI somente quando o usuário pedir explicitamente a
interface visual, navegação manual, intervenção por teclado ou uma sessão
interativa persistente. A pane continua obrigatória nos dois modos.

1. **Modo Interativo (Janela interativa / TUI completa, somente se solicitado)**:
   - O subagente roda com a interface visual de terminal que o humano usaria (atalhos, status bar, menu, sessão interativa).
   - Ideal quando o usuário quer acompanhar a TUI completa, navegar visualmente ou intervir/assumir o controle pelo teclado.
   - Fluxo: `herdr pane split` -> `herdr agent start <nome> --kind <kind> --pane <id> -- <flags-yolo>` -> `herdr agent prompt <nome> "<prompt>" --wait`.

2. **Modo Direto / Resposta Limpa (Headless no Pane, padrão)**:
   - Abre uma pane dedicada e executa o comando headless diretamente nela; não use `herdr agent start`, pois esse comando inicia um agente interativo.
   - No Codex, use `codex exec` com a flag autônoma suportada pela versão local e, quando necessário, `--output-last-message FILE` para obter somente a resposta final.
   - No Agy, use `agy -p ... --dangerously-skip-permissions`; preserve o `conversation_id` retornado quando for necessário continuar a sessão.
   - Para prompts longos ou com espaços, prefira alimentar `codex exec -` por stdin com `herdr pane send-text` e finalizar com `herdr pane send-keys <pane-id> ctrl+d`, evitando que o shell divida o prompt em argumentos.
   - Fluxo: `herdr pane split` -> `herdr pane run <pane-id> <comando-headless>` -> enviar o prompt quando necessário -> aguardar a conclusão -> ler o arquivo de resposta final ou `herdr pane read`.

## Comandos oficiais

> **Regra Obrigatória (Modo YOLO)**: Sempre execute os subagentes no modo totalmente autônomo e sem bloqueio de permissão ("modo yolo"):
> - No **Codex**, use `--yolo` quando essa flag existir no contrato local; em `codex exec`, use `--dangerously-bypass-approvals-and-sandbox` quando for a flag equivalente suportada pela versão instalada.
> - No **Agy**, nunca esqueça da flag `--dangerously-skip-permissions`.
> - No **Claude**, use `--dangerously-skip-permissions`.

Escolha o agente e o modelo antes de iniciar. Quando o usuário não informar outro modelo, use `gpt-5.6-luna` (Luna Medium) para Codex. Para Gemini, use o CLI `agy` com `--model gemini-3.8-flash --effort low`. Para os demais agentes, mantenha o modelo explicitamente configurado ou remova a opção conforme o contrato local; não troque silenciosamente de provedor.

Codex, em modo não interativo:

```bash
codex exec --dangerously-bypass-approvals-and-sandbox --model {model} -C {workdir} --output-last-message {file} "{prompt}"
codex exec resume {session_id} --dangerously-bypass-approvals-and-sandbox --model {model} -C {workdir} --output-last-message {file} "{prompt}"
```

Use a flag autônoma equivalente suportada pela versão local para autoaprovação de comandos/escrita, `--output-last-message FILE` para a resposta final e `--json` somente quando outro programa precisar processar eventos JSONL. Para executar em uma pane sem abrir a TUI, use `herdr pane run <pane-id> codex exec ...`; para prompts longos, use `codex exec -` e forneça o texto por stdin. Reasoning é configurado pelo perfil/opções aceitos pela versão local do Codex; valide com `codex exec --help` antes de adicionar uma flag específica.

Claude Code, em modo print:

```bash
claude -p --model {model} --dangerously-skip-permissions --output-format json "{prompt}"
claude -p --resume {session_id} --model {model} --dangerously-skip-permissions --output-format json "{prompt}"
```

Use `--max-turns N`, `--permission-mode plan|acceptEdits|bypassPermissions` ou `--dangerously-skip-permissions` para não travar em solicitações de permissão. Claude não possui uma flag universal chamada `reasoning`; não invente `--effort` para ele. Ajustes de esforço dependem do modelo/versão e devem ser confirmados em `claude --help`.

Agy/Antigravity, em modo headless:

```bash
agy -p "{prompt}" --model {model} --effort {reasoning} --dangerously-skip-permissions
agy -p "{prompt}" --conversation {session_id} --model {model} --effort {reasoning} --dangerously-skip-permissions
```

`--effort` aceita `low`, `medium` ou `high`; `--agent NAME` seleciona um agente listado por `agy agents`; `--dangerously-skip-permissions` libera todas as ferramentas automaticamente. O primeiro resultado JSON contém `conversation_id`, que deve ser preservado como `{session_id}` para a continuação.

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

### 3. Executar o subagente headless na pane (padrão)

Execute o processo diretamente na pane criada. Exemplo Codex:

```bash
herdr pane run <pane-id> codex exec --dangerously-bypass-approvals-and-sandbox --model gpt-5.6-luna -C "$PWD" --color never --output-last-message /tmp/<nome>.txt -
herdr pane send-text <pane-id> "<prompt>"
herdr pane send-keys <pane-id> ctrl+d
```

Leia `/tmp/<nome>.txt` para obter somente a resposta final. Não use
`herdr agent start` nem `herdr agent prompt` neste caminho, pois eles operam
uma sessão interativa e podem abrir a TUI.

Para Agy, execute `agy -p "<prompt>" --model <model> --effort <reasoning>
--dangerously-skip-permissions` diretamente com `herdr pane run`, preservando
o `conversation_id` quando a sessão precisar continuar.

### 4. Iniciar o subagente no modo interativo (somente se solicitado)

Inicie o agente suportado (`agy`, `codex`, `claude` ou `gemini`) no painel criado com um nome único somente após pedido explícito de TUI ou intervenção manual. **Sempre passe as flags do modo YOLO após `--`**:
- Para **Agy**: inclua `--dangerously-skip-permissions`
- Para **Codex**: inclua a flag autônoma suportada pela versão instalada, normalmente `--yolo` ou `--dangerously-bypass-approvals-and-sandbox`.

```bash
# Exemplo Agy com modo YOLO e modelo:
herdr agent start worker1 --kind agy --pane <pane-id> -- --dangerously-skip-permissions --model gemini-3.8-flash --effort low

# Exemplo Codex com modo YOLO:
herdr agent start worker1 --kind codex --pane <pane-id> -- --dangerously-bypass-approvals-and-sandbox --model gpt-5.6-luna
```
O comando aguarda o subagente estar interativo e pronto para receber entrada (`interactive_ready`).

### 5. Submeter a tarefa interativa com espera bloqueante (sem polling)
Envie o prompt com a flag `--wait`:
```bash
herdr agent prompt worker1 "Investigue a falha X e reporte as causas e os arquivos afetados." --wait --timeout 120000
```
O Herdr aguarda nativamente até que o agente atinja o estado `idle`, `done` ou `blocked`, sem necessidade de loops de consulta ou polling.

### 6. Ler o resultado limpo
Obtenha a resposta limpa e formatada do agente:
```bash
herdr agent read worker1 --source recent-unwrapped --lines 150
```

### 7. Continuar a sessão
Para continuar a conversa ou enviar novas instruções no mesmo contexto:
```bash
herdr agent prompt worker1 "Com base nessa análise, elabore o plano de ação." --wait --timeout 120000
```
Para controle de teclas no terminal:
```bash
herdr agent send-keys worker1 ctrl+c
```

### 8. Encerrar e limpar o painel
Ao término da tarefa, encerre o painel descartável:
```bash
herdr pane close <pane-id>
```

Em falha, timeout ou cancelamento, inspecione a saída com `herdr agent read`, feche apenas os painéis concluídos e relate as evidências ao usuário.
