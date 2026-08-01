import React, { useEffect } from 'react';
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

import { X } from 'lucide-react';
import type { Contract, NodeData } from '../types';
import { CustomNode } from './CustomNode';

interface FocusDetailModalProps {
  nodeId: number;
  contract: Contract;
  theme: 'light' | 'dark';
  onClose: () => void;
}

const nodeTypes = {
  custom: CustomNode
};

export const FocusDetailModal: React.FC<FocusDetailModalProps> = ({
  nodeId,
  contract,
  theme,
  onClose
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<NodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    const currentNode = contract.nodes.find((n) => n.id === nodeId);
    if (!currentNode) return;

    // Find predecessors and successors
    const predEdges = contract.edges.filter((e) => e.to === nodeId);
    const succEdges = contract.edges.filter((e) => e.from === nodeId);

    const predNodes = contract.nodes.filter((n) => predEdges.some((e) => e.from === n.id));
    const succNodes = contract.nodes.filter((n) => succEdges.some((e) => e.to === n.id));

    const P = predNodes.length;
    const S = succNodes.length;
    const maxRows = Math.max(P, S, 1);
    
    // Center Y coordinate
    const centerY = ((maxRows - 1) * 220) / 2;

    const presentationKey = `stdd-draw-presentation:${contract.id}`;
    let presentationColors = {} as any;
    try {
      const saved = localStorage.getItem(presentationKey);
      if (saved) {
        presentationColors = JSON.parse(saved).nodes || {};
      }
    } catch (_) {}

    const mapNode = (n: NodeData, x: number, y: number) => {
      const savedStyles = presentationColors[String(n.id)] || {};
      return {
        id: String(n.id),
        type: 'custom',
        position: { x, y },
        data: {
          ...n,
          background: savedStyles.background,
          text: savedStyles.text
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

    // Build Edges
    const DEFAULT_CONDITION = 1;
    const formattedEdges = [
      ...predEdges.map((edge) => {
        const cond = Number(edge.condition) || DEFAULT_CONDITION;
        
        const visual = {
          1: { color: theme === 'light' ? '#1e293b' : '#94a3b8', dash: undefined },
          2: { color: '#d97706', dash: '8 6' },
          3: { color: '#059669', dash: '3 6' }
        }[cond] || { color: '#1e293b', dash: undefined };

        const predIdx = predNodes.findIndex((n) => n.id === edge.from);
        const predY = centerY - ((P - 1) * 220) / 2 + predIdx * 220;
        const targetHandle = predY <= centerY ? 'target-in-top' : 'target-in-bottom';

        return {
          id: `focus-edge-pred-${edge.id}`,
          source: String(edge.from),
          target: String(edge.to),
          type: 'default', // curved bezier edge
          sourceHandle: `source-${cond}-right`,
          targetHandle: targetHandle,
          label: `${
            { 1: 'então', 2: 'ou', 3: 'se' }[cond]
          }${edge.label ? ` - ${edge.label}` : ''}`,
          data: edge,
          animated: true,
          style: {
            stroke: visual.color,
            strokeWidth: 3, // thicker in focus view
            strokeDasharray: visual.dash
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: visual.color,
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
          1: { color: theme === 'light' ? '#1e293b' : '#94a3b8', dash: undefined },
          2: { color: '#d97706', dash: '8 6' },
          3: { color: '#059669', dash: '3 6' }
        }[cond] || { color: '#1e293b', dash: undefined };

        const succIdx = succNodes.findIndex((n) => n.id === edge.to);
        const succY = centerY - ((S - 1) * 220) / 2 + succIdx * 220;
        const targetHandle = succY >= centerY ? 'target-in-top' : 'target-in-bottom';

        return {
          id: `focus-edge-succ-${edge.id}`,
          source: String(edge.from),
          target: String(edge.to),
          type: 'default', // curved bezier edge
          sourceHandle: `source-${cond}-right`,
          targetHandle: targetHandle,
          label: `${
            { 1: 'então', 2: 'ou', 3: 'se' }[cond]
          }${edge.label ? ` - ${edge.label}` : ''}`,
          data: edge,
          animated: true,
          style: {
            stroke: visual.color,
            strokeWidth: 3,
            strokeDasharray: visual.dash
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: visual.color,
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

    setEdges(formattedEdges);
  }, [contract, nodeId, theme]);

  const currentNode = contract.nodes.find((n) => n.id === nodeId);
  if (!currentNode) return null;

  return (
    <div className="dialog-overlay" style={{ background: 'rgba(15, 23, 42, 0.75)', backdropFilter: 'blur(8px)' }}>
      <dialog className="app-dialog" open style={{ width: 'min(1300px, calc(100vw - 32px))', height: '85vh', maxHeight: '85vh' }}>
        <div className="dialog-content" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          
          {/* Header */}
          <div className="dialog-header" style={{ marginBottom: '16px' }}>
            <div>
              <p className="eyebrow">STDD · Visão de Vizinhança (Zoom)</p>
              <h2>Foco no Bloco: {currentNode.label}</h2>
            </div>
            <button className="close-btn" onClick={onClose} type="button">
              <X size={20} />
            </button>
          </div>

          {/* Interactive Mini-Canvas */}
          <div style={{
            flex: 1,
            border: '1.5px solid var(--line)',
            borderRadius: '16px',
            overflow: 'hidden',
            background: 'var(--paper-light, #f8fafc)',
            position: 'relative'
          }}>
            <ReactFlowProvider>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
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
  );
};
