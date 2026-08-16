export interface QuestionOption {
  id: number;
  label: string;
}

export interface Question {
  id: number;
  type: 'open' | 'boolean' | 'choice';
  prompt: string;
  options?: QuestionOption[];
  answer: string | boolean | number | null;
}

export interface ImprovementSession {
  version: number;
  id: string;
  kind: 'draw-improvement';
  title: string;
  draw_id: string;
  status: 'draft' | 'ready' | 'applied';
  questions: Question[];
  created_at?: string;
  updated_at?: string;
}

export interface ImprovementIndexEntry {
  id: string;
  file?: string;
  title: string;
  draw_id: string;
  status: ImprovementSession['status'];
  answered_count: number;
  question_count: number;
  updated_at?: string;
}

export interface NodeData {
  id: number;
  label: string;
  group?: number;
  theme?: 'light' | 'dark' | 'black';
  description: string;
  test_ref?: { file: string; symbols: string[] } | null;
  test_refs?: Array<{ file: string; symbols: string[] }>;
  questions?: Question[];
  isHighlighted?: boolean;
  isDimmed?: boolean;
  background?: string;
  text?: string;
  draw_ref?: string;
  backlogChecklist?: {
    taskId: string;
    test: boolean;
    implementation: boolean;
  };
  [key: string]: any;
}

export interface CodeReference {
  symbol: string;
  file?: string;
  source_dependencies?: string[];
  identity?: string;
}

export interface TraceabilityFacts {
  version?: number;
  draw_id?: string;
  nodes?: Record<string, {
    references?: Array<{ symbol?: string; status?: string; file?: string }>;
    source_dependencies?: string[];
    files?: string[];
    tests?: string[];
    unresolved?: string[];
  }>;
}

export interface StaticAnalysisKpiReport {
  version?: number;
  generated_at?: string;
  status?: string;
  reason?: string;
  adapter_command?: string[] | null;
  stack?: { languages?: string[]; frameworks?: string[]; test_runners?: string[] };
  indicators?: Array<{ id: string; label: string; value: number; unit?: string; status?: string }>;
  summary?: {
    symbols?: number;
    dependencies?: number;
    complexity?: number;
    structural_metrics?: number;
    files?: string[];
    quality_findings?: number;
    severity?: Record<string, number>;
    findings_by_kind?: Record<string, number>;
  };
  capabilities?: Record<string, boolean>;
  warnings?: string[];
  errors?: string[];
  details?: {
    quality_findings?: Array<Record<string, any>>;
    complexity?: Array<Record<string, any>>;
    structural_metrics?: Array<Record<string, any>>;
    symbols?: Array<Record<string, any>>;
    dependencies?: Array<Record<string, any>>;
  };
}

export interface EdgeData {
  id: number;
  from: number;
  to: number;
  kind: string;
  condition: number; // 1: 'então', 2: 'ou', 3: 'se'
  label: string;
  description: string;
  isHighlighted?: boolean;
  isDimmed?: boolean;
  [key: string]: any;
}

export interface Group {
  id: number;
  label: string;
  description?: string;
  color?: string;
}

export interface FlowStep {
  node: number;
  text: string;
}

export interface FlowPath {
  id: number;
  label: string;
  title: string;
  summary: string;
  steps: FlowStep[];
}

export interface DrawHierarchy {
  level?: number;
  role?: string;
  parent_draw_ref?: string | null;
  parent_node_id?: number | null;
  root_draw_ref?: string | null;
}

export interface DrawIndexEntry {
  id: string;
  file?: string;
  title: string;
  subtitle?: string;
  kind?: string;
  updated_at?: string;
  node_count?: number;
  edge_count?: number;
  subdraw_count?: number;
  hierarchy?: DrawHierarchy;
}

export interface Contract {
  version: number;
  id: string;
  title: string;
  subtitle?: string;
  kind: string;
  notes?: string[];
  groups: Group[];
  nodes: NodeData[];
  edges: EdgeData[];
  flows?: FlowPath[];
  hierarchy?: DrawHierarchy;
  tradeoffs?: any[];
}

export interface RunRecord {
  run_id: string;
  timestamp: string;
  description: string;
  work_types: string[];
  checkpoint?: boolean;
  diff_stats: {
    lines_added?: number;
    lines_deleted?: number;
    files_changed?: number;
    [key: string]: any;
  };
}

export interface BacklogTask {
  id: string;
  draw_id: string;
  backlog_id?: string;
  parent_task_id?: string | null;
  draw_title?: string;
  node_id: number;
  level?: number;
  label: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'done';
  questions?: Question[];
  code_refs?: CodeReference[];
  symbols?: string[];
  source_dependencies?: string[];
  traceability?: Array<{ symbol: string; status?: string; file?: string }>;
  test_ref?: { file: string; symbols: string[] } | null;
  test_status?: 'missing' | 'in_progress' | 'done' | 'not-required';
  test_evidence?: { status?: string; file?: string | null; symbols?: string[]; missing_symbols?: string[]; reason?: string };
  test_owner_task_id?: string | null;
  checklist_state?: { test: boolean; implementation: boolean };
  child_checklist_id?: string;
  child_backlog_id?: string;
  child_task_ids?: string[];
  child_branch_ids?: string[];
  branch?: { id: string; position: number; terminal?: boolean; terminal_node_id?: number; terminal_reason?: string };
  branches?: Array<{ id: string; position: number; terminal?: boolean; terminal_node_id?: number; terminal_reason?: string }>;
}

export interface BacklogDocument {
  version: number;
  kind: 'backlog';
  generated_at?: string;
  system?: { root_draw_ids?: string[] };
  checklists?: Array<{ id: string; title?: string; items?: Array<{ id: string; status: string }> }>;
  phase_checklists?: {
    test: BacklogChecklistItem[];
    implementation: BacklogChecklistItem[];
  };
  backlogs?: Array<{ id: string; draw_id: string; title?: string; parent_task_id?: string | null; task_ids?: string[] }>;
  tasks: BacklogTask[];
  execution: {
    current_task_id?: string | null;
    current_backlog_id?: string | null;
    current_branch_id?: string | null;
    branch_position?: number | null;
    current_phase?: 'test' | 'implementation' | null;
    current_parent_task_id?: string | null;
    current_subtask_id?: string | null;
    completed_branches?: string[];
    branches?: Array<{ id: string; completed?: boolean; terminal_reason?: string; task_ids?: string[]; node_ids?: number[]; edges?: EdgeData[]; flow_id?: number | null; backlog_id?: string; parent_task_id?: string; scope?: string }>;
  };
}

export interface BacklogChecklistItem {
  id: string;
  task_id: string;
  draw_id?: string;
  node_id?: number;
  label: string;
  parent_task_id?: string | null;
  checked: boolean;
  evidence_status?: string;
  status?: string;
}
