export interface ConfigText {
  label: string;
  description: string;
  hint: string;
  detail?: string;
}

export interface OptionText {
  label: string;
  tooltip: string;
  recommended?: boolean;
}

export interface ConfigPreset {
  id: string;
  label: string;
  icon: string;
  description: string;
  values: Record<string, unknown>;
}

export const CONFIG_TEXTS: Record<string, ConfigText> = {
  'backlog.development_mode': { label: 'Ordem de desenvolvimento', description: 'Define se as telas são criadas antes de toda a lógica ou se telas e lógica se alternam.', hint: 'Na maioria dos projetos, “Telas primeiro” facilita a revisão visual antes de conectar o backend.', detail: 'Em “Telas primeiro”, o Looper conclui telas e navegação antes de iniciar controllers, models e regras de negócio. Em “Intercalado”, cada feature recebe tela e backend em sequência.' },
  'backlog.task_delivery_scope': { label: 'Tamanho de cada entrega', description: 'Controla quanto trabalho é entregue de cada vez.', hint: 'Entregas menores facilitam a revisão; entregas por nó reduzem ciclos quando o padrão já está estável.', detail: '“Uma tarefa por vez” mantém mudanças pequenas e focadas. “Nó completo” agrupa a tela principal e seus subfluxos relacionados.' },
  'backlog.test_loop_enabled': { label: 'Criar testes antes de implementar', description: 'Exige que os testes existam antes de liberar a implementação.', hint: 'Recomendado para projetos novos. Desative se os testes já existem ou se a implementação direta for intencional.' },
  'backlog.bootstrap_task': { label: 'Preparação inicial do projeto', description: 'Cria uma tarefa para configurar stack, runners e análise antes das features.', hint: 'Útil na primeira configuração; em projetos já preparados, pode ser desativada.' },
  'backlog.final_verification_task': { label: 'Verificação final', description: 'Adiciona uma conferência completa ao final do backlog.', hint: 'Funciona como uma última verificação da jornada inteira.' },
  'backlog.test_scope': { label: 'O que será testado', description: 'Escolha quais partes do projeto recebem testes automáticos.', hint: 'Para cobertura completa, use “Telas e backend”. “Somente backend” mantém o foco na regressão da codebase.' },
  'backlog.test_loop.mode': { label: 'Ordem dos testes', description: 'Define a sequência usada para criar e liberar testes.', hint: '“Ordem do backlog” é a opção mais previsível para começar.' },
  'backlog.test_loop.batch_size': { label: 'Testes por lote', description: 'Quantos testes são criados e liberados a cada avanço.', hint: 'O valor 1 oferece mais controle; aumente quando o fluxo estiver estável.' },
  'backlog.implementation_loop.mode': { label: 'Ordem da implementação', description: 'Define a sequência usada para implementar features.', hint: '“Ordem do backlog” mantém a execução alinhada à sequência aprovada.' },
  'backlog.implementation_loop.batch_size': { label: 'Implementações por lote', description: 'Quantas implementações são entregues a cada avanço.', hint: 'O valor 1 é o mais seguro; lotes maiores reduzem interrupções.' },
  'backlog.l4_group_size': { label: 'Detalhes técnicos por entrega', description: 'Quantos detalhes técnicos são entregues junto com cada funcionalidade backend.', hint: 'O padrão 3 equilibra contexto e foco da revisão.' },
  'contract.enabled': { label: 'Validar documentação dos testes', description: 'Confere se os testes seguem o formato e a linguagem esperados.', hint: 'Quando ativo, testes fora do contrato são bloqueados com o motivo.' },
  'static_analysis.enabled': { label: 'Análise de qualidade do código', description: 'Calcula métricas de complexidade, dependências e estrutura.', hint: 'Precisa de um adaptador configurado para produzir resultados.' },
  'review.enabled': { label: 'Revisão automática por agente', description: 'Chama um agente externo para conferir as tasks e registrar lacunas como changes.', hint: 'A revisão registra evidências e usa Codex por padrão.' },
  'review.interval_tasks': { label: 'Revisar a cada quantas tasks', description: 'Define depois de quantas tasks concluídas o agente será chamado.', hint: 'Use 1 para revisar cada task ou um número maior para revisar em lotes.', detail: 'A revisão não cria uma nova task de implementação. O agente é chamado no terminal ou em uma sessão tmux e, quando encontra um problema, registra uma change no Draw correspondente.' },
  'review.execution_mode': { label: 'Forma de chamar o agente', description: 'Escolha como o processo do agente será executado localmente.', hint: 'Terminal direto é o padrão; tmux mantém a revisão em uma sessão separada.' },
  'review.default_agent': { label: 'Agente de revisão', description: 'Escolha qual CLI local fará a revisão das tasks.', hint: 'Agy é o padrão e usa aprovação automática de permissões; Codex continua disponível como alternativa.' },
  'review.agents.agy.model': { label: 'Modelo do Agy', description: 'Identificador do modelo usado pelo Agy na revisão.', hint: 'Use um modelo listado por `agy models`; deixe vazio para usar o padrão do CLI.' },
  'review.agents.codex.model': { label: 'Modelo do Codex', description: 'Identificador do modelo usado pelo Codex na revisão.', hint: 'Use o nome aceito por `codex exec --model`; deixe vazio para usar o padrão do CLI.' },
};

export const OPTION_TEXTS: Record<string, Record<string, OptionText>> = {
  'backlog.development_mode': { sequential: { label: 'Intercalado', tooltip: 'Cada feature recebe tela e backend em sequência.' }, separated: { label: 'Telas primeiro', tooltip: 'Conclui telas e navegação antes das regras de backend.', recommended: true } },
  'backlog.task_delivery_scope': { task: { label: 'Uma tarefa por vez', tooltip: 'Entregas pequenas e focadas.', recommended: true }, node: { label: 'Nó completo', tooltip: 'Agrupa a tela e seus subfluxos relacionados.' } },
  'backlog.test_scope': { l2: { label: 'Somente telas', tooltip: 'Cria testes de interface; a execução Playwright exige opt-in explícito.' }, l3: { label: 'Somente backend', tooltip: 'Testa controllers, models, regras e integrações.', recommended: true }, both: { label: 'Telas e backend', tooltip: 'Cobre as duas camadas conforme as tarefas forem liberadas.' } },
  'backlog.test_loop.mode': { task_order: { label: 'Ordem do backlog', tooltip: 'Segue a sequência definida pelas tarefas.', recommended: true }, node_complete: { label: 'Completar nó', tooltip: 'Só avança quando o nó atual estiver completo.' }, node_then_children: { label: 'Nó e depois detalhes', tooltip: 'Testa o comportamento principal e depois os subfluxos.' }, all_level2_then_level3: { label: 'Todas as telas primeiro', tooltip: 'Cria testes de tela antes dos testes de backend.' } },
  'backlog.implementation_loop.mode': { task_order: { label: 'Ordem do backlog', tooltip: 'Segue a sequência definida pelas tarefas.', recommended: true }, node_complete: { label: 'Completar nó', tooltip: 'Só avança quando o nó atual estiver completo.' }, node_then_children: { label: 'Nó e depois detalhes', tooltip: 'Implementa o comportamento principal e depois os detalhes.' }, all_level2_then_level3: { label: 'Todas as telas primeiro', tooltip: 'Implementa todas as telas antes do backend.' } },
  'review.execution_mode': { terminal: { label: 'Terminal direto', tooltip: 'Executa Codex, Claude ou Agy como processo local.', recommended: true }, tmux: { label: 'Sessão tmux', tooltip: 'Executa o agente em uma sessão tmux e aguarda o resultado.' } },
  'review.default_agent': { agy: { label: 'Agy', tooltip: 'Usa o CLI agy com --dangerously-skip-permissions.', recommended: true }, codex: { label: 'Codex CLI', tooltip: 'Usa codex exec como processo local.' } },
  'review.agents.agy.model': { '': { label: 'Padrão do Agy', tooltip: 'Deixa o Agy escolher o modelo padrão.', recommended: true }, 'gemini-3.7-flash-high': { label: 'Gemini 3.7 Flash High', tooltip: 'Modelo listado pelo agy models.' }, 'gemini-3.7-flash-medium': { label: 'Gemini 3.7 Flash Medium', tooltip: 'Modelo listado pelo agy models.' }, 'gemini-3.7-flash-low': { label: 'Gemini 3.7 Flash Low', tooltip: 'Modelo listado pelo agy models.' }, 'gemini-3.6-flash-high': { label: 'Gemini 3.6 Flash High', tooltip: 'Modelo listado pelo agy models.' }, 'gemini-3.6-flash-medium': { label: 'Gemini 3.6 Flash Medium', tooltip: 'Modelo listado pelo agy models.' }, 'gemini-3.6-flash-low': { label: 'Gemini 3.6 Flash Low', tooltip: 'Modelo listado pelo agy models.' }, 'gemini-3.1-pro-high': { label: 'Gemini 3.1 Pro High', tooltip: 'Modelo listado pelo agy models.' }, 'gemini-3.1-pro-low': { label: 'Gemini 3.1 Pro Low', tooltip: 'Modelo listado pelo agy models.' }, 'claude-sonnet-4-6': { label: 'Claude Sonnet 4.6', tooltip: 'Modelo listado pelo agy models.' }, 'claude-opus-4-6-thinking': { label: 'Claude Opus 4.6 Thinking', tooltip: 'Modelo listado pelo agy models.' }, 'gpt-oss-120b-medium': { label: 'GPT-OSS 120B Medium', tooltip: 'Modelo listado pelo agy models.' } },
  'review.agents.codex.model': { '': { label: 'Padrão do Codex', tooltip: 'Deixa o Codex escolher o modelo padrão.', recommended: true }, 'gpt-5.6-luna': { label: 'gpt-5.6-luna', tooltip: 'Modelo configurado no Codex CLI local.' } },
};

const common = {
  'backlog.test_loop_enabled': true, 'backlog.bootstrap_task': true, 'backlog.final_verification_task': true,
  'backlog.task_delivery_scope': 'task', 'backlog.test_loop.mode': 'task_order', 'backlog.test_loop.batch_size': 1,
  'backlog.implementation_loop.mode': 'task_order', 'backlog.implementation_loop.batch_size': 1, 'backlog.l4_group_size': 3,
  'contract.enabled': true, 'static_analysis.enabled': true, 'review.enabled': true,
};

export const CONFIG_PRESETS: ConfigPreset[] = [
  { id: 'new_project', label: 'Projeto novo completo', icon: '01', description: 'Telas primeiro, testes e backend, bootstrap e revisão.', values: { ...common, 'backlog.development_mode': 'separated', 'backlog.test_scope': 'both' } },
  { id: 'screen_focus', label: 'Foco em telas', icon: '02', description: 'Telas primeiro, com foco na experiência visual.', values: { ...common, 'backlog.development_mode': 'separated', 'backlog.test_scope': 'l2' } },
  { id: 'backend_focus', label: 'Foco em backend', icon: '03', description: 'Telas primeiro, com foco na regressão da codebase.', values: { ...common, 'backlog.development_mode': 'separated', 'backlog.test_scope': 'l3' } },
  { id: 'feature_by_feature', label: 'Feature por feature', icon: '04', description: 'Intercalado, uma feature completa por vez.', values: { ...common, 'backlog.development_mode': 'sequential', 'backlog.test_scope': 'both' } },
  { id: 'fast', label: 'Rápido', icon: '05', description: 'Sem loop de testes, com lotes maiores.', values: { ...common, 'backlog.development_mode': 'sequential', 'backlog.test_loop_enabled': false, 'backlog.bootstrap_task': false, 'backlog.final_verification_task': false, 'backlog.task_delivery_scope': 'node', 'backlog.test_loop.batch_size': 3, 'backlog.implementation_loop.batch_size': 3, 'backlog.l4_group_size': 5, 'contract.enabled': false, 'static_analysis.enabled': false, 'review.enabled': false } },
  { id: 'existing_project', label: 'Projeto existente', icon: '06', description: 'Intercalado, lotes de 2 e sem bootstrap.', values: { ...common, 'backlog.development_mode': 'sequential', 'backlog.bootstrap_task': false, 'backlog.test_scope': 'both', 'backlog.test_loop.batch_size': 2, 'backlog.implementation_loop.batch_size': 2 } },
  { id: 'max_quality', label: 'Máxima qualidade', icon: '07', description: 'Todos os gates, lotes pequenos e nós completos.', values: { ...common, 'backlog.development_mode': 'separated', 'backlog.test_scope': 'both', 'backlog.test_loop.mode': 'node_complete', 'backlog.implementation_loop.mode': 'node_complete', 'backlog.l4_group_size': 2 } },
  { id: 'implement_only', label: 'Só implementar', icon: '08', description: 'Sem loop de testes, mantendo qualidade e revisão.', values: { ...common, 'backlog.development_mode': 'separated', 'backlog.test_loop_enabled': false, 'backlog.test_scope': 'both' } },
];

export const CUSTOM_PRESET: ConfigPreset = { id: 'custom', label: 'Personalizado', icon: '—', description: 'Mantém os valores atuais para ajuste manual.', values: {} };
