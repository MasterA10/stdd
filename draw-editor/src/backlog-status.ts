import type { BacklogDocument, BacklogTask } from './types';

export type BacklogPhaseStatus = 'pending' | 'in_progress' | 'done';

export const taskTestStatus = (task: BacklogTask): BacklogPhaseStatus => {
  if (task.checklist_state?.test === true && (task.test_status === 'done' || task.test_status === 'not-required' || task.test_manual === true)) return 'done';
  if (task.test_status === 'in_progress') return 'in_progress';
  return 'pending';
};

export const taskImplementationStatus = (task: BacklogTask): BacklogPhaseStatus => task.status;

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
