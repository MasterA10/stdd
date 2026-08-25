import React, { useState } from 'react';
import { CheckCircle2, ChevronDown, CircleDot, ListChecks, Play, RefreshCw } from 'lucide-react';
import type { BacklogDocument, BacklogTask } from '../types';
import { deliveryScopeFor, parentTaskFor, pendingTestTasks, phaseStatusLabel, taskImplementationStatus, taskTestStatus, testScopeFor } from '../backlog-status';

interface BacklogPanelProps {
  backlog: BacklogDocument | null;
  onClaimTask: () => void;
  onClaimTest: () => void;
  onRefresh: () => void;
  onCompleteTask: (taskId: string) => void;
  onUpdateChecklist: (taskId: string, phase: 'test' | 'implementation', checked: boolean) => void;
}

export const BacklogPanel: React.FC<BacklogPanelProps> = ({ backlog, onClaimTask, onClaimTest, onRefresh, onCompleteTask, onUpdateChecklist }) => {
  const [showCompletedTasks, setShowCompletedTasks] = useState(false);
  if (!backlog) {
    return <div className="runs-empty-sidebar backlog-empty"><ListChecks size={22} /><strong>Backlog ainda não gerado</strong><span>Execute <code>looper backlog generate</code> para criar as tasks.</span></div>;
  }
  const currentTask = backlog.tasks.find((task) => task.id === backlog.execution.current_task_id);
  const remaining = backlog.tasks.filter((task) => task.status !== 'done');
  const completedTasks = backlog.tasks.filter((task) => task.status === 'done');
  const pendingTests = pendingTestTasks(backlog);
  const trackedTasks = backlog.tasks.filter((task) => task.level === 2 || task.level === 3);
  const testCounts = trackedTasks.reduce((counts, task) => {
    counts[taskTestStatus(task)] += 1;
    return counts;
  }, { pending: 0, in_progress: 0, done: 0 });
  const implementationCounts = trackedTasks.reduce((counts, task) => {
    counts[taskImplementationStatus(task)] += 1;
    return counts;
  }, { pending: 0, in_progress: 0, done: 0 });
  const activeTasks = backlog.tasks.filter((task) => task.status !== 'done');
  const branch = currentTask?.branch;
  const branchOccurrences = currentTask?.branches || (branch ? [branch] : []);
  const parentTask = currentTask ? parentTaskFor(backlog, currentTask) : undefined;
  const contextTaskIds = parentTask ? new Set([parentTask.id, ...(parentTask.child_task_ids || [])]) : new Set<string>();
  const nextSubtask = parentTask?.child_task_ids?.map((id) => backlog.tasks.find((task) => task.id === id)).find((task) => task && task.status !== 'done');
  const testChecklist = (backlog.phase_checklists?.test || []).filter((item) => contextTaskIds.has(item.task_id));
  const implementationChecklist = (backlog.phase_checklists?.implementation || []).filter((item) => contextTaskIds.has(item.task_id));
  const isTestPhase = backlog.execution.current_phase === 'test';
  const referenceStatus = (task: BacklogTask) => {
    const statuses = (task.traceability || []).map((reference) => reference.status);
    if (statuses.includes('unresolved')) return 'não encontrado';
    if (statuses.includes('not-analyzed')) return 'aguardando análise';
    return 'resolvido';
  };
  const currentTestScope = currentTask ? testScopeFor(backlog, currentTask) : [];
  const currentScopeReady = currentTestScope.length > 0 && currentTestScope.every((task) => taskTestStatus(task) === 'done');
  return (
    <div className="sidebar-pane backlog-pane">
      <div className="runs-sidebar-heading"><div><span className="eyebrow">Execução por jornada</span><h3>Backlog</h3></div><div className="backlog-heading-actions"><button type="button" className="backlog-refresh-btn" onClick={onRefresh} title="Atualizar tarefas e evidências"><RefreshCw size={14} /></button><span className="runs-total-badge">{remaining.length}</span></div></div>
      <div className="backlog-summary-card">
        <strong>{remaining.length === 0 ? 'Tudo concluído' : `${remaining.length} task(s) restantes`}</strong>
        <span>Escopo: {deliveryScopeFor(backlog) === 'node' ? 'L2 com subfluxos internos' : 'cada task separadamente'}</span>
        <div className="backlog-phase-summary">
          <span><b>Testes</b> {testCounts.done} concluídos · {testCounts.in_progress} em andamento · {testCounts.pending} pendentes</span>
          <span><b>Implementação</b> {implementationCounts.done} concluídas · {implementationCounts.in_progress} em andamento · {implementationCounts.pending} pendentes</span>
        </div>
        <span>{pendingTests.length} entrega(s) aguardando testes · {backlog.execution.completed_branches?.length || 0} branch(es) concluída(s)</span>
      </div>
      {currentTask ? (
        <article className="backlog-current-task">
          <div className="backlog-task-heading"><span className="eyebrow">{isTestPhase ? 'Task de testes' : 'Task de implementação'}</span><span className={`backlog-status ${isTestPhase ? 'testing' : 'in_progress'}`}>{isTestPhase ? 'testes em andamento' : 'implementação em andamento'}</span></div>
          <h4>{currentTask.label}</h4><code className="backlog-task-id">{currentTask.id}</code><p>{currentTask.description || 'Sem descrição.'}</p>
          {parentTask && parentTask.id !== currentTask.id && <div className="backlog-parent-context"><strong>Task pai</strong><span>{parentTask.label}</span><code>{parentTask.id}</code></div>}
          {nextSubtask && nextSubtask.id !== currentTask.id && <div className="backlog-parent-context"><strong>Próxima subtask</strong><span>{nextSubtask.label}</span><code>{nextSubtask.id}</code></div>}
          {currentTask.child_task_ids && currentTask.child_task_ids.length > 0 && <div className="backlog-parent-context"><strong>Subtasks</strong><span>{currentTask.child_task_ids.length} subtasks no contexto desta task</span></div>}
          <div className="backlog-branch-meta">Branch {branch?.id} · posição {branch?.position}{branch?.terminal ? ' · terminal' : ''}{branchOccurrences.length > 1 ? ` · presente em ${branchOccurrences.length} caminhos` : ''}</div>
          {currentTask.child_backlog_id && <div className="backlog-branch-meta">Backlog interno: {currentTask.child_backlog_id} · {(currentTask.child_task_ids || []).length} task(s)</div>}
          <div className="backlog-detail-section"><strong>Perguntas e respostas</strong>{(currentTask.questions || []).length === 0 ? <span>Nenhuma pergunta.</span> : (currentTask.questions || []).map((question) => <div className="backlog-question" key={question.id}><span>{question.prompt}</span><code>{question.answer === null || question.answer === '' ? 'sem resposta' : String(question.answer)}</code></div>)}</div>
          <div className="backlog-detail-section"><strong>Símbolos associados</strong>{(currentTask.symbols || []).length === 0 ? <span>Nenhum símbolo associado.</span> : (currentTask.symbols || []).map((symbol) => <div className="backlog-symbol" key={symbol}><code>{symbol}</code><small>{referenceStatus(currentTask)}</small></div>)}</div>
          <div className="backlog-detail-section"><strong>Testes associados e status da fase de testes</strong><span className={`backlog-phase-badge test ${taskTestStatus(currentTask)}`}>{phaseStatusLabel(taskTestStatus(currentTask))}</span>{currentScopeReady && currentTestScope.length > 1 && <small>Escopo completo: esta task e {currentTestScope.length - 1} subfluxo(s) interno(s).</small>}{currentTask.test_ref ? <><code>{currentTask.test_ref.file}</code>{(currentTask.test_ref.symbols || []).map((symbol) => <code key={symbol}>{symbol}</code>)}</> : <span>{currentTask.test_evidence?.reason || 'Acompanhe o checklist de teste do escopo.'}</span>}</div>
          {(currentTask.source_dependencies || []).length > 0 && <div className="backlog-detail-section"><strong>Dependências</strong>{currentTask.source_dependencies?.map((dependency) => <code key={dependency}>{dependency}</code>)}</div>}
          <div className="backlog-detail-section backlog-phase-checklists"><strong>Checklist de teste</strong>{testChecklist.length === 0 ? <span>Nenhum item.</span> : testChecklist.map((item) => <label className="backlog-checklist-item" key={item.id}><input type="checkbox" checked={item.checked} onChange={(event) => onUpdateChecklist(item.task_id, 'test', event.target.checked)} /><span>{item.label}</span><small>{item.checked ? 'concluído' : item.evidence_status === 'in_progress' ? 'em andamento' : 'pendente'}</small></label>)}</div>
          <div className="backlog-detail-section backlog-phase-checklists"><strong>Checklist de implementação</strong>{implementationChecklist.length === 0 ? <span>Nenhum item.</span> : implementationChecklist.map((item) => <label className="backlog-checklist-item" key={item.id}><input type="checkbox" checked={item.checked} onChange={(event) => onUpdateChecklist(item.task_id, 'implementation', event.target.checked)} /><span>{item.label}</span></label>)}</div>
          <button className="sidebar-submit-btn backlog-complete-btn" onClick={() => onCompleteTask(currentTask.id)}><CheckCircle2 size={14} /> {isTestPhase ? 'Concluir testes' : 'Concluir task'}</button>
        </article>
      ) : remaining.length > 0 ? (
        <div className="runs-empty-sidebar backlog-empty"><CircleDot size={22} /><strong>{pendingTests.length > 0 ? 'Testes pendentes' : 'Próxima task disponível'}</strong><span>{pendingTests.length > 0 ? 'Os testes devem ser executados antes da implementação.' : 'Reserve a próxima etapa da jornada para começar.'}</span>{pendingTests.length > 0 ? <button className="sidebar-submit-btn" onClick={onClaimTest}><Play size={14} /> Reservar testes</button> : <button className="sidebar-submit-btn" onClick={onClaimTask}><Play size={14} /> Reservar implementação</button>}</div>
      ) : (
        <div className="runs-empty-sidebar backlog-empty"><CheckCircle2 size={22} /><strong>Backlog vazio</strong><span>Não há mais tasks pendentes nesta jornada.</span></div>
      )}
      <div className="backlog-task-list">
        <div className="backlog-task-list-heading">
          <span className="eyebrow">Tasks</span>
          <button
            type="button"
            className={`backlog-completed-toggle ${showCompletedTasks ? 'open' : ''}`}
            aria-expanded={showCompletedTasks}
            aria-controls="backlog-completed-tasks"
            onClick={() => setShowCompletedTasks((current) => !current)}
          >
            <span>{showCompletedTasks ? 'Ocultar concluídas' : `Concluídas (${completedTasks.length})`}</span>
            <ChevronDown size={14} aria-hidden="true" />
          </button>
        </div>
        {activeTasks.map((task) => (
          <div className={`backlog-task-row ${task.status}`} key={task.id}>
            <div className="backlog-task-label"><span>{task.label}</span><small>Nível {task.level || '—'}</small></div>
            <div className="backlog-task-statuses">
              <small className={`backlog-phase-badge test ${taskTestStatus(task)}`}>Teste: {phaseStatusLabel(taskTestStatus(task))}</small>
              <small className={`backlog-phase-badge implementation ${taskImplementationStatus(task)}`}>Impl.: {phaseStatusLabel(taskImplementationStatus(task))}</small>
            </div>
          </div>
        ))}
        {activeTasks.length === 0 && completedTasks.length === 0 && <span className="backlog-task-list-empty">Nenhuma task registrada.</span>}
        {showCompletedTasks && <div id="backlog-completed-tasks" className="backlog-completed-tasks" aria-label="Tasks concluídas">
          {completedTasks.length === 0 ? <span className="backlog-task-list-empty">Nenhuma implementação concluída ainda.</span> : completedTasks.map((task) => (
            <div className="backlog-task-row done" key={task.id}>
              <div className="backlog-task-label"><span>{task.label}</span><small>Nível {task.level || '—'}</small></div>
              <div className="backlog-task-statuses">
                <small className={`backlog-phase-badge test ${taskTestStatus(task)}`}>Teste: {phaseStatusLabel(taskTestStatus(task))}</small>
                <small className="backlog-phase-badge implementation done">Impl.: concluída</small>
              </div>
            </div>
          ))}
        </div>}
      </div>
    </div>
  );
};
