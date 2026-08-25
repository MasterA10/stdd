import type { BacklogDocument, BacklogTask } from './types';

export type BacklogPhaseStatus = 'pending' | 'in_progress' | 'done';

export const taskTestStatus = (task: BacklogTask): BacklogPhaseStatus => {
  if (task.checklist_state?.test === true && (task.test_status === 'done' || task.test_status === 'not-required' || task.test_manual === true)) return 'done';
  if (task.test_status === 'in_progress') return 'in_progress';
  return 'pending';
};

export const taskImplementationStatus = (task: BacklogTask): BacklogPhaseStatus => task.status;

export const currentExecutionTask = (backlog: BacklogDocument, phase?: 'test' | 'implementation'): BacklogTask | undefined => {
  if (!backlog || !Array.isArray(backlog.tasks) || !backlog.execution || typeof backlog.execution !== 'object') return undefined;
  const { execution } = backlog;
  const candidates: Array<{ id: string; phase: 'test' | 'implementation' }> = [];
  const addCandidate = (id: string | null | undefined, candidatePhase: 'test' | 'implementation' | null | undefined) => {
    if (id && candidatePhase && (!phase || candidatePhase === phase)) candidates.push({ id, phase: candidatePhase });
  };

  addCandidate(execution.current_task_id, execution.current_phase);
  addCandidate(execution.current_subtask_id, execution.current_phase);
  const lanes = execution.lanes && typeof execution.lanes === 'object' && !Array.isArray(execution.lanes)
    ? execution.lanes
    : {};
  Object.entries(lanes).forEach(([laneId, lane]) => {
    if (!lane || typeof lane !== 'object') return;
    const lanePhase = lane.current_phase || (laneId.startsWith('test:') ? 'test' : laneId.startsWith('implementation:') ? 'implementation' : null);
    addCandidate(lane.current_task_id, lanePhase);
    addCandidate(lane.current_subtask_id, lanePhase);
  });

  const byId = new Map(backlog.tasks.map((task) => [task.id, task]));
  const findImplementationDescendant = (id: string, visited = new Set<string>()): BacklogTask | undefined => {
    if (visited.has(id)) return undefined;
    visited.add(id);
    const task = byId.get(id);
    if (!task) return undefined;
    if (task.status === 'in_progress') return task;
    return (task.child_task_ids || []).map((childId) => findImplementationDescendant(childId, visited)).find(Boolean);
  };

  for (const candidate of candidates) {
    const task = byId.get(candidate.id);
    if (!task) continue;
    if (candidate.phase === 'implementation') {
      const active = findImplementationDescendant(candidate.id);
      if (active) return active;
    } else {
      return task;
    }
  }

  if (phase === 'implementation') {
    return backlog.tasks.find((task) => task.status === 'in_progress' && task.level === 3)
      || backlog.tasks.find((task) => task.status === 'in_progress');
  }
  if (phase === 'test') return backlog.tasks.find((task) => task.test_status === 'in_progress');
  return backlog.tasks.find((task) => task.status === 'in_progress');
};

export const parentTaskFor = (backlog: BacklogDocument, task: BacklogTask): BacklogTask => {
  let current = task;
  const visited = new Set<string>();
  const byId = new Map(backlog.tasks.map((item) => [item.id, item]));
  while (current.parent_task_id && !visited.has(current.id)) {
    visited.add(current.id);
    const parent = byId.get(current.parent_task_id);
    if (!parent) break;
    current = parent;
  }
  return current;
};

export const deliveryScopeFor = (backlog: BacklogDocument): 'task' | 'node' => (
  backlog.execution.task_delivery_scope === 'node' ? 'node' : 'task'
);

export const testScopeFor = (backlog: BacklogDocument, task: BacklogTask): BacklogTask[] => {
  if (deliveryScopeFor(backlog) === 'task') return [task];
  const parent = parentTaskFor(backlog, task);
  const byId = new Map(backlog.tasks.map((item) => [item.id, item]));
  return [parent, ...(parent.child_task_ids || []).map((id) => byId.get(id)).filter((item): item is BacklogTask => Boolean(item))];
};

export const taskNeedsTests = (backlog: BacklogDocument, task: BacklogTask): boolean => (
  testScopeFor(backlog, task).some((item) => taskTestStatus(item) !== 'done')
);

export const pendingTestTasks = (backlog: BacklogDocument): BacklogTask[] => backlog.tasks.filter((task) => {
  const isDeliveryTask = deliveryScopeFor(backlog) === 'node' ? task.level === 2 : task.level === 2 || task.level === 3;
  return isDeliveryTask && taskNeedsTests(backlog, task);
});

export const phaseStatusLabel = (status: BacklogPhaseStatus): string => ({
  pending: 'pendente',
  in_progress: 'em andamento',
  done: 'concluída'
}[status]);
