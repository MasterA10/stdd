import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType
} from '@xyflow/react';
import type { Connection, Edge, EdgeChange, Node, EdgeTypes } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import type { Contract, NodeData, EdgeData, RunRecord } from './types';
import { CustomNode } from './components/CustomNode';
import { LoopEdge } from './components/LoopEdge';
import { Sidebar } from './components/Sidebar';
import { QuestionsModal } from './components/QuestionsModal';
import { ImportExportModal } from './components/ImportExportModal';
import { MetadataModal } from './components/MetadataModal';
import { ConfirmModal } from './components/ConfirmModal';
import { FocusDetailModal } from './components/FocusDetailModal';
import { layoutCurvedGraph, computeEdgeHandles } from './layout';
import { RotateCcw, Save, Download, Sun, Moon } from 'lucide-react';

import defaultContract from '../contract.json';

const typedDefaultContract = defaultContract as Contract;

const nodeTypes = {
  custom: CustomNode
};

const edgeTypes: EdgeTypes = {
  loop: LoopEdge
};

const DEFAULT_CONDITION = 1;

const getApiOrigin = () => {
  if (window.location.protocol === 'file:') {
    return `http://127.0.0.1:8765`;
  }
  return window.location.origin;
};

const checkBackendAvailable = async (): Promise<boolean> => {
  try {
    const origin = getApiOrigin();
    const response = await fetch(`${origin}/.stdd/draws/index.json`, { method: 'GET', cache: 'no-store' });
    return response.ok;
  } catch (_) {
    return false;
  }
};

export const App: React.FC = () => {
  // --- Drawings & Storage States ---
  const [contract, setContract] = useState<Contract>(typedDefaultContract);
  const [drawingsIndex, setDrawingsIndex] = useState<any[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [storageMode, setStorageMode] = useState<'backend' | 'local'>('local');
  const [navigation, setNavigation] = useState<string[]>([]);
  
  // --- UI States ---
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<number | null>(null);
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [activeFlowId, setActiveFlowId] = useState<number | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [isDirty, setIsDirty] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectionRevision, setSelectionRevision] = useState(0);
  const [presentationPositionsState, setPresentationPositionsState] = useState<Record<string, { x: number; y: number }>>({});

  // --- Dialogs & Modals States ---
  const [questionsNode, setQuestionsNode] = useState<NodeData | null>(null);
  const [activeDetailNodeId, setActiveDetailNodeId] = useState<number | null>(null);
  const [importExportMode, setImportExportMode] = useState<'import' | 'export' | null>(null);
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

  // --- React Flow Node & Edge States ---
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<NodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    let cancelled = false;

    const loadRuns = async () => {
      try {
        const origin = getApiOrigin();
        const indexResponse = await fetch(`${origin}/.stdd/runs/index.json`, { cache: 'no-store' });
        if (!indexResponse.ok) return;

        const index = await indexResponse.json();
        const days = Array.isArray(index.days) ? index.days : [];
        const summaries = await Promise.all(days.map(async (day: { summary?: string }) => {
          if (!day.summary) return null;
          const response = await fetch(`${origin}/.stdd/runs/${day.summary}`, { cache: 'no-store' });
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

  const readPresentationPositions = (id: string) => {
    try {
      const saved = localStorage.getItem(`stdd-draw-presentation:${id}`);
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
      const isBackend = await checkBackendAvailable();
      const mode = isBackend ? 'backend' : 'local';
      setStorageMode(mode);

      // 2. Load index
      let indexData: any[] = [];
      if (isBackend) {
        try {
          const origin = getApiOrigin();
          const response = await fetch(`${origin}/.stdd/draws/index.json`, { cache: 'no-store' });
          if (response.ok) {
            const data = await response.json();
            indexData = data.draws || [];
          }
        } catch (_) {}
      } else {
        const savedIndex = localStorage.getItem('stdd-draws-index');
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
            subdraw_count: typedDefaultContract.nodes.filter((n) => !!n.draw_ref).length
          }
        ];
        localStorage.setItem('stdd-draws-index', JSON.stringify({ version: 1, draws: initialIndex }));
        localStorage.setItem(`stdd-draw:${defaultId}`, JSON.stringify(typedDefaultContract));
        indexData = initialIndex;
      }

      setDrawingsIndex(indexData);

      // 4. Determine initial drawing to load
      const searchParams = new URLSearchParams(window.location.search);
      const requestedId = searchParams.get('draw');
      if (requestedId && indexData.some((d) => d.id === requestedId)) {
        await loadDrawingById(requestedId, { resetNavigation: true, indexData, mode });
      } else if (indexData.length > 0) {
        await loadDrawingById(indexData[0].id, { resetNavigation: true, indexData, mode });
      }
    };

    initializeApp();
  }, []);

  // --- Fetching Drawings Index ---
  const loadDrawingsIndex = async () => {
    if (storageMode === 'backend') {
      try {
        const origin = getApiOrigin();
        const response = await fetch(`${origin}/.stdd/draws/index.json`, { cache: 'no-store' });
        if (response.ok) {
          const data = await response.json();
          setDrawingsIndex(data.draws || []);
        }
      } catch (_) {}
    } else {
      const savedIndex = localStorage.getItem('stdd-draws-index');
      if (savedIndex) {
        try {
          const data = JSON.parse(savedIndex);
          setDrawingsIndex(data.draws || []);
        } catch (_) {}
      }
    }
  };

  // --- Load individual Drawing ---
  const loadDrawingById = async (
    id: string,
    opts?: { resetNavigation?: boolean; indexData?: any[]; mode?: 'backend' | 'local' }
  ) => {
    const activeMode = opts?.mode || storageMode;

    if (isDirty) {
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
        const response = await fetch(`${origin}/.stdd/draws/${encodeURIComponent(id)}.json`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        setContract(data);
        setPresentationPositionsForDrawing(id);
        window.currentDrawId = id;
        setIsDirty(false);
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
      } catch (err: any) {
        alert(`Erro ao carregar desenho do backend: ${err.message}`);
      }
    } else {
      const saved = localStorage.getItem(`stdd-draw:${id}`);
      if (saved) {
        try {
          const data = JSON.parse(saved);
          setContract(data);
          setPresentationPositionsForDrawing(id);
          window.currentDrawId = id;
          setIsDirty(false);
          setSelectedNodeId(null);
          setSelectedEdgeId(null);
        } catch (_) {
          alert('Erro ao carregar desenho local: JSON corrompido.');
        }
      } else if (id === typedDefaultContract.id) {
        setContract(typedDefaultContract);
        setPresentationPositionsForDrawing(id);
        window.currentDrawId = id;
        setIsDirty(false);
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
      } else {
        alert('Desenho não encontrado no armazenamento local.');
      }
    }
  };

  // --- Save Logic & Strip Presentation Details from Logical JSON ---
  const cleanLogicalPayload = (payload: Contract): Contract => {
    const doc = JSON.parse(JSON.stringify(payload));
    delete doc.isHighlighted;
    delete doc.isDimmed;
    
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

  const performSave = async (contractToSave: Contract) => {
    const id = contractToSave.id;
    const cleanPayload = cleanLogicalPayload(contractToSave);
    const presentationKey = `stdd-draw-presentation:${id}`;
    try {
      const saved = localStorage.getItem(presentationKey);
      const presentation = saved ? JSON.parse(saved) : {};
      presentation.positions = presentationPositionsRef.current;
      localStorage.setItem(presentationKey, JSON.stringify(presentation));
    } catch (_) {}

    if (storageMode === 'backend') {
      try {
        const origin = getApiOrigin();
        const response = await fetch(`${origin}/__stdd/api/draws/${encodeURIComponent(id)}.json`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cleanPayload)
        });
        if (!response.ok) {
          const result = await response.json().catch(() => ({}));
          throw new Error(result.error || `HTTP ${response.status}`);
        }
        setIsDirty(false);
        await loadDrawingsIndex();
      } catch (err: any) {
        alert(`Erro ao salvar no backend: ${err.message}`);
      }
    } else {
      // Local Storage
      localStorage.setItem(`stdd-draw:${id}`, JSON.stringify(cleanPayload));
      
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
        subdraw_count: contractToSave.nodes.filter((n) => !!n.draw_ref).length
      };

      if (existingIdx >= 0) {
        drawings[existingIdx] = metadata;
      } else {
        drawings.push(metadata);
      }

      drawings.sort((a, b) => a.title.localeCompare(b.title));
      localStorage.setItem('stdd-draws-index', JSON.stringify({ version: 1, draws: drawings }));
      setDrawingsIndex(drawings);
      setIsDirty(false);
    }
  };

  const handleSave = () => {
    performSave(contract);
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
  const handleGoBack = () => {
    if (navigation.length === 0) return;
    const parentId = navigation[navigation.length - 1];
    setNavigation((prev) => prev.slice(0, -1));
    loadDrawingById(parentId);
  };

  // --- Node & Edge Mappings ---
  const presentationPositions = useMemo(() => {
    const presentationKey = `stdd-draw-presentation:${contract.id}`;
    try {
      const saved = localStorage.getItem(presentationKey);
      if (saved) {
        return { ...(JSON.parse(saved).positions || {}), ...presentationPositionsState };
      }
    } catch (_) {}
    return presentationPositionsState;
  }, [contract.id, isDirty, presentationPositionsState]);

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

    const hasSearch = searchQuery.trim() !== '';
    const searchLower = searchQuery.toLowerCase();
    
    // Set of matching node IDs for search filtering
    const matchingNodeIds = new Set<number>();
    if (hasSearch) {
      contract.nodes.forEach((node) => {
        const matches =
          node.label.toLowerCase().includes(searchLower) ||
          node.description.toLowerCase().includes(searchLower) ||
          (node.group !== undefined && String(node.group).includes(searchLower));
        if (matches) {
          matchingNodeIds.add(node.id);
        }
      });
    }

    const filteredNodes = contract.nodes.map((node) => {
      const inPath = activeFlowId !== null && activeNodeIds.has(node.id);
      let isDimmed = activeFlowId !== null && !inPath;
      let isHighlighted = activeFlowId !== null && inPath;

      const matchesSearch = hasSearch && matchingNodeIds.has(node.id);

      if (matchesSearch) {
        isHighlighted = true;
      }

      // Priority overrides for dimming: Search overrides Selection, Selection overrides default
      if (hasSearch) {
        if (matchesSearch) {
          isDimmed = false;
        } else {
          isDimmed = true;
        }
      } else if (hasSelection && !hasMultiSelection) {
        if (connectedNodeIds.has(node.id)) {
          isDimmed = false;
        } else {
          isDimmed = true;
        }
      }

      return {
        ...node,
        groupOptions: contract.groups,
        isHighlighted,
        isDimmed
      };
    });

    const formattedNodes = layoutCurvedGraph(filteredNodes, contract.edges, presentationPositions);
    const selectedNodeIds = new Set(selectionOrderRef.current);
    const nodesWithSelection = formattedNodes.map((node) => ({
      ...node,
      selected: selectedNodeIds.has(Number(node.id))
    }));
    setNodes(nodesWithSelection);

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

      // Priority overrides for edge dimming
      if (hasSearch) {
        if (matchingNodeIds.has(edge.from) && matchingNodeIds.has(edge.to)) {
          isDimmed = false;
        } else {
          isDimmed = true;
        }
      } else if (hasSelection && !hasMultiSelection) {
        if (edge.from === selectedNodeId || edge.to === selectedNodeId) {
          isDimmed = false;
        } else {
          isDimmed = true;
        }
      }

      const edgeHandles = computeEdgeHandles(edge, positions, contract.nodes, contract.edges);
      const condition = Number(edge.condition) || DEFAULT_CONDITION;
      
      const visual =
        {
          1: { color: theme === 'light' ? '#1e293b' : '#94a3b8', dash: undefined },
          2: { color: '#d97706', dash: '8 6' },
          3: { color: '#059669', dash: '3 6' }
        }[condition] || { color: '#1e293b', dash: undefined };

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
        data: edge,
        style: {
          stroke: isHighlighted ? '#10b981' : visual.color,
          strokeWidth: isHighlighted ? 3.5 : (connectsSelection ? 2.5 : 2),
          strokeDasharray: visual.dash,
          opacity: isDimmed ? 0.03 : 1
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isHighlighted ? '#10b981' : visual.color,
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

    setEdges(formattedEdges);
  }, [contract, activeFlowId, presentationPositions, searchQuery, theme, selectedNodeId, isFocusMode, selectionRevision]);

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
    const selectedIds = selection.nodes.map((node) => Number(node.id));
    if (selectedIds.length === 0 && selectionOrderRef.current.length > 0) return;
    const availableIds = new Set(contract.nodes.map((node) => node.id));
    const ordered = selectionOrderRef.current.filter((id) => availableIds.has(id));
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
      setSelectedNodeId(id);
    } else {
      const currentSelection = selectionOrderRef.current.length > 0
        ? selectionOrderRef.current
        : selectedNodeId !== null
          ? [selectedNodeId]
          : [];
      if (!currentSelection.includes(id)) {
        selectionOrderRef.current = [...currentSelection, id];
      }
      setSelectedNodeId(selectionOrderRef.current[0] ?? id);
    }
    setSelectedEdgeId(null);
    setSelectionRevision((value) => value + 1);
  };

  const onEdgeClick = (_: any, edge: Edge) => {
    setSelectedEdgeId(Number(edge.id));
    setSelectedNodeId(null);
    setIsFocusMode(false);
  };

  const onPaneClick = () => {
    window.dispatchEvent(new Event('stdd:clear-node-editing'));
    selectionOrderRef.current = [];
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

  const deleteSelectedItems = useCallback(() => {
    const selectedIds = getOrderedSelectedNodeIds();
    if (selectedIds.length > 0) {
      const deleted = new Set(selectedIds);
      setContract((prev) => ({
        ...prev,
        nodes: prev.nodes.filter((node) => !deleted.has(node.id)),
        edges: prev.edges.filter((edge) => !deleted.has(edge.from) && !deleted.has(edge.to))
      }));
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
  }, [getOrderedSelectedNodeIds, selectedEdgeId]);

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
  }, [connectSelectedNodes, createInstantNode, deleteSelectedItems, duplicateSelectedNodes, selectedNodeId]);

  const onConnect = useCallback(
    (params: Connection) => {
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
          from: Number(params.source),
          to: Number(params.target),
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
      const presentationKey = `stdd-draw-presentation:${contractRef.current.id}`;
      let parsed = { positions: {} as { [key: string]: { x: number; y: number } }, nodes: {} as any };
      try {
        const saved = localStorage.getItem(presentationKey);
        if (saved) parsed = JSON.parse(saved);
      } catch (_) {}

      const nextPositions = {
        ...presentationPositionsRef.current,
        ...parsed.positions,
        [String(node.id)]: node.position
      };
      presentationPositionsRef.current = nextPositions;
      setPresentationPositionsState(nextPositions);
      parsed.positions = nextPositions;
      localStorage.setItem(presentationKey, JSON.stringify(parsed));
      setIsDirty(false);
    },
    []
  );

  // --- Exposed Window Functions for Nodes ---
  useEffect(() => {
    window.updateNodeField = (id: number, field: 'label' | 'description', value: string) => {
      setContract((prev) => ({
        ...prev,
        nodes: prev.nodes.map((n) => (n.id === id ? { ...n, [field]: value } : n))
      }));
      setIsDirty(true);
    };

    window.deleteNode = async (id: number) => {
      const proceed = await askConfirm(
        'Excluir Bloco?',
        'Deseja realmente remover este bloco e todas as suas conexões?',
        'Excluir',
        true
      );
      if (proceed) {
        setContract((prev) => ({
          ...prev,
          nodes: prev.nodes.filter((n) => n.id !== id),
          edges: prev.edges.filter((e) => e.from !== id && e.to !== id)
        }));
        setSelectedNodeId(null);
        selectionOrderRef.current = [];
        setSelectionRevision((value) => value + 1);
        setIsDirty(true);
      }
    };

    window.openQuestionsModal = (node: NodeData) => {
      setQuestionsNode(node);
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

  }, []);

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
        localStorage.removeItem(`stdd-draw:${contract.id}`);
        const presentationKey = `stdd-draw-presentation:${contract.id}`;
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

  const handleTriggerAutoLayout = () => {
    const presentationKey = `stdd-draw-presentation:${contract.id}`;
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

  return (
    <div className={`app-container ${theme}-theme`}>
      {/* Top Header / Toolbar Overlay */}
      <header className="top-toolbar">
        <div className="title-container" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {navigation.length > 0 && (
            <button 
              className="icon-btn" 
              onClick={handleGoBack} 
              title="Voltar para o desenho pai"
              style={{ padding: '4px 10px', height: '30px', margin: 0 }}
            >
              <span>Voltar</span>
            </button>
          )}
          {renderBreadcrumbs()}
          <span className="doc-type-badge">{contract.kind.toUpperCase()}</span>
          {isDirty && <span className="dirty-dot-indicator" title="Alterações pendentes de salvamento" />}
        </div>

        <div className="search-bar-container">
          <input
            className="search-input"
            placeholder="Pesquisar blocos..."
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="header-actions">
          <button className="theme-toggle-btn" onClick={() => setTheme(prev => prev === 'light' ? 'dark' : 'light')} title="Alternar Tema">
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
          </button>
          <button className="icon-btn success" onClick={handleSave} title="Salvar Desenho">
            <Save size={16} />
            <span>Salvar</span>
          </button>
          <button className="icon-btn" onClick={handleExportJson} title="Exportar Contrato JSON">
            <Download size={16} />
            <span>Exportar</span>
          </button>
          <button className="icon-btn danger" onClick={handleReset} title="Resetar Fluxo">
            <RotateCcw size={16} />
            <span>Resetar</span>
          </button>
        </div>
      </header>

      {/* Main Layout Grid */}
      <div className="app-workspace-layout">
        {/* Sidebar */}
        <Sidebar
          contract={contract}
          selectedNode={selectedNodeData}
          selectedEdge={selectedEdgeData}
          activeFlowId={activeFlowId}
          onUpdateContract={setContract}
          onSelectNode={(node) => setSelectedNodeId(node ? node.id : null)}
          onSelectEdge={(edge) => setSelectedEdgeId(edge ? edge.id : null)}
          onTriggerAutoLayout={handleTriggerAutoLayout}
          onSelectFlow={setActiveFlowId}
          onOpenImportExport={setImportExportMode}
          // Drawings support
          drawingsIndex={drawingsIndex}
          currentDrawingId={contract.id}
          onLoadDrawing={(id) => loadDrawingById(id, { resetNavigation: true })}
          onNewDrawing={() => setMetadataModalConfig({ isOpen: true, mode: 'create' })}
          storageMode={storageMode}
          runs={runs}
        />

        {/* Canvas Area */}
        <main className="workspace">
          <ReactFlowProvider>
            <div className="react-flow-stage">
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={handleEdgesChange}
                deleteKeyCode={null}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                onNodeClick={onNodeClick}
                onSelectionChange={onSelectionChange}
                multiSelectionKeyCode={['Shift']}
                onEdgeClick={onEdgeClick}
                onPaneClick={onPaneClick}
                onConnect={onConnect}
                onNodeDragStop={onNodeDragStop}
                fitView
                minZoom={0.01}
                maxZoom={4}
              >
                <Controls />
                <MiniMap zoomable pannable style={{ borderRadius: '14px', overflow: 'hidden' }} />
                <Background gap={24} size={1} />
              </ReactFlow>
            </div>
          </ReactFlowProvider>
        </main>
      </div>

      <footer className="shortcut-footer" aria-label="Atalhos do editor">
        <span><kbd>Espaço</kbd> novo bloco</span>
        <span><kbd>Delete</kbd>/<kbd>Backspace</kbd> apagar</span>
        <span><kbd>Ctrl</kbd> isolar</span>
        <span><kbd>Alt</kbd> detalhes</span>
        <span><kbd>Shift</kbd> selecionar vários</span>
        <span><kbd>Z</kbd>/<kbd>X</kbd>/<kbd>C</kbd> conectar</span>
        <span><kbd>Ctrl+D</kbd> duplicar</span>
        <span><kbd>Ctrl+Z</kbd> desfazer</span>
        <span><kbd>V</kbd> perguntas</span>
      </footer>

      {/* Modal Dialogs */}
      {questionsNode && (
        <QuestionsModal
          node={questionsNode}
          onClose={() => setQuestionsNode(null)}
          onUpdateQuestions={handleUpdateQuestions}
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
