# Contexto estruturado dos Draws

Filtros: draw=looper-journey-log

## Nível 3 — Implementação da jornada de evidência
Draw: `looper-journey-log` · papel: implementation
Pai: `looper-user-journeys` · nó 5
Resumo: Como looper log registra contagens incrementais

### Nó 1 — Receber descrição e tipo
Aceita descrição curta e tipo implementacao, teste, bug ou refactor.
então[A descrição é acompanhada por contagens incrementais de linhas adicionadas e removidas.] -> Nó 2 — Coletar contagens e snapshot (então mede)
### Código
- `src/looper/cli.py::looper.cli.log_work`
Dependências: looper.core.record_run_entry

### Nó 2 — Coletar contagens e snapshot
Compara o estado atual com o checkpoint, calcula linhas adicionadas/removidas e salva somente as contagens no resumo; o snapshot mantém apenas o estado necessário para a próxima medição.
então[O registro é salvo nos artefatos internos.] -> Nó 3 — Registrar execução (então persiste)
### Código
- `src/looper/core.py::looper.core.get_incremental_diff_stats`
Dependências: looper.core.get_workspace_snapshot

### Nó 3 — Registrar execução
Persiste o registro sem incluir segredos e marca retrabalho quando aplicável.
então[A evidência fica disponível para revisão.] -> Nó 4 — Evidência disponível (então expõe)
### Código
- `src/looper/core.py::looper.core.record_run_entry`
Dependências: looper.runs.update_runs_index

### Nó 4 — Evidência disponível
O usuário pode revisar no painel a soma das linhas adicionadas e removidas por execução e no período selecionado; patches textuais não são persistidos.
### Código
- `src/looper/runs.py::looper.runs.runs_directory`
