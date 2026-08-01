import React from 'react';
import { BaseEdge, EdgeLabelRenderer, useNodes } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import type { EdgeData } from '../types';

const NODE_WIDTH = 290;
const NODE_HEIGHT = 160;
const PAD = 24; // Padding around nodes for clearing corridors

const lineIntersectsBox = (x1: number, y1: number, x2: number, y2: number, box: any) => {
  const minSegmentX = Math.min(x1, x2);
  const maxSegmentX = Math.max(x1, x2);
  const minSegmentY = Math.min(y1, y2);
  const maxSegmentY = Math.max(y1, y2);

  const l = box.left;
  const r = box.right;
  const t = box.top;
  const b = box.bottom;

  // Vertical line segment
  if (x1 === x2) {
    return x1 >= l && x1 <= r && minSegmentY <= b && maxSegmentY >= t;
  }
  // Horizontal line segment
  if (y1 === y2) {
    return y1 >= t && y1 <= b && minSegmentX <= r && maxSegmentX >= l;
  }
  return false;
};

// BFS-based shortest path finder on a grid made from columns/rows of nodes boundaries
function findGridPath(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
  boxes: any[]
): { x: number; y: number }[] | null {
  const xCoords = Array.from(new Set([
    startX,
    endX,
    ...boxes.flatMap(b => [b.left, b.right])
  ])).sort((a, b) => a - b);

  const yCoords = Array.from(new Set([
    startY,
    endY,
    ...boxes.flatMap(b => [b.top, b.bottom])
  ])).sort((a, b) => a - b);

  // Restrict search space to bounding box + 150px margin
  const minX = Math.min(startX, endX) - 150;
  const maxX = Math.max(startX, endX) + 150;
  const minY = Math.min(startY, endY) - 150;
  const maxY = Math.max(startY, endY) + 150;

  const gridX = xCoords.filter(x => x >= minX && x <= maxX);
  const gridY = yCoords.filter(y => y >= minY && y <= maxY);

  const startIdxX = gridX.indexOf(startX);
  const startIdxY = gridY.indexOf(startY);
  const endIdxX = gridX.indexOf(endX);
  const endIdxY = gridY.indexOf(endY);

  if (startIdxX === -1 || startIdxY === -1 || endIdxX === -1 || endIdxY === -1) {
    return null;
  }

  interface PointKey {
    xIdx: number;
    yIdx: number;
  }

  const queue: PointKey[] = [{ xIdx: startIdxX, yIdx: startIdxY }];
  const visited = new Set<string>();
  visited.add(`${startIdxX},${startIdxY}`);
  
  const parent = new Map<string, string>();
  let found = false;

  while (queue.length > 0) {
    const curr = queue.shift()!;
    if (curr.xIdx === endIdxX && curr.yIdx === endIdxY) {
      found = true;
      break;
    }

    const neighbors: PointKey[] = [];
    if (curr.xIdx > 0) neighbors.push({ xIdx: curr.xIdx - 1, yIdx: curr.yIdx });
    if (curr.xIdx < gridX.length - 1) neighbors.push({ xIdx: curr.xIdx + 1, yIdx: curr.yIdx });
    if (curr.yIdx > 0) neighbors.push({ xIdx: curr.xIdx, yIdx: curr.yIdx - 1 });
    if (curr.yIdx < gridY.length - 1) neighbors.push({ xIdx: curr.xIdx, yIdx: curr.yIdx + 1 });

    for (const next of neighbors) {
      const key = `${next.xIdx},${next.yIdx}`;
      if (visited.has(key)) continue;

      const cx = gridX[curr.xIdx];
      const cy = gridY[curr.yIdx];
      const nx = gridX[next.xIdx];
      const ny = gridY[next.yIdx];

      let intersects = false;
      for (const box of boxes) {
        if (lineIntersectsBox(cx, cy, nx, ny, box)) {
          intersects = true;
          break;
        }
      }

      if (!intersects) {
        visited.add(key);
        parent.set(key, `${curr.xIdx},${curr.yIdx}`);
        queue.push(next);
      }
    }
  }

  if (!found) return null;

  const path: { x: number; y: number }[] = [];
  let currKey = `${endIdxX},${endIdxY}`;
  while (currKey) {
    const [xIdxStr, yIdxStr] = currKey.split(',');
    const x = gridX[parseInt(xIdxStr)];
    const y = gridY[parseInt(yIdxStr)];
    path.push({ x, y });
    currKey = parent.get(currKey) || '';
  }

  path.reverse();
  
  // Collinear simplification
  const simplified: { x: number; y: number }[] = [];
  if (path.length > 0) simplified.push(path[0]);
  for (let i = 1; i < path.length - 1; i++) {
    const prev = path[i - 1];
    const curr = path[i];
    const next = path[i + 1];

    const collinear = (prev.x === curr.x && curr.x === next.x) || (prev.y === curr.y && curr.y === next.y);
    if (!collinear) {
      simplified.push(curr);
    }
  }
  if (path.length > 1) simplified.push(path[path.length - 1]);

  return simplified;
}

function pointsToSvgPath(points: { x: number; y: number }[], borderRadius = 12): string {
  if (points.length === 0) return '';
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

  let path = `M ${points[0].x} ${points[0].y}`;
  
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    
    if (i === points.length - 1) {
      path += ` L ${curr.x} ${curr.y}`;
      break;
    }
    
    const next = points[i + 1];
    
    const dx1 = curr.x - prev.x;
    const dy1 = curr.y - prev.y;
    const len1 = Math.sqrt(dx1 * dx1 + dy1 * dy1);
    
    const dx2 = next.x - curr.x;
    const dy2 = next.y - curr.y;
    const len2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);
    
    const r = Math.min(borderRadius, len1 / 2, len2 / 2);
    
    const startBendX = curr.x - (dx1 / (len1 || 1)) * r;
    const startBendY = curr.y - (dy1 / (len1 || 1)) * r;
    const endBendX = curr.x + (dx2 / (len2 || 1)) * r;
    const endBendY = curr.y + (dy2 / (len2 || 1)) * r;
    
    path += ` L ${startBendX} ${startBendY}`;
    path += ` Q ${curr.x} ${curr.y} ${endBendX} ${endBendY}`;
  }
  
  return path;
}

export const AvoidEdge: React.FC<EdgeProps> = ({
  id,
  source,
  target,
  label,
  style,
  markerEnd,
  data
}) => {
  const nodes = useNodes();
  
  const sourceNode = nodes.find(n => n.id === source);
  const targetNode = nodes.find(n => n.id === target);

  if (!sourceNode || !targetNode) {
    return null;
  }

  const cond = Number((data as EdgeData)?.condition) || 1;

  const srcX = sourceNode.position.x;
  const srcY = sourceNode.position.y;
  const srcW = sourceNode.measured?.width || NODE_WIDTH;
  const srcH = sourceNode.measured?.height || NODE_HEIGHT;

  const tgtX = targetNode.position.x;
  const tgtY = targetNode.position.y;
  const tgtW = targetNode.measured?.width || NODE_WIDTH;
  const tgtH = targetNode.measured?.height || NODE_HEIGHT;

  // Build obstacle boxes (other nodes)
  const boxes = nodes
    .filter(n => n.id !== source && n.id !== target)
    .map(n => {
      const x = n.position.x;
      const y = n.position.y;
      const w = n.measured?.width || NODE_WIDTH;
      const h = n.measured?.height || NODE_HEIGHT;
      return {
        left: x - PAD,
        right: x + w + PAD,
        top: y - PAD,
        bottom: y + h + PAD
      };
    });

  // Helper to resolve specific port coordinates based on condition offset
  const getSourcePort = (dir: string) => {
    const condOffset = 0.2 * cond + 0.2; // cond 1 -> 40%, 2 -> 60%, 3 -> 80%
    if (dir === 'left') return { x: srcX, y: srcY + srcH * condOffset, dirX: -1, dirY: 0 };
    if (dir === 'right') return { x: srcX + srcW, y: srcY + srcH * condOffset, dirX: 1, dirY: 0 };
    if (dir === 'top') return { x: srcX + srcW * condOffset, y: srcY, dirX: 0, dirY: -1 };
    return { x: srcX + srcW * condOffset, y: srcY + srcH, dirX: 0, dirY: 1 }; // bottom
  };

  const getTargetPort = (dir: string) => {
    const offset = 0.2; // target-in ports are styled at 20%
    if (dir === 'left') return { x: tgtX, y: tgtY + tgtH * offset, dirX: -1, dirY: 0 };
    if (dir === 'right') return { x: tgtX + tgtW, y: tgtY + tgtH * offset, dirX: 1, dirY: 0 };
    if (dir === 'top') return { x: tgtX + tgtW * offset, y: tgtY, dirX: 0, dirY: -1 };
    return { x: tgtX + tgtW * offset, y: tgtY + tgtH, dirX: 0, dirY: 1 }; // bottom
  };

  // Evaluate candidate directions to pick the one with 0 (or least) intersections & shortest path length
  const dirs = ['left', 'right', 'top', 'bottom'];
  let bestPath: { x: number; y: number }[] = [];
  let minIntersections = Infinity;
  let minPathLen = Infinity;

  for (const srcDir of dirs) {
    for (const tgtDir of dirs) {
      const pSrc = getSourcePort(srcDir);
      const pTgt = getTargetPort(tgtDir);

      const startX = pSrc.x + pSrc.dirX * 24;
      const startY = pSrc.y + pSrc.dirY * 24;
      const endX = pTgt.x + pTgt.dirX * 24;
      const endY = pTgt.y + pTgt.dirY * 24;

      // Construct standard orthogonal 3-segment path
      let stdPoints: { x: number; y: number }[] = [];
      if (pSrc.dirX !== 0) {
        const midX = (startX + endX) / 2;
        stdPoints = [
          { x: pSrc.x, y: pSrc.y },
          { x: startX, y: startY },
          { x: midX, y: startY },
          { x: midX, y: endY },
          { x: endX, y: endY },
          { x: pTgt.x, y: pTgt.y }
        ];
      } else {
        const midY = (startY + endY) / 2;
        stdPoints = [
          { x: pSrc.x, y: pSrc.y },
          { x: startX, y: startY },
          { x: startX, y: midY },
          { x: endX, y: midY },
          { x: endX, y: endY },
          { x: pTgt.x, y: pTgt.y }
        ];
      }

      // Count intersections of standard path
      let intersects = 0;
      for (let i = 0; i < stdPoints.length - 1; i++) {
        for (const box of boxes) {
          if (lineIntersectsBox(stdPoints[i].x, stdPoints[i].y, stdPoints[i + 1].x, stdPoints[i + 1].y, box)) {
            intersects++;
          }
        }
      }

      let candidatePath: { x: number; y: number }[] = stdPoints;
      
      // If standard path intersects, try grid routing
      if (intersects > 0) {
        const gridRoute = findGridPath(startX, startY, endX, endY, boxes);
        if (gridRoute) {
          intersects = 0; // successfully bypassed obstacles!
          candidatePath = [
            { x: pSrc.x, y: pSrc.y },
            ...gridRoute,
            { x: pTgt.x, y: pTgt.y }
          ];
        }
      }

      // Calculate path length
      let pathLen = 0;
      for (let i = 0; i < candidatePath.length - 1; i++) {
        const dx = candidatePath[i+1].x - candidatePath[i].x;
        const dy = candidatePath[i+1].y - candidatePath[i].y;
        pathLen += Math.sqrt(dx*dx + dy*dy);
      }

      // Selection priority: least intersections, then shortest length
      if (intersects < minIntersections) {
        minIntersections = intersects;
        minPathLen = pathLen;
        bestPath = candidatePath;
      } else if (intersects === minIntersections && pathLen < minPathLen) {
        minPathLen = pathLen;
        bestPath = candidatePath;
      }
    }
  }

  // Draw smooth steps SVG
  const path = pointsToSvgPath(bestPath);

  // Compute label position midway through the path
  let midPoint = { x: (srcX + tgtX)/2, y: (srcY + tgtY)/2 };
  if (bestPath.length >= 3) {
    const idx = Math.floor(bestPath.length / 2);
    midPoint = bestPath[idx];
  }
  const labelX = midPoint.x;
  const labelY = midPoint.y - 10;
  const labelColor = style?.stroke || '#1e293b';

  return (
    <>
      <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />
      {label && (
        <EdgeLabelRenderer>
          <div
            className="loop-edge-label"
            style={{
              color: labelColor,
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              position: 'absolute',
              pointerEvents: 'all',
              ...((style as any)?.opacity !== undefined ? { opacity: (style as any).opacity } : {})
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};
