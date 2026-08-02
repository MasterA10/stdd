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
  tradeoffs?: any[];
}
