import React from 'react';
import { CheckCircle2, CircleDot, ListChecks, Play } from 'lucide-react';
import type { BacklogDocument, BacklogTask } from '../types';

interface BacklogPanelProps {
  backlog: BacklogDocument | null;
  onClaimTask: () => void;
  onCompleteTask: (taskId: string) => void;
  onUpdateChecklist: (taskId: string, phase: 'test' | 'implementation', checked: boolean) => void;
}

export const BacklogPanel: React.FC<BacklogPanelProps> = ({ backlog, onClaimTask, onCompleteTask, onUpdateChecklist }) => {
  if (!backlog) {
    return <div className="runs-empty-sidebar backlog-empty"><ListChecks size={22} /><strong>Backlog ainda não gerado</strong><span>Execute <code>stdd backlog generate</code> para criar as tasks.</span></div>;
  }
  const currentTask = backlog.tasks.find((task) => task.id === backlog.execution.current_task_id);
  const remaining = backlog.tasks.filter((task) => task.status !== 'done');
  const branch = currentTask?.branch;
  const branchOccurrences = currentTask?.branches || (branch ? [branch] : []);
  const parentTask = currentTask?.parent_task_id ? backlog.tasks.find((task) => task.id === currentTask.parent_task_id) : currentTask;
  const contextTaskIds = parentTask ? new Set([parentTask.id, ...(parentTask.child_task_ids || [])]) : new Set<string>();
  const nextSubtask = parentTask?.child_task_ids?.map((id) => backlog.tasks.find((task) => task.id === id)).find((task) => task && task.status !== 'done');
  const testChecklist = (backlog.phase_checklists?.test || []).filter((item) => contextTaskIds.has(item.task_id));
  const implementationChecklist = (backlog.phase_checklists?.implementation || []).filter((item) => contextTaskIds.has(item.task_id));
  const referenceStatus = (task: BacklogTask) => {
    const statuses = (task.traceability || []).map((reference) => reference.status);
    if (statuses.includes('unresolved')) return 'não encontrado';
    if (statuses.includes('not-analyzed')) return 'aguardando análise';
    return 'resolvido';
  };
  return (
    <div className="sidebar-pane backlog-pane">
      <div className="runs-sidebar-heading"><div><span className="eyebrow">Execução por jornada</span><h3>Backlog</h3></div><span className="runs-total-badge">{remaining.length}</span></div>
      <div className="backlog-summary-card"><strong>{remaining.length === 0 ? 'Tudo concluído' : `${remaining.length} task(s) restantes`}</strong><span>{backlog.execution.completed_branches?.length || 0} branch(es) concluída(s)</span></div>
      {currentTask ? (
        <article className="backlog-current-task">
          <div className="backlog-task-heading"><span className="eyebrow">Task atual</span><span className="backlog-status in_progress">em andamento</span></div>
          <h4>{currentTask.label}</h4><code className="backlog-task-id">{currentTask.id}</code><p>{currentTask.description || 'Sem descrição.'}</p>
          {parentTask && parentTask.id !== currentTask.id && <div className="backlog-parent-context"><strong>Task pai</strong><span>{parentTask.label}</span><code>{parentTask.id}</code></div>}
          {nextSubtask && nextSubtask.id !== currentTask.id && <div className="backlog-parent-context"><strong>Próxima subtask</strong><span>{nextSubtask.label}</span><code>{nextSubtask.id}</code></div>}
          {currentTask.child_task_ids && currentTask.child_task_ids.length > 0 && <div className="backlog-parent-context"><strong>Subtasks</strong><span>{currentTask.child_task_ids.length} subtasks no contexto desta task</span></div>}
          <div className="backlog-branch-meta">Branch {branch?.id} · posição {branch?.position}{branch?.terminal ? ' · terminal' : ''}{branchOccurrences.length > 1 ? ` · presente em ${branchOccurrences.length} caminhos` : ''}</div>
          {currentTask.child_backlog_id && <div className="backlog-branch-meta">Backlog interno: {currentTask.child_backlog_id} · {(currentTask.child_task_ids || []).length} task(s)</div>}
          <div className="backlog-detail-section"><strong>Perguntas e respostas</strong>{(currentTask.questions || []).length === 0 ? <span>Nenhuma pergunta.</span> : (currentTask.questions || []).map((question) => <div className="backlog-question" key={question.id}><span>{question.prompt}</span><code>{question.answer === null || question.answer === '' ? 'sem resposta' : String(question.answer)}</code></div>)}</div>
          <div className="backlog-detail-section"><strong>Símbolos associados</strong>{(currentTask.symbols || []).length === 0 ? <span>Nenhum símbolo associado.</span> : (currentTask.symbols || []).map((symbol) => <div className="backlog-symbol" key={symbol}><code>{symbol}</code><small>{referenceStatus(currentTask)}</small></div>)}</div>
          {(currentTask.source_dependencies || []).length > 0 && <div className="backlog-detail-section"><strong>Dependências</strong>{currentTask.source_dependencies?.map((dependency) => <code key={dependency}>{dependency}</code>)}</div>}
          <div className="backlog-detail-section backlog-phase-checklists"><strong>Checklist de teste</strong>{testChecklist.length === 0 ? <span>Nenhum item.</span> : testChecklist.map((item) => <label className="backlog-checklist-item" key={item.id}><input type="checkbox" checked={item.checked} onChange={(event) => onUpdateChecklist(item.task_id, 'test', event.target.checked)} /><span>{item.label}</span></label>)}</div>
          <div className="backlog-detail-section backlog-phase-checklists"><strong>Checklist de implementação</strong>{implementationChecklist.length === 0 ? <span>Nenhum item.</span> : implementationChecklist.map((item) => <label className="backlog-checklist-item" key={item.id}><input type="checkbox" checked={item.checked} onChange={(event) => onUpdateChecklist(item.task_id, 'implementation', event.target.checked)} /><span>{item.label}</span></label>)}</div>
          <button className="sidebar-submit-btn backlog-complete-btn" onClick={() => onCompleteTask(currentTask.id)}><CheckCircle2 size={14} /> Concluir task</button>
        </article>
      ) : remaining.length > 0 ? (
        <div className="runs-empty-sidebar backlog-empty"><CircleDot size={22} /><strong>Próxima task disponível</strong><span>Reserve a próxima etapa da jornada para começar.</span><button className="sidebar-submit-btn" onClick={onClaimTask}><Play size={14} /> Backlog task</button></div>
      ) : (
        <div className="runs-empty-sidebar backlog-empty"><CheckCircle2 size={22} /><strong>Backlog vazio</strong><span>Não há mais tasks pendentes nesta jornada.</span></div>
      )}
      <div className="backlog-task-list"><span className="eyebrow">Tasks</span>{backlog.tasks.map((task) => <div className={`backlog-task-row ${task.status}`} key={task.id}><span>{task.label}</span><small>{task.status === 'done' ? 'concluída' : task.status === 'in_progress' ? 'em andamento' : 'pendente'}</small></div>)}</div>
    </div>
  );
};
