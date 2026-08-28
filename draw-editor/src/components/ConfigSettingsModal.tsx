import React, { useEffect, useState } from 'react';
import { AlertCircle, Check, ChevronDown, HelpCircle, Loader2, Save, Settings, X } from 'lucide-react';

export type LooperConfig = Record<string, any>;

interface Props {
  open: boolean;
  apiOrigin: string;
  onClose: () => void;
}

const setPath = (value: LooperConfig, path: string, next: any): LooperConfig => {
  const result = JSON.parse(JSON.stringify(value));
  const parts = path.split('.');
  let cursor = result;
  parts.slice(0, -1).forEach((part) => { cursor[part] ??= {}; cursor = cursor[part]; });
  cursor[parts.at(-1)!] = next;
  return result;
};

const getPath = (value: LooperConfig, path: string, fallback: any = ''): any =>
  path.split('.').reduce<any>((cursor, part) => cursor?.[part], value) ?? fallback;

const HINTS: Record<string, string> = {
  'backlog.development_mode': 'Exemplo: “Separar L2 antes de L3” termina todas as telas antes de começar regras de negócio. Use “Sequencial” para intercalar as fases.',
  'backlog.task_delivery_scope': 'Exemplo: “Uma tarefa por vez” entrega pequenas mudanças; “Nó completo” agrupa a tela e seus subfluxos relacionados.',
  'backlog.test_loop.mode': 'Exemplo: “Todas as telas antes do backend” mantém o trabalho visual consistente antes de liberar controllers e models.',
  'backlog.implementation_loop.mode': 'Exemplo: “Nó e depois filhos” conclui o comportamento principal e só então entrega seus detalhes técnicos L4.',
  'backlog.test_loop.batch_size': 'Exemplo: 1 é mais controlado; 3 acelera o fluxo entregando três unidades para revisão a cada avanço.',
  'backlog.implementation_loop.batch_size': 'Exemplo: aumente para 2 ou 3 quando o padrão das tarefas estiver estável e você quiser reduzir interrupções.',
  'backlog.l4_group_size': 'Exemplo: 3 entrega três detalhes L4 junto do pai L3. Um número menor deixa a revisão mais focada.',
  'backlog.test_loop_enabled': 'Desative apenas quando quiser implementar diretamente. Com a opção ativa, o Looper exige testes antes de liberar a implementação.',
  'backlog.bootstrap_task': 'Exemplo: mantém uma tarefa inicial para preparar stack, runners, contrato e análise antes das features.',
  'backlog.final_verification_task': 'Exemplo: cria uma última conferência para validar a jornada completa depois que o backlog terminar.',
  'contract.enabled': 'Exemplo: se ativo, uma descrição de teste fora do formato esperado bloqueia a validação e mostra o motivo.',
  'static_analysis.enabled': 'Exemplo: com adapter configurado, o Looper recalcula símbolos, dependências e complexidade após mudanças.',
  'review.enabled': 'Exemplo: ao concluir uma task, executa o agente local de revisão configurado e registra a evidência.'
};

const OPTION_HINTS: Record<string, Record<string, string>> = {
  'backlog.development_mode': { sequential: 'Alterna telas e backend conforme a ordem das tasks.', separated: 'Conclui todas as telas L2 antes de liberar o backend L3.' },
  'backlog.task_delivery_scope': { task: 'Entrega uma unidade pequena por avanço.', node: 'Entrega o nó com seus subfluxos relacionados.' },
  'backlog.test_loop.mode': { task_order: 'Segue a ordem das tarefas do backlog.', node_complete: 'Só avança quando o nó atual estiver completo.', node_then_children: 'Faz o nó principal e depois os filhos.', all_level2_then_level3: 'Prioriza todas as telas antes do backend.' },
  'backlog.implementation_loop.mode': { task_order: 'Segue a ordem das tarefas do backlog.', node_complete: 'Só avança quando o nó atual estiver completo.', node_then_children: 'Faz o nó principal e depois os filhos.', all_level2_then_level3: 'Prioriza todas as telas antes do backend.' }
};

const Hint: React.FC<{ path: string; label: string }> = ({ path, label }) => {
  const hint = HINTS[path];
  if (!hint) return null;
  return <button type="button" className="config-hint" title={hint} aria-label={`Exemplo para ${label}: ${hint}`}><HelpCircle size={14} /></button>;
};

const Section: React.FC<{ title: string; description: string; children: React.ReactNode; defaultOpen?: boolean }> = ({ title, description, children, defaultOpen = true }) => (
  <details className="config-section" open={defaultOpen}>
    <summary><span><strong>{title}</strong><small>{description}</small></span><ChevronDown size={17} /></summary>
    <div className="config-section-content">{children}</div>
  </details>
);

export const ConfigSettingsModal: React.FC<Props> = ({ open, apiOrigin, onClose }) => {
  const [config, setConfig] = useState<LooperConfig>({});
  const [state, setState] = useState<'loading' | 'ready' | 'saving' | 'saved' | 'error'>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setState('loading'); setError('');
    fetch(`${apiOrigin}/__looper/api/config`, { cache: 'no-store' })
      .then(async (response) => { if (!response.ok) throw new Error((await response.json()).error || `HTTP ${response.status}`); return response.json(); })
      .then((value) => { setConfig(value); setState('ready'); })
      .catch((reason) => { setError(reason.message || 'Não foi possível carregar a configuração.'); setState('error'); });
  }, [open, apiOrigin]);

  if (!open) return null;
  const update = (path: string, value: any) => { setConfig((current) => setPath(current, path, value)); setState('ready'); };
  const input = (path: string, label: string, description: string, options?: Array<[string, string]>) => (
    <label className="config-field"><span className="config-label"><span><strong>{label}</strong><small>{description}</small></span><Hint path={path} label={label} /></span>
      {options ? <div className="config-choice-list" role="radiogroup" aria-label={label}>{options.map(([value, text]) => <button key={value} type="button" className={`config-choice ${String(getPath(config, path)) === value ? 'selected' : ''}`} data-tooltip={OPTION_HINTS[path]?.[value] || 'Selecionar esta opção.'} aria-label={`${text}: ${OPTION_HINTS[path]?.[value] || 'Selecionar esta opção.'}`} aria-pressed={String(getPath(config, path)) === value} onClick={() => update(path, value)}><strong>{text}</strong></button>)}</div> : <input type="number" min="0" value={getPath(config, path, 0)} onChange={(event) => update(path, Number(event.target.value))} />}
    </label>
  );
  const toggle = (path: string, label: string, description: string) => (
    <label className="config-toggle"><span className="config-label"><span><strong>{label}</strong><small>{description}</small></span><Hint path={path} label={label} /></span><input type="checkbox" checked={Boolean(getPath(config, path))} onChange={(event) => update(path, event.target.checked)} /><i /></label>
  );
  const save = async () => {
    setState('saving'); setError('');
    try { const response = await fetch(`${apiOrigin}/__looper/api/config`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) }); if (!response.ok) throw new Error((await response.json()).error || `HTTP ${response.status}`); setState('saved'); }
    catch (reason: any) { setError(reason.message || 'Não foi possível salvar.'); setState('error'); }
  };

  return <div className="config-overlay" role="dialog" aria-modal="true" aria-labelledby="config-title">
    <div className="config-modal"><div className="config-accent" />
      <header className="config-header"><div className="config-heading"><span className="config-icon"><Settings size={20} /></span><div><h2 id="config-title">Configurações do Looper</h2><p>Defina como os loops trabalham neste projeto. As alterações são gravadas em <code>.looper/config.yaml</code>.</p></div></div><button className="icon-btn" onClick={onClose} aria-label="Fechar configurações"><X size={18} /></button></header>
      {state === 'loading' ? <div className="config-feedback"><Loader2 className="spin" /> Carregando configuração…</div> : state === 'error' && !Object.keys(config).length ? <div className="config-feedback error"><AlertCircle /> {error}</div> : <div className="config-scroll">
        <div className="config-intro"><strong>Fluxo recomendado</strong><span>Comece pela ordem de desenvolvimento, ajuste os lotes e só depois refine revisão e instruções.</span></div>
        <Section title="Orquestração do backlog" description="A estrutura geral das tarefas e fases.">{toggle('backlog.test_loop_enabled', 'Loop de testes', 'Cria e libera testes antes da implementação.')}{toggle('backlog.bootstrap_task', 'Bootstrap inicial', 'Prepara o projeto antes das tarefas de negócio.')}{toggle('backlog.final_verification_task', 'Verificação final', 'Adiciona uma conferência E2E no fim do backlog.')}{input('backlog.development_mode', 'Ordem das fases', 'Escolha entre concluir telas antes do backend ou intercalar as fases.', [['sequential', 'Sequencial'], ['separated', 'Separar L2 antes de L3']])}{input('backlog.task_delivery_scope', 'Entrega das tarefas', 'Controla o tamanho conceitual de cada entrega.', [['task', 'Uma tarefa por vez'], ['node', 'Nó completo']])}</Section>
        <Section title="Loops de teste e implementação" description="Presets, lotes e contexto entregue aos agentes.">{input('backlog.test_loop.mode', 'Preset do loop de testes', 'Define a ordem usada para liberar testes.', [['task_order', 'Ordem das tarefas'], ['node_complete', 'Concluir nó'], ['node_then_children', 'Nó e depois filhos'], ['all_level2_then_level3', 'Todas as telas antes do backend']])}{input('backlog.test_loop.batch_size', 'Lote de testes', 'Quantidade de unidades por avanço.', undefined)}{input('backlog.implementation_loop.mode', 'Preset do loop de implementação', 'Define a ordem usada para implementar.', [['task_order', 'Ordem das tarefas'], ['node_complete', 'Concluir nó'], ['node_then_children', 'Nó e depois filhos'], ['all_level2_then_level3', 'Todas as telas antes do backend']])}{input('backlog.implementation_loop.batch_size', 'Lote de implementação', 'Quantidade de unidades por avanço.', undefined)}{input('backlog.l4_group_size', 'Grupo L4', 'Quantidade de detalhes técnicos entregues com o pai L3.', undefined)}</Section>
        <Section title="Qualidade e rastreabilidade" description="Gates que protegem a execução e a documentação.">{toggle('contract.enabled', 'Validar contrato', 'Confere se os testes e Draws seguem o contrato do projeto.')}{toggle('static_analysis.enabled', 'Análise estática', 'Calcula símbolos, dependências e indicadores quando há adapter configurado.')}{toggle('review.enabled', 'Revisão automática', 'Executa uma revisão local após uma tarefa concluída.')}</Section>
        <Section title="Instruções dos agentes" description="Orientações persistentes por tipo de loop." defaultOpen={false}><label className="config-field config-textarea"><span>Backend<small>Usada em backend, testes e bootstrap.</small></span><textarea value={getPath(config, 'instructions.backend')} onChange={(event) => update('instructions.backend', event.target.value)} /></label><label className="config-field config-textarea"><span>Frontend<small>Usada nas telas e experiências do usuário.</small></span><textarea value={getPath(config, 'instructions.frontend')} onChange={(event) => update('instructions.frontend', event.target.value)} /></label><label className="config-field config-textarea"><span>Changes<small>Usada nas correções incrementais.</small></span><textarea value={getPath(config, 'instructions.change')} onChange={(event) => update('instructions.change', event.target.value)} /></label></Section>
      </div>}
      <footer className="config-footer">{error && <span className="config-error"><AlertCircle size={15} /> {error}</span>}{state === 'saved' && <span className="config-saved"><Check size={15} /> Salvo no projeto</span>}<button className="icon-btn" onClick={onClose}>Cancelar</button><button className="icon-btn success" onClick={save} disabled={state === 'loading' || state === 'saving'}><Save size={16} /> {state === 'saving' ? 'Salvando…' : 'Salvar configurações'}</button></footer>
    </div></div>;
};
