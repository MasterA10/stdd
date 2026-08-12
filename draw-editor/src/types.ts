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

export interface NodeData {
  id: number;
  label: string;
  group?: number;
  description: string;
  questions?: Question[];
  isHighlighted?: boolean;
  isDimmed?: boolean;
  background?: string;
  text?: string;
  draw_ref?: string;
  [key: string]: any;
}

export interface CodeReference {
  symbol: string;
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
