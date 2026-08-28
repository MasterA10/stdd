import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  useNodesInitialized,
  MarkerType
} from '@xyflow/react';
import type { Connection, Edge, EdgeChange, Node, EdgeTypes } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import type { BacklogActionResponse, BacklogDocument, Contract, DrawIndexEntry, ImprovementIndexEntry, ImprovementSession, NodeData, EdgeData, RunRecord, TraceabilityFacts, StaticAnalysisKpiReport } from './types';
import { currentExecutionTask, deliveryScopeFor, pendingTestTasks, taskNeedsTests, testScopeFor } from './backlog-status';
import { CustomNode } from './components/CustomNode';
import { LoopEdge } from './components/LoopEdge';
import { Sidebar } from './components/Sidebar';
import { QuestionsModal } from './components/QuestionsModal';
import { ChangesModal } from './components/ChangesModal';
import { CodeReferencesModal } from './components/CodeReferencesModal';
import { ImportExportModal } from './components/ImportExportModal';
import { MetadataModal } from './components/MetadataModal';
import { ConfirmModal } from './components/ConfirmModal';
import { FocusDetailModal } from './components/FocusDetailModal';
import { ImprovementEditor } from './components/ImprovementEditor';
import { NodeEditModal } from './components/NodeEditModal';
import { ParentNavigationModal, type ParentNavigationOption } from './components/ParentNavigationModal';
import { ConfigSettingsModal } from './components/ConfigSettingsModal';
import { layoutCurvedGraph, computeEdgeHandles, getCycleEdges } from './layout';
import { ArrowUp, RotateCcw, Save, Download, Sun, Moon, Contrast, Sparkles, ClipboardList, X, PanelBottom, PanelLeft, Eye, EyeOff, Settings } from 'lucide-react';

import defaultContract from '../contract.json';

const typedDefaultContract = defaultContract as Contract;

const nodeTypes = {
  custom: CustomNode
};

const edgeTypes: EdgeTypes = {
  loop: LoopEdge
};

const DEFAULT_CONDITION = 1;
const THEN_EDGE_GRADIENT = 'url(#looper-then-edge-gradient)';
const THEN_EDGE_MARKER_COLOR = '#fb923c';

const DEFAULT_DRAW_SERVER_ORIGIN = 'http://127.0.0.1:8765';
let detectedBackendOrigin: string | null = null;

const getApiOrigins = () => {
  const origins = window.location.protocol === 'file:'
    ? [DEFAULT_DRAW_SERVER_ORIGIN]
    : [window.location.origin, DEFAULT_DRAW_SERVER_ORIGIN];
  return [...new Set(origins)];
};

const getApiOrigin = () => detectedBackendOrigin || getApiOrigins()[0];

const isImprovementAnswer = (answer: ImprovementSession['questions'][number]['answer']) =>
  answer !== null && !(typeof answer === 'string' && answer.trim() === '');

function parseClipboardNodeJson(text: string): NodeData[] {
  const parsed: unknown = JSON.parse(text);
  const candidates = Array.isArray(parsed) ? parsed : [parsed];
  if (candidates.length === 0 || candidates.some((candidate) => (
    !candidate || typeof candidate !== 'object' || Array.isArray(candidate)
  ))) {
    throw new Error('O JSON não contém um nó válido.');
  }

  return candidates.map((candidate) => {
    const node = JSON.parse(JSON.stringify(candidate)) as Partial<NodeData>;
    if (typeof node.label !== 'string' || typeof node.description !== 'string') {
      throw new Error('O JSON precisa conter label e description do nó.');
    }
    return node as NodeData;
  });
}

interface DrawSearchResult {
  drawId: string;
  drawTitle: string;
  nodeId: number;
  nodeLabel: string;
  associations: string[];
}

const checkBackendAvailable = async (): Promise<string | null> => {
  for (const origin of getApiOrigins()) {
    try {
      const response = await fetch(`${origin}/.looper/draws/index.json`, { method: 'GET', cache: 'no-store' });
      if (response.ok) return origin;
    } catch (_) {
      // Tenta a próxima origem, especialmente o Draw Server em outra porta.
    }
  }
  return null;
};

export const App: React.FC = () => {
  // --- Drawings & Storage States ---
  const [contract, setContract] = useState<Contract>(typedDefaultContract);
  const [drawingsIndex, setDrawingsIndex] = useState<DrawIndexEntry[]>([]);
  const [improvementsIndex, setImprovementsIndex] = useState<ImprovementIndexEntry[]>([]);
  const [currentImprovement, setCurrentImprovement] = useState<ImprovementSession | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [backlog, setBacklog] = useState<BacklogDocument | null>(null);
  const [storageMode, setStorageMode] = useState<'backend' | 'local'>('local');
  const [navigation, setNavigation] = useState<string[]>([]);
  
  // --- UI States ---
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<number | null>(null);
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [activeFlowId, setActiveFlowId] = useState<number | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark' | 'black'>('black');
  const [isSidebarVisible, setIsSidebarVisible] = useState(true);
  const [sidebarDock, setSidebarDock] = useState<'side' | 'bottom'>('side');
  const [isDirty, setIsDirty] = useState(false);
  const [isImprovementDirty, setIsImprovementDirty] = useState(false);
  const [drawSyncState, setDrawSyncState] = useState<'local' | 'checking' | 'synced' | 'pending' | 'error'>('local');
  const [observerMode, setObserverMode] = useState(false);
  const [observerStatus, setObserverStatus] = useState('Desativado');
  const [observerTarget, setObserverTarget] = useState<{ taskId: string; drawId: string; nodeId: number; label: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<DrawSearchResult[]>([]);
  const [isSearchLoading, setIsSearchLoading] = useState(false);
  const [selectionRevision, setSelectionRevision] = useState(0);
  const [reactFlowReady, setReactFlowReady] = useState(0);
  const [presentationPositionsState, setPresentationPositionsState] = useState<Record<string, { x: number; y: number }>>({});
  const [showConfigSettings, setShowConfigSettings] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('settings') === '1') setShowConfigSettings(true);
  }, []);

  // --- Dialogs & Modals States ---
  const [questionsNode, setQuestionsNode] = useState<NodeData | null>(null);
  const [changesNode, setChangesNode] = useState<NodeData | null>(null);
  const [showImprovementModal, setShowImprovementModal] = useState(false);
  const [codeReferencesNode, setCodeReferencesNode] = useState<NodeData | null>(null);
  const [traceabilityFacts, setTraceabilityFacts] = useState<TraceabilityFacts | null>(null);
  const [staticAnalysisKpis, setStaticAnalysisKpis] = useState<StaticAnalysisKpiReport | null>(null);
  const [activeDetailNodeId, setActiveDetailNodeId] = useState<number | null>(null);
  const [importExportMode, setImportExportMode] = useState<'import' | 'export' | null>(null);
  const [parentNavigationOptions, setParentNavigationOptions] = useState<ParentNavigationOption[] | null>(null);
  const [isParentNavigationLoading, setIsParentNavigationLoading] = useState(false);
  const [metadataModalConfig, setMetadataModalConfig] = useState<{
    isOpen: boolean;
    mode: 'create' | 'edit';
    initialValues?: { title: string; subtitle: string; kind: string };
  } | null>(null);
  const [confirmConfig, setConfirmConfig] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    isDanger?: boolean;
    resolve: (val: boolean) => void;
  } | null>(null);
  const [editNodeData, setEditNodeData] = useState<NodeData | null>(null);

  // --- React Flow Node & Edge States ---
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<NodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const nodesInitialized = useNodesInitialized({ includeHiddenNodes: true });
  const backlogRequestRef = useRef(0);
  const backlogPollInFlightRef = useRef(false);
  const renderedNodesSignatureRef = useRef<string | null>(null);
  const renderedEdgesSignatureRef = useRef<string | null>(null);

  const loadBacklog = useCallback(async () => {
    const requestId = backlogRequestRef.current + 1;
    backlogRequestRef.current = requestId;
    const applyBacklog = (value: unknown): boolean => {
      if (!value || typeof value !== 'object') return false;
      const candidate = value as Partial<BacklogDocument>;
      if (!Array.isArray(candidate.tasks) || !candidate.execution || typeof candidate.execution !== 'object') return false;
      if (requestId === backlogRequestRef.current) setBacklog(candidate as BacklogDocument);
      return true;
    };

    const origins = [...new Set([getApiOrigin(), ...getApiOrigins()])];
    for (const origin of origins) {
      try {
        const response = await fetch(`${origin}/.looper/backlog.json`, { cache: 'no-store' });
        if (response.ok) {
          if (applyBacklog(await response.json())) return;
        }
      } catch (_) {}
    }
    try {
      const saved = localStorage.getItem('looper-backlog');
      if (saved && applyBacklog(JSON.parse(saved))) return;
    } catch (_) {
      // Preserve the last valid snapshot while the producer is updating it.
    }
  }, []);

  useEffect(() => { loadBacklog(); }, [loadBacklog, storageMode]);

  useEffect(() => {
    if (!observerMode) return;
    let cancelled = false;
    const pollBacklog = async () => {
      if (cancelled || document.visibilityState === 'hidden' || backlogPollInFlightRef.current) return;
      backlogPollInFlightRef.current = true;
      try {
        await loadBacklog();
        if (!cancelled) setObserverStatus('Observando o backlog');
      } finally {
        backlogPollInFlightRef.current = false;
      }
    };
    void pollBacklog();
    const interval = window.setInterval(pollBacklog, 2000);
    const handleVisibility = () => { if (document.visibilityState === 'visible') void pollBacklog(); };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [loadBacklog, observerMode]);

  const updateLocalBacklog = useCallback((updater: (previous: BacklogDocument) => BacklogDocument) => {
    setBacklog((previous) => {
      if (!previous) return previous;
      const next = updater(previous);
      localStorage.setItem('looper-backlog', JSON.stringify(next));
      return next;
    });
  }, []);

  const claimBacklogTask = async () => {
    if (storageMode === 'backend') {
      try {
        const response = await fetch(`${getApiOrigin()}/__looper/api/backlog/task`, { method: 'POST' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        await loadBacklog();
        return;
      } catch (error: any) { alert(`Erro ao reservar task: ${error.message}`); return; }
    }
    updateLocalBacklog((previous) => {
      if (previous.execution.current_phase === 'test') return previous;
      const current = previous.execution.current_task_id;
      const task = previous.tasks.find((item) => item.id === current) || previous.tasks.find((item) => item.status !== 'done' && !taskNeedsTests(previous, item));
      if (!task) return previous;
      const tasks = previous.tasks.map((item) => item.id === task.id ? { ...item, status: 'in_progress' as const } : item);
      return { ...previous, tasks, execution: { ...previous.execution, current_task_id: task.id, current_backlog_id: task.backlog_id, current_branch_id: task.branch?.id, branch_position: task.branch?.position, current_phase: 'implementation' as const } };
    });
  };

  const claimBacklogTest = async () => {
    if (storageMode === 'backend') {
      try {
        const response = await fetch(`${getApiOrigin()}/__looper/api/backlog/test`, { method: 'POST' });
        const result = await response.json().catch(() => ({})) as BacklogActionResponse;
        if (!response.ok) throw new Error((result as any).error || `HTTP ${response.status}`);
        await loadBacklog();
        return;
      } catch (error: any) { alert(`Erro ao reservar testes: ${error.message}`); return; }
    }
    updateLocalBacklog((previous) => {
      if (previous.execution.current_task_id) return previous;
      const task = pendingTestTasks(previous)[0];
      if (!task) return previous;
      const tasks = previous.tasks.map((item) => item.id === task.id
        ? { ...item, status: 'in_progress' as const, test_status: 'in_progress' as const }
        : item);
      return {
        ...previous,
        tasks,
        execution: {
          ...previous.execution,
          current_task_id: task.id,
          current_backlog_id: task.backlog_id,
          current_branch_id: task.branch?.id,
          branch_position: task.branch?.position,
          current_phase: 'test' as const
        }
      };
    });
  };

  const refreshBacklog = async () => {
    if (storageMode === 'backend') {
      try {
        const response = await fetch(`${getApiOrigin()}/__looper/api/backlog/refresh`, { method: 'POST' });
        const result = await response.json().catch(() => ({})) as BacklogActionResponse;
        if (!response.ok) throw new Error((result as any).error || `HTTP ${response.status}`);
        setBacklog(result.backlog || null);
        return;
      } catch (error: any) { alert(`Erro ao atualizar backlog: ${error.message}`); return; }
    }
    await loadBacklog();
  };

  const completeBacklogTask = async (taskId: string) => {
    if (storageMode === 'backend') {
      try {
        const response = await fetch(`${getApiOrigin()}/__looper/api/backlog/tasks/${encodeURIComponent(taskId)}/complete`, { method: 'POST' });
        if (!response.ok) { const result = await response.json().catch(() => ({})); throw new Error(result.error || `HTTP ${response.status}`); }
        await loadBacklog();
        return;
      } catch (error: any) { alert(`Erro ao concluir task: ${error.message}`); return; }
    }
    updateLocalBacklog((previous) => {
      if (previous.execution.current_task_id !== taskId) return previous;
      if (previous.execution.current_phase === 'test') {
        const current = previous.tasks.find((item) => item.id === taskId);
        if (!current) return previous;
        const scopeIds = new Set(testScopeFor(previous, current).map((item) => item.id));
        const tasks = previous.tasks.map((item) => scopeIds.has(item.id)
          ? { ...item, test_status: 'done' as const, checklist_state: { ...(item.checklist_state || { test: false, implementation: false }), test: true } }
          : item);
        return {
          ...previous,
          tasks,
          phase_checklists: {
            ...(previous.phase_checklists || { test: [], implementation: [] }),
            test: (previous.phase_checklists?.test || []).map((item) => ({ ...item, checked: tasks.find((task) => task.id === item.task_id)?.checklist_state?.test === true }))
          },
          execution: { ...previous.execution, current_task_id: null, current_backlog_id: null, current_phase: null }
        };
      }
      const current = previous.tasks.find((item) => item.id === taskId);
      if (!current) return previous;
      const scopeIds = deliveryScopeFor(previous) === 'node'
        ? new Set(testScopeFor(previous, current).map((item) => item.id))
        : new Set([current.id]);
      const tasks = previous.tasks.map((item) => scopeIds.has(item.id)
        ? { ...item, status: 'done' as const, checklist_state: { ...(item.checklist_state || { test: false, implementation: false }), implementation: true } }
        : item);
      return {
        ...previous,
        tasks,
        phase_checklists: {
          ...(previous.phase_checklists || { test: [], implementation: [] }),
          implementation: (previous.phase_checklists?.implementation || []).map((item) => ({ ...item, checked: tasks.find((task) => task.id === item.task_id)?.checklist_state?.implementation === true, status: tasks.find((task) => task.id === item.task_id)?.status }))
        },
        execution: { ...previous.execution, current_task_id: null, current_backlog_id: null, current_phase: null }
      };
    });
  };

  const updateBacklogChecklist = useCallback(async (taskId: string, phase: 'test' | 'implementation', checked: boolean, drawId?: string, nodeId?: number) => {
    if (storageMode === 'backend') {
      const stableIdentity = /^task:(.+):node:(\d+)$/.exec(taskId);
      const resolvedDrawId = drawId || stableIdentity?.[1];
      const resolvedNodeId = nodeId ?? (stableIdentity ? Number(stableIdentity[2]) : undefined);
      try {
        const response = await fetch(`${getApiOrigin()}/__looper/api/backlog/checklist`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task_id: taskId, phase, checked, draw_id: resolvedDrawId, node_id: resolvedNodeId })
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        await loadBacklog();
        return;
      } catch (error: any) { alert(`Erro ao atualizar checklist: ${error.message}`); return; }
    }
    updateLocalBacklog((previous) => {
      const task = previous.tasks.find((item) => item.id === taskId);
      if (!task) return previous;
      const state = { test: Boolean(task.checklist_state?.test), implementation: Boolean(task.checklist_state?.implementation) };
      if (phase === 'implementation' && checked) {
        const parentId = task.parent_task_id || task.id;
        const parent = previous.tasks.find((item) => item.id === parentId) || task;
        const scopeIds = new Set([parent.id, ...(parent.child_task_ids || [])]);
        const complete = previous.tasks.filter((item) => scopeIds.has(item.id)).every((item) => item.checklist_state?.test === true);
        if (!complete) {
          alert('O checklist de teste do nó e dos subfluxos ainda não foi concluído.');
          return previous;
        }
      }
      state[phase] = checked;
      let tasks = previous.tasks.map((item) => item.id === taskId ? { ...item, checklist_state: state, status: phase === 'implementation' ? (checked ? 'done' as const : 'pending' as const) : item.status } : item);
      if (phase === 'test' && !checked) {
        const parentId = task.parent_task_id || task.id;
        const parent = tasks.find((item) => item.id === parentId) || task;
        const scopeIds = new Set([parent.id, ...(parent.child_task_ids || [])]);
        tasks = tasks.map((item) => scopeIds.has(item.id) ? { ...item, checklist_state: { ...(item.checklist_state || { test: false, implementation: false }), implementation: false }, status: 'pending' as const } : item);
      }
      const phaseChecklists = previous.phase_checklists || { test: [], implementation: [] };
      return {
        ...previous,
        tasks,
        phase_checklists: {
          test: (phaseChecklists.test || []).map((item) => ({ ...item, checked: tasks.find((taskItem) => taskItem.id === item.task_id)?.checklist_state?.test === true })),
          implementation: (phaseChecklists.implementation || []).map((item) => ({ ...item, checked: tasks.find((taskItem) => taskItem.id === item.task_id)?.checklist_state?.implementation === true, status: tasks.find((taskItem) => taskItem.id === item.task_id)?.status }))
        }
      };
    });
  }, [loadBacklog, storageMode, updateLocalBacklog]);

  useEffect(() => {
    let cancelled = false;

    const loadRuns = async () => {
      try {
        const origin = getApiOrigin();
        const indexResponse = await fetch(`${origin}/.looper/runs/index.json`, { cache: 'no-store' });
        if (!indexResponse.ok) return;

        const index = await indexResponse.json();
        const days = Array.isArray(index.days) ? index.days : [];
        const summaries = await Promise.all(days.map(async (day: { summary?: string }) => {
          if (!day.summary) return null;
          const response = await fetch(`${origin}/.looper/runs/${day.summary}`, { cache: 'no-store' });
          return response.ok ? response.json() : null;
        }));
        const records = summaries.flatMap((summary) => (
          Array.isArray(summary?.runs) ? summary.runs : []
        )) as RunRecord[];
        records.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        if (!cancelled) setRuns(records);
      } catch (_) {
        if (!cancelled) setRuns([]);
      }
    };

    loadRuns();
    return () => { cancelled = true; };
  }, []);

  // UseRef to maintain latest contract reference and avoid stale closures in window functions
  const contractRef = useRef(contract);
  const selectionOrderRef = useRef<number[]>([]);
  const contractHistoryRef = useRef<Contract[]>([]);
  const lastContractSnapshotRef = useRef<string | null>(null);
  const skipHistoryRef = useRef(false);
  const presentationPositionsRef = useRef<Record<string, { x: number; y: number }>>({});
  const searchRequestRef = useRef(0);
  const drawingLoadRequestRef = useRef(0);
  const pendingSearchFocusRef = useRef<{ drawId: string; nodeId: number } | null>(null);
  const drawRevisionRef = useRef<string | null>(null);
  const savingContractRef = useRef(false);
  const pendingExternalRevisionRef = useRef<string | null>(null);
  const dirtyStateRef = useRef({ isDirty: false, isImprovementDirty: false });
  const pendingAutoFitDrawRef = useRef<string | null>(null);
  const observerTargetRef = useRef<string | null>(null);
  const observerFocusedKeyRef = useRef<string | null>(null);
  const reactFlowInstanceRef = useRef<any>(null);
  const lastAutoFitKeyRef = useRef<string | null>(null);
  const [renderedDrawId, setRenderedDrawId] = useState<string | null>(null);
  const [autoFitRevision, setAutoFitRevision] = useState(0);

  dirtyStateRef.current = { isDirty, isImprovementDirty };

  const flowNodeSignature = useMemo(
    () => nodes.map((node) => `${String(node.id)}:${node.data.label}:${node.data.description}`).join('|'),
    [nodes]
  );
  const contractNodeSignature = useMemo(
    () => contract.nodes.map((node) => `${String(node.id)}:${node.label}:${node.description}`).join('|'),
    [contract.nodes]
  );

  const readPresentationPositions = (id: string) => {
    try {
      const saved = localStorage.getItem(`looper-draw-presentation:${id}`);
      return saved ? JSON.parse(saved).positions || {} : {};
    } catch (_) {
      return {};
    }
  };

  const setPresentationPositionsForDrawing = (id: string) => {
    const positions = readPresentationPositions(id);
    presentationPositionsRef.current = positions;
    setPresentationPositionsState(positions);
  };

  const enrichDrawingsWithHierarchy = async (
    indexData: DrawIndexEntry[],
    mode: 'backend' | 'local'
  ): Promise<DrawIndexEntry[]> => {
    const origins = mode === 'backend'
      ? [getApiOrigin(), ...getApiOrigins()]
      : getApiOrigins();
    const uniqueOrigins = [...new Set(origins)];

    return Promise.all(indexData.map(async (entry) => {
      let document: Partial<Contract> | null = null;

      if (mode === 'local') {
        const saved = localStorage.getItem(`looper-draw:${entry.id}`);
        if (saved) {
          try {
            document = JSON.parse(saved) as Partial<Contract>;
          } catch (_) {
            document = null;
          }
        }
      }

      if (!document) {
        for (const origin of uniqueOrigins) {
          try {
            const response = await fetch(`${origin}/.looper/draws/${encodeURIComponent(entry.id)}.json`, { cache: 'no-store' });
            if (!response.ok) continue;
            document = await response.json() as Partial<Contract>;
            break;
          } catch (_) {
            // A lista continua utilizável mesmo quando um desenho não responde.
          }
        }
      }

      if (!document && entry.id === typedDefaultContract.id) {
        document = typedDefaultContract;
      }

      return {
        ...entry,
        hierarchy: document?.hierarchy || entry.hierarchy
      };
    }));
  };

  useEffect(() => {
    const snapshot = JSON.stringify(contract);
    if (lastContractSnapshotRef.current === null) {
      lastContractSnapshotRef.current = snapshot;
      return;
    }
    if (lastContractSnapshotRef.current !== snapshot) {
      if (!skipHistoryRef.current && isDirty) {
        const previous = JSON.parse(lastContractSnapshotRef.current) as Contract;
        contractHistoryRef.current = [...contractHistoryRef.current.slice(-49), previous];
      }
      skipHistoryRef.current = false;
      lastContractSnapshotRef.current = snapshot;
    }
  }, [contract, isDirty]);

  useEffect(() => {
    contractRef.current = contract;
    window.currentDrawId = contract.id;
  }, [contract]);

  useEffect(() => {
    let cancelled = false;
    setTraceabilityFacts(null);
    const needsTraceabilityFacts = contract.nodes.some((node) => Array.isArray(node.code_refs) && node.code_refs.length > 0);
    if (!needsTraceabilityFacts) return () => { cancelled = true; };
    const loadFacts = async () => {
      for (const origin of getApiOrigins()) {
        try {
          const response = await fetch(`${origin}/.looper/facts/${encodeURIComponent(contract.id)}.facts.json`, { cache: 'no-store' });
          if (!response.ok) continue;
          const data = await response.json();
          if (!cancelled) setTraceabilityFacts(data as TraceabilityFacts);
          return;
        } catch (_) {
          // O viewer continua funcional quando os facts ainda não existem.
        }
      }
    };
    loadFacts();
    return () => { cancelled = true; };
  }, [contract.id, storageMode]);

  useEffect(() => {
    let cancelled = false;
    const loadKpis = async () => {
      for (const origin of getApiOrigins()) {
        try {
          const response = await fetch(`${origin}/.looper/adapters/static-analysis-kpis.json`, { cache: 'no-store' });
          if (!response.ok) continue;
          const data = await response.json();
          if (!cancelled) setStaticAnalysisKpis(data as StaticAnalysisKpiReport);
          return;
        } catch (_) {
          // O painel permanece disponível quando a análise ainda não foi executada.
        }
      }
      if (!cancelled) setStaticAnalysisKpis(null);
    };
    loadKpis();
    return () => { cancelled = true; };
  }, [storageMode]);

  // Non-blocking Promise-based Confirm Dialogue
  const askConfirm = (title: string, message: string, confirmLabel?: string, isDanger?: boolean): Promise<boolean> => {
    return new Promise((resolve) => {
      setConfirmConfig({
        isOpen: true,
        title,
        message,
        confirmLabel,
        isDanger,
        resolve
      });
    });
  };

  // --- Initialize Drawings & Storage Mode ---
  useEffect(() => {
    const initializeApp = async () => {
      // 1. Detect backend
      const backendOrigin = await checkBackendAvailable();
      detectedBackendOrigin = backendOrigin;
      const mode = backendOrigin ? 'backend' : 'local';
      setStorageMode(mode);

      // 2. Load index
      let indexData: DrawIndexEntry[] = [];
      if (backendOrigin) {
        try {
          const origin = getApiOrigin();
          const response = await fetch(`${origin}/.looper/draws/index.json`, { cache: 'no-store' });
          if (response.ok) {
            const data = await response.json();
            indexData = data.draws || [];
          }
        } catch (_) {}
      } else {
        const savedIndex = localStorage.getItem('looper-draws-index');
        if (savedIndex) {
          try {
            indexData = JSON.parse(savedIndex).draws || [];
          } catch (_) {}
        }
      }

      // 3. Pre-populate default contract in Local Storage if empty
      if (mode === 'local' && indexData.length === 0) {
        const defaultId = typedDefaultContract.id;
        const initialIndex = [
          {
            id: defaultId,
            file: `${defaultId}.json`,
            title: typedDefaultContract.title,
            subtitle: typedDefaultContract.subtitle || '',
            kind: typedDefaultContract.kind,
            updated_at: new Date().toISOString(),
            node_count: typedDefaultContract.nodes.length,
            edge_count: typedDefaultContract.edges.length,
            subdraw_count: typedDefaultContract.nodes.reduce((total, n) => total + (n.draw_refs?.length || (n.draw_ref ? 1 : 0)), 0)
          }
        ];
        localStorage.setItem('looper-draws-index', JSON.stringify({ version: 1, draws: initialIndex }));
        localStorage.setItem(`looper-draw:${defaultId}`, JSON.stringify(typedDefaultContract));
        indexData = initialIndex;
      }

      const enrichedIndex = await enrichDrawingsWithHierarchy(indexData, mode);
      setDrawingsIndex(enrichedIndex);
      indexData = enrichedIndex;

      let improvementData: ImprovementIndexEntry[] = [];
      if (mode === 'backend') {
        try {
          const response = await fetch(`${getApiOrigin()}/.looper/improvements/index.json`, { cache: 'no-store' });
          if (response.ok) improvementData = (await response.json()).improvements || [];
        } catch (_) {}
      } else {
        try {
          improvementData = JSON.parse(localStorage.getItem('looper-improvements-index') || '{"improvements":[]}').improvements || [];
        } catch (_) {}
      }
      setImprovementsIndex(improvementData);

      // 4. Determine initial drawing to load
      const searchParams = new URLSearchParams(window.location.search);
      const requestedImprovement = searchParams.get('improvement');
      const requestedId = searchParams.get('draw');
      const improvementEntry = requestedImprovement
        ? improvementData.find((item) => item.id === requestedImprovement)
        : undefined;
      const improvementDrawExists = Boolean(improvementEntry && indexData.some((draw) => draw.id === improvementEntry.draw_id));
      if (improvementEntry && improvementDrawExists && improvementEntry.status !== 'applied') {
        await loadImprovementById(requestedImprovement!, mode);
      } else if (improvementEntry && improvementDrawExists) {
        // Sessões aplicadas são histórico, não uma tela inicial. Ao recarregar
        // uma URL antiga, retorne ao Draw associado sem reabrir a melhoria.
        searchParams.delete('improvement');
        searchParams.set('draw', improvementEntry.draw_id);
        window.history.replaceState({}, '', `${window.location.pathname}?${searchParams.toString()}`);
        await loadDrawingById(improvementEntry.draw_id, { resetNavigation: true, indexData, mode });
      } else if (requestedImprovement) {
        // Não deixe uma sessão removida ou de outro projeto bloquear o bootstrap.
        searchParams.delete('improvement');
        window.history.replaceState({}, '', `${window.location.pathname}${searchParams.toString() ? `?${searchParams.toString()}` : ''}`);
        const fallbackId = requestedId && indexData.some((draw) => draw.id === requestedId)
          ? requestedId
          : indexData[0]?.id;
        if (fallbackId) await loadDrawingById(fallbackId, { resetNavigation: true, indexData, mode });
      } else if (requestedId && indexData.some((d) => d.id === requestedId)) {
        await loadDrawingById(requestedId, { resetNavigation: true, indexData, mode });
      } else if (indexData.length > 0) {
        await loadDrawingById(indexData[0].id, { resetNavigation: true, indexData, mode });
      }
    };

    initializeApp();
  }, []);

  // --- Fetching Drawings Index ---
  const loadDrawingsIndex = async () => {
    let indexData: DrawIndexEntry[] = [];
    if (storageMode === 'backend') {
      try {
        const origin = getApiOrigin();
        const response = await fetch(`${origin}/.looper/draws/index.json`, { cache: 'no-store' });
        if (response.ok) {
          const data = await response.json();
          indexData = data.draws || [];
        }
      } catch (_) {}
    } else {
      const savedIndex = localStorage.getItem('looper-draws-index');
      if (savedIndex) {
        try {
          const data = JSON.parse(savedIndex);
          indexData = data.draws || [];
        } catch (_) {}
      }
    }
    const enrichedIndex = await enrichDrawingsWithHierarchy(indexData, storageMode);
    setDrawingsIndex(enrichedIndex);
  };

  const loadImprovementsIndex = async () => {
    let indexData: ImprovementIndexEntry[] = [];
    if (storageMode === 'backend') {
      try {
        const response = await fetch(`${getApiOrigin()}/.looper/improvements/index.json`, { cache: 'no-store' });
        if (response.ok) indexData = (await response.json()).improvements || [];
      } catch (_) {}
    } else {
      try {
        indexData = JSON.parse(localStorage.getItem('looper-improvements-index') || '{"improvements":[]}').improvements || [];
      } catch (_) {}
    }
    setImprovementsIndex(indexData);
  };

  const loadContractForSearch = async (entry: DrawIndexEntry, mode: 'backend' | 'local'): Promise<Contract | null> => {
    if (mode === 'local') {
      const saved = localStorage.getItem(`looper-draw:${entry.id}`);
      if (saved) {
        try {
          return JSON.parse(saved) as Contract;
        } catch (_) {
          // Tenta a fonte HTTP abaixo quando o cache local estiver inválido.
        }
      }
    }

    const origins = mode === 'backend'
      ? [getApiOrigin(), ...getApiOrigins()]
      : getApiOrigins();
    for (const origin of [...new Set(origins)]) {
      try {
        const response = await fetch(`${origin}/.looper/draws/${encodeURIComponent(entry.id)}.json`, { cache: 'no-store' });
        if (response.ok) return await response.json() as Contract;
      } catch (_) {
        // Um Draw indisponível não deve impedir a busca nos demais.
      }
    }

    return entry.id === typedDefaultContract.id ? typedDefaultContract : null;
  };

  useEffect(() => {
    const query = searchQuery.trim().toLocaleLowerCase();
    if (!query || currentImprovement || drawingsIndex.length === 0) {
      setSearchResults([]);
      setIsSearchLoading(false);
      return;
    }

    const requestId = searchRequestRef.current + 1;
    searchRequestRef.current = requestId;
    let cancelled = false;
    setIsSearchLoading(true);

    const searchDrawings = async () => {
      const contracts = await Promise.all(drawingsIndex.map(async (entry) => ({
        entry,
        document: await loadContractForSearch(entry, storageMode)
      })));
      if (cancelled || requestId !== searchRequestRef.current) return;

      const results: DrawSearchResult[] = [];
      contracts.forEach(({ entry, document }) => {
        if (!document) return;
        document.nodes.forEach((node) => {
          const references = Array.isArray(node.code_refs) ? node.code_refs : [];
          const associations = [...new Set([
            ...references.map((reference: any) => reference?.symbol || reference?.qualified_name || reference?.identity || ''),
            ...(Array.isArray(node.symbols) ? node.symbols : [])
          ].filter(Boolean).map(String))];
          const searchable = [
            entry.title,
            entry.subtitle,
            entry.kind,
            entry.file,
            document.title,
            document.subtitle,
            document.kind,
            node.label,
            node.description,
            node.group === undefined ? '' : String(node.group),
            ...associations,
            ...references.flatMap((reference: any) => [
              reference?.file,
              ...(Array.isArray(reference?.source_dependencies) ? reference.source_dependencies : [])
            ])
          ].filter(Boolean).join(' ').toLocaleLowerCase();

          if (searchable.includes(query)) {
            results.push({
              drawId: document.id || entry.id,
              drawTitle: document.title || entry.title,
              nodeId: node.id,
              nodeLabel: node.label,
              associations
            });
          }
        });
      });

      setSearchResults(results);
      setIsSearchLoading(false);
    };

    searchDrawings().catch(() => {
      if (!cancelled && requestId === searchRequestRef.current) {
        setSearchResults([]);
        setIsSearchLoading(false);
      }
    });

    return () => { cancelled = true; };
  }, [currentImprovement, drawingsIndex, searchQuery, storageMode]);

  // --- Load individual Drawing ---
  const loadDrawingById = async (
    id: string,
    opts?: { resetNavigation?: boolean; indexData?: DrawIndexEntry[]; mode?: 'backend' | 'local' }
  ) => {
    const requestId = drawingLoadRequestRef.current + 1;
    drawingLoadRequestRef.current = requestId;
    const isCurrentRequest = () => drawingLoadRequestRef.current === requestId;
    const activeMode = opts?.mode || storageMode;

    const clearRenderedFlow = () => {
      // Não deixe o viewport do desenho pai disputar com o fit do desenho
      // filho enquanto o React Flow troca os nós controlados.
      setRenderedDrawId(null);
      // Mantém o último frame válido até o novo contrato ser renderizado.
      // Limpar os arrays aqui podia deixar a tela vazia se a assinatura do
      // novo Draw coincidisse com a anterior.
      renderedNodesSignatureRef.current = '';
      renderedEdgesSignatureRef.current = '';
    };

    if (isDirty || isImprovementDirty) {
      const proceed = await askConfirm(
        'Descartar alterações?',
        'Existem alterações não salvas no desenho atual. Deseja descartá-las?',
        'Descartar',
        true
      );
      if (!proceed) return;
    }

    if (opts?.resetNavigation) {
      setNavigation([]);
    }

    const url = new URL(window.location.href);
    url.searchParams.set('draw', id);
    window.history.replaceState({}, '', url);

    if (activeMode === 'backend') {
      try {
        const origin = getApiOrigin();
        const response = await fetch(`${origin}/.looper/draws/${encodeURIComponent(id)}.json`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (!isCurrentRequest()) return;
        pendingAutoFitDrawRef.current = id;
        clearRenderedFlow();
        setContract(data);
        setCurrentImprovement(null);
        setPresentationPositionsForDrawing(id);
        window.currentDrawId = id;
        setIsDirty(false);
        setIsImprovementDirty(false);
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
      } catch (err: any) {
        alert(`Erro ao carregar desenho do backend: ${err.message}`);
      }
    } else {
      const saved = localStorage.getItem(`looper-draw:${id}`);
      if (saved) {
        try {
          const data = JSON.parse(saved);
          if (!isCurrentRequest()) return;
          pendingAutoFitDrawRef.current = id;
          clearRenderedFlow();
          setContract(data);
          setCurrentImprovement(null);
          setPresentationPositionsForDrawing(id);
          window.currentDrawId = id;
          setIsDirty(false);
          setIsImprovementDirty(false);
          setSelectedNodeId(null);
          setSelectedEdgeId(null);
        } catch (_) {
          alert('Erro ao carregar desenho local: JSON corrompido.');
        }
      } else if (id === typedDefaultContract.id) {
        if (!isCurrentRequest()) return;
        pendingAutoFitDrawRef.current = id;
        clearRenderedFlow();
        setContract(typedDefaultContract);
        setCurrentImprovement(null);
        setPresentationPositionsForDrawing(id);
        window.currentDrawId = id;
        setIsDirty(false);
        setIsImprovementDirty(false);
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
      } else {
        // A detecção do backend acontece de forma assíncrona. Se o usuário
        // abrir um subfluxo antes dela terminar, tente o Draw Server antes
        // de concluir que o desenho não existe no modo offline.
        for (const origin of getApiOrigins()) {
          try {
            const response = await fetch(`${origin}/.looper/draws/${encodeURIComponent(id)}.json`, { cache: 'no-store' });
            if (!response.ok) continue;
            const data = await response.json();
            if (!isCurrentRequest()) return;
            detectedBackendOrigin = origin;
            setStorageMode('backend');
            pendingAutoFitDrawRef.current = id;
            clearRenderedFlow();
            setContract(data);
            setCurrentImprovement(null);
            setPresentationPositionsForDrawing(id);
            window.currentDrawId = id;
            setIsDirty(false);
            setIsImprovementDirty(false);
            setSelectedNodeId(null);
            setSelectedEdgeId(null);
            return;
          } catch (_) {
            // Continua procurando no próximo endpoint local.
          }
        }
        alert('Desenho não encontrado no armazenamento local.');
      }
    }
  };

  // Mantém o fluxo aberto atualizado sem substituir rascunhos locais.
  useEffect(() => {
    if (storageMode !== 'backend' || currentImprovement) {
      setDrawSyncState(storageMode === 'backend' ? 'synced' : 'local');
      return;
    }

    drawRevisionRef.current = null;
    pendingExternalRevisionRef.current = null;
    let cancelled = false;
    const checkRevision = async () => {
      if (document.visibilityState === 'hidden' || cancelled || savingContractRef.current) return;
      setDrawSyncState((state) => state === 'pending' ? state : 'checking');
      try {
        const response = await fetch(
          `${getApiOrigin()}/.looper/api/draws/${encodeURIComponent(contract.id)}/revision`,
          { cache: 'no-store' }
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const revision = await response.json() as { revision?: string };
        if (!revision.revision || cancelled) return;
        if (savingContractRef.current) {
          drawRevisionRef.current = revision.revision;
          return;
        }
        if (drawRevisionRef.current === null) {
          drawRevisionRef.current = revision.revision;
          setDrawSyncState('synced');
          return;
        }
        if (revision.revision === drawRevisionRef.current) {
          if (pendingExternalRevisionRef.current && !dirtyStateRef.current.isDirty && !dirtyStateRef.current.isImprovementDirty) {
            pendingExternalRevisionRef.current = null;
            await loadDrawingById(contract.id, { mode: 'backend' });
            if (!cancelled) setDrawSyncState('synced');
          } else {
            setDrawSyncState((state) => state === 'pending' ? state : 'synced');
          }
          return;
        }
        drawRevisionRef.current = revision.revision;
        if (dirtyStateRef.current.isDirty || dirtyStateRef.current.isImprovementDirty) {
          pendingExternalRevisionRef.current = revision.revision;
          setDrawSyncState('pending');
          return;
        }
        if (pendingExternalRevisionRef.current === revision.revision) return;
        pendingExternalRevisionRef.current = revision.revision;
        await loadDrawingById(contract.id, { mode: 'backend' });
        if (!cancelled) {
          pendingExternalRevisionRef.current = null;
          setDrawSyncState('synced');
        }
      } catch (_) {
        if (!cancelled) setDrawSyncState('error');
      }
    };

    void checkRevision();
    const interval = window.setInterval(checkRevision, 2000);
    const handleVisibility = () => { if (document.visibilityState === 'visible') void checkRevision(); };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [contract.id, currentImprovement, storageMode]);

  useEffect(() => {
    if (!observerMode || currentImprovement || !backlog) return;
    const execution = backlog.execution;
    const task = currentExecutionTask(backlog, 'implementation');

    if (!task) {
      observerTargetRef.current = null;
      setObserverTarget(null);
      setObserverStatus(execution.current_phase === 'test' ? 'Aguardando implementação' : 'Nenhuma implementação em andamento');
      return;
    }

    const target = { taskId: task.id, drawId: task.draw_id, nodeId: task.node_id, label: task.label };
    const targetKey = `${target.taskId}:${target.drawId}:${target.nodeId}`;
    setObserverTarget(target);
    setObserverStatus(`Observando: ${task.label}`);
    if (observerTargetRef.current === targetKey) return;

    observerTargetRef.current = targetKey;
    observerFocusedKeyRef.current = null;
    if (contract.id !== target.drawId) {
      void loadDrawingById(target.drawId, { resetNavigation: true, mode: storageMode });
    }
  }, [backlog, contract.id, currentImprovement, observerMode, storageMode]);

  useEffect(() => {
    if (
      !observerMode ||
      !observerTarget ||
      observerTarget.drawId !== contract.id ||
      renderedDrawId !== contract.id ||
      !nodesInitialized ||
      !reactFlowInstanceRef.current
    ) return;
    const focusKey = `${observerTarget.taskId}:${observerTarget.drawId}:${observerTarget.nodeId}`;
    if (observerFocusedKeyRef.current === focusKey) return;
    const targetNode = nodes.find((node) => Number(node.id) === observerTarget.nodeId);
    if (!targetNode) return;

    selectionOrderRef.current = [observerTarget.nodeId];
    setSelectedNodeId(observerTarget.nodeId);
    setSelectedEdgeId(null);
    setIsFocusMode(false);
    setSelectionRevision((value) => value + 1);

    // O alvo só é considerado focado depois que a instância e as dimensões
    // reais do nó estão disponíveis. Assim a troca de draw não perde o zoom
    // por ocorrer durante a desmontagem do fluxo anterior.
    const frame = requestAnimationFrame(() => {
      const instance = reactFlowInstanceRef.current;
      if (!instance) return;
      instance.fitView({
        nodes: [{ id: String(targetNode.id) }],
        padding: 0.42,
        minZoom: 0.85,
        maxZoom: 1.8,
        duration: 650
      });
      observerFocusedKeyRef.current = focusKey;
    });

    return () => cancelAnimationFrame(frame);
  }, [contract.id, nodes, nodesInitialized, observerMode, observerTarget, reactFlowReady, renderedDrawId]);

  const loadImprovementById = async (id: string, mode = storageMode) => {
    if (isDirty || isImprovementDirty) {
      const proceed = await askConfirm(
        'Descartar alterações?',
        'Existem respostas ou alterações não salvas. Deseja descartá-las?',
        'Descartar',
        true
      );
      if (!proceed) return;
    }

    try {
      let session: ImprovementSession | null = null;
      if (mode === 'backend') {
        const response = await fetch(`${getApiOrigin()}/.looper/improvements/${encodeURIComponent(id)}.json`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        session = await response.json() as ImprovementSession;
      } else {
        const saved = localStorage.getItem(`looper-improvement:${id}`);
        if (saved) session = JSON.parse(saved) as ImprovementSession;
      }
      if (!session) throw new Error('sessão não encontrada');
      setCurrentImprovement(session);
      // A sessão de melhoria abre diretamente nas perguntas; o botão do topo
      // continua disponível apenas como atalho para reabrir o editor.
      setShowImprovementModal(true);
      setIsDirty(false);
      setIsImprovementDirty(false);
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      setNavigation([]);
      const url = new URL(window.location.href);
      url.searchParams.delete('draw');
      url.searchParams.set('improvement', id);
      window.history.replaceState({}, '', url);
    } catch (err: any) {
      alert(`Erro ao carregar sessão de melhoria: ${err.message}`);
    }
  };

  // --- Save Logic & Strip Presentation Details from Logical JSON ---
  const cleanLogicalPayload = (payload: Contract): Contract => {
    const doc = JSON.parse(JSON.stringify(payload));
    delete doc.isHighlighted;
    delete doc.isDimmed;
    // Migração de Draws antigos: decisões legadas nunca reaparecem no JSON salvo.
    delete doc.tradeoffs;
    
    doc.nodes = doc.nodes.map((node: any) => {
      const cleanNode = { ...node };
      delete cleanNode.isHighlighted;
      delete cleanNode.isDimmed;
      delete cleanNode.background;
      delete cleanNode.text;
      delete cleanNode.type;
      return cleanNode;
    });

    doc.edges = doc.edges.map((edge: any) => {
      const cleanEdge = { ...edge };
      delete cleanEdge.isHighlighted;
      delete cleanEdge.isDimmed;
      return cleanEdge;
    });

    return doc;
  };

  const performSave = async (contractToSave: Contract): Promise<boolean> => {
    const id = contractToSave.id;
    const cleanPayload = cleanLogicalPayload(contractToSave);
    const presentationKey = `looper-draw-presentation:${id}`;
    try {
      const saved = localStorage.getItem(presentationKey);
      const presentation = saved ? JSON.parse(saved) : {};
      presentation.positions = presentationPositionsRef.current;
      localStorage.setItem(presentationKey, JSON.stringify(presentation));
    } catch (_) {}

    if (storageMode === 'backend') {
      try {
        const origin = getApiOrigin();
        const response = await fetch(`${origin}/__looper/api/draws/${encodeURIComponent(id)}.json`, {
          method: 'PUT',
          // O editor precisa conseguir persistir estados intermediários. A
          // API ainda valida o schema e todas as referências; somente a
          // conectividade pode ficar pendente até a próxima edição.
          headers: { 'Content-Type': 'application/json', 'X-Looper-Editor-Draft': 'true' },
          body: JSON.stringify(cleanPayload)
        });
        if (!response.ok) {
          const result = await response.json().catch(() => ({}));
          throw new Error(result.error || `HTTP ${response.status}`);
        }
        setIsDirty(false);
        await loadDrawingsIndex();
        return true;
      } catch (err: any) {
        alert(`Erro ao salvar no backend: ${err.message}`);
        return false;
      }
    } else {
      // Local Storage
      const savedLogicalPayload = localStorage.getItem(`looper-draw:${id}`);
      if (savedLogicalPayload) {
        try {
          if (JSON.stringify(JSON.parse(savedLogicalPayload)) === JSON.stringify(cleanPayload)) {
            setIsDirty(false);
            return true;
          }
        } catch (_) {}
      }
      localStorage.setItem(`looper-draw:${id}`, JSON.stringify(cleanPayload));
      
      // Update index
      const timestamp = new Date().toISOString();
      const drawings = [...drawingsIndex];
      const existingIdx = drawings.findIndex((d) => d.id === id);
      const metadata = {
        id,
        file: `${id}.json`,
        title: contractToSave.title,
        subtitle: contractToSave.subtitle || '',
        kind: contractToSave.kind,
        updated_at: timestamp,
        node_count: contractToSave.nodes.length,
        edge_count: contractToSave.edges.length,
        subdraw_count: contractToSave.nodes.reduce((total, n) => total + (n.draw_refs?.length || (n.draw_ref ? 1 : 0)), 0),
        hierarchy: contractToSave.hierarchy
      };

      if (existingIdx >= 0) {
        drawings[existingIdx] = metadata;
      } else {
        drawings.push(metadata);
      }

      drawings.sort((a, b) => a.title.localeCompare(b.title));
      localStorage.setItem('looper-draws-index', JSON.stringify({ version: 1, draws: drawings }));
      setDrawingsIndex(drawings);
      setIsDirty(false);
      return true;
    }
  };

  const handleSave = () => {
    performSave(contract);
  };

  const performImprovementSave = async () => {
    if (!currentImprovement || currentImprovement.status === 'applied') return;
    const isAnswered = (answer: ImprovementSession['questions'][number]['answer']) =>
      answer !== null && !(typeof answer === 'string' && answer.trim() === '');
    const nextStatus: ImprovementSession['status'] = currentImprovement.questions.every((question) => isAnswered(question.answer)) ? 'ready' : 'draft';
    if (!isImprovementDirty && nextStatus === currentImprovement.status) return;
    const payload: ImprovementSession = { ...currentImprovement, status: nextStatus };

    if (storageMode === 'backend') {
      try {
        const response = await fetch(`${getApiOrigin()}/__looper/api/improvements/${encodeURIComponent(payload.id)}.json`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!response.ok) {
          const result = await response.json().catch(() => ({}));
          throw new Error(result.error || `HTTP ${response.status}`);
        }
        const refreshed = await fetch(`${getApiOrigin()}/.looper/improvements/${encodeURIComponent(payload.id)}.json`, { cache: 'no-store' });
        if (refreshed.ok) setCurrentImprovement(await refreshed.json() as ImprovementSession);
        setIsImprovementDirty(false);
        await loadImprovementsIndex();
      } catch (err: any) {
        alert(`Erro ao salvar sessão de melhoria: ${err.message}`);
      }
      return;
    }

    const timestamp = new Date().toISOString();
    const savedPayload = { ...payload, updated_at: timestamp };
    localStorage.setItem(`looper-improvement:${payload.id}`, JSON.stringify(savedPayload));
    const nextIndex: ImprovementIndexEntry = {
      id: payload.id,
      file: `${payload.id}.json`,
      title: payload.title,
      draw_id: payload.draw_id,
      status: payload.status,
      answered_count: payload.questions.filter((question) => isAnswered(question.answer)).length,
      question_count: payload.questions.length,
      updated_at: timestamp
    };
    const updatedIndex = [...improvementsIndex.filter((item) => item.id !== payload.id), nextIndex];
    updatedIndex.sort((left, right) => left.title.localeCompare(right.title));
    localStorage.setItem('looper-improvements-index', JSON.stringify({ version: 1, improvements: updatedIndex }));
    setCurrentImprovement(savedPayload);
    setImprovementsIndex(updatedIndex);
    setIsImprovementDirty(false);
  };

  const handleSaveAll = async () => {
    await performSave(contract);
    await performImprovementSave();
  };

  const handleImprovementAnswer = (questionId: number, answer: string | boolean | number | null) => {
    setCurrentImprovement((previous) => previous ? {
      ...previous,
      questions: previous.questions.map((question) => question.id === questionId ? { ...question, answer } : question)
    } : previous);
    setIsImprovementDirty(true);
  };

  // --- New Drawing Creation ---
  const slugify = (text: string) => {
    return text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'novo-desenho';
  };

  const handleCreateDrawing = async (title: string, subtitle: string, kind: string) => {
    const baseId = slugify(title);
    let newId = baseId;
    let suffix = 2;
    const isIdUsed = (id: string) => drawingsIndex.some((d) => d.id === id);
    while (isIdUsed(newId)) {
      newId = `${baseId}-${suffix}`;
      suffix++;
    }

    const newContract: Contract = {
      version: 1,
      id: newId,
      title,
      subtitle,
      kind,
      groups: [],
      nodes: [],
      edges: [],
      flows: []
    };

    setContract(newContract);
    presentationPositionsRef.current = {};
    setPresentationPositionsState({});
    window.currentDrawId = newId;
    setNodes([]);
    setEdges([]);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setActiveFlowId(null);
    
    // Save to trigger index addition
    await performSave(newContract);
  };

  // --- Subdraw Navigation ---
  const findParentNavigationOptions = async (childId: string): Promise<ParentNavigationOption[]> => {
    const options: ParentNavigationOption[] = [];
    const seen = new Set<string>();
    const addOption = (option: ParentNavigationOption) => {
      const key = `${option.drawId}:${option.nodeId ?? 'draw'}`;
      if (option.drawId === childId || seen.has(key)) return;
      seen.add(key);
      options.push(option);
    };

    const entries = drawingsIndex.filter((entry) => entry.id !== childId);
    const documents = await Promise.all(entries.map(async (entry) => ({
      entry,
      document: await loadContractForSearch(entry, storageMode)
    })));

    documents.forEach(({ entry, document }) => {
      document?.nodes.forEach((node) => {
        if (node.draw_ref !== childId) return;
        addOption({
          drawId: entry.id,
          title: entry.title || entry.id,
          nodeId: node.id,
          nodeLabel: node.label || `Nó ${node.id}`,
          level: entry.hierarchy?.level
        });
      });
    });

    const hierarchyParentId = contract.hierarchy?.parent_draw_ref;
    if (hierarchyParentId) {
      const hierarchyParentEntry = drawingsIndex.find((entry) => entry.id === hierarchyParentId);
      const hierarchyParentDocument = documents.find(({ entry }) => entry.id === hierarchyParentId)?.document
        || (hierarchyParentEntry ? await loadContractForSearch(hierarchyParentEntry, storageMode) : null);
      const hierarchyParentNodeId = contract.hierarchy?.parent_node_id ?? null;
      const hierarchyParentNode = hierarchyParentDocument?.nodes.find((node) => node.id === hierarchyParentNodeId);
      addOption({
        drawId: hierarchyParentId,
        title: hierarchyParentEntry?.title || hierarchyParentId,
        nodeId: hierarchyParentNodeId,
        nodeLabel: hierarchyParentNode?.label || (hierarchyParentNodeId === null ? 'Desenho pai' : `Nó ${hierarchyParentNodeId}`),
        level: hierarchyParentEntry?.hierarchy?.level
      });
    }

    const historyParentId = navigation[navigation.length - 1];
    if (historyParentId && !options.some((option) => option.drawId === historyParentId)) {
      const historyParentEntry = drawingsIndex.find((entry) => entry.id === historyParentId);
      addOption({
        drawId: historyParentId,
        title: historyParentEntry?.title || historyParentId,
        nodeId: null,
        nodeLabel: 'Desenho pai',
        level: historyParentEntry?.hierarchy?.level
      });
    }

    return options;
  };

  const navigateToParent = (option: ParentNavigationOption) => {
    setParentNavigationOptions(null);
    const visitedParentIndex = navigation.lastIndexOf(option.drawId);
    setNavigation((prev) => visitedParentIndex >= 0 ? prev.slice(0, visitedParentIndex) : []);
    if (option.nodeId !== null) {
      pendingSearchFocusRef.current = { drawId: option.drawId, nodeId: option.nodeId };
    }
    loadDrawingById(option.drawId);
  };

  const handleGoBack = async () => {
    if (currentImprovement || isParentNavigationLoading) return;
    setIsParentNavigationLoading(true);
    try {
      const options = await findParentNavigationOptions(contract.id);
      if (options.length === 0) return;
      if (options.length === 1) {
        navigateToParent(options[0]);
      } else {
        setParentNavigationOptions(options);
      }
    } finally {
      setIsParentNavigationLoading(false);
    }
  };

  // --- Node & Edge Mappings ---
  const presentationPositions = useMemo(() => {
    const presentationKey = `looper-draw-presentation:${contract.id}`;
    try {
      const saved = localStorage.getItem(presentationKey);
      if (saved) {
        return { ...(JSON.parse(saved).positions || {}), ...presentationPositionsState };
      }
    } catch (_) {}
    return presentationPositionsState;
  }, [contract.id, isDirty, presentationPositionsState]);
  const cycleEdges = useMemo(() => getCycleEdges(contract.nodes, contract.edges), [contract.nodes, contract.edges]);

  useEffect(() => {
    let activeNodeIds = new Set<number>();
    let activeEdgeConnections = new Set<string>();

    if (activeFlowId !== null && contract.flows) {
      const activeFlow = contract.flows.find((f) => f.id === activeFlowId);
      if (activeFlow && activeFlow.steps.length > 0) {
        activeFlow.steps.forEach((step) => activeNodeIds.add(step.node));
        for (let i = 0; i < activeFlow.steps.length - 1; i++) {
          activeEdgeConnections.add(
            `${activeFlow.steps[i].node}->${activeFlow.steps[i + 1].node}`
          );
        }
      }
    }

    // Nodes highlighting/dimming based on selectedNodeId (Predecessors & Successors)
    const hasSelection = selectedNodeId !== null && isFocusMode;
    const hasMultiSelection = selectionOrderRef.current.length > 1;
    let connectedNodeIds = new Set<number>();
    if (hasSelection && selectedNodeId !== null) {
      connectedNodeIds.add(selectedNodeId);
      contract.edges.forEach((edge) => {
        if (edge.from === selectedNodeId) {
          connectedNodeIds.add(edge.to);
        }
        if (edge.to === selectedNodeId) {
          connectedNodeIds.add(edge.from);
        }
      });
    }

    const filteredNodes = contract.nodes.map((node) => {
      const inPath = activeFlowId !== null && activeNodeIds.has(node.id);
      let isDimmed = activeFlowId !== null && !inPath;
      let isHighlighted = activeFlowId !== null && inPath;
      const backlogTask = backlog?.tasks.find((task) => task.draw_id === contract.id && task.node_id === node.id);

      if (hasSelection && !hasMultiSelection) {
        if (connectedNodeIds.has(node.id)) {
          isDimmed = false;
        } else {
          isDimmed = true;
        }
      }

      return {
        ...node,
        groupOptions: contract.groups,
        theme,
        isHighlighted,
        isDimmed,
        backlogChecklist: backlogTask ? {
          taskId: backlogTask.id,
          test: backlogTask.checklist_state?.test === true,
          implementation: backlogTask.checklist_state?.implementation === true,
          status: backlogTask.status
        } : undefined
      };
    });

    const formattedNodes = layoutCurvedGraph(filteredNodes, contract.edges, presentationPositions);
    const selectedNodeIds = new Set(selectionOrderRef.current);
    const nodesWithSelection = formattedNodes.map((node) => ({
      ...node,
      selected: selectedNodeIds.has(Number(node.id))
    }));
    const nextNodesSignature = nodesWithSelection.map((node) => (
      `${contract.id}:${node.id}:${node.position.x}:${node.position.y}:${node.selected ? 1 : 0}:${node.data.isHighlighted ? 1 : 0}:${node.data.isDimmed ? 1 : 0}:${node.data.backlogChecklist?.status || ''}`
    )).join('|');
    if (renderedNodesSignatureRef.current !== nextNodesSignature) {
      renderedNodesSignatureRef.current = nextNodesSignature;
      setNodes(nodesWithSelection);
    }
    setRenderedDrawId(contract.id);
    if (pendingAutoFitDrawRef.current === contract.id) {
      pendingAutoFitDrawRef.current = null;
      setAutoFitRevision((value) => value + 1);
    }

    const positions = Object.fromEntries(
      nodesWithSelection.map((n) => [n.id, n.position])
    );

    const formattedEdges = contract.edges.map((edge) => {
      const sourceActive = activeNodeIds.has(edge.from);
      const targetActive = activeNodeIds.has(edge.to);
      const isHighlighted =
        activeFlowId !== null &&
        sourceActive &&
        targetActive &&
        activeEdgeConnections.has(`${edge.from}->${edge.to}`);
      let isDimmed = activeFlowId !== null && !isHighlighted;

      if (hasSelection && !hasMultiSelection) {
        if (edge.from === selectedNodeId || edge.to === selectedNodeId) {
          isDimmed = false;
        } else {
          isDimmed = true;
        }
      }

      const edgeHandles = computeEdgeHandles(edge, positions, contract.nodes, contract.edges, cycleEdges);
      const condition = Number(edge.condition) || DEFAULT_CONDITION;
      
      const visual =
        {
          1: { color: theme === 'light' ? '#1e293b' : '#94a3b8', edgeStroke: THEN_EDGE_GRADIENT, markerColor: THEN_EDGE_MARKER_COLOR, dash: undefined },
          2: { color: '#22c55e', edgeStroke: '#22c55e', markerColor: '#22c55e', dash: '8 6' },
          3: { color: '#059669', edgeStroke: '#059669', markerColor: '#059669', dash: '3 6' }
        }[condition] || { color: '#1e293b', edgeStroke: '#1e293b', markerColor: '#1e293b', dash: undefined };

      const connectsSelection = hasSelection && !hasMultiSelection && (edge.from === selectedNodeId || edge.to === selectedNodeId);

      return {
        id: String(edge.id),
        source: String(edge.from),
        target: String(edge.to),
        type: edgeHandles.loop ? 'loop' : 'default',
        pathOptions: edgeHandles.loop ? undefined : { borderRadius: 14, offset: 20 },
        animated: isHighlighted || connectsSelection || edge.kind === 'flow',
        sourceHandle: edgeHandles.loop ? edgeHandles.sourceHandle : `source-${condition}-right`,
        targetHandle: edgeHandles.targetHandle,
        label: `${
          { 1: 'então', 2: 'ou', 3: 'se' }[condition]
        }${edge.label ? ` - ${edge.label}` : ''}`,
        data: { ...edge, labelColor: visual.color, markerColor: isHighlighted ? '#10b981' : visual.markerColor },
        style: {
          stroke: isHighlighted ? '#10b981' : visual.edgeStroke,
          strokeWidth: isHighlighted ? 3.5 : (connectsSelection ? 2.5 : 2),
          strokeDasharray: visual.dash,
          opacity: isDimmed ? 0.03 : 1
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isHighlighted ? '#10b981' : visual.markerColor,
          width: 28,
          height: 28
        },
        labelStyle: {
          fill: isHighlighted
            ? '#10b981'
            : theme === 'light'
            ? visual.color
            : '#e2e8f0',
          fontWeight: 800,
          fontSize: 10,
          opacity: isDimmed ? 0.03 : 1
        },
        labelBgStyle: {
          fill: theme === 'light' ? '#ffffff' : '#0f172a',
          fillOpacity: isDimmed ? 0.03 : 0.95,
          stroke: isHighlighted ? '#10b981' : visual.color,
          strokeWidth: 1,
          opacity: isDimmed ? 0.03 : 1
        },
        labelBgPadding: [6, 4] as [number, number],
        labelBgBorderRadius: 6
      };
    });

    const nextEdgesSignature = formattedEdges.map((edge) => (
      `${contract.id}:${edge.id}:${edge.source}:${edge.target}:${edge.animated ? 1 : 0}:${edge.style?.opacity || 1}:${edge.data?.labelColor || ''}`
    )).join('|');
    if (renderedEdgesSignatureRef.current !== nextEdgesSignature) {
      renderedEdgesSignatureRef.current = nextEdgesSignature;
      setEdges(formattedEdges);
    }
  }, [backlog, contract, activeFlowId, presentationPositions, theme, selectedNodeId, isFocusMode, selectionRevision, cycleEdges]);

  useEffect(() => {
    if (
      !reactFlowInstanceRef.current ||
      !nodesInitialized ||
      nodes.length === 0 ||
      !flowNodeSignature ||
      renderedDrawId !== contract.id ||
      flowNodeSignature !== contractNodeSignature
    ) return;
    if (pendingSearchFocusRef.current?.drawId === contract.id) return;
    const fitKey = `${contract.id}:${contractNodeSignature}:${autoFitRevision}`;
    if (lastAutoFitKeyRef.current === fitKey) return;
    lastAutoFitKeyRef.current = fitKey;

    let secondFrame: number | null = null;
    const frame = requestAnimationFrame(() => {
      // O primeiro frame aplica os nós no store interno; o segundo garante
      // que as dimensões dos CustomNodes já estejam disponíveis ao fitView.
      secondFrame = requestAnimationFrame(() => {
        reactFlowInstanceRef.current?.fitView({
          nodes: contract.nodes.map((node) => ({ id: String(node.id) })),
          includeHiddenNodes: true,
          duration: 450,
          padding: 0.22,
          maxZoom: 1.25
        });
      });
    });

    return () => {
      cancelAnimationFrame(frame);
      if (secondFrame !== null) cancelAnimationFrame(secondFrame);
    };
  }, [autoFitRevision, contract.id, contract.nodes, contractNodeSignature, flowNodeSignature, nodes.length, nodesInitialized, reactFlowReady, renderedDrawId]);

  useEffect(() => {
    const request = pendingSearchFocusRef.current;
    if (!request || request.drawId !== contract.id || !nodes.some((node) => Number(node.id) === request.nodeId)) return;

    pendingSearchFocusRef.current = null;
    selectionOrderRef.current = [request.nodeId];
    setSelectedNodeId(request.nodeId);
    setSelectedEdgeId(null);
    setIsFocusMode(false);

    requestAnimationFrame(() => {
      reactFlowInstanceRef.current?.fitView({
        nodes: [{ id: String(request.nodeId) }],
        duration: 450,
        padding: 0.35,
        maxZoom: 1.6
      });
    });
  }, [contract.id, nodes, reactFlowReady, selectionRevision]);

  const focusSearchResult = async (result: DrawSearchResult) => {
    pendingSearchFocusRef.current = { drawId: result.drawId, nodeId: result.nodeId };
    setSelectionRevision((value) => value + 1);

    if (contractRef.current.id !== result.drawId) {
      await loadDrawingById(result.drawId, { resetNavigation: true });
    }
  };

  // --- Callbacks on Canvas Actions ---
  const getOrderedSelectedNodeIds = useCallback(() => {
    const availableIds = new Set(contract.nodes.map((node) => node.id));
    const ordered = selectionOrderRef.current.filter((id) => availableIds.has(id));
    if (ordered.length > 0) return ordered;

    const selectedIds = new Set(nodes.filter((node) => node.selected).map((node) => Number(node.id)));
    const reactFlowOrder = selectionOrderRef.current.filter((id) => selectedIds.has(id));
    nodes.forEach((node) => {
      const id = Number(node.id);
      if (node.selected && !reactFlowOrder.includes(id)) reactFlowOrder.push(id);
    });
    if (reactFlowOrder.length === 0 && selectedNodeId !== null) reactFlowOrder.push(selectedNodeId);
    return reactFlowOrder;
  }, [contract.nodes, nodes, selectedNodeId]);

  const onSelectionChange = useCallback((selection: { nodes: Node[] }) => {
    const availableIds = new Set(contract.nodes.map((node) => node.id));
    const selectedIds = [...new Set(selection.nodes.map((node) => Number(node.id)).filter((id) => availableIds.has(id)))];
    const selectedSet = new Set(selectedIds);
    const ordered = selectionOrderRef.current.filter((id) => selectedSet.has(id));
    selectedIds.forEach((id) => {
      if (!ordered.includes(id)) ordered.push(id);
    });
    selectionOrderRef.current = ordered;
    setSelectedNodeId(ordered[0] ?? null);
    if (ordered.length > 0) setSelectedEdgeId(null);
    setSelectionRevision((value) => value + 1);
  }, [contract.nodes]);

  const onNodeClick = (event: React.MouseEvent, node: Node) => {
    const id = Number(node.id);
    if (event.altKey) {
      event.preventDefault();
      setActiveDetailNodeId(id);
      return;
    }
    const isMultiSelect = event.shiftKey;
    setIsFocusMode((event.ctrlKey || event.metaKey) && !isMultiSelect);
    if (!isMultiSelect) {
      selectionOrderRef.current = [id];
    } else {
      const currentSelection = selectionOrderRef.current.length > 0
        ? selectionOrderRef.current
        : selectedNodeId !== null
          ? [selectedNodeId]
          : [];
      selectionOrderRef.current = currentSelection.includes(id)
        ? currentSelection.filter((selectedId) => selectedId !== id)
        : [...currentSelection, id];
    }
    setSelectedNodeId(selectionOrderRef.current[0] ?? null);
    setSelectedEdgeId(null);
    setSelectionRevision((value) => value + 1);
  };

  const onEdgeClick = (_: any, edge: Edge) => {
    setSelectedEdgeId(Number(edge.id));
    setSelectedNodeId(null);
    setIsFocusMode(false);
  };

  const onEdgeDoubleClick = (_event: React.MouseEvent, edge: Edge) => {
    setSelectedEdgeId(Number(edge.id));
    setSelectedNodeId(null);
    selectionOrderRef.current = [];
    setIsFocusMode(false);
    setSelectionRevision((value) => value + 1);
    window.dispatchEvent(new Event('looper:edit-edge'));
  };

  const onPaneClick = () => {
    window.dispatchEvent(new Event('looper:clear-node-editing'));
    selectionOrderRef.current = [];
    // React Flow mantém `selected` dentro do array controlado de nós. Limpar
    // apenas a ordem local deixa a seleção visual reaparecer no próximo
    // `onSelectionChange`, especialmente depois de uma seleção com Shift.
    setNodes((currentNodes) => currentNodes.map((node) => (
      node.selected ? { ...node, selected: false } : node
    )));
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setIsFocusMode(false);
    setSelectionRevision((value) => value + 1);
  };

  const handleEdgesChange = useCallback((changes: EdgeChange[]) => {
    const removedIds = changes
      .filter((change) => change.type === 'remove')
      .map((change) => Number(change.id));
    if (removedIds.length > 0) {
      setContract((prev) => ({
        ...prev,
        edges: prev.edges.filter((edge) => !removedIds.includes(edge.id))
      }));
      setIsDirty(true);
    }
    onEdgesChange(changes);
  }, [onEdgesChange]);

  const removeNodesFromContract = useCallback((previous: Contract, deleted: Set<number>): Contract => ({
    ...previous,
    nodes: previous.nodes.filter((node) => !deleted.has(node.id)),
    edges: previous.edges.filter((edge) => !deleted.has(edge.from) && !deleted.has(edge.to)),
    flows: previous.flows?.map((flow) => ({
      ...flow,
      steps: flow.steps.filter((step) => !deleted.has(step.node))
    }))
  }), []);

  const deleteSelectedItems = useCallback(() => {
    const selectedIds = getOrderedSelectedNodeIds();
    if (selectedIds.length > 0) {
      const deleted = new Set(selectedIds);
      setContract((prev) => removeNodesFromContract(prev, deleted));
      const remainingPositions = { ...presentationPositionsRef.current };
      selectedIds.forEach((id) => delete remainingPositions[String(id)]);
      presentationPositionsRef.current = remainingPositions;
      setPresentationPositionsState(remainingPositions);
      selectionOrderRef.current = [];
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      setSelectionRevision((value) => value + 1);
      setIsDirty(true);
      return true;
    }
    if (selectedEdgeId !== null) {
      const edgeId = selectedEdgeId;
      setContract((prev) => ({ ...prev, edges: prev.edges.filter((edge) => edge.id !== edgeId) }));
      setSelectedEdgeId(null);
      setIsDirty(true);
      return true;
    }
    return false;
  }, [getOrderedSelectedNodeIds, removeNodesFromContract, selectedEdgeId]);

  const connectSelectedNodes = useCallback((condition: number) => {
    const ordered = getOrderedSelectedNodeIds();
    if (ordered.length < 2) return;
    const sourceId = ordered[0];
    const targetIds = ordered.slice(1).filter((id) => id !== sourceId);
    if (targetIds.length === 0) return;

    setContract((prev) => {
      let nextEdgeId = prev.edges.length ? Math.max(...prev.edges.map((edge) => edge.id)) + 1 : 1;
      const nextEdges = [...prev.edges];
      targetIds.forEach((targetId) => {
        const existing = nextEdges.find((edge) => edge.from === sourceId && edge.to === targetId);
        if (existing) {
          existing.condition = condition;
          return;
        }
        nextEdges.push({
          id: nextEdgeId++,
          from: sourceId,
          to: targetId,
          kind: 'flow',
          condition,
          label: '',
          description: ''
        });
      });
      return { ...prev, edges: nextEdges };
    });
    setIsDirty(true);
  }, [getOrderedSelectedNodeIds]);

  const duplicateSelectedNodes = useCallback(() => {
    const selectedIds = getOrderedSelectedNodeIds();
    if (selectedIds.length === 0) return;

    setContract((prev) => {
      const selected = prev.nodes.filter((node) => selectedIds.includes(node.id));
      const nextIdStart = prev.nodes.length ? Math.max(...prev.nodes.map((node) => node.id)) + 1 : 1;
      const idMap = new Map<number, number>();
      selected.forEach((node, index) => idMap.set(node.id, nextIdStart + index));
      const copies = selected.map((node) => ({
        ...JSON.parse(JSON.stringify(node)),
        id: idMap.get(node.id),
        label: `${node.label} (cópia)`
      }));
      const copiedEdges = prev.edges
        .filter((edge) => idMap.has(edge.from) && idMap.has(edge.to))
        .map((edge) => ({
          ...JSON.parse(JSON.stringify(edge)),
          id: 0,
          from: idMap.get(edge.from),
          to: idMap.get(edge.to)
        }));
      let nextEdgeId = prev.edges.length ? Math.max(...prev.edges.map((edge) => edge.id)) + 1 : 1;
      copiedEdges.forEach((edge) => { edge.id = nextEdgeId++; });
      selectionOrderRef.current = copies.map((node) => node.id);
      setSelectedNodeId(copies[0]?.id ?? null);
      return { ...prev, nodes: [...prev.nodes, ...copies], edges: [...prev.edges, ...copiedEdges] };
    });
    setIsDirty(true);
  }, [getOrderedSelectedNodeIds]);

  const copySelectedNodesAsJson = useCallback(async (selectedIds: number[]) => {
    const selectedNodes = contractRef.current.nodes.filter((node) => selectedIds.includes(node.id));
    if (selectedNodes.length === 0) return;

    const payload = selectedNodes.length === 1 ? selectedNodes[0] : selectedNodes;
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    } catch (error: any) {
      alert(`Não foi possível copiar o JSON do nó: ${error.message}`);
    }
  }, []);

  const pasteNodesFromJsonClipboard = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      const pastedNodes = parseClipboardNodeJson(text);
      setContract((prev) => {
        const nextIdStart = prev.nodes.length
          ? Math.max(...prev.nodes.map((node) => node.id)) + 1
          : 1;
        const copies = pastedNodes.map((node, index) => ({
          ...node,
          id: nextIdStart + index
        }));
        selectionOrderRef.current = copies.map((node) => node.id);
        setSelectedNodeId(copies[0]?.id ?? null);
        setSelectedEdgeId(null);
        setIsFocusMode(false);
        setSelectionRevision((value) => value + 1);
        return { ...prev, nodes: [...prev.nodes, ...copies] };
      });
      setIsDirty(true);
    } catch (error: any) {
      alert(`Não foi possível colar o JSON do nó: ${error.message}`);
    }
  }, []);

  const createInstantNode = useCallback(() => {
    const nextNodeId = contractRef.current.nodes.length
      ? Math.max(...contractRef.current.nodes.map((node) => node.id)) + 1
      : 1;
    const newNode: NodeData = {
      id: nextNodeId,
      label: `Novo bloco ${nextNodeId}`,
      description: 'Bloco criado pelo atalho de espaço.',
      questions: []
    };

    setContract((prev) => ({ ...prev, nodes: [...prev.nodes, newNode] }));
    selectionOrderRef.current = [nextNodeId];
    setSelectedNodeId(nextNodeId);
    setSelectedEdgeId(null);
    setIsFocusMode(false);
    setSelectionRevision((value) => value + 1);
    setIsDirty(true);
  }, []);

  useEffect(() => {
    const isEditableTarget = (target: EventTarget | null) => {
      const element = target as HTMLElement | null;
      return element?.tagName === 'INPUT' || element?.tagName === 'TEXTAREA' || element?.isContentEditable;
    };

    const handleKeyboardShortcuts = (event: KeyboardEvent) => {
      if (observerMode) return;
      if (isEditableTarget(event.target)) return;
      const key = event.key.toLowerCase();
      const modifier = event.metaKey || event.ctrlKey;

      if (!modifier && !event.altKey && !event.shiftKey && key === 'v') {
        const selectedNode = selectedNodeId === null
          ? null
          : contractRef.current.nodes.find((node) => node.id === selectedNodeId);
        if (selectedNode) {
          event.preventDefault();
          window.openQuestionsModal?.(selectedNode);
        }
        return;
      }

      if (modifier && key === 'c') {
        const selectedIds = getOrderedSelectedNodeIds();
        if (selectedIds.length > 0) {
          event.preventDefault();
          void copySelectedNodesAsJson(selectedIds);
        }
        return;
      }

      if (modifier && key === 'v') {
        event.preventDefault();
        void pasteNodesFromJsonClipboard();
        return;
      }

      if (!modifier && !event.altKey && (key === 'delete' || key === 'backspace')) {
        if (deleteSelectedItems()) event.preventDefault();
        return;
      }

      if (!modifier && !event.altKey && !event.shiftKey && event.code === 'Space') {
        event.preventDefault();
        createInstantNode();
        return;
      }

      if (modifier && key === 'z') {
        event.preventDefault();
        const previous = contractHistoryRef.current.pop();
        if (!previous) return;
        skipHistoryRef.current = true;
        setContract(previous);
        setIsDirty(true);
        return;
      }

      if (modifier && key === 'd') {
        event.preventDefault();
        duplicateSelectedNodes();
        return;
      }

      if (!modifier && !event.altKey && !event.shiftKey) {
        const conditions: Record<string, number> = { z: 1, x: 2, c: 3 };
        if (conditions[key]) {
          event.preventDefault();
          connectSelectedNodes(conditions[key]);
        }
      }
    };

    window.addEventListener('keydown', handleKeyboardShortcuts);
    return () => window.removeEventListener('keydown', handleKeyboardShortcuts);
  }, [connectSelectedNodes, copySelectedNodesAsJson, createInstantNode, deleteSelectedItems, duplicateSelectedNodes, getOrderedSelectedNodeIds, observerMode, pasteNodesFromJsonClipboard, selectedNodeId]);

  const onConnect = useCallback(
    (params: Connection) => {
      const source = Number(params.source);
      const target = Number(params.target);
      const nodeIds = new Set(contractRef.current.nodes.map((node) => node.id));
      if (!Number.isInteger(source) || !Number.isInteger(target) || !nodeIds.has(source) || !nodeIds.has(target)) return;
      let condition = DEFAULT_CONDITION;
      if (params.sourceHandle) {
        const parts = params.sourceHandle.split('-');
        if (parts.length >= 2) {
          const parsed = Number(parts[1]);
          if (!isNaN(parsed)) condition = parsed;
        }
      }

      setContract((prev) => {
        const nextId = prev.edges.length
          ? Math.max(...prev.edges.map((e) => e.id)) + 1
          : 1;
        const newEdge: EdgeData = {
          id: nextId,
          from: source,
          to: target,
          kind: 'flow',
          condition,
          label: '',
          description: ''
        };
        return {
          ...prev,
          edges: [...prev.edges, newEdge]
        };
      });
      setIsDirty(true);
    },
    [setContract]
  );

  const onNodeDragStop = useCallback(
    (_: any, node: Node) => {
      if (!Number.isFinite(node.position.x) || !Number.isFinite(node.position.y)) return;
      const presentationKey = `looper-draw-presentation:${contractRef.current.id}`;
      let parsed = { positions: {} as { [key: string]: { x: number; y: number } }, nodes: {} as any };
      try {
        const saved = localStorage.getItem(presentationKey);
        if (saved) parsed = JSON.parse(saved);
      } catch (_) {}

      const nextPositions = {
        ...parsed.positions,
        ...presentationPositionsRef.current,
        [String(node.id)]: node.position
      };
      presentationPositionsRef.current = nextPositions;
      setPresentationPositionsState(nextPositions);
      parsed.positions = nextPositions;
      localStorage.setItem(presentationKey, JSON.stringify(parsed));
    },
    []
  );

  // --- Exposed Window Functions for Nodes ---
  useEffect(() => {
    window.openNodeEditModal = (node: NodeData) => {
      setEditNodeData(node);
    };

    window.updateNodeField = (id: number, field: 'label' | 'description' | 'success_criteria' | 'failure_criteria', value: string) => {
      setContract((prev) => ({
        ...prev,
        nodes: prev.nodes.map((n) => (n.id === id ? { ...n, [field]: value } : n))
      }));
      setIsDirty(true);
    };
    window.saveNodeCriteria = async (id: number, successCriteria: string, failureCriteria: string) => {
      const nextContract = {
        ...contract,
        nodes: contract.nodes.map((node) => node.id === id
          ? { ...node, success_criteria: successCriteria || undefined, failure_criteria: failureCriteria || undefined }
          : node)
      };
      savingContractRef.current = true;
      try {
        const saved = await performSave(nextContract);
        if (saved) {
          setContract(nextContract);
          // O próximo poll apenas estabelece a nova revisão; não recarrega o
          // desenho e não desmonta o canvas recém-editado.
          drawRevisionRef.current = null;
        } else {
          setIsDirty(true);
        }
      } finally {
        savingContractRef.current = false;
      }
    };

    window.deleteNode = async (id: number) => {
      const proceed = await askConfirm(
        'Excluir Bloco?',
        'Deseja realmente remover este bloco e todas as suas conexões?',
        'Excluir',
        true
      );
      if (proceed) {
        setContract((prev) => removeNodesFromContract(prev, new Set([id])));
        setSelectedNodeId(null);
        selectionOrderRef.current = [];
        setSelectionRevision((value) => value + 1);
        setIsDirty(true);
      }
    };

    window.openQuestionsModal = (node: NodeData) => {
      setQuestionsNode(node);
    };

    window.openChangesModal = (node: NodeData) => {
      setChangesNode(node);
    };

    window.openCodeReferencesModal = (node: NodeData) => {
      setCodeReferencesNode(node);
    };

    window.openDetailViewer = (id: number) => {
      setActiveDetailNodeId(id);
    };

    window.getGroupName = (groupId: number) => {
      const group = contractRef.current.groups.find((g) => g.id === groupId);
      return group ? group.label : '';
    };

    window.getGroupInfo = (groupId: number) => {
      return contractRef.current.groups.find((g) => g.id === groupId);
    };

    window.updateNodeGroup = (id: number, groupId?: number) => {
      setContract((prev) => ({
        ...prev,
        nodes: prev.nodes.map((node) => node.id === id ? { ...node, group: groupId } : node)
      }));
      setIsDirty(true);
    };

    window.openSubdraw = (id: string) => {
      setNavigation((prev) => [...prev, contractRef.current.id]);
      loadDrawingById(id);
    };

  }, [contract, removeNodesFromContract]);

  useEffect(() => {
    window.updateBacklogChecklist = updateBacklogChecklist;
    return () => {
      delete window.updateBacklogChecklist;
    };
  }, [updateBacklogChecklist]);

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(contract, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${contract.id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleImportJson = (jsonString: string) => {
    try {
      const parsed = JSON.parse(jsonString);
      if (!parsed || !Array.isArray(parsed.nodes) || !Array.isArray(parsed.edges)) {
        throw new Error('Formato inválido. Nodes e Edges são necessários.');
      }
      setContract(parsed);
      setImportExportMode(null);
      setIsDirty(true);
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      alert('Desenho importado com sucesso!');
    } catch (err: any) {
      alert(`Falha na importação: ${err.message}`);
    }
  };

  const handleReset = async () => {
    const proceed = await askConfirm(
      'Resetar Fluxo?',
      'Deseja descartar as alterações e reiniciar com o fluxo original?',
      'Resetar',
      true
    );
    if (proceed) {
      if (storageMode === 'backend') {
        loadDrawingById(contract.id);
      } else {
        localStorage.removeItem(`looper-draw:${contract.id}`);
        const presentationKey = `looper-draw-presentation:${contract.id}`;
        localStorage.removeItem(presentationKey);
        presentationPositionsRef.current = {};
        setPresentationPositionsState({});
        if (contract.id === typedDefaultContract.id) {
          setContract(typedDefaultContract);
        } else {
          setContract({ ...contract, nodes: [], edges: [], flows: [] });
        }
        setIsDirty(false);
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
        setActiveFlowId(null);
        loadDrawingsIndex();
      }
    }
  };

  const handleOrganize = () => {
    const presentationKey = `looper-draw-presentation:${contract.id}`;
    localStorage.removeItem(presentationKey);
    presentationPositionsRef.current = {};
    setPresentationPositionsState({});
    setIsDirty(true);
    setContract((prev) => ({ ...prev }));
  };

  const handleUpdateQuestions = (nodeId: number, questions: NodeData['questions'] = []) => {
    setContract((prev) => ({
      ...prev,
      nodes: prev.nodes.map((node) => node.id === nodeId ? { ...node, questions } : node)
    }));
    setQuestionsNode((prev) => prev && prev.id === nodeId ? { ...prev, questions } : prev);
    setIsDirty(true);
  };

  const handleUpdateChanges = (nodeId: number, changes: NonNullable<NodeData['changes']>) => {
    setContract((prev) => ({
      ...prev,
      nodes: prev.nodes.map((node) => node.id === nodeId ? { ...node, changes } : node)
    }));
    setChangesNode((prev) => prev && prev.id === nodeId ? { ...prev, changes } : prev);
    setIsDirty(true);
  };

  const handleMetadataSubmit = (data: { title: string; subtitle: string; kind: string }) => {
    setMetadataModalConfig(null);
    if (metadataModalConfig?.mode === 'create') {
      handleCreateDrawing(data.title, data.subtitle, data.kind);
    } else {
      setContract((prev) => ({
        ...prev,
        title: data.title,
        subtitle: data.subtitle,
        kind: data.kind
      }));
      setIsDirty(true);
    }
  };

  const selectedNodeData = useMemo(() => {
    if (selectedNodeId === null) return null;
    return contract.nodes.find((n) => n.id === selectedNodeId) || null;
  }, [selectedNodeId, contract.nodes]);

  const selectedEdgeData = useMemo(() => {
    if (selectedEdgeId === null) return null;
    return contract.edges.find((e) => e.id === selectedEdgeId) || null;
  }, [selectedEdgeId, contract.edges]);

  // --- Render Breadcrumbs helper ---
  const renderBreadcrumbs = () => {
    if (currentImprovement) {
      return <span className="doc-title">Melhoria: {currentImprovement.title}</span>;
    }
    if (navigation.length === 0) {
      return (
        <span 
          className="doc-title" 
          onDoubleClick={() => setMetadataModalConfig({ isOpen: true, mode: 'edit', initialValues: { title: contract.title, subtitle: contract.subtitle || '', kind: contract.kind } })}
          style={{ cursor: 'pointer' }}
          title="Dê duplo clique para editar metadados"
        >
          {contract.title || 'Sem Nome'}
        </span>
      );
    }

    return (
      <div className="breadcrumbs" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '15px', fontWeight: 800 }}>
        {navigation.map((navId, index) => {
          const drawInfo = drawingsIndex.find((d) => d.id === navId);
          const drawTitle = drawInfo ? drawInfo.title : navId;
          
          return (
            <React.Fragment key={navId}>
              <span
                onClick={() => {
                  setNavigation((prev) => prev.slice(0, index));
                  loadDrawingById(navId);
                }}
                style={{ cursor: 'pointer', color: 'var(--muted)' }}
                className="breadcrumb-item"
              >
                {drawTitle}
              </span>
              <span style={{ color: 'var(--line-strong)' }}>›</span>
            </React.Fragment>
          );
        })}
        <span 
          className="doc-title active"
          onDoubleClick={() => setMetadataModalConfig({ isOpen: true, mode: 'edit', initialValues: { title: contract.title, subtitle: contract.subtitle || '', kind: contract.kind } })}
          style={{ cursor: 'pointer' }}
          title="Dê duplo clique para editar metadados"
        >
          {contract.title}
        </span>
      </div>
    );
  };

  const pendingImprovementQuestions = currentImprovement
    ? currentImprovement.questions.filter((question) => !isImprovementAnswer(question.answer)).length
    : 0;
  const improvementNeedsSave = Boolean(currentImprovement && (
    isImprovementDirty ||
    pendingImprovementQuestions > 0 ||
    currentImprovement.status === 'draft'
  ));
  const canGoUp = !currentImprovement && Boolean(
    navigation.length > 0 || contract.hierarchy?.parent_draw_ref || (contract.hierarchy?.level && contract.hierarchy.level > 1)
  );
  const observerToggleDisabled = Boolean(currentImprovement || isDirty || isImprovementDirty);
  const toggleObserverMode = () => {
    if (observerToggleDisabled && !observerMode) return;
    setObserverMode((enabled) => !enabled);
    if (observerMode) {
      observerTargetRef.current = null;
      observerFocusedKeyRef.current = null;
      setObserverTarget(null);
      setObserverStatus('Desativado');
      setSelectedNodeId(null);
      selectionOrderRef.current = [];
      setSelectionRevision((value) => value + 1);
    }
  };

  return (
    <div className={`app-container ${theme}-theme ${observerMode ? 'observer-mode' : ''}`}>
      <svg className="edge-gradient-definitions" aria-hidden="true">
        <defs>
          <linearGradient id="looper-then-edge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="100%" stopColor="#fb923c" />
          </linearGradient>
        </defs>
      </svg>
      {/* Top Header / Toolbar Overlay */}
      <header className="top-toolbar">
        <div className="title-container" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {canGoUp && (
            <button 
              className="icon-btn level-up-btn"
              onClick={handleGoBack} 
              disabled={isParentNavigationLoading}
              title="Voltar um nível acima"
              aria-label="Voltar um nível acima"
            >
              <ArrowUp size={16} />
              <span>{isParentNavigationLoading ? 'Procurando...' : 'Subir nível'}</span>
            </button>
          )}
          {renderBreadcrumbs()}
          <span className="doc-type-badge">{currentImprovement ? 'IMPROVEMENT' : contract.kind.toUpperCase()}</span>
          <button
            className={`observer-toggle ${observerMode ? 'active' : ''}`}
            type="button"
            onClick={toggleObserverMode}
            disabled={observerToggleDisabled && !observerMode}
            title={observerToggleDisabled && !observerMode ? 'Salve ou descarte as alterações antes de observar' : `${observerMode ? 'Desativar' : 'Ativar'} modo Observador`}
            aria-label={`${observerMode ? 'Desativar' : 'Ativar'} modo Observador`}
            aria-pressed={observerMode}
          >
            {observerMode ? <EyeOff size={14} /> : <Eye size={14} />}
            <span>{observerMode ? 'Observador ativo' : 'Observar'}</span>
          </button>
          {observerMode && <span className="observer-status" title={observerStatus}>{observerStatus}</span>}
          {!currentImprovement && storageMode === 'backend' && (
            <span className={`draw-sync-status ${drawSyncState}`} title="Sincronização do fluxo">
              <span aria-hidden="true" />
              {drawSyncState === 'checking' ? 'Verificando' : drawSyncState === 'pending' ? 'Atualização pendente' : drawSyncState === 'error' ? 'Servidor indisponível' : 'Sincronizado'}
            </span>
          )}
          {(isDirty || isImprovementDirty) && <span className="dirty-dot-indicator" title="Alterações pendentes de salvamento" />}
        </div>

        <div className="search-bar-container">
          <input
            className="search-input"
            placeholder={currentImprovement ? 'Pesquisar perguntas...' : 'Buscar em todos os fluxos...'}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {!currentImprovement && searchQuery.trim() && (
            <div className="search-results" role="listbox" aria-label="Resultados da busca nos fluxos">
              {isSearchLoading ? (
                <div className="search-results-empty">Buscando nos fluxos...</div>
              ) : searchResults.length === 0 ? (
                <div className="search-results-empty">Nenhuma associação encontrada.</div>
              ) : (
                searchResults.map((result) => (
                  <button
                    key={`${result.drawId}:${result.nodeId}`}
                    type="button"
                    className="search-result"
                    role="option"
                    onClick={() => focusSearchResult(result)}
                  >
                    <span className="search-result-title">{result.nodeLabel}</span>
                    <span className="search-result-flow">{result.drawTitle} · nó {result.nodeId}</span>
                    <span className="search-result-association">
                      {result.associations.length > 0
                        ? result.associations.join(', ')
                        : 'sem símbolo associado'}
                    </span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <div className="header-actions">
          <button
            className="icon-btn settings-btn"
            type="button"
            onClick={() => setShowConfigSettings(true)}
            title="Configurações do Looper"
            aria-label="Abrir configurações do Looper"
          >
            <Settings size={16} />
            <span>Configurações</span>
          </button>
          <button
            className="icon-btn sidebar-layout-btn"
            type="button"
            onClick={() => setIsSidebarVisible((visible) => !visible)}
            title={isSidebarVisible ? 'Ocultar barra lateral' : 'Mostrar barra lateral'}
            aria-label={isSidebarVisible ? 'Ocultar barra lateral' : 'Mostrar barra lateral'}
            aria-pressed={isSidebarVisible}
          >
            <PanelLeft size={16} />
            <span>{isSidebarVisible ? 'Ocultar painel' : 'Mostrar painel'}</span>
          </button>
          <button
            className="icon-btn sidebar-layout-btn"
            type="button"
            onClick={() => setSidebarDock((dock) => dock === 'side' ? 'bottom' : 'side')}
            title={sidebarDock === 'side' ? 'Mover barra lateral para baixo' : 'Mover barra lateral para o lado'}
            aria-label={sidebarDock === 'side' ? 'Mover barra lateral para baixo' : 'Mover barra lateral para o lado'}
            aria-pressed={sidebarDock === 'bottom'}
            disabled={!isSidebarVisible}
          >
            {sidebarDock === 'side' ? <PanelBottom size={16} /> : <PanelLeft size={16} />}
            <span>{sidebarDock === 'side' ? 'Painel embaixo' : 'Painel ao lado'}</span>
          </button>
          <button
            className="theme-toggle-btn"
            onClick={() => setTheme((prev) => prev === 'light' ? 'dark' : prev === 'dark' ? 'black' : 'light')}
            title={`Tema atual: ${theme === 'light' ? 'claro' : theme === 'dark' ? 'escuro' : 'preto'}. Clique para alternar.`}
            aria-label="Alternar tema"
          >
            {theme === 'light' ? <Moon size={16} /> : theme === 'dark' ? <Contrast size={16} /> : <Sun size={16} />}
          </button>
          <button className="icon-btn success" onClick={improvementNeedsSave ? handleSaveAll : handleSave} title={improvementNeedsSave ? 'Salvar alterações do fluxo e respostas' : 'Salvar Desenho'}>
            <Save size={16} />
            <span>{improvementNeedsSave ? 'Salvar fluxo + respostas' : 'Salvar'}</span>
          </button>
          {currentImprovement && pendingImprovementQuestions > 0 && (
            <button
              className="improvement-open-btn"
              type="button"
              onClick={() => setShowImprovementModal(true)}
              title={`Abrir perguntas da melhoria. ${pendingImprovementQuestions} pendente(s).`}
              aria-label={`Abrir perguntas da melhoria. ${pendingImprovementQuestions} pendente(s).`}
            >
              <ClipboardList size={16} />
              <span>Perguntas</span>
              <strong>{pendingImprovementQuestions}</strong>
            </button>
          )}
          <button
            className="icon-btn organize"
            onClick={handleOrganize}
            title="Limpar as posições locais e reorganizar o fluxo automaticamente"
            aria-label="Organizar fluxo"
          >
            <Sparkles size={16} />
            <span>Organizar</span>
          </button>
          <button className="icon-btn" onClick={handleExportJson} title="Exportar Contrato JSON">
            <Download size={16} />
            <span>Exportar</span>
          </button>
          <button className="icon-btn danger" onClick={handleReset} disabled={Boolean(currentImprovement)} title="Resetar Fluxo">
            <RotateCcw size={16} />
            <span>Resetar</span>
          </button>
        </div>
      </header>

      <ConfigSettingsModal open={showConfigSettings} apiOrigin={getApiOrigin()} onClose={() => setShowConfigSettings(false)} />

      {/* Main Layout Grid */}
      <div className={`app-workspace-layout sidebar-${sidebarDock} ${isSidebarVisible ? 'sidebar-visible' : 'sidebar-hidden'}`}>
        {/* Sidebar */}
        <Sidebar
          dock={sidebarDock}
          contract={contract}
          selectedNode={selectedNodeData}
          selectedEdge={selectedEdgeData}
          activeFlowId={activeFlowId}
          onUpdateContract={setContract}
          onSelectNode={(node) => setSelectedNodeId(node ? node.id : null)}
          onSelectEdge={(edge) => setSelectedEdgeId(edge ? edge.id : null)}
          onSelectFlow={setActiveFlowId}
          onOpenImportExport={setImportExportMode}
          // Drawings support
          drawingsIndex={drawingsIndex}
          currentDrawingId={contract.id}
          onLoadDrawing={(id) => loadDrawingById(id, { resetNavigation: true })}
          onNewDrawing={() => setMetadataModalConfig({ isOpen: true, mode: 'create' })}
          improvementsIndex={improvementsIndex}
          currentImprovementId={currentImprovement?.id || null}
          onLoadImprovement={(id) => loadImprovementById(id)}
          runs={runs}
          staticAnalysisKpis={staticAnalysisKpis}
          backlog={backlog}
          onClaimBacklogTask={claimBacklogTask}
          onClaimBacklogTest={claimBacklogTest}
          onRefreshBacklog={refreshBacklog}
          onCompleteBacklogTask={completeBacklogTask}
          onUpdateBacklogChecklist={updateBacklogChecklist}
        />

        {/* Canvas Area */}
        <main className="workspace">
          <div className="react-flow-stage">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={handleEdgesChange}
              deleteKeyCode={null}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              onInit={(instance) => {
                reactFlowInstanceRef.current = instance;
                setReactFlowReady((value) => value + 1);
              }}
              onNodeClick={onNodeClick}
              onSelectionChange={onSelectionChange}
              multiSelectionKeyCode={['Shift']}
              onEdgeClick={onEdgeClick}
              onEdgeDoubleClick={onEdgeDoubleClick}
              onPaneClick={onPaneClick}
              onConnect={onConnect}
              onNodeDragStop={onNodeDragStop}
              minZoom={0.01}
              maxZoom={4}
            >
              <Controls />
              <MiniMap zoomable pannable style={{ borderRadius: '14px', overflow: 'hidden' }} />
              <Background gap={24} size={1} />
            </ReactFlow>
          </div>
        </main>
      </div>

      <footer className="shortcut-footer" aria-label="Atalhos do editor">
        <span><kbd>Espaço</kbd> novo bloco</span>
        <span><kbd>Delete</kbd>/<kbd>Backspace</kbd> apagar</span>
        <span><kbd>Ctrl</kbd> isolar</span>
        <span><kbd>Alt</kbd> detalhes</span>
        <span><kbd>Shift</kbd> selecionar vários</span>
        <span><kbd>Z</kbd>/<kbd>X</kbd>/<kbd>C</kbd> conectar</span>
        <span><kbd>Ctrl+C</kbd>/<kbd>Ctrl+V</kbd> copiar/colar JSON</span>
        <span><kbd>Ctrl+D</kbd> duplicar</span>
        <span><kbd>Ctrl+Z</kbd> desfazer</span>
        <span><kbd>V</kbd> perguntas</span>
      </footer>

      {/* Modal Dialogs */}
      {editNodeData && (
        <NodeEditModal
          node={editNodeData}
          onClose={() => setEditNodeData(null)}
          onSave={(id, label, description, successCriteria, failureCriteria) => {
            if (window.updateNodeField) {
              window.updateNodeField(id, 'label', label);
              window.updateNodeField(id, 'description', description);
              window.updateNodeField(id, 'success_criteria', successCriteria || '');
              window.updateNodeField(id, 'failure_criteria', failureCriteria || '');
            }
          }}
        />
      )}
      {questionsNode && (
        <QuestionsModal
          node={questionsNode}
          onClose={() => setQuestionsNode(null)}
          onUpdateQuestions={handleUpdateQuestions}
        />
      )}
      {changesNode && (
        <ChangesModal
          node={changesNode}
          onClose={() => setChangesNode(null)}
          onUpdateChanges={handleUpdateChanges}
        />
      )}

      {currentImprovement && showImprovementModal && (
        <div className="dialog-overlay improvement-dialog-overlay">
          <dialog
            className="app-dialog improvement-dialog"
            open
            onCancel={(event) => { event.preventDefault(); setShowImprovementModal(false); }}
          >
            <div className="improvement-dialog-topbar">
              <span className="eyebrow">Perguntas da melhoria</span>
              <button
                className="close-btn"
                type="button"
                onClick={() => setShowImprovementModal(false)}
                aria-label="Fechar perguntas da melhoria"
              >
                <X size={18} />
              </button>
            </div>
            <ImprovementEditor session={currentImprovement} onChange={handleImprovementAnswer} />
          </dialog>
        </div>
      )}

      {codeReferencesNode && (
        <CodeReferencesModal
          node={codeReferencesNode}
          facts={traceabilityFacts}
          onClose={() => setCodeReferencesNode(null)}
        />
      )}

      {importExportMode && (
        <ImportExportModeModalWrapper
          mode={importExportMode}
          exportData={JSON.stringify(contract, null, 2)}
          onClose={() => setImportExportMode(null)}
          onImport={handleImportJson}
        />
      )}

      {metadataModalConfig && (
        <MetadataModal
          isOpen={metadataModalConfig.isOpen}
          onClose={() => setMetadataModalConfig(null)}
          onSubmit={handleMetadataSubmit}
          initialValues={metadataModalConfig.initialValues}
          titleText={metadataModalConfig.mode === 'create' ? 'Criar Novo Desenho' : 'Editar Metadados'}
          submitLabel={metadataModalConfig.mode === 'create' ? 'Criar Desenho' : 'Salvar Metadados'}
        />
      )}

      {confirmConfig && (
        <ConfirmModal
          isOpen={confirmConfig.isOpen}
          title={confirmConfig.title}
          message={confirmConfig.message}
          confirmLabel={confirmConfig.confirmLabel}
          isDanger={confirmConfig.isDanger}
          onConfirm={() => {
            confirmConfig.resolve(true);
            setConfirmConfig(null);
          }}
          onCancel={() => {
            confirmConfig.resolve(false);
            setConfirmConfig(null);
          }}
        />
      )}

      {parentNavigationOptions && (
        <ParentNavigationModal
          isOpen={parentNavigationOptions.length > 1}
          childTitle={contract.title}
          options={parentNavigationOptions}
          onSelect={navigateToParent}
          onClose={() => setParentNavigationOptions(null)}
        />
      )}

      {activeDetailNodeId !== null && (
        <FocusDetailModal
          nodeId={activeDetailNodeId}
          contract={contract}
          theme={theme}
          onClose={() => setActiveDetailNodeId(null)}
        />
      )}
    </div>
  );
};

// Helper wrapper to fix typescript type import for ImportExportModal
const ImportExportModeModalWrapper: React.FC<{
  mode: 'import' | 'export';
  exportData: string;
  onClose: () => void;
  onImport: (jsonString: string) => void;
}> = ({ mode, exportData, onClose, onImport }) => {
  return <ImportExportModal mode={mode} exportData={exportData} onClose={onClose} onImport={onImport} />;
};

export default App;
