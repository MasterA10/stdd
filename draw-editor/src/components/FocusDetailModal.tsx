import React, { useEffect, useState } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType
} from '@xyflow/react';
import type { Edge, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Eye, EyeOff, X } from 'lucide-react';
import type { Contract, NodeData } from '../types';
import { CustomNode } from './CustomNode';
import { FocusLoopEdge } from './FocusLoopEdge';
import { computeEdgeHandles } from '../layout';

const THEN_EDGE_GRADIENT = 'url(#stdd-then-edge-gradient)';
const THEN_EDGE_MARKER_COLOR = '#fb923c';

interface FocusDetailModalProps {
  nodeId: number;
  contract: Contract;
  theme: 'light' | 'dark' | 'black';
  onClose: () => void;
}

const nodeTypes = {
  custom: CustomNode
};

const edgeTypes = {
  'focus-loop': FocusLoopEdge
};

export const FocusDetailModal: React.FC<FocusDetailModalProps> = ({
  nodeId,
  contract,
  theme,
  onClose
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<NodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [showLoops, setShowLoops] = useState(true);
  const focusCanvasBackground = theme === 'light'
    ? 'var(--canvas, #f8fafc)'
    : 'var(--canvas, #0f172a)';

  useEffect(() => {
    const currentNode = contract.nodes.find((n) => n.id === nodeId);
    if (!currentNode) return;

    // Find predecessors and successors
    const predEdges = contract.edges.filter((e) => e.to === nodeId);
    const succEdges = contract.edges.filter((e) => e.from === nodeId);

    const incomingIds = new Set(predEdges.map((edge) => edge.from));
    const outgoingIds = new Set(succEdges.map((edge) => edge.to));
    const loopIds = new Set(
      [...incomingIds].filter((neighborId) => outgoingIds.has(neighborId))
    );
    const neighborNodes = contract.nodes.filter((node) =>
      incomingIds.has(node.id) || outgoingIds.has(node.id)
    );
    // A direção da conexão define o lado. Um par bidirecional fica à direita,
    // pois a entrada correspondente é o retorno ortogonal do loop.
    const predNodes = neighborNodes.filter((node) =>
      incomingIds.has(node.id) && !loopIds.has(node.id) && !outgoingIds.has(node.id)
    );
    const succNodes = neighborNodes.filter((node) =>
      outgoingIds.has(node.id) || loopIds.has(node.id)
    );

    const P = predNodes.length;
    const S = succNodes.length;
    const maxRows = Math.max(P, S, 1);
    
    // Center Y coordinate
    const centerY = ((maxRows - 1) * 220) / 2;

    const mapNode = (n: NodeData, x: number, y: number) => {
      return {
        id: String(n.id),
        type: 'custom',
        position: { x, y },
        data: {
          ...n,
          groupOptions: contract.groups,
          theme
        }
      };
    };

    // 1. Build Predecessor Nodes (Left column, x = 60)
    const formattedPredNodes = predNodes.map((n, i) => {
      const offset = centerY - ((P - 1) * 220) / 2;
      return mapNode(n, 60, offset + i * 220);
    });

    // 2. Build Current Node (Center, x = 500)
    const formattedCurrentNode = mapNode(currentNode, 500, centerY);

    // 3. Build Successor Nodes (Right column, x = 940)
    const formattedSuccNodes = succNodes.map((n, i) => {
      const offset = centerY - ((S - 1) * 220) / 2;
      return mapNode(n, 940, offset + i * 220);
    });

    setNodes([...formattedPredNodes, formattedCurrentNode, ...formattedSuccNodes]);

    const focusPositions = Object.fromEntries(
      [...formattedPredNodes, formattedCurrentNode, ...formattedSuccNodes]
        .map((node) => [Number(node.id), node.position])
    );

    // Build Edges
    const DEFAULT_CONDITION = 1;
    const formattedEdges = [
      ...predEdges.map((edge) => {
        const cond = Number(edge.condition) || DEFAULT_CONDITION;
        
        const visual = {
          1: { color: theme === 'light' ? '#1e293b' : '#94a3b8', edgeStroke: THEN_EDGE_GRADIENT, markerColor: THEN_EDGE_MARKER_COLOR, dash: undefined },
          2: { color: '#22c55e', edgeStroke: '#22c55e', markerColor: '#22c55e', dash: '8 6' },
          3: { color: '#059669', edgeStroke: '#059669', markerColor: '#059669', dash: '3 6' }
        }[cond] || { color: '#1e293b', edgeStroke: '#1e293b', markerColor: '#1e293b', dash: undefined };

        const targetHandle = 'target-in-left';
        const route = computeEdgeHandles(edge, focusPositions, contract.nodes, contract.edges);
        const hasReverseEdge = contract.edges.some((candidate) =>
          candidate.from === edge.to && candidate.to === edge.from
        );
        const isOrthogonalLoop = route.loop && hasReverseEdge;

        if (isOrthogonalLoop && !showLoops) return null;

        return {
          id: `focus-edge-pred-${edge.id}`,
          source: String(edge.from),
          target: String(edge.to),
          type: isOrthogonalLoop ? 'focus-loop' : 'default',
          sourceHandle: isOrthogonalLoop ? route.sourceHandle : `source-${cond}-right`,
          targetHandle: isOrthogonalLoop ? route.targetHandle : targetHandle,
          label: `${
            { 1: 'então', 2: 'ou', 3: 'se' }[cond]
          }${edge.label ? ` - ${edge.label}` : ''}`,
          data: { ...edge, labelColor: visual.color, markerColor: visual.markerColor },
          animated: true,
          style: {
            stroke: visual.edgeStroke,
            strokeWidth: 3, // thicker in focus view
            strokeDasharray: visual.dash
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: visual.markerColor,
            width: 24,
            height: 24
          },
          labelStyle: {
            fill: theme === 'light' ? visual.color : '#e2e8f0',
            fontWeight: 800,
            fontSize: 10
          },
          labelBgStyle: {
            fill: theme === 'light' ? '#ffffff' : '#0f172a',
            fillOpacity: 0.95,
            stroke: visual.color,
            strokeWidth: 1
          },
          labelBgPadding: [6, 4] as [number, number],
          labelBgBorderRadius: 6
        };
      }),
      ...succEdges.map((edge) => {
        const cond = Number(edge.condition) || DEFAULT_CONDITION;
        
        const visual = {
          1: { color: theme === 'light' ? '#1e293b' : '#94a3b8', edgeStroke: THEN_EDGE_GRADIENT, markerColor: THEN_EDGE_MARKER_COLOR, dash: undefined },
          2: { color: '#22c55e', edgeStroke: '#22c55e', markerColor: '#22c55e', dash: '8 6' },
          3: { color: '#059669', edgeStroke: '#059669', markerColor: '#059669', dash: '3 6' }
        }[cond] || { color: '#1e293b', edgeStroke: '#1e293b', markerColor: '#1e293b', dash: undefined };

        const targetHandle = 'target-in-left';
        const route = computeEdgeHandles(edge, focusPositions, contract.nodes, contract.edges);
        const hasReverseEdge = contract.edges.some((candidate) =>
          candidate.from === edge.to && candidate.to === edge.from
        );
        const isOrthogonalLoop = route.loop && hasReverseEdge;

        if (isOrthogonalLoop && !showLoops) return null;

        return {
          id: `focus-edge-succ-${edge.id}`,
          source: String(edge.from),
          target: String(edge.to),
          type: isOrthogonalLoop ? 'focus-loop' : 'default',
          sourceHandle: isOrthogonalLoop ? route.sourceHandle : `source-${cond}-right`,
          targetHandle: isOrthogonalLoop ? route.targetHandle : targetHandle,
          label: `${
            { 1: 'então', 2: 'ou', 3: 'se' }[cond]
          }${edge.label ? ` - ${edge.label}` : ''}`,
          data: { ...edge, labelColor: visual.color, markerColor: visual.markerColor },
          animated: true,
          style: {
            stroke: visual.edgeStroke,
            strokeWidth: 3,
            strokeDasharray: visual.dash
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: visual.markerColor,
            width: 24,
            height: 24
          },
          labelStyle: {
            fill: theme === 'light' ? visual.color : '#e2e8f0',
            fontWeight: 800,
            fontSize: 10
          },
          labelBgStyle: {
            fill: theme === 'light' ? '#ffffff' : '#0f172a',
            fillOpacity: 0.95,
            stroke: visual.color,
            strokeWidth: 1
          },
          labelBgPadding: [6, 4] as [number, number],
          labelBgBorderRadius: 6
        };
      })
    ];

    setEdges(formattedEdges.filter((edge) => edge !== null) as Edge[]);
  }, [contract, nodeId, theme, showLoops]);

  const currentNode = contract.nodes.find((n) => n.id === nodeId);
  if (!currentNode) return null;

  const onNodeClick = (event: React.MouseEvent, node: Node) => {
    if (!event.altKey) return;
    event.preventDefault();
    if (window.openDetailViewer) {
      window.openDetailViewer(Number(node.id));
    }
  };

  return (
    <>
      <svg className="edge-gradient-definitions" aria-hidden="true">
        <defs>
          <linearGradient id="stdd-then-edge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="100%" stopColor="#fb923c" />
          </linearGradient>
        </defs>
      </svg>
    <div className="dialog-overlay" style={{ background: 'rgba(15, 23, 42, 0.75)', backdropFilter: 'blur(8px)' }}>
      <dialog className="app-dialog" open style={{ width: 'min(1300px, calc(100vw - 32px))', height: '85vh', maxHeight: '85vh' }}>
        <div className="dialog-content" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          
          {/* Header */}
          <div className="dialog-header" style={{ marginBottom: '16px' }}>
            <div>
              <p className="eyebrow">STDD · Visão de Vizinhança (Zoom)</p>
              <h2>Foco no Bloco: {currentNode.label}</h2>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                className="quick-action-btn secondary"
                onClick={() => setShowLoops((visible) => !visible)}
                type="button"
                title={showLoops ? 'Ocultar loops' : 'Mostrar loops'}
              >
                {showLoops ? <Eye size={14} /> : <EyeOff size={14} />}
                <span>Loops {showLoops ? 'visíveis' : 'ocultos'}</span>
              </button>
              <button className="close-btn" onClick={onClose} type="button">
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Interactive Mini-Canvas */}
          <div style={{
            flex: 1,
            border: '1.5px solid var(--line)',
            borderRadius: '16px',
            overflow: 'hidden',
            background: focusCanvasBackground,
            position: 'relative'
          }}>
            <ReactFlowProvider>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                onNodeClick={onNodeClick}
                fitView
                fitViewOptions={{ maxZoom: 1.2, padding: 0.15 }}
                minZoom={0.2}
                maxZoom={3}
                nodesConnectable={false}
                nodesDraggable={true}
              >
                <Controls showInteractive={false} />
                <Background gap={16} size={1} />
              </ReactFlow>
            </ReactFlowProvider>
          </div>

          {/* Actions */}
          <div className="dialog-actions" style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--line)' }}>
            <button className="primary" onClick={onClose} style={{ padding: '10px 24px' }}>
              Fechar Foco
            </button>
          </div>

        </div>
      </dialog>
    </div>
    </>
  );
};
