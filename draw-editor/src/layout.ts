import type { Node as RFNode } from '@xyflow/react';
import type { NodeData, EdgeData } from './types';

const EDGE_CONDITIONS: { [key: number]: string } = { 1: 'então', 2: 'ou', 3: 'se' };

const NODE_WIDTH = 290;
const NODE_HEIGHT = 160;
const H_GAP = 240;    // Horizontal gap for breathing room
const V_GAP = 150;    // Vertical gap for step placement
const MAX_PER_COL = 4; // Max nodes stacked before shifting to sub-column

// Step 1: Build forward DAG, detect back-edges via DFS
function buildRanks(nodes: NodeData[], edges: EdgeData[]) {
  const ids = nodes.map(n => n.id);
  const idSet = new Set(ids);
  const outgoing: { [key: number]: number[] } = Object.fromEntries(ids.map(id => [id, []]));
  edges.forEach(e => {
    if (e.from in outgoing && idSet.has(e.to)) {
      outgoing[e.from].push(e.to);
    }
  });

  const visiting = new Set<number>();
  const visited = new Set<number>();
  const order: number[] = [];
  const backEdges = new Set<string>();

  function visit(id: number) {
    if (visited.has(id)) return;
    if (visiting.has(id)) return;
    visiting.add(id);
    for (const target of (outgoing[id] || [])) {
      if (visiting.has(target)) {
        backEdges.add(`${id}->${target}`);
      } else {
        visit(target);
      }
    }
    visiting.delete(id);
    visited.add(id);
    order.push(id);
  }

  ids.forEach(visit);
  order.reverse();

  // Longest-path ranking on forward DAG
  const forwardOut: { [key: number]: number[] } = Object.fromEntries(ids.map(id => [id, []]));
  edges.forEach(e => {
    if (!backEdges.has(`${e.from}->${e.to}`) && e.from in forwardOut && idSet.has(e.to)) {
      forwardOut[e.from].push(e.to);
    }
  });

  const ranks: { [key: number]: number } = Object.fromEntries(ids.map(id => [id, 0]));
  order.forEach(id => {
    for (const target of (forwardOut[id] || [])) {
      ranks[target] = Math.max(ranks[target], ranks[id] + 1);
    }
  });

  return { ranks, backEdges, topoOrder: order };
}

// Step 2: Barycentric ordering with multiple sweeps to minimize crossings
function barycentricOrder(nodes: NodeData[], edges: EdgeData[], ranks: { [key: number]: number }, backEdges: Set<string>) {
  const idSet = new Set(nodes.map(n => n.id));

  // Build forward adjacency
  const fwdAdj: { [key: number]: number[] } = {};   // parent -> [children]
  const revAdj: { [key: number]: number[] } = {};   // child -> [parents]
  nodes.forEach(n => { fwdAdj[n.id] = []; revAdj[n.id] = []; });
  edges.forEach(e => {
    if (!backEdges.has(`${e.from}->${e.to}`) && idSet.has(e.from) && idSet.has(e.to)) {
      fwdAdj[e.from].push(e.to);
      revAdj[e.to].push(e.from);
    }
  });

  // Group nodes into layers
  const layers = new Map<number, NodeData[]>();
  nodes.forEach(n => {
    const r = ranks[n.id] || 0;
    if (!layers.has(r)) layers.set(r, []);
    layers.get(r)!.push(n);
  });
  const sortedRanks = [...layers.keys()].sort((a, b) => a - b);

  // Initial order: by original id for stability
  sortedRanks.forEach(r => {
    layers.get(r)!.sort((a, b) => a.id - b.id);
  });

  // Assign initial positions (index within layer)
  const pos: { [key: number]: number } = {};
  sortedRanks.forEach(r => {
    layers.get(r)!.forEach((n, i) => { pos[n.id] = i; });
  });

  // Barycentric sweeps (8 iterations, alternating direction)
  for (let iter = 0; iter < 8; iter++) {
    const isDownward = iter % 2 === 0;
    const rankOrder = isDownward ? sortedRanks : [...sortedRanks].reverse();

    for (const r of rankOrder) {
      const layer = layers.get(r)!;
      layer.forEach(n => {
        const neighbors = isDownward ? revAdj[n.id] : fwdAdj[n.id];
        if (neighbors.length > 0) {
          const avg = neighbors.reduce((s, id) => s + (pos[id] ?? 0), 0) / neighbors.length;
          pos[n.id] = avg;
        }
      });
      // Re-sort layer by barycenter and assign integer positions
      layer.sort((a, b) => (pos[a.id] ?? 0) - (pos[b.id] ?? 0));
      layer.forEach((n, i) => { pos[n.id] = i; });
    }
  }

  return { layers, sortedRanks, pos };
}

// Step 3: Generous 2D positioning with vertical step placement & anti-overlap clearance
export function layoutGraph(
  nodes: NodeData[],
  edges: EdgeData[],
  presentationPositions?: { [id: string]: { x: number; y: number } }
): RFNode<NodeData>[] {
  if (!nodes.length) return [];

  const { ranks, backEdges } = buildRanks(nodes, edges);
  const { layers, sortedRanks } = barycentricOrder(nodes, edges, ranks, backEdges);
  const calculatedPositions: { [id: string]: { x: number; y: number } } = {};

  // Calculate dynamic column widths based on edge label lengths
  const colGaps: { [key: number]: number } = {};
  edges.forEach(edge => {
    const sr = ranks[edge.from];
    const tr = ranks[edge.to];
    if (sr === undefined || tr === undefined || tr <= sr) return;
    const labelText = `${EDGE_CONDITIONS[edge.condition || 1] || ''} ${edge.label || ''}`.trim();
    const labelPx = Math.min(260, Math.max(40, labelText.length * 8 + 24));
    const needed = NODE_WIDTH + H_GAP + labelPx;
    colGaps[sr] = Math.max(colGaps[sr] || (NODE_WIDTH + H_GAP), needed);
  });

  // Build outgoing/incoming count for fan-out/fan-in detection
  const outCount: { [key: number]: number } = {};
  const inCount: { [key: number]: number } = {};
  nodes.forEach(n => { outCount[n.id] = 0; inCount[n.id] = 0; });
  edges.forEach(e => {
    if (!backEdges.has(`${e.from}->${e.to}`)) {
      outCount[e.from] = (outCount[e.from] || 0) + 1;
      inCount[e.to] = (inCount[e.to] || 0) + 1;
    }
  });

  // Position columns left to right with wide spacing
  let colX = 80;
  const columnXMap: { [key: number]: number } = {}; // rank -> x

  sortedRanks.forEach(r => {
    columnXMap[r] = colX;
    colX += colGaps[r] || (NODE_WIDTH + H_GAP);
  });

  // Initial placement within each column
  sortedRanks.forEach(r => {
    const layer = layers.get(r)!;
    const baseX = columnXMap[r];
    const count = layer.length;

    if (count <= MAX_PER_COL) {
      const startY = 100;
      layer.forEach((n, i) => {
        calculatedPositions[String(n.id)] = {
          x: baseX,
          y: startY + i * (NODE_HEIGHT + V_GAP)
        };
      });
    } else {
      const subColSize = MAX_PER_COL;
      const subColOffset = NODE_WIDTH * 0.5;
      layer.forEach((n, i) => {
        const subCol = Math.floor(i / subColSize);
        const posInSub = i % subColSize;
        calculatedPositions[String(n.id)] = {
          x: baseX + subCol * subColOffset,
          y: 100 + posInSub * (NODE_HEIGHT + V_GAP) + subCol * (V_GAP * 0.7)
        };
      });
    }
  });

  // Pass A: Vertical Step Alignment
  // If a node V is a 1-to-1 child of U (or a vertical branch step below U), place V in U's column if free
  nodes.forEach(v => {
    const parentEdge = edges.find(e => e.to === v.id && !backEdges.has(`${e.from}->${e.to}`));
    if (parentEdge && inCount[v.id] === 1) {
      const u = parentEdge.from;
      const uPos = calculatedPositions[String(u)];
      const vPos = calculatedPositions[String(v.id)];
      if (uPos && vPos && ranks[v.id] === ranks[u] + 1) {
        // Check if vertical position below U is available
        const targetY = uPos.y + NODE_HEIGHT + V_GAP;
        const occupied = nodes.some(other => {
          if (other.id === v.id) return false;
          const oPos = calculatedPositions[String(other.id)];
          return oPos && Math.abs(oPos.x - uPos.x) < NODE_WIDTH * 0.5 && Math.abs(oPos.y - targetY) < NODE_HEIGHT * 0.6;
        });
        if (!occupied && outCount[u] >= 2) {
          // If parent branches (fan-out), stack branches vertically under same/near column
          vPos.x = uPos.x;
          vPos.y = targetY;
        }
      }
    }
  });

  // Pass B: Obstacle & Corridor Clearance Pass
  edges.forEach(edge => {
    if (backEdges.has(`${edge.from}->${edge.to}`)) return;
    const srcPos = calculatedPositions[String(edge.from)];
    const tgtPos = calculatedPositions[String(edge.to)];
    if (!srcPos || !tgtPos) return;

    const minX = Math.min(srcPos.x, tgtPos.x);
    const maxX = Math.max(srcPos.x, tgtPos.x);

    if (maxX - minX > NODE_WIDTH + H_GAP * 0.7) {
      const minY = Math.min(srcPos.y, tgtPos.y);
      const maxY = Math.max(srcPos.y, tgtPos.y);

      nodes.forEach(w => {
        if (w.id === edge.from || w.id === edge.to) return;
        const wPos = calculatedPositions[String(w.id)];
        if (!wPos) return;

        if (wPos.x > minX + 20 && wPos.x < maxX - 20) {
          if (wPos.y >= minY - 40 && wPos.y <= maxY + NODE_HEIGHT + 40) {
            wPos.y += NODE_HEIGHT * 0.6 + V_GAP * 0.5;
          }
        }
      });
    }
  });

  // Pass C: Center convergence nodes
  nodes.forEach(n => {
    if ((inCount[n.id] || 0) >= 2) {
      const parents = edges
        .filter(e => e.to === n.id && !backEdges.has(`${e.from}->${e.to}`) && calculatedPositions[String(e.from)])
        .map(e => calculatedPositions[String(e.from)].y);

      if (parents.length >= 2) {
        const avgY = parents.reduce((s, y) => s + y, 0) / parents.length;
        const curPos = calculatedPositions[String(n.id)];
        if (curPos) {
          const sameCol = nodes.filter(other =>
            other.id !== n.id &&
            calculatedPositions[String(other.id)] &&
            Math.abs(calculatedPositions[String(other.id)].x - curPos.x) < NODE_WIDTH * 0.5
          );
          const wouldOverlap = sameCol.some(other => {
            const otherY = calculatedPositions[String(other.id)].y;
            return Math.abs(avgY - otherY) < NODE_HEIGHT + V_GAP * 0.5;
          });
          if (!wouldOverlap) {
            curPos.y = avgY;
          }
        }
      }
    }
  });

  // Pass D: Strict Anti-Overlap Guarantee
  const nodeKeys = Object.keys(calculatedPositions).sort((a, b) => calculatedPositions[a].y - calculatedPositions[b].y);
  for (let i = 0; i < nodeKeys.length; i++) {
    for (let j = i + 1; j < nodeKeys.length; j++) {
      const posA = calculatedPositions[nodeKeys[i]];
      const posB = calculatedPositions[nodeKeys[j]];
      if (!posA || !posB) continue;

      const dx = Math.abs(posA.x - posB.x);
      const dy = Math.abs(posA.y - posB.y);

      if (dx < NODE_WIDTH + 30 && dy < NODE_HEIGHT + 30) {
        posB.y = posA.y + NODE_HEIGHT + V_GAP;
      }
    }
  }

  return nodes.map(n => {
    const customPos = presentationPositions?.[String(n.id)] || calculatedPositions[String(n.id)] || { x: 100, y: 100 };
    return {
      id: String(n.id),
      type: 'custom',
      position: customPos,
      data: n
    };
  });
}

// Compute edge handle connections dynamically
export function computeEdgeHandles(
  edge: EdgeData,
  positions: { [id: string]: { x: number; y: number } },
  nodes: NodeData[],
  edges: EdgeData[]
) {
  const { backEdges } = buildRanks(nodes, edges);
  const isBackEdge = backEdges.has(`${edge.from}->${edge.to}`);
  const cond = Number(edge.condition) || 1;

  const sourcePos = positions[String(edge.from)];
  const targetPos = positions[String(edge.to)];
  if (!sourcePos || !targetPos) {
    return {
      loop: isBackEdge,
      sourceHandle: `source-${cond}-right`,
      targetHandle: `target-in-top`
    };
  }

  // Center-to-center relative vector
  const srcCenterX = sourcePos.x + NODE_WIDTH / 2;
  const srcCenterY = sourcePos.y + NODE_HEIGHT / 2;
  const tgtCenterX = targetPos.x + NODE_WIDTH / 2;
  const tgtCenterY = targetPos.y + NODE_HEIGHT / 2;

  const dx = tgtCenterX - srcCenterX;
  const dy = tgtCenterY - srcCenterY;

  let dir = 'right';
  if (isBackEdge) {
    if (dx < -NODE_WIDTH * 0.3) {
      if (Math.abs(dy) < NODE_HEIGHT * 0.6) {
        return { loop: true, sourceHandle: `source-${cond}-bottom`, targetHandle: `target-in-top` };
      } else if (dy < 0) {
        return { loop: true, sourceHandle: `source-${cond}-top`, targetHandle: `target-in-bottom` };
      } else {
        return { loop: true, sourceHandle: `source-${cond}-bottom`, targetHandle: `target-in-top` };
      }
    }
    return { loop: true, sourceHandle: `source-${cond}-bottom`, targetHandle: `target-in-top` };
  }

  const absDx = Math.abs(dx);
  const absDy = Math.abs(dy);

  if (absDx > absDy * 1.1) {
    dir = dx > 0 ? 'right' : 'left';
  } else if (absDy > absDx * 1.1) {
    dir = dy > 0 ? 'bottom' : 'top';
  } else {
    dir = dx >= 0 ? 'right' : (dy >= 0 ? 'bottom' : 'top');
  }

  // The input (target) of a block must always be on the top or bottom side, never left or right
  const targetDir = dy >= 0 ? 'top' : 'bottom';

  return {
    loop: false,
    sourceHandle: `source-${cond}-${dir}`,
    targetHandle: `target-in-${targetDir}`
  };
}

export function layoutCurvedGraph(
  nodes: NodeData[],
  edges: EdgeData[],
  presentationPositions?: { [id: string]: { x: number; y: number } }
): RFNode<NodeData>[] {
  if (!nodes.length) return [];

  const ids = nodes.map(n => n.id);
  const idSet = new Set(ids);
  
  // DFS to build ranks and ignore back-edges (cycles)
  const outgoing: { [key: number]: number[] } = Object.fromEntries(ids.map(id => [id, []]));
  edges.forEach(e => {
    if (e.from in outgoing && idSet.has(e.to)) {
      outgoing[e.from].push(e.to);
    }
  });

  const visiting = new Set<number>();
  const visited = new Set<number>();
  const order: number[] = [];
  const backEdges = new Set<string>();

  function visit(id: number) {
    if (visited.has(id)) return;
    if (visiting.has(id)) return;
    visiting.add(id);
    for (const target of (outgoing[id] || [])) {
      if (visiting.has(target)) {
        backEdges.add(`${id}->${target}`);
      } else {
        visit(target);
      }
    }
    visiting.delete(id);
    visited.add(id);
    order.push(id);
  }

  ids.forEach(visit);
  order.reverse();

  // Longest-path ranking
  const forwardOut: { [key: number]: number[] } = Object.fromEntries(ids.map(id => [id, []]));
  const revAdj: { [key: number]: number[] } = Object.fromEntries(ids.map(id => [id, []]));
  edges.forEach(e => {
    if (!backEdges.has(`${e.from}->${e.to}`) && e.from in forwardOut && idSet.has(e.to)) {
      forwardOut[e.from].push(e.to);
      revAdj[e.to].push(e.from);
    }
  });

  const ranks: { [key: number]: number } = Object.fromEntries(ids.map(id => [id, 0]));
  order.forEach(id => {
    for (const target of (forwardOut[id] || [])) {
      ranks[target] = Math.max(ranks[target], ranks[id] + 1);
    }
  });

  const levels = new Map<number, NodeData[]>();
  nodes.forEach(n => {
    const r = ranks[n.id] || 0;
    if (!levels.has(r)) levels.set(r, []);
    levels.get(r)!.push(n);
  });
  const sortedRanks = [...levels.keys()].sort((a, b) => a - b);

  const calculatedPositions: { [id: string]: { x: number; y: number } } = {};
  const V_GAP_CURVED = 220;
  const H_GAP_CURVED = 240;
  const COL_WIDTH = NODE_WIDTH + H_GAP_CURVED;

  sortedRanks.forEach(r => {
    const layer = levels.get(r)!;
    const count = layer.length;
    const baseX = 100 + r * COL_WIDTH;
    const startY = 100 + (r % 2 === 0 ? 0 : 40); // small shift to stag vertical alignments

    layer.sort((a, b) => {
      const inEdgesA = edges.filter(e => e.to === a.id && !backEdges.has(`${e.from}->${e.to}`) && e.from in calculatedPositions);
      const inEdgesB = edges.filter(e => e.to === b.id && !backEdges.has(`${e.from}->${e.to}`) && e.from in calculatedPositions);

      const getTargetWeight = (inEdges: typeof edges, nodeId: number) => {
        if (inEdges.length === 0) return nodeId;
        let sum = 0;
        inEdges.forEach(e => {
          const parentY = calculatedPositions[String(e.from)]?.y || 0;
          const cond = Number(e.condition) || 1;
          const offset = cond === 1 ? -120 : (cond === 3 ? 120 : 0);
          sum += (parentY + offset);
        });
        return sum / inEdges.length;
      };

      const weightA = getTargetWeight(inEdgesA, a.id);
      const weightB = getTargetWeight(inEdgesB, b.id);
      return weightA - weightB;
    });

    layer.forEach((n, idx) => {
      const offset = (count - 1) * V_GAP_CURVED / 2;
      calculatedPositions[String(n.id)] = {
        x: baseX,
        y: startY + idx * V_GAP_CURVED - offset
      };
    });
  });

  // Strict Anti-Overlap Guarantee
  const nodeKeys = Object.keys(calculatedPositions).sort((a, b) => calculatedPositions[a].y - calculatedPositions[b].y);
  for (let i = 0; i < nodeKeys.length; i++) {
    for (let j = i + 1; j < nodeKeys.length; j++) {
      const posA = calculatedPositions[nodeKeys[i]];
      const posB = calculatedPositions[nodeKeys[j]];
      if (!posA || !posB) continue;

      const dx = Math.abs(posA.x - posB.x);
      const dy = Math.abs(posA.y - posB.y);

      if (dx < NODE_WIDTH + 30 && dy < NODE_HEIGHT + 30) {
        posB.y = posA.y + NODE_HEIGHT + V_GAP_CURVED;
      }
    }
  }

  return nodes.map(n => {
    const calcPos = calculatedPositions[String(n.id)] || { x: 100, y: 100 };
    const customY = presentationPositions?.[String(n.id)]?.y;
    return {
      id: String(n.id),
      type: 'custom',
      position: {
        x: calcPos.x,
        y: customY !== undefined ? customY : calcPos.y
      },
      data: n
    };
  });
}
